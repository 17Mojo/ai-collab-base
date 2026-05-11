"""
Activation handler context routing tests.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ai_collab.activation_handler import ActivationHandler, AIType


def _write_state(tmp_path: Path, payload: dict) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "collaboration_state.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_extract_context_prefers_same_ai_from_active_tasks(tmp_path):
    _write_state(
        tmp_path,
        {
            "active_tasks": ["TASK-CLAUDE", "TASK-CODEARTS"],
            "tasks": {
                "TASK-CLAUDE": {
                    "task_id": "TASK-CLAUDE",
                    "ai_type": "claude_code",
                    "status": "implementing",
                    "description": "Claude task",
                },
                "TASK-CODEARTS": {
                    "task_id": "TASK-CODEARTS",
                    "ai_type": "codearts_agent",
                    "status": "implementing",
                    "description": "CodeArts task",
                },
            },
        },
    )

    handler = ActivationHandler(AIType.CODEARTS_AGENT, workspace_path=str(tmp_path))
    context = handler._extract_context_from_state()

    assert context["task_id"] == "TASK-CODEARTS"
    assert context["ai_type"] == "codearts_agent"


def test_extract_context_supports_codearts_copilot_alias(tmp_path):
    _write_state(
        tmp_path,
        {
            "active_tasks": ["TASK-COPILOT"],
            "tasks": {
                "TASK-COPILOT": {
                    "task_id": "TASK-COPILOT",
                    "ai_type": "copilot",
                    "status": "implementing",
                    "description": "Legacy copilot task",
                }
            },
        },
    )

    handler = ActivationHandler(AIType.CODEARTS_AGENT, workspace_path=str(tmp_path))
    context = handler._extract_context_from_state()

    assert context["task_id"] == "TASK-COPILOT"
    assert context["ai_type"] == "copilot"


def test_extract_context_fallbacks_to_any_active_task(tmp_path):
    _write_state(
        tmp_path,
        {
            "active_tasks": ["TASK-CLAUDE"],
            "tasks": {
                "TASK-CLAUDE": {
                    "task_id": "TASK-CLAUDE",
                    "ai_type": "claude_code",
                    "status": "implementing",
                    "description": "Claude task",
                }
            },
        },
    )

    handler = ActivationHandler(AIType.CODEARTS_AGENT, workspace_path=str(tmp_path))
    context = handler._extract_context_from_state()

    assert context["task_id"] == "TASK-CLAUDE"
