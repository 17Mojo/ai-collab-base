"""
Scenario detection tests.
"""

from __future__ import annotations

from pathlib import Path

from ai_collab.context.scenario import (
    ScenarioDetector,
    ScenarioEvidence,
    ScenarioScore,
    detect_current_scenario,
    get_best_scenario_match,
)
from ai_collab.context.schema import ScenarioType


class TestScenarioEvidence:
    """Test ScenarioEvidence dataclass."""

    def test_evidence_creation(self):
        evidence = ScenarioEvidence(
            evidence_type="file",
            value="test.py",
            weight=0.5,
            description="Found Python file",
        )
        assert evidence.evidence_type == "file"
        assert evidence.value == "test.py"
        assert evidence.weight == 0.5
        assert evidence.description == "Found Python file"


class TestScenarioScore:
    """Test ScenarioScore dataclass."""

    def test_score_creation(self):
        score = ScenarioScore(
            scenario=ScenarioType.CODING,
            score=0.85,
        )
        assert score.scenario == ScenarioType.CODING
        assert score.score == 0.85
        assert score.evidence == []

    def test_score_with_evidence(self):
        evidence_list = [
            ScenarioEvidence("directory", "src/", 0.3, "Found src directory"),
            ScenarioEvidence("file", "main.py", 0.4, "Found Python file"),
        ]
        score = ScenarioScore(
            scenario=ScenarioType.CODING,
            score=0.7,
            evidence=evidence_list,
        )
        assert len(score.evidence) == 2
        assert score.evidence[0].weight == 0.3


