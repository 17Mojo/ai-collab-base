"""
Pack Executor Core
实现 Pack Workflow 的真实执行逻辑
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StepResult:
    """步骤执行结果"""
    id: str
    type: str
    status: str
    output: Optional[str] = None
    description: str = ""
    duration_ms: int = 0
    branches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionState:
    """执行状态"""
    input: Dict[str, Any]
    output: Optional[str] = None
    steps: List[StepResult] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    current_step_id: Optional[str] = None
    iterations: int = 0


class BranchEvaluator:
    """分支条件评估器"""

    @staticmethod
    def evaluate(branch: Dict[str, Any], execution: ExecutionState) -> Dict[str, Any]:
        """评估分支条件"""
        target_field = branch.get("target_field", "output")
        target_value = BranchEvaluator._get_target_value(target_field, execution)

        condition_type = branch.get("condition_type", "regex_match")
        matched = False

        if condition_type == "regex_match":
            regex_config = branch.get("regex_config", {})
            pattern = regex_config.get("pattern", "")
            flags = regex_config.get("flags", "")

            flag_value = 0
            if "i" in flags:
                flag_value |= re.IGNORECASE
            if "m" in flags:
                flag_value |= re.MULTILINE

            if pattern and target_value:
                match = re.search(pattern, str(target_value), flag_value)
                matched = match is not None

                # 提取捕获组数据
                if matched and regex_config.get("extract_fields"):
                    for group_name, field_name in regex_config["extract_fields"].items():
                        if match and match.groups():
                            execution.extracted_data[field_name] = match.group(1) if match.groups() else ""

        elif condition_type == "contains":
            condition_value = branch.get("condition_value", "")
            matched = condition_value in str(target_value)

        elif condition_type == "equals":
            condition_value = branch.get("condition_value", "")
            matched = str(target_value) == condition_value

        elif condition_type == "exists":
            matched = target_value is not None and str(target_value) != ""

        # 否定条件
        if branch.get("negate", False):
            matched = not matched

        return {
            "matched": matched,
            "target_step": branch.get("target_step") if matched else None
        }

    @staticmethod
    def _get_target_value(target_field: str, execution: ExecutionState) -> Any:
        """获取目标字段值"""
        if target_field == "output":
            return execution.output
        elif target_field == "input":
            return execution.input
        elif target_field == "last_step_output":
            if execution.steps:
                return execution.steps[-1].output
            return None
        else:
            return execution.extracted_data.get(target_field)


class PackExecutor:
    """Pack 执行器"""

    def __init__(self, pack_data: Dict[str, Any]):
        self.pack_data = pack_data
        self.workflow = pack_data.get("workflow", {})
        self.steps = self.workflow.get("steps", [])
        self.step_index = {step.get("id"): i for i, step in enumerate(self.steps)}
        self.max_iterations = len(self.steps) * 3

    def execute(self, input_data: Dict[str, Any]) -> ExecutionState:
        """执行 Pack workflow"""
        execution = ExecutionState(input=input_data)

        current_index = 0
        executed_steps = set()

        while current_index < len(self.steps) and execution.iterations < self.max_iterations:
            step = self.steps[current_index]
            step_id = step.get("id")
            execution.iterations += 1

            # 防止重复执行同一步骤（循环防护）
            if step_id in executed_steps and step_id != self.steps[0].get("id"):
                break
            executed_steps.add(step_id)

            # 执行步骤
            start_time = time.perf_counter()
            result = self._execute_step(step, execution)
            result.duration_ms = int((time.perf_counter() - start_time) * 1000)

            execution.steps.append(result)
            execution.output = result.output
            execution.current_step_id = step_id

            # 评估分支
            branches = step.get("branches", [])
            if branches:
                for branch in branches:
                    eval_result = BranchEvaluator.evaluate(branch, execution)
                    if eval_result["matched"]:
                        target_step = eval_result["target_step"]
                        if target_step == "end":
                            current_index = len(self.steps)
                            break
                        if target_step in self.step_index:
                            current_index = self.step_index[target_step]
                        break
                continue

            # 检查显式 next_step
            next_step = step.get("next_step")
            if next_step:
                if next_step in self.step_index:
                    current_index = self.step_index[next_step]
                else:
                    current_index += 1
            else:
                current_index += 1

        return execution

    def _execute_step(self, step: Dict[str, Any], execution: ExecutionState) -> StepResult:
        """执行单个步骤"""
        step_id = step.get("id")
        step_type = step.get("type", "local")
        description = step.get("description", "")
        branches = step.get("branches", [])

        # 模拟执行输出（真实执行需要连接 AI 平台）
        output = None

        if step_type == "local":
            # 本地处理
            output = execution.input.get("user_input", "local_processed")

        elif step_type in ["analysis", "generation"]:
            # AI 分析/生成
            output = f"AI_{step_type}: {execution.input.get('user_input', 'processed')}"

        elif step_type == "validation":
            # 验证
            output = "validation_passed"

        elif step_type == "fusion":
            # 融合
            output = "fusion_completed"

        return StepResult(
            id=step_id,
            type=step_type,
            status="completed",
            output=output,
            description=description,
            branches=branches
        )


def execute_pack(pack_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行 Pack 并返回结果"""
    executor = PackExecutor(pack_data)
    execution = executor.execute(input_data)

    return {
        "steps": [
            {
                "id": s.id,
                "type": s.type,
                "status": s.status,
                "output": s.output,
                "description": s.description,
                "branches": s.branches
            }
            for s in execution.steps
        ],
        "iterations": execution.iterations,
        "extracted_data": execution.extracted_data,
        "current_step_id": execution.current_step_id,
        "branch_logic_enabled": any(s.get("branches") for s in executor.steps)
    }
