"""
Skills 到 Prompt Pack v2.0 自动转换工具

支持两种转换模式:
1. 直接映射模式: 简单的结构转换
2. 增强重构模式: 添加优化建议和增强功能
"""

import ast
import importlib.util
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class SkillAnalyzer:
    """分析 Python Skill 类"""

    def __init__(self, skill_path: str):
        """
        初始化 Skill 分析器

        Args:
            skill_path: Python Skill 文件路径
        """
        self.skill_path = Path(skill_path)
        self.skill_class = None
        self.skill_module = None
        self._analyze()

    def _analyze(self):
        """加载并分析 Skill"""
        spec = importlib.util.spec_from_file_location("skill_module", self.skill_path)
        self.skill_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.skill_module)

        # 查找主要的 Skill 类
        for name, obj in inspect.getmembers(self.skill_module):
            if inspect.isclass(obj) and name.endswith("Skill"):
                self.skill_class = obj
                break

    def get_parameters(self, method_name: str = "__init__") -> List[Dict[str, Any]]:
        """
        获取方法参数

        Args:
            method_name: 方法名称

        Returns:
            参数列表
        """
        if not self.skill_class:
            return []

        method = getattr(self.skill_class, method_name, None)
        if not method:
            return []

        sig = inspect.signature(method)
        params = []

        for name, param in sig.parameters.items():
            if name == "self":
                continue

            param_info = {
                "name": name,
                "type": str(param.annotation)
                if param.annotation != inspect.Parameter.empty
                else "Any",
                "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
            }
            params.append(param_info)

        return params

    def get_methods(self) -> List[Dict[str, Any]]:
        """获取所有公开方法"""
        if not self.skill_class:
            return []

        methods = []
        for name, method in inspect.getmembers(self.skill_class, predicate=inspect.isfunction):
            if not name.startswith("_"):
                sig = inspect.signature(method)
                methods.append(
                    {
                        "name": name,
                        "docstring": inspect.getdoc(method) or "",
                        "parameters": [
                            {
                                "name": p,
                                "type": str(sig.parameters[p].annotation),
                                "required": sig.parameters[p].default == inspect.Parameter.empty,
                            }
                            for p in sig.parameters
                            if p != "self"
                        ],
                        "returns": str(sig.return_annotation)
                        if sig.return_annotation != inspect.Signature.empty
                        else "Any",
                    }
                )

        return methods

    def get_docstring(self) -> str:
        """获取类的文档字符串"""
        if not self.skill_class:
            return ""
        return inspect.getdoc(self.skill_class) or ""

    def get_dependencies(self) -> List[str]:
        """获取导入的依赖"""
        with open(self.skill_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        # 过滤标准库和本地模块
        third_party = []
        for imp in imports:
            parts = imp.split(".")
            if parts[0] not in {
                "typing",
                "datetime",
                "pathlib",
                "json",
                "sys",
                "os",
                "re",
                "collections",
                "itertools",
                "functools",
                "asyncio",
                "inspect",
                "ast",
                "dataclasses",
                "enum",
            }:
                if not parts[0].startswith("ai_collab"):
                    third_party.append(imp)

        return third_party


class SkillToPackConverter:
    """Skill 到 Prompt Pack 转换器"""

    def __init__(self, skill_path: str, mode: str = "enhanced"):
        """
        初始化转换器

        Args:
            skill_path: Skill 文件路径
            mode: 转换模式 (direct, enhanced)
        """
        self.analyzer = SkillAnalyzer(skill_path)
        self.mode = mode
        self.skill_name = (
            self.analyzer.skill_class.__name__ if self.analyzer.skill_class else "Unknown"
        )

    def convert(self) -> Dict[str, Any]:
        """
        执行转换

        Returns:
            Prompt Pack V2 字典
        """
        if self.mode == "direct":
            return self._convert_direct()
        elif self.mode == "enhanced":
            return self._convert_enhanced()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _convert_direct(self) -> Dict[str, Any]:
        """直接映射转换模式"""
        # 生成 metadata
        # skill_class 保留接口兼容性,当前直接通过 analyzer 访问数据
        _ = self.analyzer.skill_class  # 保留此行以维持原有接口逻辑

        metadata = {
            "pack_id": f"converted-{self.skill_name.lower()}",
            "pack_name": f"{self.skill_name} Pack",
            "version": "1.0.0",
            "type": "custom",
            "description": self.analyzer.get_docstring() or f"Converted from {self.skill_name}",
            "designer": "Skills Converter",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "category": "Conversions",
            "tags": ["skills", "converted", self.skill_name],
            "language": "zh",
            "estimated_efficiency_gain": "60%",
        }

        # 生成 domain
        domain = {
            "primary_domain": "技能转换",
            "secondary_domains": ["自动化", "工具"],
            "target_platforms": ["generic"],
            "target_audience": "开发者",
            "brand_tone": "专业、简洁",
            "compliance_rules": [],
        }

        # 生成 workflow
        methods = self.analyzer.get_methods()
        steps = []

        for i, method in enumerate(methods):
            step = {
                "id": f"step_{method['name']}",
                "name": f"{method['name']}",
                "type": "local" if method["name"] == "__init__" else "analysis",
                "description": method.get("docstring", ""),
                "input_fields": [p["name"] for p in method.get("parameters", [])],
                "output_field": f"{method['name']}_output",
                "parallel": False,
                "estimated_time": 5,
            }
            steps.append(step)

        workflow = {"steps": steps, "max_parallel_steps": 1, "allow_parallel": False}

        # 生成 quality_metrics
        quality_metrics = {
            "metrics": {
                "correctness": {
                    "description": "正确性 - 输出结果是否符合预期",
                    "check_method": "compare_with_expected",
                    "weight": 0.4,
                    "min_threshold": 0.8,
                },
                "performance": {
                    "description": "性能 - 执行速度",
                    "check_method": "measure_execution_time",
                    "weight": 0.3,
                    "min_threshold": 0.0,
                },
                "completeness": {
                    "description": "完整性 - 是否包含所有必要字段",
                    "check_method": "check_output_fields",
                    "weight": 0.3,
                    "min_threshold": 0.8,
                },
            },
            "normalization_method": "linear",
            "validation_tolerance": 0.01,
        }

        # 生成剩余字段
        example_library = {"good_examples": [], "bad_examples": [], "few_shot_template": ""}

        generation_params = {
            "diversity_enhancement": True,
            "output_versions": 1,
            "diversity_dimensions": ["format", "style"],
            "confidence_display": True,
            "critical_facts_only": True,
            "temperature": 0.7,
            "output_format": "json",
            "require_code_blocks": False,
        }

        optimization = {
            "enabled": True,
            "strategy": "feedback_driven",
            "auto_refine_threshold": 60.0,
            "periodic_review_days": 30,
            "allowed_actions": [
                "auto_refine_low_scoring",
                "periodic_template_optimization",
                "example_library_update",
            ],
        }

        performance_tracking = {
            "enabled": True,
            "metrics": ["execution_time", "success_rate"],
            "retention_days": 90,
        }

        collaboration = {
            "shared_with": [],
            "edit_permission": [],
            "use_permission": [],
            "is_public": False,
        }

        system_prompt = f"""你是一个 {self.skill_name} Pack，负责执行转换后的 Skill 功能。

使用场景:
{self.analyzer.get_docstring()}

工作流程:
"""

        for step in steps:
            system_prompt += f"\n步骤 {step['id']}: {step['name']}"
            if step.get("description"):
                system_prompt += f"\n  {step['description']}"

        quality_validation_rules = """质量验证规则:
1. 输出必须包含所有必需字段
2. 数据类型必须匹配模式定义
3. 必须遵循指定格式
4. 必须通过质量阈值检查
"""

        return {
            "metadata": metadata,
            "domain": domain,
            "workflow": workflow,
            "quality_metrics": quality_metrics,
            "example_library": example_library,
            "generation_params": generation_params,
            "optimization": optimization,
            "performance_tracking": performance_tracking,
            "collaboration": collaboration,
            "system_prompt": system_prompt,
            "quality_validation_rules": quality_validation_rules,
        }

    def _convert_enhanced(self) -> Dict[str, Any]:
        """增强重构转换模式"""
        base_pack = self._convert_direct()

        # 添加 enhanced 模式的改进
        base_pack["metadata"]["version"] = "2.0.0"
        base_pack["metadata"]["tags"].append("enhanced")
        base_pack["metadata"]["estimated_efficiency_gain"] = "80%"

        # 改进 workflow
        methods = self.analyzer.get_methods()
        enhanced_steps = []

        for i, method in enumerate(methods):
            enhanced_step = {
                "id": f"step_{method['name']}",
                "name": f"{method['name']}",
                "type": self._infer_step_type(method["name"]),
                "description": method.get("docstring", ""),
                "input_fields": [p["name"] for p in method.get("parameters", [])],
                "output_field": f"{method['name']}_output",
                "parallel": False,
                "cross_review": self._needs_cross_review(method["name"]),
                "validation_criteria": self._generate_validation_criteria(method),
                "estimated_time": self._estimate_time(method["name"]),
                "config": {"source_skill": self.skill_name, "source_method": method["name"]},
            }
            enhanced_steps.append(enhanced_step)

        base_pack["workflow"]["steps"] = enhanced_steps
        base_pack["workflow"]["allow_parallel"] = True
        base_pack["workflow"]["max_parallel_steps"] = 3

        # 增强质量指标
        base_pack["quality_metrics"]["metrics"]["correctness"]["weight"] = 0.35
        base_pack["quality_metrics"]["metrics"]["performance"]["weight"] = 0.25
        base_pack["quality_metrics"]["metrics"]["completeness"]["weight"] = 0.25
        base_pack["quality_metrics"]["metrics"]["maintainability"] = {
            "description": "可维护性 - 代码/输出的可读性和可维护性",
            "check_method": "code_quality_analysis",
            "weight": 0.15,
            "min_threshold": 0.7,
        }

        # 增强 system prompt
        base_pack[
            "system_prompt"
        ] = f"""你是 {self.skill_name} Pack (Enhanced 版本)，提供增强的功能和优化。

核心能力:
- 智能参数推断和验证
- 自动重试和错误恢复
- 性能优化和缓存
- 交叉验证和质量保证

工作流程:
"""

        for step in enhanced_steps:
            base_pack["system_prompt"] += f"\n{step['type'].upper()}: {step['id']} - {step['name']}"
            if step.get("description"):
                base_pack["system_prompt"] += f"\n  {step['description']}"

        base_pack[
            "system_prompt"
        ] += """

增强规则:
1. 优先使用缓存结果
2. 失败时自动重试（最多3次）
3. 对关键步骤进行交叉验证
4. 输出标准化格式
5. 提供详细的错误信息
"""

        return base_pack

    def _infer_step_type(self, method_name: str) -> str:
        """推断步骤类型"""
        method_name_lower = method_name.lower()

        if any(x in method_name_lower for x in ["create", "generate", "build"]):
            return "generation"
        elif any(x in method_name_lower for x in ["validate", "check", "verify"]):
            return "validation"
        elif any(x in method_name_lower for x in ["analyze", "process", "parse"]):
            return "analysis"
        elif method_name_lower in ["init", "setup", "configure"]:
            return "local"
        else:
            return "local"

    def _needs_cross_review(self, method_name: str) -> bool:
        """判断是否需要交叉验证"""
        method_name_lower = method_name.lower()
        return any(x in method_name_lower for x in ["generate", "create", "validate", "check"])

    def _generate_validation_criteria(self, method: Dict[str, Any]) -> List[str]:
        """生成验证标准"""
        criteria = []
        params = method.get("parameters", [])

        for param in params:
            criteria.append(f"{param['name']} 在范围内")

        criteria.append("输出格式正确")
        criteria.append("无运行时错误")

        return criteria

    def _estimate_time(self, method_name: str) -> int:
        """估算执行时间（秒）"""
        method_name_lower = method_name.lower()

        if any(x in method_name_lower for x in ["generate", "create", "process"]):
            return 10
        elif any(x in method_name_lower for x in ["validate", "check"]):
            return 3
        else:
            return 5


class BatchConverter:
    """批量转换器"""

    def __init__(self, skills_dir: str, output_dir: str, mode: str = "enhanced"):
        """
        初始化批量转换器

        Args:
            skills_dir: Skills 目录
            output_dir: 输出目录
            mode: 转换模式
        """
        self.skills_dir = Path(skills_dir)
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_all(self, pattern: str = "*skill.py") -> Dict[str, Any]:
        """
        转换所有匹配的 Skills

        Args:
            pattern: 文件匹配模式

        Returns:
            转换结果汇总
        """
        results = {"total": 0, "success": 0, "failed": 0, "errors": [], "converted": []}

        for skill_file in self.skills_dir.rglob(pattern):
            results["total"] += 1

            try:
                converter = SkillToPackConverter(str(skill_file), mode=self.mode)
                pack_data = converter.convert()

                # 保存转换结果
                output_file = self.output_dir / f"{skill_file.stem}_pack.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(pack_data, f, indent=2, ensure_ascii=False)

                results["success"] += 1
                results["converted"].append(
                    {
                        "skill": str(skill_file),
                        "pack": str(output_file),
                        "pack_name": pack_data["metadata"]["pack_name"],
                    }
                )

                print(f"✅ 转换成功: {skill_file.name} → {output_file.name}")

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"skill": str(skill_file), "error": str(e)})
                print(f"❌ 转换失败: {skill_file.name} - {e}")

        return results