class TestScenarioDetector:
    """Test ScenarioDetector class."""

    def test_detector_initialization(self, tmp_path):
        detector = ScenarioDetector(str(tmp_path))
        assert detector.root_dir == tmp_path

    def test_detector_default_root(self):
        detector = ScenarioDetector()
        assert detector.root_dir == Path.cwd()

    def test_detect_coding_scenario(self, tmp_path):
        # Create coding directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass")
        (tmp_path / "src" / "utils.py").write_text("def helper(): pass")

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["src/main.py", "src/utils.py"])

        assert result.scenario == ScenarioType.CODING
        assert result.score > 0.5

    def test_detect_research_scenario(self, tmp_path):
        # Create research directory structure
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "paper.md").write_text("# Research Paper\n\n## Abstract")
        (tmp_path / "research").mkdir()
        (tmp_path / "research" / "notes.md").write_text("# Notes\n\n## Analysis")

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(
            active_files=["docs/paper.md", "research/notes.md"],
        )

        # Prefer research scenario
        assert result.scenario in [ScenarioType.RESEARCH, ScenarioType.DOCUMENTATION]
        assert result.score > 0.3

    def test_detect_writing_scenario(self, tmp_path):
        # Create content structure
        (tmp_path / "posts").mkdir()
        (tmp_path / "posts" / "article1.md").write_text(
            "---\ntitle: Test\ndate: 2026-04-03\n---\nContent"
        )

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["posts/article1.md"])

        # Should detect writing or documentation
        assert result.scenario in [
            ScenarioType.WRITING,
            ScenarioType.DOCUMENTATION,
        ]
        assert result.score > 0.2

    def test_detect_debugging_scenario(self, tmp_path):
        # Create debugging files
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "error.log").write_text("ERROR: Something went wrong")
        (tmp_path / "test_main.py").write_text("def test_something(): assert True")

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["logs/error.log", "test_main.py"])

        # Should detect debugging
        assert result.scenario == ScenarioType.DEBUGGING
        assert result.score > 0.3

    def test_detect_design_scenario(self, tmp_path):
        # Create design files
        (tmp_path / "assets" / "styles").mkdir(parents=True)
        (tmp_path / "assets/styles/main.css").write_text(
            ".container { width: 100%; height: 100%; color: blue; }"
        )

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["assets/styles/main.css"])

        # Should detect design
        assert result.scenario == ScenarioType.DESIGN
        assert result.score > 0.5

    def test_detect_project_planning_scenario(self, tmp_path):
        # Create planning files
        (tmp_path / "plans").mkdir()
        (tmp_path / "plans" / "todo.md").write_text("TODO\n- Task 1\n- Task 2")

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["plans/todo.md"])

        # Should detect project planning
        assert result.scenario == ScenarioType.PROJECT_PLANNING
        assert result.score > 0.3

    def test_detect_all_scenarios(self, tmp_path):
        detector = ScenarioDetector(str(tmp_path))
        scores = detector.detect_all()

        assert len(scores) > 0
        # Scores should be sorted in descending order
        for i in range(len(scores) - 1):
            assert scores[i].score >= scores[i + 1].score

    def test_evidence_collection(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("class MyClass:\n    def method(self): pass")

        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["src/main.py"], include_content=True)

        # Should have evidence
        assert len(result.evidence) > 0
        # Check evidence types
        evidence_types = {e.evidence_type for e in result.evidence}
        assert evidence_types.issubset(["directory", "file", "content", "pattern"])

    def test_get_scenario_suggestion(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("def app(): pass")

        detector = ScenarioDetector(str(tmp_path))
        scenario, confidence, is_confident = detector.get_scenario_suggestion()

        # Should return a scenario
        assert scenario is not None
        assert 0 <= confidence <= 1

    def test_get_scenario_suggestion_with_threshold(self, tmp_path):
        (tmp_path / "src").mkdir()
        confidence_files = [
            "src/main.py",
            "src/app.py",
            "src/utils.py",
            "src/models.py",
            "src/views.py",
        ]
        for file_path in confidence_files:
            (tmp_path / file_path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / file_path).write_text("# Python code")

        detector = ScenarioDetector(str(tmp_path))
        scenario, confidence, is_confident = detector.get_scenario_suggestion(threshold=0.3)

        # Should be confident with many Python files
        assert scenario == ScenarioType.CODING
        assert confidence >= 0.3
        assert is_confident is True

    def test_explain_detection(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "code.py").write_text("def hello(): pass")

        detector = ScenarioDetector(str(tmp_path))
        scores = detector.detect_all()
        explanation = detector.explain_detection(scores)

        # Should have header
        assert "=== 场景检测结果 ===" in explanation
        # Should contain scenarios
        assert any(scenario in explanation for scenario in ["coding", "debugging"])

    def test_match_pattern_helper(self, tmp_path):
        detector = ScenarioDetector(str(tmp_path))

        # Test glob patterns
        assert detector._match_pattern("main.py", "*.py")
        assert detector._match_pattern("main.py", "*.py")
        assert not detector._match_pattern("main.py", "*.js")

        # Test wildcards
        assert detector._match_pattern("test_main.py", "test_*.py")
        assert detector._match_pattern("main_test.py", "*_test.py")

    def test_content_analysis_enabled(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("class App:\n    def run(self): pass")

        detector = ScenarioDetector(str(tmp_path))

        # Without content analysis
        result_no_content = detector.detect(active_files=["src/app.py"], include_content=False)

        # With content analysis
        result_with_content = detector.detect(active_files=["src/app.py"], include_content=True)

        # Both should detect coding
        assert result_no_content.scenario == ScenarioType.CODING
        assert result_with_content.scenario == ScenarioType.CODING

        # With content should have more detailed evidence
        assert len(result_with_content.evidence) >= len(result_no_content.evidence)

    def test_empty_active_files(self, tmp_path):
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=[])

        # Should still return a result (based on directory structure)
        assert result.scenario is not None
        assert 0 <= result.score <= 1

    def test_multiple_scenarios_overlap(self, tmp_path):
        # Create mixed structure
        (tmp_path / "src").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / "src" / "app.py").write_text("def app(): pass")
        (tmp_path / "docs" / "README.md").write_text("# Document")

        detector = ScenarioDetector(str(tmp_path))

        # Active files in coding directory
        coding_result = detector.detect(active_files=["src/app.py"])
        assert coding_result.scenario == ScenarioType.CODING

        # Active files in docs directory
        doc_result = detector.detect(active_files=["docs/README.md"])
        assert doc_result.scenario in [
            ScenarioType.DOCUMENTATION,
            ScenarioType.WRITING,
            ScenarioType.RESEARCH,
        ]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_current_scenario(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        import os

        os.chdir(str(tmp_path))

        result = detect_current_scenario(root_dir=str(tmp_path))

        assert result.scenario is not None

    def test_get_best_scenario_match(self, tmp_path):
        (tmp_path / "src").mkdir()
        for i in range(5):
            file_path = tmp_path / "src" / f"module{i}.py"
            file_path.write_text(f"def module{i}(): pass")

        scenario = get_best_scenario_match(
            root_dir=str(tmp_path),
            active_files=["src/module0.py", "src/module1.py"],
            threshold=0.6,
        )

        # Should return coding scenario with high confidence
        assert scenario == ScenarioType.CODING

    def test_get_best_scenario_match_below_threshold(self, tmp_path):
        # Create minimal structure
        (tmp_path / "temp.txt").write_text("test")

        scenario = get_best_scenario_match(
            root_dir=str(tmp_path),
            active_files=["temp.txt"],
            threshold=0.9,  # High threshold
        )

        # Should return None if below threshold
        assert scenario is None


class TestScenarioCoverage:
    """Test coverage of all scenario types."""

    def test_all_scenarios_have_rules(self):
        """Verify all scenario types have detection rules."""
        detector = ScenarioDetector()
        all_scenarios = list(ScenarioType)

        for scenario in all_scenarios:
            assert scenario in detector.SCENARIO_RULES, f"Missing rules for {scenario}"

    def test_scenario_rules_structure(self):
        """Verify all scenario rules have required fields."""
        detector = ScenarioDetector()

        for scenario, rules in detector.SCENARIO_RULES.items():
            assert "directories" in rules, f"Missing 'directories' in {scenario}"
            assert "files" in rules, f"Missing 'files' in {scenario}"
            assert "patterns" in rules, f"Missing 'patterns' in {scenario}"
            assert "weight" in rules, f"Missing 'weight' in {scenario}"
            assert 0 <= rules["weight"] <= 1, f"Invalid weight in {scenario}"


class TestScenarioEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_coding_with_handlers_dir(self, tmp_path):
        """handlers/ directory should be recognized as coding."""
        (tmp_path / "handlers").mkdir()
        (tmp_path / "handlers" / "event.py").write_text("class EventHandler: pass")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["handlers/event.py"])
        assert result.scenario == ScenarioType.CODING

    def test_coding_with_api_dir(self, tmp_path):
        """api/ directory should be recognized as coding."""
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "routes.py").write_text("def get(): pass")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["api/routes.py"])
        assert result.scenario == ScenarioType.CODING

    def test_research_with_studies_dir(self, tmp_path):
        """studies/ directory should be recognized as research."""
        (tmp_path / "studies").mkdir()
        (tmp_path / "studies" / "analysis.md").write_text("# Analysis\n## Introduction")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["studies/analysis.md"])
        assert result.scenario in [ScenarioType.RESEARCH, ScenarioType.DOCUMENTATION]

    def test_writing_with_pages_dir(self, tmp_path):
        """pages/ directory should be recognized as writing."""
        (tmp_path / "pages").mkdir()
        (tmp_path / "pages" / "about.md").write_text("---\ntitle: About\n---\nContent")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["pages/about.md"])
        assert result.scenario in [ScenarioType.WRITING, ScenarioType.DOCUMENTATION]

    def test_debugging_with_fixtures_dir(self, tmp_path):
        """fixtures/ directory should contribute to debugging score."""
        (tmp_path / "fixtures").mkdir()
        (tmp_path / "fixtures" / "mock_data.py").write_text("MOCK = True")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["fixtures/mock_data.py"])
        # fixtures dir contributes to debugging, but .py files also match coding
        assert result.scenario in [ScenarioType.DEBUGGING, ScenarioType.CODING]

    def test_tsx_files_as_coding(self, tmp_path):
        """.tsx files should be recognized as coding."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "App.tsx").write_text("export default function App() {}")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["src/App.tsx"])
        assert result.scenario == ScenarioType.CODING

    def test_ipynb_files_as_research(self, tmp_path):
        """.ipynb files should be recognized as research."""
        (tmp_path / "notebooks").mkdir()
        (tmp_path / "notebooks" / "analysis.ipynb").write_text("{}")
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["notebooks/analysis.ipynb"])
        # ipynb is in research files list
        assert result.score > 0

    def test_score_always_between_0_and_1(self, tmp_path):
        """Scores should always be between 0 and 1."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass")
        detector = ScenarioDetector(str(tmp_path))
        scores = detector.detect_all(active_files=["src/main.py"])
        for score in scores:
            assert 0 <= score.score <= 1

    def test_detect_with_nonexistent_files(self, tmp_path):
        """Detection should handle non-existent active files gracefully."""
        detector = ScenarioDetector(str(tmp_path))
        result = detector.detect(active_files=["nonexistent/file.py"])
        assert result.scenario is not None
        assert 0 <= result.score <= 1
