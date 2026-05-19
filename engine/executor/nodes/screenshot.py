"""screenshot 节点 - 截图（全页面或指定元素）"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict
from .base import BaseNode


class ScreenshotNode(BaseNode):
    def _default_node_type(self) -> str:
        return "screenshot"

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        save_dir = self.config.get("save_dir", "screenshots")
        filename = self.config.get("filename", "")
        full_page = self.config.get("full_page", False)
        selector = self.config.get("selector", "")

        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)

        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screenshot_{ts}.png"

        filepath = os.path.join(save_dir, filename)

        if selector:
            from .click import ClickNode
            helper = ClickNode.__new__(ClickNode)
            element = helper._find_element(page, selector)
            if element:
                element.get_screenshot(path=filepath, name=filename)
            else:
                return {"success": False, "error": f"未找到元素: {selector}"}
        elif full_page:
            page.get_screenshot(path=filepath, name=filename, full_page=True)
        else:
            page.get_screenshot(path=filepath, name=filename)

        await asyncio.sleep(0.2)

        # 将截图路径存入上下文
        context.setdefault("screenshots", []).append(filepath)

        return {
            "success": True,
            "path": os.path.abspath(filepath),
        }
