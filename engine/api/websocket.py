"""websocket.py - WebSocket 路由和广播"""

import asyncio
import json
import logging
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# 主 WebSocket 连接集合
_ws_clients: Set[WebSocket] = set()
# Chrome 扩展 WebSocket 连接集合
_ext_clients: Set[WebSocket] = set()


async def ws_broadcast(message: Dict[str, Any], target: str = "all"):
    """广播消息到所有/指定 WebSocket 连接

    Args:
        message: 消息字典，格式:
            {
                "type": "log" | "node_status" | "error" | "complete" | "element_selected",
                "data": {...}
            }
        target: "all" | "main" | "extension"
    """
    payload = json.dumps(message, ensure_ascii=False)

    async def _send(ws: WebSocket):
        try:
            await ws.send_text(payload)
        except Exception:
            pass

    if target in ("all", "main"):
        disconnected = set()
        for ws in list(_ws_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.add(ws)
        _ws_clients -= disconnected

    if target in ("all", "extension"):
        disconnected = set()
        for ws in list(_ext_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.add(ws)
        _ext_clients -= disconnected


@router.websocket("/ws")
async def websocket_main(websocket: WebSocket):
    """主 WebSocket 端点（桌面客户端连接）"""
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"WebSocket 主客户端已连接，当前共 {len(_ws_clients)} 个")
    try:
        # 发送欢迎消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "FlowRPA Engine 已连接"}
        }))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await _handle_client_message(msg, websocket)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON"}
                }))
    except WebSocketDisconnect:
        logger.info("主客户端断开连接")
    finally:
        _ws_clients.discard(websocket)


@router.websocket("/ws/extension")
async def websocket_extension(websocket: WebSocket):
    """Chrome 扩展 WebSocket 端点"""
    await websocket.accept()
    _ext_clients.add(websocket)
    logger.info(f"Chrome扩展已连接，当前共 {len(_ext_clients)} 个扩展")
    try:
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "FlowRPA Extension 连接成功"}
        }))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # 来自扩展的消息转发给主客户端
                msg["_from"] = "extension"
                await ws_broadcast(msg, target="main")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("Chrome扩展断开连接")
    finally:
        _ext_clients.discard(websocket)


async def _handle_client_message(msg: Dict, websocket: WebSocket):
    """处理来自主客户端的消息"""
    msg_type = msg.get("type", "")

    if msg_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong", "data": {}}))

    elif msg_type == "forward_to_extension":
        # 转发消息给所有扩展
        await ws_broadcast(msg.get("data", {}), target="extension")

    elif msg_type == "get_status":
        from api.deps import get_runner
        runner = get_runner()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": runner.status
        }))
