"""click 节点 - 点击元素（支持 CSS/XPath/文本选择器）"""

import asyncio
import random
from typing import Any, Dict
from .base import BaseNode


class ClickNode(BaseNode):
    def _default_node_type(self) -> str:
        return "click"

    def _validate_config(self):
        super()._validate_config()
        if not self.config.get("selector") and not self.config.get("css") and not self.config.get("xpath") and not self.config.get("text"):
            raise ValueError(f"click 节点 [{self.node_id}] 缺少选择器参数")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        selector = self._get_selector(context)
        click_type = self.config.get("click_type", "single")  # single / double
        wait_after = self.config.get("wait_after", 1.0)
        timeout = self.config.get("timeout", 10)

        # 根据选择器类型查找元素
        element = self._find_element(page, selector, timeout)
        if not element:
            return {"success": False, "error": f"未找到元素: {selector}"}

        # 确保元素可见
        try:
            element.wait.displayed(timeout=timeout)
        except Exception:
            # 尝试滚动到元素可见
            element.scroll.to_see()
            await asyncio.sleep(0.3)

        # 随机延迟模拟人工
        await asyncio.sleep(0.2 + random.random() * 0.5)

        if click_type == "double":
            element.click(by_js=False)
            await asyncio.sleep(0.1)
            element.click(by_js=False)
        else:
            # 优先尝试普通点击，失败则用 JS 点击
            try:
                element.click(by_js=False)
            except Exception:
                element.click(by_js=True)

        await asyncio.sleep(wait_after + random.random() * 0.5)

        return {"success": True, "selector": selector}

    def _find_element(self, page: Any, selector: str, timeout: int = 10) -> Any:
        """根据选择器前缀查找元素"""
        if selector.startswith("xpath:"):
            xpath = selector[6:]
            try:
                return page.ele(f"xpath:{xpath}", timeout=timeout)
            except Exception:
                return None
        elif selector.startswith("text:"):
            text = selector[5:]
            try:
                return page.ele(f"text:{text}", timeout=timeout)
            except Exception:
                return None
        elif selector.startswith("css:"):
            css = selector[4:]
            try:
                return page.ele(f"css:{css}", timeout=timeout)
            except Exception:
                return None
        else:
            # 默认当作 CSS 选择器
            try:
                return page.ele(selector, timeout=timeout)
            except Exception:
                return None
