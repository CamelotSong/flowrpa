"""loop 节点 - 循环执行子节点"""

import asyncio
from typing import Any, Dict, List
from .base import BaseNode


class LoopNode(BaseNode):
    def _default_node_type(self) -> str:
        return "loop"

    def _validate_config(self):
        super()._validate_config()
        if "loop_body" not in self.config and "sub_nodes" not in self.config:
            raise ValueError(f"loop 节点 [{self.node_id}] 缺少 loop_body/sub_nodes")

    async def execute(self, page: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        loop_type = self.config.get("loop_type", "count")  # count / while / for_each
        max_iterations = self.config.get("max_iterations", 100)
        iteration_count = 0
        results = []

        if loop_type == "count":
            count = self.config.get("count", 1)
            count = min(count, max_iterations)
            for i in range(count):
                result = await self._execute_body(i, page, context)
                results.append(result)
                iteration_count += 1

        elif loop_type == "while":
            while iteration_count < max_iterations:
                if not self._check_while_condition(context):
                    break
                result = await self._execute_body(iteration_count, page, context)
                results.append(result)
                iteration_count += 1

        elif loop_type == "for_each":
            items_var = self.config.get("items_variable", "")
            items = context.get("variables", {}).get(items_var, [])
            item_var = self.config.get("item_variable", "item")
            for i, item in enumerate(items):
                if i >= max_iterations:
                    break
                context.setdefault("variables", {})[item_var] = item
                context["variables"]["loop_index"] = i
                result = await self._execute_body(i, page, context)
                results.append(result)
                iteration_count += 1

        return {
            "success": True,
            "iterations": iteration_count,
            "results": results,
        }

    async def _execute_body(self, iteration: int, page: Any, context: Dict[str, Any]) -> Dict:
        """执行循环体内的子节点"""
        from ..runner import WorkflowRunner

        sub_nodes = self.config.get("loop_body", self.config.get("sub_nodes", []))
        if not sub_nodes:
            return {"success": True, "iteration": iteration}

        # 用 runner 执行子节点序列
        runner = WorkflowRunner.__new__(WorkflowRunner)
        runner.workflow = {"nodes": sub_nodes, "edges": []}
        runner.context = context
        runner._running = True
        runner._page = page

        iteration_results = []
        for node_config in sub_nodes:
            if not runner._running:
                break
            node = runner._create_node(node_config)
            if node:
                try:
                    result = await node.execute(page, context)
                    iteration_results.append(result)
                except Exception as e:
                    iteration_results.append({"success": False, "error": str(e)})
                    break

        return {"success": True, "iteration": iteration, "node_results": iteration_results}

    def _check_while_condition(self, context: Dict[str, Any]) -> bool:
        """检查 while 条件"""
        cond = self.config.get("while_condition", {})
        var_name = cond.get("variable", "")
        op = cond.get("operator", "eq")
        value = cond.get("value")

        actual = context.get("variables", {}).get(var_name)
        if op == "eq":
            return actual == value
        elif op == "ne":
            return actual != value
        elif op == "gt":
            return float(actual) > float(value)
        elif op == "lt":
            return float(actual) < float(value)
        elif op == "is_not_empty":
            return bool(actual)
        return False
