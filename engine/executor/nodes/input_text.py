"""input_text 节点 - 模拟人工逐字输入文字"""

import asyncio
import random
from typing import Any, Dict
from .base import BaseNode


class InputTextNode(BaseNode):
    def _default_node_type(self) -> str:
        return "input_text"

    def _validate_config(self):
        super()._validate_config()
        if not self.config.get("selector") and not self.config.get("css") and not self.config.get("xpath"):
            raise ValueError(f"input_text 节点 [{self.node_id}] 缺少选择器参数")
        if "text" not in self.config:
            raise ValueError(f"input_text 节点 [{self.node_id}] 缺少 text 参数")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        from .click import ClickNode
        selector = self._get_selector(context)
        text = self._resolve_variables(str(self.config["text"]), context)
        clear_first = self.config.get("clear_first", True)
        human_like = self.config.get("human_like", True)
        # 每字符最小/最大延迟(秒)
        char_delay_min = self.config.get("char_delay_min", 0.05)
        char_delay_max = self.config.get("char_delay_max", 0.18)

        helper = ClickNode.__new__(ClickNode)
        element = helper._find_element(page, selector)
        if not element:
            return {"success": False, "error": f"未找到输入框: {selector}"}

        # 确保元素可见并点击聚焦
        try:
            element.scroll.to_see()
            await asyncio.sleep(0.3)
            element.click(by_js=False)
        except Exception:
            element.click(by_js=True)

        await asyncio.sleep(0.3 + random.random() * 0.3)

        if clear_first:
            # Ctrl+A 全选后删除
            element.input("", clear=True)
            await asyncio.sleep(0.2)

        if human_like:
            # 逐字符输入，随机延迟
            for char in text:
                element.input(char, clear=False)
                delay = char_delay_min + random.random() * (char_delay_max - char_delay_min)
                # 偶尔有较长停顿，模拟思考
                if random.random() < 0.05:
                    delay += random.uniform(0.3, 0.8)
                await asyncio.sleep(delay)
        else:
            element.input(text, clear=False)

        await asyncio.sleep(0.2 + random.random() * 0.3)

        return {
            "success": True,
            "text_length": len(text),
        }
