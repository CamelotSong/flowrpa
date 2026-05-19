"""BaseNode - 所有工作流节点的抽象基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseNode(ABC):
    """工作流节点抽象基类

    每个节点必须实现 execute 方法，接收 page (DrissionPage) 和 context (执行上下文)，
    返回结果字典。
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.node_id: str = config.get("id", "")
        self.node_type: str = config.get("type", self._default_node_type())
        self.next_node: Optional[str] = config.get("next", None)
        self.retry_count: int = config.get("retry", 3)
        self._validate_config()

    @abstractmethod
    def _default_node_type(self) -> str:
        """返回节点默认类型标识"""
        ...

    @abstractmethod
    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行节点逻辑

        Args:
            page: DrissionPage 的 ChromiumPage 实例
            context: 执行上下文字典，用于节点间传递数据

        Returns:
            执行结果字典，至少包含 {"success": bool}
        """
        ...

    def _validate_config(self):
        """通用参数验证，子类可覆盖扩展"""
        if not self.node_id:
            raise ValueError(f"节点缺少 id 字段: {self.config}")

    def _get_selector(self, context: Dict[str, Any]) -> str:
        """从配置中获取选择器，支持从上下文解析变量

        支持格式: css:xxx, xpath:xxx, text:xxx
        """
        selector = self.config.get("selector", "")
        if not selector:
            selector = self.config.get("css", "")
            if selector:
                selector = f"css:{selector}"
        return self._resolve_variables(selector, context)

    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """解析文本中的 {{variable}} 变量引用"""
        import re
        def replacer(match):
            var_name = match.group(1)
            return str(context.get("variables", {}).get(var_name, match.group(0)))
        return re.sub(r'\{\{(\w+)\}\}', replacer, text)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.node_id} type={self.node_type}>"
