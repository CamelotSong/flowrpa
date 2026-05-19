"""WorkflowRunner - 工作流执行器

按节点顺序执行工作流，通过 ws_broadcast 推送状态。
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .nodes.base import BaseNode
from .nodes.open_url import OpenUrlNode
from .nodes.click import ClickNode
from .nodes.input_text import InputTextNode
from .nodes.scroll import ScrollNode
from .nodes.wait import WaitNode
from .nodes.screenshot import ScreenshotNode
from .nodes.get_text import GetTextNode
from .nodes.condition import ConditionNode
from .nodes.loop import LoopNode

logger = logging.getLogger(__name__)

NODE_TYPE_MAP = {
    "open_url": OpenUrlNode,
    "click": ClickNode,
    "input_text": InputTextNode,
    "scroll": ScrollNode,
    "wait": WaitNode,
    "screenshot": ScreenshotNode,
    "get_text": GetTextNode,
    "condition": ConditionNode,
    "loop": LoopNode,
}


class WorkflowRunner:
    """工作流执行器"""

    def __init__(self):
        self.workflow: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {"variables": {}, "screenshots": []}
        self._running: bool = False
        self._page: Any = None
        self._current_node_id: Optional[str] = None
        self._results: List[Dict[str, Any]] = []
        self._ws_broadcast: Optional[Callable] = None
        self._node_status: Dict[str, str] = {}  # node_id -> pending/running/success/error

    def set_ws_broadcast(self, fn: Callable):
        """设置 WebSocket 广播回调"""
        self._ws_broadcast = fn

    def load_workflow(self, path_or_dict) -> None:
        """加载工作流 JSON

        Args:
            path_or_dict: 文件路径(str/Path) 或字典
        """
        if isinstance(path_or_dict, (str, Path)):
            with open(path_or_dict, "r", encoding="utf-8") as f:
                self.workflow = json.load(f)
        elif isinstance(path_or_dict, dict):
            self.workflow = path_or_dict
        else:
            raise ValueError(f"不支持的输入类型: {type(path_or_dict)}")

        # 初始化节点状态
        for node in self.workflow.get("nodes", []):
            self._node_status[node.get("id", "")] = "pending"

    def _create_node(self, node_config: Dict[str, Any]) -> Optional[BaseNode]:
        """根据配置创建节点实例"""
        node_type = node_config.get("type", "")
        node_class = NODE_TYPE_MAP.get(node_type)
        if not node_class:
            logger.warning(f"未知节点类型: {node_type}")
            return None
        try:
            return node_class(node_config)
        except Exception as e:
            logger.error(f"创建节点失败 [{node_type}]: {e}")
            return None

    async def run(self) -> Dict[str, Any]:
        """按节点顺序执行工作流"""
        if not self.workflow:
            return {"success": False, "error": "未加载工作流"}

        nodes = self.workflow.get("nodes", [])
        edges = self.workflow.get("edges", [])

        # 构建 edges 映射: source_id -> target_id
        edge_map: Dict[str, str] = {}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src and tgt:
                edge_map[src] = tgt

        self._running = True
        self._results = []

        # 初始化 DrissionPage
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
            from anti_detect.stealth import get_stealth_options

            co = get_stealth_options()
            self._page = ChromiumPage(co)
        except ImportError:
            logger.warning("DrissionPage 未安装，使用无浏览器模式")
            self._page = None
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            self._page = None

        # 广播开始
        await self._broadcast({"type": "log", "data": {"level": "INFO", "message": "工作流开始执行"}})

        # 按顺序执行节点（如果无 edges 则按列表顺序）
        execution_order = self._resolve_execution_order(nodes, edge_map)

        for node_config in execution_order:
            if not self._running:
                await self._broadcast({"type": "log", "data": {"level": "WARN", "message": "工作流已被停止"}})
                break

            node_id = node_config.get("id", "")
            self._current_node_id = node_id
            self._node_status[node_id] = "running"

            await self._broadcast({
                "type": "node_status",
                "data": {"node_id": node_id, "status": "running"}
            })

            node = self._create_node(node_config)
            if not node:
                self._node_status[node_id] = "error"
                await self._broadcast({
                    "type": "node_status",
                    "data": {"node_id": node_id, "status": "error", "error": "节点创建失败"}
                })
                continue

            # 带重试的执行
            result = await self._execute_with_retry(node, node_config)

            if result.get("success"):
                self._node_status[node_id] = "success"
                await self._broadcast({
                    "type": "node_status",
                    "data": {"node_id": node_id, "status": "success", "result": result}
                })
            else:
                self._node_status[node_id] = "error"
                await self._broadcast({
                    "type": "node_status",
                    "data": {"node_id": node_id, "status": "error", "error": result.get("error", "未知错误")}
                })

            self._results.append({"node_id": node_id, **result})

            # 条件节点：更新后续执行路径
            if isinstance(node, ConditionNode):
                condition_next = self.context.get("_condition_next")
                if condition_next:
                    # 重新排列后续节点顺序
                    pass  # TODO: 条件分支动态路径

        self._running = False
        self._current_node_id = None

        await self._broadcast({
            "type": "complete",
            "data": {"total": len(execution_order), "results": self._results}
        })

        return {
            "success": True,
            "total_nodes": len(execution_order),
            "results": self._results,
        }

    async def _execute_with_retry(self, node: BaseNode, node_config: Dict) -> Dict[str, Any]:
        """带重试的节点执行"""
        max_retries = node_config.get("retry", 3)
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                result = await node.execute(self._page, self.context)
                if result.get("success"):
                    return result
                last_error = result.get("error", "执行失败")
                await self._broadcast({
                    "type": "log",
                    "data": {"level": "WARN", "message": f"节点 {node.node_id} 第{attempt}次执行失败: {last_error}"}
                })
            except Exception as e:
                last_error = str(e)
                await self._broadcast({
                    "type": "log",
                    "data": {"level": "WARN", "message": f"节点 {node.node_id} 第{attempt}次执行异常: {last_error}"}
                })

            if attempt < max_retries:
                await asyncio.sleep(1.0 * attempt)  # 递增延迟

        return {"success": False, "error": f"重试{max_retries}次后仍失败: {last_error}"}

    def _resolve_execution_order(self, nodes: List[Dict], edge_map: Dict[str, str]) -> List[Dict]:
        """根据边映射解析执行顺序"""
        if not edge_map:
            return nodes

        node_map = {n["id"]: n for n in nodes if "id" in n}
        # 找起始节点（无入边的）
        targets = set(edge_map.values())
        start_ids = [nid for nid in node_map if nid not in targets]
        if not start_ids:
            start_ids = [nodes[0]["id"]] if nodes else []

        ordered = []
        visited = set()
        for start_id in start_ids:
            current = start_id
            while current and current not in visited and current in node_map:
                ordered.append(node_map[current])
                visited.add(current)
                current = edge_map.get(current)

        # 加入未在链中的节点
        for n in nodes:
            if n.get("id") and n["id"] not in visited:
                ordered.append(n)

        return ordered

    def stop(self):
        """停止执行"""
        self._running = False

    @property
    def status(self) -> Dict[str, Any]:
        """获取当前执行状态"""
        return {
            "running": self._running,
            "current_node": self._current_node_id,
            "node_status": dict(self._node_status),
            "context_variables": dict(self.context.get("variables", {})),
        }

    async def _broadcast(self, message: Dict[str, Any]):
        """广播消息到 WebSocket"""
        if self._ws_broadcast:
            try:
                if asyncio.iscoroutinefunction(self._ws_broadcast):
                    await self._ws_broadcast(message)
                else:
                    self._ws_broadcast(message)
            except Exception as e:
                logger.warning(f"广播消息失败: {e}")