# ==================== CLI 接口 ====================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Skills 到 Prompt Pack v2.0 转换工具")
    parser.add_argument("input", help="输入: Skill 文件或目录")
    parser.add_argument(
        "-o", "--output", default="converted_packs", help="输出目录 (默认: converted_packs)"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["direct", "enhanced"],
        default="enhanced",
        help="转换模式 (默认: enhanced)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"错误: 路径不存在: {input_path}")
        sys.exit(1)

    if input_path.is_file():
        # 单个文件转换
        try:
            converter = SkillToPackConverter(str(input_path), mode=args.mode)
            pack_data = converter.convert()

            output_file = Path(args.output) / f"{input_path.stem}_pack.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(pack_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 转换完成: {input_path.name} → {output_file.name}")
            print(f"📦 Pack 名称: {pack_data['metadata']['pack_name']}")
            print(f"🔌 步骤数: {len(pack_data['workflow']['steps'])}")
            print(f"🔍 质量指标: {len(pack_data['quality_metrics']['metrics'])}")

        except Exception as e:
            print(f"❌ 转换失败: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)

    else:
        # 批量转换
        batch = BatchConverter(str(input_path), args.output, mode=args.mode)
        results = batch.convert_all()

        print(f"\n{'='*60}")
        print("转换完成")
        print(f"{'='*60}")
        print(f"总计: {results['total']}")
        print(f"成功: {results['success']}")
        print(f"失败: {results['failed']}")

        if results["failed"] > 0 and args.verbose:
            print("\n错误详情:")
            for error in results["errors"]:
                print(f"  - {error['skill']}: {error['error']}")


if __name__ == "__main__":
    main()
