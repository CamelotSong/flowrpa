/**
 * FlowRPA Background Service Worker
 *
 * 功能：
 * 1. WebSocket 连接管理（连接引擎，自动重连）
 * 2. 消息路由（content <-> WS <-> popup）
 * 3. Tab 管理
 */

'use strict';

const WS_URL = 'ws://127.0.0.1:9222/ws/extension';
const RECONNECT_DELAY_MS = 5000;

let ws = null;
let wsConnected = false;
let reconnectTimer = null;
let activeTabId = null;

// ── WebSocket 管理 ──

function connectWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  console.log('[FlowRPA] 连接 WebSocket:', WS_URL);
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    wsConnected = true;
    clearTimeout(reconnectTimer);
    console.log('[FlowRPA] WebSocket 已连接');
    broadcastStatus({ connected: true });
    ws.send(JSON.stringify({ type: 'hello', data: { source: 'extension', version: '1.0.0' } }));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWsMessage(msg);
    } catch (e) {
      console.error('[FlowRPA] WS消息解析失败:', e);
    }
  };

  ws.onerror = (err) => {
    console.warn('[FlowRPA] WebSocket 错误:', err);
  };

  ws.onclose = () => {
    wsConnected = false;
    ws = null;
    broadcastStatus({ connected: false });
    console.log(`[FlowRPA] WebSocket 断开，${RECONNECT_DELAY_MS / 1000}s后重连...`);
    reconnectTimer = setTimeout(connectWS, RECONNECT_DELAY_MS);
  };
}

function sendToWS(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
    return true;
  }
  return false;
}

// ── 消息处理 ──

function handleWsMessage(msg) {
  const { type, data } = msg;

  switch (type) {
    case 'start_pick':
      forwardToContent({ action: 'start_pick' });
      break;
    case 'stop_pick':
      forwardToContent({ action: 'stop_pick' });
      break;
    case 'start_record':
      forwardToContent({ action: 'start_record' });
      break;
    case 'stop_record':
      forwardToContent({ action: 'stop_record' });
      break;
    case 'highlight':
      forwardToContent({ action: 'highlight', selector: data?.selector });
      break;
    default:
      // 其他消息转发给 popup
      broadcastToPopup(msg);
  }
}

function forwardToContent(msg) {
  // 发给当前活跃 tab
  const tabId = activeTabId;
  if (tabId) {
    chrome.tabs.sendMessage(tabId, msg, (resp) => {
      if (chrome.runtime.lastError) {
        console.warn('[FlowRPA] 发送给content失败:', chrome.runtime.lastError.message);
      }
    });
  } else {
    // 发给所有 tab
    chrome.tabs.query({ active: true }, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, msg, () => {
          if (chrome.runtime.lastError) {}
        });
      });
    });
  }
}

function broadcastStatus(status) {
  broadcastToPopup({ type: 'ws_status', data: status });
}

function broadcastToPopup(msg) {
  chrome.runtime.sendMessage(msg).catch(() => {});
}

// ── 来自 content/popup 的消息 ──

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const { type, data } = msg;

  if (sender.tab) {
    // 来自 content script
    if (type === 'element_selected') {
      sendToWS({ type: 'element_selected', data });
      broadcastToPopup({ type: 'element_selected', data });
    } else if (type === 'recorded_action') {
      sendToWS({ type: 'recorded_action', data });
    } else if (type === 'record_stopped') {
      sendToWS({ type: 'record_stopped', data });
      broadcastToPopup({ type: 'record_stopped', data });
    } else if (type === 'canvas_data') {
      sendToWS({ type: 'canvas_data', data: { url: sender.tab?.url, imageData: data } });
    }
    activeTabId = sender.tab.id;
  } else {
    // 来自 popup
    if (type === 'start_pick') {
      forwardToContent({ action: 'start_pick' });
      sendResponse({ ok: true });
    } else if (type === 'stop_pick') {
      forwardToContent({ action: 'stop_pick' });
      sendResponse({ ok: true });
    } else if (type === 'start_record') {
      forwardToContent({ action: 'start_record' });
      sendResponse({ ok: true });
    } else if (type === 'stop_record') {
      forwardToContent({ action: 'stop_record' });
      sendResponse({ ok: true });
    } else if (type === 'get_ws_status') {
      sendResponse({ connected: wsConnected });
    }
  }

  return true;
});

// ── Tab 管理 ──

chrome.tabs.onActivated.addListener((activeInfo) => {
  activeTabId = activeInfo.tabId;
});

chrome.webNavigation.onCompleted.addListener((details) => {
  if (details.frameId === 0) {
    // 页面加载完成，可在此注入额外脚本
    activeTabId = details.tabId;
  }
});

// ── 启动 ──

connectWS();

console.log('[FlowRPA] Background service worker 已启动');
