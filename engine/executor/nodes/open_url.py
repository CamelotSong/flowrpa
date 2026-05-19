"""open_url 节点 - 打开指定 URL"""

import asyncio
from typing import Any, Dict
from .base import BaseNode


class OpenUrlNode(BaseNode):
    def _default_node_type(self) -> str:
        return "open_url"

    def _validate_config(self):
        super()._validate_config()
        if not self.config.get("url"):
            raise ValueError(f"open_url 节点 [{self.node_id}] 缺少 url 参数")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        url = self._resolve_variables(self.config["url"], context)
        wait_load = self.config.get("wait_load", True)
        timeout = self.config.get("timeout", 10)

        page.get(url)

        if wait_load:
            try:
                page.wait.load_start(timeout=timeout)
                page.wait.doc_loaded(timeout=timeout * 2)
            except Exception:
                pass  # 部分页面不触发标准加载事件，忽略超时

        # 随机等待，模拟人工操作
        await asyncio.sleep(0.8 + __import__("random").random() * 1.2)

        return {
            "success": True,
            "url": page.url,
            "title": page.title,
        }
