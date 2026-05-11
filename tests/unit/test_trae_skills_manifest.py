"""Validate the 8-role Trae skill manifests."""

from __future__ import annotations

import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = WORKSPACE_ROOT / ".trae" / "skills"
REQUIRED_SKILLS = (
    "frontend-architect",
    "backend-architect",
    "ui-designer",
    "api-test-pro",
    "performance-expert",
    "compliance-checker",
    "devops-architect",
    "ai-integration-engineer",
)


def _extract_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("frontmatter must start with '---'")

    end_index = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = idx
            break

    if end_index is None:
        raise AssertionError("frontmatter closing '---' is missing")

    return "\n".join(lines[1:end_index])


def _parse_frontmatter(block: str) -> dict[str, object]:
    data: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in block.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", stripped)
        if key_match:
            key = key_match.group(1)
            value = key_match.group(2).strip()
            if value == "":
                data[key] = []
            else:
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                data[key] = value
            current_key = key
            continue

        if stripped.startswith("- "):
            if current_key is None or not isinstance(data.get(current_key), list):
                raise AssertionError(f"list item without list key: {stripped}")
            item = stripped[2:].strip()
            if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"}:
                item = item[1:-1]
            casted_list = data[current_key]
            assert isinstance(casted_list, list)
            casted_list.append(item)
            continue

        raise AssertionError(f"unsupported frontmatter line: {stripped}")

    return data


def test_required_skill_files_exist() -> None:
    for skill in REQUIRED_SKILLS:
        skill_file = SKILLS_ROOT / skill / "SKILL.md"
        assert skill_file.exists(), f"missing skill file: {skill_file}"


def test_required_skill_frontmatter_contract() -> None:
    for skill in REQUIRED_SKILLS:
        skill_file = SKILLS_ROOT / skill / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(_extract_frontmatter(content))

        assert "name" in frontmatter, f"{skill}: missing 'name'"
        assert "description" in frontmatter, f"{skill}: missing 'description'"
        assert "allowed-tools" in frontmatter, f"{skill}: missing 'allowed-tools'"

        name = frontmatter["name"]
        assert (
            isinstance(name, str) and name == skill
        ), f"{skill}: name must equal directory name, got {name!r}"

        allowed_tools = frontmatter["allowed-tools"]
        assert isinstance(allowed_tools, list), f"{skill}: allowed-tools must be a list"
        assert allowed_tools, f"{skill}: allowed-tools must not be empty"
        assert len(allowed_tools) == len(
            set(allowed_tools)
        ), f"{skill}: allowed-tools contains duplicates"
