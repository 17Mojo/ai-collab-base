# 场景识别引擎
# src/ai_collab/context/scenario.py

"""
场景识别引擎

根据项目文件结构和用户行为识别当前使用场景
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .schema import ScenarioType


@dataclass
class ScenarioEvidence:
    """场景证据"""

    evidence_type: str  # 证据类型 (directory/file/content/pattern)
    value: str  # 证据值
    weight: float  # 权重 (0-1)
    description: str  # 描述


@dataclass
class ScenarioScore:
    """场景评分"""

    scenario: ScenarioType
    score: float  # 总分 (0-1)
    evidence: List[ScenarioEvidence] = field(default_factory=list)  # 证据列表


class ScenarioDetector:
    """场景检测器"""

    # 场景定义和识别规则
    SCENARIO_RULES = {
        ScenarioType.CODING: {
            "directories": ["src", "app", "lib", "services", "controllers", "models"],
            "files": ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs", "*.cpp"],
            "patterns": [
                "class \\w+",
                "def \\w+",
                "function \\w+",
                "import ",
                "require(",
                "export ",
            ],
            "weight": 1.0,
        },
        ScenarioType.RESEARCH: {
            "directories": ["docs", "research", "references", "literature", "papers"],
            "files": ["*.md", "*.pdf", "*.doc", "*.docx", "*.bib", "*.tex"],
            "patterns": ["# ", "## ", "### ", "### ", "[1]", "[2]", "@article"],
            "weight": 1.0,
        },
        ScenarioType.WRITING: {
            "directories": ["content", "posts", "articles", "blog", "drafts"],
            "files": ["*.md", "*.txt", "*.rst", "*.adoc"],
            "patterns": ["title:", "---\n", "date:", "tags:"],
            "weight": 1.0,
        },
        ScenarioType.DEBUGGING: {
            "directories": ["logs", "tests", "debug", "trace"],
            "files": ["*test*.py", "*spec*.js", "*.log", "error.txt"],
            "patterns": [
                "print(",
                "console.log(",
                "assert ",
                "raise Error",
                "throw new Error",
                "debugger",
            ],
            "weight": 0.9,
        },
        ScenarioType.DESIGN: {
            "directories": ["design", "assets", "images", "styles", "ui"],
            "files": ["*.fig", "*.sketch", "*.psd", "*.css", "*.scss", "*.less"],
            "patterns": ["width:", "height:", "color:", "background:", "font-size:"],
            "weight": 0.95,
        },
        ScenarioType.PROJECT_PLANNING: {
            "directories": ["plans", "roadmaps", "tasks", "milestones"],
            "files": ["*.md", "todo.txt", "plan.md", "roadmap.md"],
            "patterns": ["TODO", "FIXME", "Sprint", "Milestone", "Timeline"],
            "weight": 0.85,
        },
        ScenarioType.DOCUMENTATION: {
            "directories": ["doc", "docs", "api-doc", "user-guide"],
            "files": ["*.md", "README*", "CHANGELOG*", "LICENSE*"],
            "patterns": ["API Reference", "Usage", "Installation", "Getting Started"],
            "weight": 0.9,
        },
        ScenarioType.UNKNOWN: {
            "directories": [],
            "files": [],
            "patterns": [],
            "weight": 0.0,
        },
    }

    def __init__(self, root_dir: Optional[str] = None):
        """
        初始化场景检测器

        Args:
            root_dir: 项目根目录 (默认为当前工作目录)
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

    def detect(
        self, active_files: Optional[List[str]] = None, include_content: bool = False
    ) -> ScenarioScore:
        """
        检测当前场景

        Args:
            active_files: 当前活跃的文件列表
            include_content: 是否包含内容分析

        Returns:
            场景评分结果
        """
        # 计算每种场景的分数
        scores = []

        for scenario, rules in self.SCENARIO_RULES.items():
            score = self._calculate_scenario_score(scenario, rules, active_files, include_content)
            scores.append(score)

        # 返回最高分的场景
        return max(scores, key=lambda s: s.score)

    def detect_all(
        self, active_files: Optional[List[str]] = None, include_content: bool = False
    ) -> List[ScenarioScore]:
        """
        检测所有场景的分数

        Args:
            active_files: 当前活跃的文件列表
            include_content: 是否包含内容分析

        Returns:
            所有场景的评分结果列表 (按分数降序)
        """
        scores = []

        for scenario, rules in self.SCENARIO_RULES.items():
            score = self._calculate_scenario_score(scenario, rules, active_files, include_content)
            scores.append(score)

        return sorted(scores, key=lambda s: s.score, reverse=True)

    def _calculate_scenario_score(
        self,
        scenario: ScenarioType,
        rules: Dict,
        active_files: Optional[List[str]],
        include_content: bool,
    ) -> ScenarioScore:
        """
        计算场景分数

        Args:
            scenario: 场景类型
            rules: 场景规则
            active_files: 活跃文件列表
            include_content: 是否包含内容分析

        Returns:
            场景评分
        """
        score = ScenarioScore(scenario=scenario, score=0.0)
        evidence_list: List[ScenarioEvidence] = []

        # 1. 目录分析 (30%)
        dir_score = self._analyze_directories(scenario, rules, evidence_list)
        score.score += dir_score * 0.3

        # 2. 文件分析 (30%)
        file_score = self._analyze_files(scenario, rules, active_files, evidence_list)
        score.score += file_score * 0.3

        # 3. 内容分析 (40%)
        if include_content:
            content_score = self._analyze_content(scenario, rules, active_files, evidence_list)
            score.score += content_score * 0.4
        else:
            # 如果不分析内容，使用模式匹配替代
            pattern_score = self._analyze_patterns(scenario, rules, active_files, evidence_list)
            score.score += pattern_score * 0.4

        # 应用场景权重
        score.score *= rules.get("weight", 1.0)

        # 限制在 0-1 范围
        score.score = min(1.0, max(0.0, score.score))

        score.evidence = evidence_list

        return score

    def _analyze_directories(
        self, scenario: ScenarioType, rules: Dict, evidence_list: List[ScenarioEvidence]
    ) -> float:
        """分析目录结构"""
        target_dirs = rules.get("directories", [])
        if not target_dirs:
            return 0.0

        found_dirs = []
        for dir_name in target_dirs:
            if (self.root_dir / dir_name).exists():
                found_dirs.append(dir_name)
                evidence_list.append(
                    ScenarioEvidence(
                        evidence_type="directory",
                        value=f"{dir_name}/",
                        weight=0.5 / len(target_dirs),
                        description=f"发现编码目录 {dir_name}",
                    )
                )

        if found_dirs:
            return 1.0
        return 0.0

    def _analyze_files(
        self,
        scenario: ScenarioType,
        rules: Dict,
        active_files: Optional[List[str]],
        evidence_list: List[ScenarioEvidence],
    ) -> float:
        """分析文件"""
        file_patterns = rules.get("files", [])
        if not file_patterns:
            return 0.0

        if active_files:
            # 分析活跃文件
            matched_files = []
            for file_path in active_files:
                file_name = os.path.basename(file_path)
                for pattern in file_patterns:
                    if self._match_pattern(file_name, pattern):
                        matched_files.append(file_path)
                        evidence_list.append(
                            ScenarioEvidence(
                                evidence_type="file",
                                value=file_path,
                                weight=0.3 / max(1, len(active_files)),
                                description=f"活跃文件匹配模式 {pattern}",
                            )
                        )
                        break

            if matched_files:
                return min(1.0, len(matched_files) / max(1, len(active_files)))

        # 分析项目中的文件分布
        matched_count = 0
        total_count = 0

        for pattern in file_patterns:
            matches = list(self.root_dir.rglob(pattern.lstrip("*")))
            matched_count += len(matches)

        # 获取相关文件总数
        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file():
                total_count += 1

        if total_count > 0:
            return min(1.0, matched_count / total_count)

        return 0.0

    def _analyze_content(
        self,
        scenario: ScenarioType,
        rules: Dict,
        active_files: Optional[List[str]],
        evidence_list: List[ScenarioEvidence],
    ) -> float:
        """分析文件内容"""
        patterns = rules.get("patterns", [])
        if not patterns or not active_files:
            return 0.0

        total_matches = 0
        total_files = 0

        for file_path in active_files:
            full_path = self.root_dir / file_path
            if not full_path.exists() or not full_path.is_file():
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    file_matches = 0
                    for pattern in patterns:
                        import re

                        if re.search(pattern, content, re.IGNORECASE):
                            file_matches += 1
                            total_matches += 1

                    if file_matches > 0:
                        evidence_list.append(
                            ScenarioEvidence(
                                evidence_type="content",
                                value=file_path,
                                weight=min(1.0, file_matches / len(patterns))
                                / max(1, len(active_files)),
                                description=f"文件内容匹配 {file_matches}/{len(patterns)} 个模式",
                            )
                        )

                total_files += 1
            except Exception:
                continue

        if total_files > 0:
            return min(1.0, total_matches / (total_files * len(patterns)))

        return 0.0

    def _analyze_patterns(
        self,
        scenario: ScenarioType,
        rules: Dict,
        active_files: Optional[List[str]],
        evidence_list: List[ScenarioEvidence],
    ) -> float:
        """仅基于文件名模式分析 (不读取内容)"""
        patterns = rules.get("patterns", [])
        if not patterns or not active_files:
            return 0.0

        matched_files = 0
        for file_path in active_files:
            file_name = os.path.basename(file_path)
            for pattern in patterns:
                if pattern in file_name.lower():
                    matched_files += 1
                    evidence_list.append(
                        ScenarioEvidence(
                            evidence_type="pattern",
                            value=file_path,
                            weight=0.25 / max(1, len(active_files)),
                            description="文件名匹配模式",
                        )
                    )
                    break

        return min(1.0, matched_files / max(1, len(active_files)))

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """匹配文件名模式"""
        if pattern.startswith("*."):
            ext = pattern[2:]
            return filename.endswith(ext)
        elif "*" in pattern:
            import fnmatch

            return fnmatch.fnmatch(filename, pattern)
        else:
            return filename == pattern

    def get_scenario_suggestion(self, threshold: float = 0.75) -> tuple[ScenarioType, float, bool]:
        """
        获取场景建议

        Args:
            threshold: 置信度阈值

        Returns:
            (场景类型, 置信度, 是否达到阈值)
        """
        result = self.detect()
        is_confident = result.score >= threshold
        return result.scenario, result.score, is_confident

    def explain_detection(self, scores: List[ScenarioScore]) -> str:
        """
        解释检测结果

        Args:
            scores: 场景评分列表

        Returns:
            解释文本
        """
        lines = ["=== 场景检测结果 ===", ""]
        top_scenarios = scores[:3]

        for i, score in enumerate(top_scenarios, 1):
            lines.append(f"{i}. {score.scenario.value}: {score.score:.2%}")
            if score.evidence:
                lines.append("   证据:")
                for evidence in score.evidence[:3]:  # 只显示前 3 个证据
                    lines.append(f"   - {evidence.description} (权重: {evidence.weight:.2f})")
            lines.append("")

        return "\n".join(lines)


