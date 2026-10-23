"""ACK 前缀的**派生路径一致性**守卫（2026-10-23）。

背景：

同一个工单的 ACK 行有两条产生路径 ——
**CLI ACK 路径**（`ai_collab.cli._cli_main.cmd_ack` → `ack_protocol.build_ack_line`）
与**回执桥接路径**（`scripts/agent_receipt_bridge.py`）。

历史缺陷：两条路径对「工单声明了 `assignee_role`」的处理不一致 ——
CLI 路径角色优先（AGENT_ARCH → `X.ACK`），桥接路径只看 provider
（claude_code → `C.ACK`）。于是同一个工单在两处记录里出现**两种前缀**，
且桥接路径还会把记录里的 `assignee_role` 字段整个抹掉。

本文件守三条不变量：

1. 两条派生路径对同一组 (provider, role) 必须给出**同一个前缀**；
2. 角色前缀优先于 provider 兜底前缀；
3. 角色必须**落进 ACK 记录**（否则下一次只拿到 provider 的写入会降级前缀）。
"""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_collab import cli
from ai_collab.ack_protocol import build_ack_line, upsert_ack_bridge_item

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCRIPT = REPO_ROOT / "scripts" / "agent_receipt_bridge.py"

# (provider, 角色, 期望前缀)
DERIVATION_CASES = [
    ("claude_code", "AGENT_ARCH", "X"),
    ("claude_code", "AGENT_TEST", "C"),
    ("codearts_agent", "AGENT_EXEC", "A"),
    ("codearts_agent", "AGENT_TEST", "C"),
]


def _load_receipt_bridge_module():
    """按路径加载 standalone 脚本（它刻意不依赖 ai_collab 包）。"""
    source = RECEIPT_SCRIPT.read_text(encoding="utf-8")
    namespace: dict = {
        "__name__": "agent_receipt_bridge_under_test",
        "__file__": str(RECEIPT_SCRIPT),
    }
    exec(compile(source, str(RECEIPT_SCRIPT), "exec"), namespace)  # noqa: S102
    return namespace


@pytest.fixture()
def receipt_bridge():
    return _load_receipt_bridge_module()


# ---------------------------------------------------------------------------
# 1. 两条派生路径同源
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider,role,expected", DERIVATION_CASES)
def test_cli_and_bridge_derive_the_same_prefix(
    receipt_bridge, provider, role, expected
):
    """CLI ACK 路径与回执桥接路径对同一 (provider, role) 必须一致。"""
    cli_line = build_ack_line(
        assignee=provider,
        task_id="TASK-X-001",
        result_file="collaboration/results/RESULT_TASK-X-001.md",
        assignee_role=role,
        workspace=REPO_ROOT,
    )
    bridge_prefix = receipt_bridge["ack_prefix_for"](
        provider, assignee_role=role, workspace=REPO_ROOT
    )

    assert cli_line.split(".", 1)[0] == expected
    assert bridge_prefix == expected


@pytest.mark.parametrize("provider,role,expected", DERIVATION_CASES)
def test_bridge_prefix_is_role_first(receipt_bridge, provider, role, expected):
    """带角色时取角色前缀；不带角色时才退到 provider 兜底字母。"""
    assert (
        receipt_bridge["ack_prefix_for"](
            provider, assignee_role=role, workspace=REPO_ROOT
        )
        == expected
    )


@pytest.mark.parametrize(
    "provider,expected", [("claude_code", "C"), ("codearts_agent", "A"), ("codex", "O")]
)
def test_bridge_prefix_falls_back_to_provider_without_role(
    receipt_bridge, provider, expected
):
    """没有角色声明时，行为与 provider 兜底表一致（不回归）。"""
    assert (
        receipt_bridge["ack_prefix_for"](provider, workspace=REPO_ROOT) == expected
    )


# ---------------------------------------------------------------------------
# 2. 角色必须落进 ACK 记录
# ---------------------------------------------------------------------------


def test_upsert_ack_bridge_item_persists_assignee_role():
    items: dict = {}
    upsert_ack_bridge_item(
        items,
        task_id="TASK-X-001",
        assignee="claude_code",
        result_file="collaboration/results/RESULT_TASK-X-001.md",
        completed_at="2026-10-23T10:00:00+08:00",
        source="cli-ack",
        bridged_at="2026-10-23T10:00:00+08:00",
        assignee_role="AGENT_ARCH",
        workspace=REPO_ROOT,
    )

    record = items["TASK-X-001"]
    assert record["assignee_role"] == "AGENT_ARCH"
    assert record["ack_line"].startswith("X.ACK|")


def test_upsert_ack_bridge_item_preserves_existing_role():
    """后续一次只拿到 provider 的写入，不得把已知的角色抹掉。"""
    items: dict = {}
    upsert_ack_bridge_item(
        items,
        task_id="TASK-X-002",
        assignee="claude_code",
        result_file="collaboration/results/RESULT_TASK-X-002.md",
        completed_at="2026-10-23T10:00:00+08:00",
        source="cli-ack",
        bridged_at="2026-10-23T10:00:00+08:00",
        assignee_role="AGENT_ARCH",
        workspace=REPO_ROOT,
    )
    # 第二次写入没带角色（老调用方 / 兜底桥接）
    upsert_ack_bridge_item(
        items,
        task_id="TASK-X-002",
        assignee="claude_code",
        result_file="collaboration/results/RESULT_TASK-X-002.md",
        completed_at="2026-10-23T10:01:00+08:00",
        source="cli-ack",
        bridged_at="2026-10-23T10:01:00+08:00",
        workspace=REPO_ROOT,
    )

    assert items["TASK-X-002"]["assignee_role"] == "AGENT_ARCH"


