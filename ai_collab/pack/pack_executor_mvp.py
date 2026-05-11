# Prompt Pack MVP - 核心执行引擎
# src/ai_collab/pack/pack_executor_mvp.py

"""
Prompt Pack MVP - 最小可用版本
专注于核心功能：加载Pack → 执行工作流 → 生成内容

设计原则：
1. 简单直接 - 不过度设计
2. 立即可用 - 先跑起来
3. 逐步完善 - 边用边改
"""

import json
from datetime import datetime
from typing import Any, Dict


class PackExecutorMVP:
    """Pack执行器 - MVP版本"""

    def __init__(self, pack_data: Dict[str, Any]):
        """
        初始化执行器

        Args:
            pack_data: Pack配置数据（字典格式）
        """
        self.pack = pack_data
        self.metadata = pack_data.get("metadata", {})
        self.workflow = pack_data.get("workflow", {})
        self.context = {}  # 执行上下文
        self.results = []  # 执行结果

    def execute(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Pack工作流

        Args:
            user_input: 用户输入数据

        Returns:
            执行结果
        """
        print(f"\n{'='*60}")
        print(f"执行 Pack: {self.metadata.get('pack_name', 'Unknown')}")
        print(f"版本: {self.metadata.get('version', 'N/A')}")
        print(f"{'='*60}\n")

        # 1. 初始化上下文
        self.context = {
            "user_input": user_input,
            "start_time": datetime.now().isoformat(),
            "current_step": 0,
        }

        # 2. 执行工作流步骤
        steps = self.workflow.get("steps", [])
        for i, step in enumerate(steps):
            print(f"\n[步骤 {i+1}/{len(steps)}] {step.get('name', 'Unknown')}")
            print(f"  类型: {step.get('type', 'Unknown')}")

            result = self._execute_step(step)
            self.results.append(result)

            if result.get("status") == "error":
                print(f"  ❌ 执行失败: {result.get('error')}")
                break
            else:
                print("  ✅ 执行成功")

        # 3. 生成最终结果
        final_result = self._generate_final_result()

        print(f"\n{'='*60}")
        print("执行完成")
        print(f"{'='*60}\n")

        return final_result

    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step: 步骤配置

        Returns:
            步骤执行结果
        """
        step_type = step.get("type", "unknown")

        # MVP版本：实现核心步骤类型
        if step_type == "LOCAL":
            return self._execute_local(step)
        elif step_type == "ANALYSIS":
            return self._execute_analysis(step)
        elif step_type == "GENERATION":
            return self._execute_generation(step)
        elif step_type == "VALIDATION":
            return self._execute_validation(step)
        elif step_type == "FUSION":
            return self._execute_fusion(step)
        elif step_type == "TRACKING":
            return self._execute_tracking(step)
        else:
            return {"status": "skipped", "message": f"步骤类型 {step_type} 暂不支持"}

    def _execute_local(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行本地处理步骤"""
        print("  📝 本地处理...")

        # 获取输入
        inputs = step.get("inputs", [])
        for inp in inputs:
            key = inp.get("key")
            source = inp.get("source", "user_input")

            if source == "user_input":
                value = self.context["user_input"].get(key)
                self.context[key] = value
                print(f"     - {key}: {value}")

        return {
            "status": "success",
            "step_type": "LOCAL",
            "outputs": {
                k: v for k, v in self.context.items() if k in [i.get("key") for i in inputs]
            },
        }

    def _execute_analysis(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析步骤"""
        print("  🔍 分析内容...")

        # MVP版本：简单分析
        analysis_result = {"keywords": [], "sentiment": "neutral", "category": "general"}

        # 从上下文获取内容
        content = self.context.get("content", "")
        if content:
            # 简单关键词提取（MVP版本）
            words = content.split()
            analysis_result["keywords"] = words[:5]  # 取前5个词
            analysis_result["word_count"] = len(words)
            print(f"     - 关键词: {analysis_result['keywords'][:3]}")
            print(f"     - 字数: {analysis_result['word_count']}")

        self.context["analysis_result"] = analysis_result

        return {"status": "success", "step_type": "ANALYSIS", "outputs": analysis_result}

    def _execute_generation(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行生成步骤"""
        print("  ✨ 生成内容...")

        # MVP版本：基于模板生成
        template = step.get("template", "默认模板")
        _ = step.get("params", {})  # 保留参数获取以维持原有接口

        # 简单模板替换
        generated_content = template
        for key, value in self.context.items():
            if isinstance(value, str):
                generated_content = generated_content.replace(f"{{{key}}}", value)

        # 如果没有模板，生成默认内容
        if not template or template == "默认模板":
            generated_content = f"""
# 生成内容

基于输入: {self.context.get('topic', '未知主题')}

内容: {self.context.get('content', '无内容')}

关键词: {self.context.get('analysis_result', {}).get('keywords', [])}

---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        self.context["generated_content"] = generated_content
        print(f"     - 生成字数: {len(generated_content)}")

        return {
            "status": "success",
            "step_type": "GENERATION",
            "outputs": {"content": generated_content, "length": len(generated_content)},
        }

    def _execute_validation(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行验证步骤"""
        print("  ✔️ 验证内容...")

        # MVP版本：简单验证
        generated_content = self.context.get("generated_content", "")

        validation_result = {"is_valid": True, "issues": [], "score": 0.8}  # 默认分数

        # 检查长度
        if len(generated_content) < 50:
            validation_result["issues"].append("内容过短")
            validation_result["score"] -= 0.2

        # 检查关键词
        keywords = self.context.get("analysis_result", {}).get("keywords", [])
        if keywords:
            keyword_count = sum(1 for kw in keywords if kw in generated_content)
            if keyword_count < len(keywords) * 0.5:
                validation_result["issues"].append("关键词覆盖率低")
                validation_result["score"] -= 0.1

        if validation_result["issues"]:
            validation_result["is_valid"] = False
            print(f"     - ⚠️ 发现问题: {validation_result['issues']}")
        else:
            print("     - ✅ 验证通过")

        print(f"     - 质量分数: {validation_result['score']:.2f}")

        self.context["validation_result"] = validation_result

        return {"status": "success", "step_type": "VALIDATION", "outputs": validation_result}

    def _generate_final_result(self) -> Dict[str, Any]:
        """生成最终结果"""
        return {
            "pack_name": self.metadata.get("pack_name", "Unknown"),
            "version": self.metadata.get("version", "N/A"),
            "execution_time": datetime.now().isoformat(),
            "status": "completed",
            "results": self.results,
            "final_content": self.context.get("generated_content", ""),
            "validation": self.context.get("validation_result", {}),
            "context": self.context,
        }

    def _execute_fusion(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行融合步骤 - 合并多个生成结果"""
        print("  🔀 融合内容...")

        fusion_strategy = step.get("strategy", "concat")
        generated_contents = [self.context.get("generated_content", "")]

        if fusion_strategy == "concat":
            fused_content = "\n\n---\n\n".join(generated_contents)
        elif fusion_strategy == "best":
            fused_content = max(generated_contents, key=len)
        else:
            fused_content = generated_contents[0] if generated_contents else ""

        self.context["fused_content"] = fused_content
        print(f"     - 融合策略: {fusion_strategy}")
        print(f"     - 最终长度: {len(fused_content)}")

        return {
            "status": "success",
            "step_type": "FUSION",
            "outputs": {"content": fused_content, "strategy": fusion_strategy},
        }

    def _execute_tracking(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行追踪步骤 - 记录和追踪生成内容"""
        print("  📊 追踪内容...")

        tracking_data = {
            "pack_name": self.metadata.get("pack_name", "Unknown"),
            "version": self.metadata.get("version", "N/A"),
            "execution_id": f"EXEC-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "content_length": len(self.context.get("generated_content", "")),
            "validation_score": self.context.get("validation_result", {}).get("score", 0),
        }

        tracking_file = step.get("output_file", "tracking_history.json")
        try:
            try:
                with open(tracking_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (OSError, json.JSONDecodeError):
                history = {"tracking_records": []}

            history["tracking_records"].append(tracking_data)

            with open(tracking_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            print(f"     - 追踪ID: {tracking_data['execution_id']}")
            print("     - 记录已保存")

        except Exception as e:
            print(f"     - ⚠️ 保存失败: {e}")

        self.context["tracking_data"] = tracking_data

        return {"status": "success", "step_type": "TRACKING", "outputs": tracking_data}


# ==================== 便捷函数 ====================


def load_pack_from_file(pack_file: str) -> Dict[str, Any]:
    """从文件加载Pack"""
    with open(pack_file, "r", encoding="utf-8") as f:
        return json.load(f)


def execute_pack(pack_data: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
    """执行Pack"""
    executor = PackExecutorMVP(pack_data)
    return executor.execute(user_input)


# ==================== MVP测试 ====================

if __name__ == "__main__":
    print("=== Prompt Pack MVP 测试 ===\n")

    # 创建一个简单的测试Pack
    test_pack = {
        "metadata": {"pack_name": "简单内容生成器", "version": "1.0.0-mvp", "type": "content_generation"},
        "workflow": {
            "steps": [
                {
                    "name": "收集输入",
                    "type": "LOCAL",
                    "inputs": [
                        {"key": "topic", "source": "user_input"},
                        {"key": "content", "source": "user_input"},
                    ],
                },
                {"name": "分析内容", "type": "ANALYSIS"},
                {
                    "name": "生成内容",
                    "type": "GENERATION",
                    "template": "主题: {topic}\n\n内容: {content}\n\n关键词: {keywords}",
                },
                {"name": "验证质量", "type": "VALIDATION"},
            ]
        },
    }

    # 测试输入
    test_input = {"topic": "AI协作系统", "content": "这是一个创新的AI协作系统，支持Claude Code和Copilot双AI协作开发"}

    # 执行
    result = execute_pack(test_pack, test_input)

    # 打印结果
    print("\n=== 执行结果 ===")
    print(f"Pack: {result['pack_name']}")
    print(f"状态: {result['status']}")
    print(f"\n生成内容:\n{result['final_content']}")
    print(f"\n验证结果: {result['validation']}")

    def _execute_fusion(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行融合步骤 - 合并多个生成结果"""
        print("  🔀 融合内容...")

        # MVP版本：简单融合策略
        fusion_strategy = step.get("strategy", "concat")

        # 获取所有生成的内容
        generated_contents = []
        for key, value in self.context.items():
            if key.startswith("generated_content"):
                generated_contents.append(value)

        # 如果没有多个内容，使用当前生成内容
        if not generated_contents:
            generated_contents = [self.context.get("generated_content", "")]

        # 融合策略
        if fusion_strategy == "concat":
            # 简单拼接
            fused_content = "\n\n---\n\n".join(generated_contents)
        elif fusion_strategy == "best":
            # 选择最长的（MVP简化版）
            fused_content = max(generated_contents, key=len)
        elif fusion_strategy == "merge":
            # 合并去重（MVP简化版）
            all_lines = []
            for content in generated_contents:
                all_lines.extend(content.split("\n"))
            # 简单去重
            unique_lines = list(dict.fromkeys(all_lines))
            fused_content = "\n".join(unique_lines)
        else:
            fused_content = generated_contents[0] if generated_contents else ""

        self.context["fused_content"] = fused_content
        print(f"     - 融合策略: {fusion_strategy}")
        print(f"     - 融合内容数: {len(generated_contents)}")
        print(f"     - 最终长度: {len(fused_content)}")

        return {
            "status": "success",
            "step_type": "FUSION",
            "outputs": {
                "content": fused_content,
                "strategy": fusion_strategy,
                "source_count": len(generated_contents),
            },
        }

    def _execute_tracking(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行追踪步骤 - 记录和追踪生成内容"""
        print("  📊 追踪内容...")

        # MVP版本：简单追踪记录
        tracking_data = {
            "pack_name": self.metadata.get("pack_name", "Unknown"),
            "version": self.metadata.get("version", "N/A"),
            "execution_id": f"EXEC-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "user_input": self.context.get("user_input", {}),
            "content_length": len(self.context.get("generated_content", "")),
            "validation_score": self.context.get("validation_result", {}).get("score", 0),
            "steps_completed": len(self.results),
        }

        # 保存追踪记录
        tracking_file = step.get("output_file", "tracking_history.json")
        try:
            # 加载现有记录
            try:
                with open(tracking_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (OSError, json.JSONDecodeError):
                history = {"tracking_records": []}

            # 添加新记录
            history["tracking_records"].append(tracking_data)

            # 保存
            with open(tracking_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            print(f"     - 追踪ID: {tracking_data['execution_id']}")
            print(f"     - 记录已保存: {tracking_file}")
            print(f"     - 历史记录数: {len(history['tracking_records'])}")

        except Exception as e:
            print(f"     - ⚠️ 保存失败: {e}")

        self.context["tracking_data"] = tracking_data

        return {"status": "success", "step_type": "TRACKING", "outputs": tracking_data}