# ==================== 便捷函数 ====================


def detect_current_scenario(
    root_dir: Optional[str] = None,
    active_files: Optional[List[str]] = None,
) -> ScenarioScore:
    """
    检测当前场景

    Args:
        root_dir: 项目根目录
        active_files: 活跃文件列表

    Returns:
        场景评分结果
    """
    detector = ScenarioDetector(root_dir)
    return detector.detect(active_files)


def get_best_scenario_match(
    root_dir: Optional[str] = None,
    active_files: Optional[List[str]] = None,
    threshold: float = 0.75,
) -> Optional[ScenarioType]:
    """
    获取最佳匹配场景

    Args:
        root_dir: 项目根目录
        active_files: 活跃文件列表
        threshold: 置信度阈值

    Returns:
        匹配的场景类型 (如果置信度足够高)
    """
    detector = ScenarioDetector(root_dir)
    result = detector.detect(active_files)

    if result.score >= threshold:
        return result.scenario
    return None


# ==================== 示例 ====================

if __name__ == "__main__":
    # 设置根目录
    root_dir_str = str(Path(__file__).parent.parent.parent.parent)

    print("=== 场景检测示例 ===\n")

    detector = ScenarioDetector(root_dir_str)

    # 测试场景 1: 编码场景
    print("场景 1: 编码场景")
    coding_files = [
        "src/ai_collab/context/schema.py",
        "src/ai_collab/cli.py",
        "src/ai_collab/pack/schema_v2.py",
    ]
    result = detector.detect(coding_files)
    print(f"检测到场景: {result.scenario.value}")
    print(f"置信度: {result.score:.2%}")
    print()

    # 测试场景 2: 文档场景
    print("场景 2: 文档场景")
    doc_files = [
        "README.md",
        "ARCHITECTURE.md",
        "CLAUDE.md",
    ]
    result = detector.detect(doc_files)
    print(f"检测到场景: {result.scenario.value}")
    print(f"置信度: {result.score:.2%}")
    print()

    # 获取所有场景分数
    print("所有场景分数:")
    scores = detector.detect_all(coding_files)
    explanation = detector.explain_detection(scores)
    print(explanation)

    # 场景建议
    scenario, confidence, is_confident = detector.get_scenario_suggestion()
    print(f"建议场景: {scenario.value}")
    print(f"置信度: {confidence:.2%}")
    print(f"是否达到阈值: {is_confident}")
    print()
    print("=== 完成 ===")
