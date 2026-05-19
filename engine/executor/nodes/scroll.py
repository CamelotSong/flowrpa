"""scroll 节点 - 页面或元素滚动"""

import asyncio
import random
from typing import Any, Dict
from .base import BaseNode


class ScrollNode(BaseNode):
    def _default_node_type(self) -> str:
        return "scroll"

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        direction = self.config.get("direction", "down")  # down / up / left / right
        amount = self.config.get("amount", 300)  # 像素
        randomize = self.config.get("randomize", True)

        if randomize:
            amount = int(amount * (0.8 + random.random() * 0.4))

        selector = self.config.get("selector")
        if selector:
            # 滚动特定元素
            from .click import ClickNode
            helper = ClickNode.__new__(ClickNode)
            element = helper._find_element(page, selector)
            if element:
                if direction == "down":
                    element.scroll.down(amount)
                elif direction == "up":
                    element.scroll.up(amount)
                elif direction == "left":
                    element.scroll.left(amount)
                elif direction == "right":
                    element.scroll.right(amount)
            else:
                return {"success": False, "error": f"未找到元素: {selector}"}
        else:
            # 滚动页面
            if direction == "down":
                page.scroll.down(amount)
            elif direction == "up":
                page.scroll.up(amount)
            elif direction == "left":
                page.scroll.left(amount)
            elif direction == "right":
                page.scroll.right(amount)
            elif direction == "top":
                page.scroll.to_top()
            elif direction == "bottom":
                page.scroll.to_bottom()

        await asyncio.sleep(0.3 + random.random() * 0.4)

        return {"success": True, "direction": direction, "amount": amount}
