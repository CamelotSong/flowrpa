"""wait 节点 - 等待（固定时间或等待元素出现）"""

import asyncio
import random
from typing import Any, Dict
from .base import BaseNode


class WaitNode(BaseNode):
    def _default_node_type(self) -> str:
        return "wait"

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        wait_type = self.config.get("wait_type", "time")  # time / element

        if wait_type == "time":
            seconds = self.config.get("seconds", 2)
            # 加入随机偏移
            randomized = seconds + random.uniform(-0.3, 0.5)
            randomized = max(0.1, randomized)
            await asyncio.sleep(randomized)
            return {"success": True, "waited": randomized}

        elif wait_type == "element":
            selector = self.config.get("selector", "")
            timeout = self.config.get("timeout", 10)
            state = self.config.get("state", "displayed")  # displayed / hidden / deleted

            if not selector:
                return {"success": False, "error": "wait(element) 缺少 selector 参数"}

            from .click import ClickNode
            helper = ClickNode.__new__(ClickNode)

            try:
                element = helper._find_element(page, selector, timeout=timeout)
                if state == "displayed" and element:
                    element.wait.displayed(timeout=timeout)
                elif state == "hidden" and element:
                    element.wait.hidden(timeout=timeout)
                elif state == "deleted":
                    try:
                        element.wait.deleted(timeout=timeout)
                    except Exception:
                        pass
                return {"success": True, "element_found": element is not None}
            except Exception as e:
                return {"success": False, "error": f"等待元素超时: {selector}, {str(e)}"}

        else:
            return {"success": False, "error": f"不支持的 wait_type: {wait_type}"}
