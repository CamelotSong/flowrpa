/**
 * FlowRPA Content Script
 *
 * 功能：
 * 1. 元素选择模式 - 悬停高亮，点击生成选择器
 * 2. 录制模式 - 监听用户操作，记录成工作流节点
 * 3. Canvas 内容监控 - 劫持 toDataURL 获取 canvas 数据
 * 4. 消息监听 - 接收来自 background 的控制指令
 */

(function () {
  'use strict';

  // ── 状态 ──
  let pickMode = false;
  let recordMode = false;
  let hoveredEl = null;
  let overlay = null;
  let tooltip = null;
  let recordedActions = [];

  // ── Canvas Hook（页面加载时立刻注入）──
  const canvasHookScript = document.createElement('script');
  canvasHookScript.textContent = `
    (function() {
      const _intercepted = [];
      const orig = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
        const result = orig.apply(this, arguments);
        try {
          window.postMessage({ __flowrpa: true, type: 'canvas_data', data: result.substring(0, 50000) }, '*');
        } catch(e) {}
        return result;
      };
    })();
  `;
  (document.head || document.documentElement).appendChild(canvasHookScript);
  canvasHookScript.remove();

  // 监听 canvas 数据（来自页面注入脚本）
  window.addEventListener('message', (e) => {
    if (e.data && e.data.__flowrpa && e.data.type === 'canvas_data') {
      chrome.runtime.sendMessage({
        type: 'canvas_data',
        data: e.data.data,
        url: location.href,
      }).catch(() => {});
    }
  });

  // ── 工具函数 ──

  function getCssSelector(el) {
    if (!el || el === document.body) return 'body';
    if (el.id) return `#${CSS.escape(el.id)}`;

    const parts = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.id) {
        selector = `#${CSS.escape(current.id)}`;
        parts.unshift(selector);
        break;
      }
      if (current.className) {
        const classes = [...current.classList]
          .filter(c => !c.startsWith('__') && c.length < 40)
          .slice(0, 3)
          .map(c => `.${CSS.escape(c)}`)
          .join('');
        if (classes) selector += classes;
      }
      // 添加 nth-child
      const parent = current.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter(c => c.tagName === current.tagName);
        if (siblings.length > 1) {
          const idx = siblings.indexOf(current) + 1;
          selector += `:nth-of-type(${idx})`;
        }
      }
      parts.unshift(selector);
      current = current.parentElement;
    }
    return parts.join(' > ');
  }

  function getXPath(el) {
    if (!el || el === document.body) return '//body';
    if (el.id) return `//*[@id="${el.id}"]`;

    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let idx = 1;
      let sibling = current.previousSibling;
      while (sibling) {
        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) idx++;
        sibling = sibling.previousSibling;
      }
      parts.unshift(`${current.tagName.toLowerCase()}[${idx}]`);
      current = current.parentNode;
    }
    return '/' + parts.join('/');
  }

  function getTextSelector(el) {
    const text = el.textContent?.trim();
    if (text && text.length > 0 && text.length < 60) {
      return `text:${text}`;
    }
    return '';
  }

  function getElementInfo(el) {
    const rect = el.getBoundingClientRect();
    return {
      tagName: el.tagName.toLowerCase(),
      id: el.id || '',
      className: el.className || '',
      text: (el.textContent?.trim() || '').substring(0, 80),
      cssSelector: getCssSelector(el),
      xpath: getXPath(el),
      textSelector: getTextSelector(el),
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    };
  }

  // ── 高亮覆盖层 ──

  function createOverlay() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.id = '__flowrpa_overlay';
    Object.assign(overlay.style, {
      position: 'fixed',
      pointerEvents: 'none',
      zIndex: '2147483646',
      border: '2px solid #4F8EF7',
      backgroundColor: 'rgba(79,142,247,0.12)',
      borderRadius: '3px',
      transition: 'all 0.08s ease',
      boxSizing: 'border-box',
      display: 'none',
    });
    document.body.appendChild(overlay);

    tooltip = document.createElement('div');
    tooltip.id = '__flowrpa_tooltip';
    Object.assign(tooltip.style, {
      position: 'fixed',
      pointerEvents: 'none',
      zIndex: '2147483647',
      backgroundColor: 'rgba(15,15,20,0.92)',
      color: '#e2e8f0',
      fontSize: '12px',
      fontFamily: 'monospace',
      padding: '6px 10px',
      borderRadius: '6px',
      border: '1px solid rgba(79,142,247,0.5)',
      maxWidth: '360px',
      lineHeight: '1.6',
      wordBreak: 'break-all',
      display: 'none',
      backdropFilter: 'blur(4px)',
    });
    document.body.appendChild(tooltip);
  }

  function updateOverlay(el) {
    if (!overlay || !tooltip) return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;

    Object.assign(overlay.style, {
      display: 'block',
      left: rect.left + 'px',
      top: rect.top + 'px',
      width: rect.width + 'px',
      height: rect.height + 'px',
    });

    const info = getElementInfo(el);
    tooltip.innerHTML = `
      <b style="color:#4F8EF7">▣ ${info.tagName}</b>
      ${info.id ? `<br/><span style="color:#68d391">#${info.id}</span>` : ''}
      ${info.text ? `<br/><span style="color:#fbd38d">"${info.text.substring(0, 40)}"</span>` : ''}
      <br/><span style="color:#a0aec0">${info.cssSelector.substring(0, 60)}</span>
    `;

    let tx = rect.left;
    let ty = rect.bottom + 6;
    if (ty + 80 > window.innerHeight) ty = rect.top - 90;
    if (tx + 380 > window.innerWidth) tx = window.innerWidth - 385;

    Object.assign(tooltip.style, {
      display: 'block',
      left: Math.max(0, tx) + 'px',
      top: Math.max(0, ty) + 'px',
    });
  }

  function hideOverlay() {
    if (overlay) overlay.style.display = 'none';
    if (tooltip) tooltip.style.display = 'none';
  }

  // ── 元素选择模式 ──

  function startPick() {
    pickMode = true;
    createOverlay();
    document.body.style.cursor = 'crosshair';
  }

  function stopPick() {
    pickMode = false;
    hideOverlay();
    document.body.style.cursor = '';
  }

  function onMouseMove(e) {
    if (!pickMode) return;
    const el = e.target;
    if (el === overlay || el === tooltip) return;
    hoveredEl = el;
    updateOverlay(el);
  }

  function onMouseClick(e) {
    if (!pickMode) return;
    e.preventDefault();
    e.stopPropagation();

    const info = getElementInfo(e.target);
    stopPick();

    chrome.runtime.sendMessage({
      type: 'element_selected',
      data: info,
    }).catch(() => {});

    return false;
  }

  // ── 录制模式 ──

  function startRecord() {
    recordMode = true;
    recordedActions = [];
    console.log('[FlowRPA] 录制已开始');
  }

  function stopRecord() {
    recordMode = false;
    chrome.runtime.sendMessage({
      type: 'record_stopped',
      data: recordedActions,
    }).catch(() => {});
    recordedActions = [];
    console.log('[FlowRPA] 录制已停止');
  }

  function recordAction(action) {
    if (!recordMode) return;
    recordedActions.push({ ...action, timestamp: Date.now() });
    chrome.runtime.sendMessage({ type: 'recorded_action', data: action }).catch(() => {});
  }

  function onRecordClick(e) {
    if (!recordMode || e.target === overlay || e.target === tooltip) return;
    const info = getElementInfo(e.target);
    recordAction({
      type: 'click',
      selector: info.cssSelector,
      xpath: info.xpath,
      text: info.text,
      element: info,
    });
  }

  function onRecordInput(e) {
    if (!recordMode) return;
    const el = e.target;
    const info = getElementInfo(el);
    recordAction({
      type: 'input_text',
      selector: info.cssSelector,
      value: el.value || el.textContent || '',
      element: info,
    });
  }

  function onRecordScroll(e) {
    if (!recordMode) return;
    recordAction({
      type: 'scroll',
      direction: 'down',
      amount: window.scrollY,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
    });
  }

  function onRecordKeydown(e) {
    if (!recordMode) return;
    if (['Enter', 'Escape', 'Tab'].includes(e.key)) {
      const info = getElementInfo(e.target);
      recordAction({
        type: 'keydown',
        key: e.key,
        selector: info.cssSelector,
        element: info,
      });
    }
  }

  // ── 事件绑定 ──

  document.addEventListener('mousemove', onMouseMove, true);
  document.addEventListener('click', onMouseClick, true);
  document.addEventListener('click', onRecordClick, true);
  document.addEventListener('change', onRecordInput, true);
  document.addEventListener('scroll', onRecordScroll, true);
  document.addEventListener('keydown', onRecordKeydown, true);

  // ── 消息监听 ──

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    switch (msg.action) {
      case 'start_pick':
        startPick();
        sendResponse({ ok: true });
        break;
      case 'stop_pick':
        stopPick();
        sendResponse({ ok: true });
        break;
      case 'start_record':
        startRecord();
        sendResponse({ ok: true });
        break;
      case 'stop_record':
        stopRecord();
        sendResponse({ ok: true });
        break;
      case 'get_status':
        sendResponse({ pickMode, recordMode, actionsCount: recordedActions.length });
        break;
      case 'get_selectors':
        if (hoveredEl) {
          sendResponse(getElementInfo(hoveredEl));
        } else {
          sendResponse(null);
        }
        break;
    }
    return true;
  });

})();
