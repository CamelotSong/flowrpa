"""condition 节点 - 条件分支，根据条件决定下一个执行节点"""

import asyncio
import operator
from typing import Any, Dict
from .base import BaseNode


OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "contains": lambda a, b: b in str(a),
    "not_contains": lambda a, b: b not in str(a),
    "startswith": lambda a, b: str(a).startswith(str(b)),
    "endswith": lambda a, b: str(a).endswith(str(b)),
    "is_empty": lambda a, b: not a,
    "is_not_empty": lambda a, b: bool(a),
    "exists": lambda a, b: a is not None,
}


class ConditionNode(BaseNode):
    def _default_node_type(self) -> str:
        return "condition"

    def _validate_config(self):
        super()._validate_config()
        if "conditions" not in self.config and "variable" not in self.config:
            raise ValueError(f"condition 节点 [{self.node_id}] 缺少条件配置")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        variables = context.get("variables", {})
        result = self._evaluate_condition(variables, context)

        # 根据结果选择不同的后续节点
        true_next = self.config.get("true_next")
        false_next = self.config.get("false_next")

        next_node = true_next if result else false_next
        # 将下一节点信息写入上下文供 runner 使用
        context["_condition_next"] = next_node

        await asyncio.sleep(0.05)
        return {"success": True, "condition_result": result, "next": next_node}

    def _evaluate_condition(self, variables: dict, context: dict) -> bool:
        """支持 AND/OR 复合条件或单一条件"""
        conditions = self.config.get("conditions")
        if conditions:
            logic = self.config.get("logic", "AND").upper()
            results = [self._check_single(c, variables, context) for c in conditions]
            if logic == "OR":
                return any(results)
            else:
                return all(results)
        else:
            return self._check_single(self.config, variables, context)

    def _check_single(self, cond: dict, variables: dict, context: dict) -> bool:
        var_name = cond.get("variable", "")
        op_name = cond.get("operator", "eq")
        expected = cond.get("value")

        # 从变量或上下文中取值
        actual = variables.get(var_name)
        if actual is None:
            actual = context.get(var_name)

        op_func = OPERATORS.get(op_name, operator.eq)
        try:
            # 尝试数值比较
            if op_name in ("gt", "gte", "lt", "lte"):
                return op_func(float(actual), float(expected))
            return op_func(actual, expected)
        except (TypeError, ValueError):
            return False