# ---------------------------------------------------------------------------
# 3. CLI ACK 路径
# ---------------------------------------------------------------------------


def _write_task(workspace: Path, task_id: str, **overrides) -> None:
    task = {
        "task_id": task_id,
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "created_at": "2026-10-23T09:00:00+08:00",
        "updated_at": "2026-10-23T09:30:00+08:00",
        "result_file": f"collaboration/results/RESULT_{task_id}.md",
    }
    task.update(overrides)
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "workspace": str(workspace),
                "tasks": {task_id: task},
                "patches": {},
                "active_tasks": [task_id],
                "completed_tasks": [],
                "conflicts": [],
                "file_status": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _ack_args(workspace: Path, task_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        workspace=str(workspace),
        task_id=task_id,
        ai=None,
        status=None,
        result_file=None,
    )


def test_cmd_ack_uses_role_prefix_for_agent_arch(capsys, tmp_path: Path):
    """工单声明 AGENT_ARCH ⇒ ACK 行带 X.ACK（席位字母，不是厂商字母）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_task(workspace, "TASK-X-ARCH-001", assignee_role="AGENT_ARCH")

    assert cli.cmd_ack(_ack_args(workspace, "TASK-X-ARCH-001")) == 0
    assert capsys.readouterr().out.strip().startswith("X.ACK|task=TASK-X-ARCH-001|")


def test_cmd_ack_falls_back_to_provider_prefix_without_role(capsys, tmp_path: Path):
    """没有角色声明 ⇒ 维持 provider 兜底字母（不回归）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_task(workspace, "TASK-X-NOROLE-001")

    assert cli.cmd_ack(_ack_args(workspace, "TASK-X-NOROLE-001")) == 0
    assert capsys.readouterr().out.strip().startswith("C.ACK|task=TASK-X-NOROLE-001|")


def test_cmd_ack_task_not_found_reuses_role_from_history(capsys, tmp_path: Path):
    """工单已不在状态机里，但历史 ACK 记录带着角色 ⇒ 仍用角色前缀。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "logs").mkdir(parents=True, exist_ok=True)
    (workspace / "logs" / "collaboration_state.json").write_text(
        json.dumps({"version": "2.0.0", "tasks": {}, "patches": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (workspace / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-X-GONE-001": {
                        "task_id": "TASK-X-GONE-001",
                        "assignee": "claude_code",
                        "assignee_role": "AGENT_ARCH",
                        "result_file": "collaboration/results/RESULT_TASK-X-GONE-001.md",
                        "ack_line": "X.ACK|task=TASK-X-GONE-001|status=ok|result=collaboration/results/RESULT_TASK-X-GONE-001.md",
                        "source": "cli-ack",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert cli.cmd_ack(_ack_args(workspace, "TASK-X-GONE-001")) == 0
    assert capsys.readouterr().out.strip().startswith("X.ACK|task=TASK-X-GONE-001|")


# ---------------------------------------------------------------------------
# 4. 桥接路径端到端
# ---------------------------------------------------------------------------


def _write_valid_result(workspace: Path, relative_path: str) -> None:
    result_file = workspace / relative_path
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# Result",
                "## 执行命令",
                "```bash",
                "echo test",
                "```",
                "## 测试结论",
                "- pass",
                "## 风险",
                "- none",
            ]
        ),
        encoding="utf-8",
    )


def test_receipt_bridge_records_role_prefixed_ack_line(tmp_path: Path):
    """端到端：AGENT_ARCH 工单被桥接收口后，记录里是 X.ACK 且角色没丢。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    task_id = "TASK-X-BRIDGE-001"
    result_rel = f"collaboration/results/RESULT_{task_id}.md"

    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "workspace": str(workspace),
                "last_updated": "2026-10-23T10:00:00+08:00",
                "tasks": {
                    task_id: {
                        "task_id": task_id,
                        "ai_type": "claude_code",
                        "assignee": "claude_code",
                        "assignee_role": "AGENT_ARCH",
                        "status": "testing",
                        "updated_at": "2026-10-23T10:00:00+08:00",
                        "notes": [],
                        "result_file": result_rel,
                    }
                },
                "patches": {},
                "active_tasks": [task_id],
                "completed_tasks": [],
                "conflicts": [],
                "file_status": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_valid_result(workspace, result_rel)

    # claude_code 必须先有显式 cli-ack 才允许收口
    ack_file = workspace / "logs" / "agent_ack_bridge_state.json"
    ack_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    task_id: {
                        "task_id": task_id,
                        "assignee": "claude_code",
                        "assignee_role": "AGENT_ARCH",
                        "result_file": result_rel,
                        "ack_line": f"X.ACK|task={task_id}|status=ok|result={result_rel}",
                        "source": "cli-ack",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(RECEIPT_SCRIPT), "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    item = json.loads(ack_file.read_text(encoding="utf-8"))["items"][task_id]
    assert item["assignee_role"] == "AGENT_ARCH"
    assert item["ack_line"].startswith(f"X.ACK|task={task_id}|")


def test_receipt_bridge_does_not_create_config_in_foreign_workspace(tmp_path: Path):
    """桥接只想「读前缀」，不该在别人的工作区里落编排配置模板。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    namespace = _load_receipt_bridge_module()
    namespace["ack_prefix_for"]("claude_code", assignee_role="AGENT_ARCH", workspace=workspace)

    assert not (workspace / "config" / "agent-orchestration.json").exists()
