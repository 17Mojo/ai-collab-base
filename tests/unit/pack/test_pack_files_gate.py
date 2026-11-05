"""sweep 口径门禁（2026-11-05 收口）：什么算 Pack + 活体轨道全量双消费面

口径对齐两个消费面：
- 判据：`metadata.pack_id` 非空（IMPORT_PACKS 处理器同款，is_pack_file 落地）——
  manifest.json / VERSION.json 无该字段，不被当 Pack 扫；
- 范围：活体轨道 packs/templates + packs/examples（2026-11-03 按「能不能跑」拆分）。
  packs/exports 是导出快照归档（历史产物，可能不满足现行 schema），不进 sweep。

N18 教训锚：validator 绿 ≠ from_dict 绿——门禁对每个 Pack 跑**双消费面**
（validate_pack(strict=True) 零 error + schema_v2.PromptPackV2.from_dict 可解析）。
"""

import json
from pathlib import Path

from ai_collab.pack.schema_validator import (
    ValidationSeverity,
    is_pack_file,
    validate_all_packs,
    validate_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_ROOTS = [REPO_ROOT / "packs" / "templates", REPO_ROOT / "packs" / "examples"]


def _live_json_files() -> list[Path]:
    files: list[Path] = []
    for root in LIVE_ROOTS:
        files.extend(sorted(root.glob("*.json")))
    return files


def _live_pack_files() -> list[Path]:
    return [p for p in _live_json_files() if is_pack_file(p)]


class TestPackFileCriterion:
    """什么算 Pack：metadata.pack_id（IMPORT_PACKS 同款判据）"""

    def test_manifest_and_version_files_are_not_packs(self):
        """变异锚：判据若放宽到「有 metadata」，api-design-pack/manifest.json 会混进来"""
        non_packs = [
            REPO_ROOT / "packs" / "api-design-pack" / "manifest.json",
            REPO_ROOT / "packs" / "demo-pack" / "VERSION.json",
            REPO_ROOT / "packs" / "demo-pack" / "manifest.json",
        ]
        for p in non_packs:
            assert p.exists(), f"锚文件缺失: {p}"
            assert not is_pack_file(p), f"{p} 不应判为 Pack"

    def test_known_pack_is_pack(self):
        p = REPO_ROOT / "packs" / "templates" / "xiaohongshu_beauty_review.json"
        assert is_pack_file(p)

    def test_criterion_accepts_parsed_dict(self):
        assert is_pack_file({"metadata": {"pack_id": "x"}})
        assert not is_pack_file({"metadata": {}})
        assert not is_pack_file({"metadata": {"pack_id": ""}})
        assert not is_pack_file({"no_metadata": 1})

    def test_validate_all_packs_skips_non_pack_json(self, tmp_path):
        (tmp_path / "real-pack.json").write_text(
            json.dumps({"metadata": {"pack_id": "p1"}}), encoding="utf-8"
        )
        (tmp_path / "manifest.json").write_text(
            json.dumps({"metadata": {"name": "not-a-pack"}}), encoding="utf-8"
        )
        results = validate_all_packs(str(tmp_path))
        assert [Path(k).name for k in results] == ["real-pack.json"]


class TestLiveRootsGate:
    """活体轨道（templates/examples）全量门禁"""

    def test_live_roots_have_packs(self):
        packs = _live_pack_files()
        assert len(packs) >= 15, f"活体 Pack 数异常偏低: {len(packs)}"

    def test_live_roots_contain_only_pack_criterion_files(self):
        """活体目录里不允许混入非 Pack JSON（判据守住轨道纯度）"""
        offenders = [str(p) for p in _live_json_files() if not is_pack_file(p)]
        assert offenders == [], f"活体轨道混入非 Pack 文件: {offenders}"

    def test_all_live_packs_validate_strict_green(self):
        errors: list[str] = []
        for p in _live_pack_files():
            result = validate_pack(str(p), strict=True)
            for issue in result.issues:
                if issue.severity == ValidationSeverity.ERROR:
                    errors.append(f"{p}: {issue.path} {issue.message}")
        assert errors == [], "validate_pack(strict) 有 error:\n" + "\n".join(errors)

    def test_all_live_packs_from_dict_parses(self):
        """N18 教训锚：validate_pack 绿的 Pack 也必须过 schema_v2.from_dict"""
        from ai_collab.pack.schema_v2 import PromptPackV2

        failures: list[str] = []
        for p in _live_pack_files():
            try:
                PromptPackV2.from_dict(json.loads(p.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001 — 门禁要抓一切解析失败
                failures.append(f"{p}: {type(exc).__name__}: {exc}")
        assert failures == [], "from_dict 解析失败:\n" + "\n".join(failures)
