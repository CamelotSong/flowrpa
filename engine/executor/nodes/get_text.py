"""get_text 节点 - 获取元素文本，存入上下文变量"""

import asyncio
from typing import Any, Dict
from .base import BaseNode


class GetTextNode(BaseNode):
    def _default_node_type(self) -> str:
        return "get_text"

    def _validate_config(self):
        super()._validate_config()
        if not self.config.get("selector") and not self.config.get("css") and not self.config.get("xpath"):
            raise ValueError(f"get_text 节点 [{self.node_id}] 缺少选择器参数")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        selector = self._get_selector(context)
        var_name = self.config.get("variable", "text_result")
        attribute = self.config.get("attribute", None)  # None 表示获取 innerText
        multiple = self.config.get("multiple", False)

        from .click import ClickNode
        helper = ClickNode.__new__(ClickNode)

        if multiple:
            # 获取所有匹配元素的文本
            elements = page.eles(selector)
            texts = []
            for el in elements:
                if attribute:
                    texts.append(el.attr(attribute) or "")
                else:
                    texts.append(el.text or "")
            context.setdefault("variables", {})[var_name] = texts
            await asyncio.sleep(0.1)
            return {"success": True, "variable": var_name, "value": texts, "count": len(texts)}
        else:
            element = helper._find_element(page, selector)
            if not element:
                return {"success": False, "error": f"未找到元素: {selector}"}

            if attribute:
                text = element.attr(attribute) or ""
            else:
                text = element.text or ""

            context.setdefault("variables", {})[var_name] = text
            await asyncio.sleep(0.1)

            return {"success": True, "variable": var_name, "value": text}
