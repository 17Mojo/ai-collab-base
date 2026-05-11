import pytest

from ai_collab.dispatch_trigger import (
    build_handoff_payload,
    build_payload_refresh_command,
    parse_trigger_phrase,
    split_orders_by_assignee,
)


def test_parse_trigger_phrase_default_dispatch():
    intent = parse_trigger_phrase("2X")
    assert intent.action == "dispatch"
    assert intent.target == "all"


def test_parse_trigger_phrase_with_action_and_target():
    intent = parse_trigger_phrase("2X DISPATCH CLAUDE")
    assert intent.action == "dispatch"
    assert intent.target == "claude_code"


def test_parse_trigger_phrase_with_target_shortcut():
    intent = parse_trigger_phrase("2X codearts")
    assert intent.action == "dispatch"
    assert intent.target == "codearts_agent"


def test_parse_trigger_phrase_with_codex_target():
    intent = parse_trigger_phrase("2X DISPATCH CODEX")
    assert intent.action == "dispatch"
    assert intent.target == "codex"


def test_parse_trigger_phrase_rejects_wrong_keyword():
    with pytest.raises(ValueError):
        parse_trigger_phrase("AX DISPATCH", keyword="2X")


def test_split_orders_by_assignee_extracts_sections():
    orders = """# Agent Dispatch Orders（自动生成）

## 发送给 `Claude` (`claude_code`)

### TASK-1
```text
payload-1
```

## 发送给 `CodeArts` (`codearts_agent`)

### TASK-2
```text
payload-2
```
"""
    sections = split_orders_by_assignee(orders)
    assert "claude_code" in sections
    assert "codearts_agent" in sections
    assert "TASK-1" in sections["claude_code"]
    assert "TASK-2" in sections["codearts_agent"]


def test_build_handoff_payload_without_section_uses_empty_template():
    payload = build_handoff_payload(
        assignee="claude_code",
        trigger_phrase="2X DISPATCH",
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
        section_markdown=None,
        generated_at="2026-03-03T16:00:00",
    )
    assert "SourceOrders" in payload
    assert "当前无待派发任务。" in payload
    assert "C.RUN" in payload
    assert "C.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>" in payload
    assert "C.ACK|task=none|status=noop|result=none" in payload
    assert "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH Claude' --target claude_code" in payload


def test_build_handoff_payload_codearts_includes_ack_guard():
    payload = build_handoff_payload(
        assignee="codearts_agent",
        trigger_phrase="2X DISPATCH CodeArts",
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
        section_markdown="## 发送给 `CodeArts` (`codearts_agent`)\n\n### TASK-A-001",
        generated_at="2026-03-04T16:10:00",
    )
    assert "A.RUN" in payload
    assert "A.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>" in payload
    assert "禁止改为执行全局串联命令" in payload
    assert "python3 -m ai_collab.cli run" in payload


def test_build_handoff_payload_codex_uses_x_run_and_x_ack():
    payload = build_handoff_payload(
        assignee="codex",
        trigger_phrase="2X DISPATCH CODEX",
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
        section_markdown=None,
        generated_at="2026-03-13T10:00:00",
    )
    assert "X.RUN" in payload
    assert "X.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>" in payload
    assert "X.ACK|task=none|status=noop|result=none" in payload


def test_build_payload_refresh_command_returns_valid_phrase_for_assignee():
    assert (
        build_payload_refresh_command("codearts_agent")
        == "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH CodeArts' --target codearts_agent"
    )
    assert build_payload_refresh_command("unknown") == "python3 -m ai_collab.cli dispatch"
