"""Pack 市场 CLI：publish / install / upgrade

对应 `ai_collab.cli pack publish|install|upgrade` 子命令（2026-11-05 落地，
此前只有模块层 market_api/dependency 无 CLI 门面）。

语义边界（如实）：
- publish：`pack validate` 同款判据 + SemVer 校验 + 入市场库（默认 PENDING，--approve 直批）；
  dependencies 来自 Pack JSON 的 `dependencies` 字段（[{name, version}, ...]）。
  市场表是 pack_id 主键**单行**（无版本历史）：同 id 发更高版本 = 单行覆盖更新
  （保留下载/评分计数），非更高版本拒发。
- install：按名称/版本范围在市场库选版 → 范围校验 → 依赖解析（安装顺序/冲突）→
  记入 packs/.packs-index.json 并累加下载计数。市场库只存元数据不存正文，也
  **不持久化 dependencies**（表无该列）——依赖图从 packs/ 下的正文 JSON 补齐；
  正文仍以 packs/ 目录下的 JSON 文件为准。
- upgrade：对比本地索引已装版本与市场最新 → 兼容性/破坏性变更提示（SemVer 主版本），
  并检查升级后与已装 Pack 的依赖约束冲突。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ..pack.market_api import PackMarketAPI
from ..pack.market_store import PackMarketStore
from ..pack.market import PackListing, PackStatus
from ..pack.dependency import DependencyNode, DependencyResolver, PackDependency
from ..pack.version import PackVersion


class PackMarketCLI:
    """publish / install / upgrade 门面"""

    def __init__(self, db_path: str = "data/packs.db", packs_root: str = "packs"):
        self.api = PackMarketAPI(db_path)
        self.store = PackMarketStore(db_path)
        self.resolver = DependencyResolver()
        self.packs_root = Path(packs_root)
        self.index_path = self.packs_root / ".packs-index.json"

    # ---------- 公共 ----------

    def _load_index(self) -> dict:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": "1.0.0", "installed": {}}

    def _save_index(self, index: dict) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load_pack_json(self, path: str) -> dict | None:
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"\n错误: 文件不存在: {path}")
            return None
        except json.JSONDecodeError as exc:
            print(f"\n错误: JSON 解析失败: {exc}")
            return None

    @staticmethod
    def _deps_from_pack(pack: dict) -> list[dict]:
        raw = pack.get("dependencies") or []
        deps = []
        for item in raw:
            if isinstance(item, dict) and item.get("name"):
                deps.append(
                    {
                        "name": str(item["name"]),
                        "version": str(item.get("version", "*")),
                        "optional": bool(item.get("optional", False)),
                    }
                )
        return deps

    @staticmethod
    def _mk_dep(name: str, range_expr: str, optional: bool = False) -> PackDependency:
        """构造 PackDependency，归一化人类写法。

        范围解析器（dependency.py）语法严格，这里有三步归一化：
        - `*`/空/x/any → `>=0.0.0`（解析器不认 `*` 通配）；
        - 部分版本号补零：`^1.0` → `^1.0.0`、`>=2` → `>=2.0.0`
          （解析器要求完整 major.minor.patch）；
        - AND 组合统一为逗号分隔：`>=1.0.0 <2.0.0` → `>=1.0.0,<2.0.0`
          （dependency.py 预存不一致：__post_init__ 校验认空格分隔，但
          is_compatible_with 的 _check_single_expression 只认 `,`/`&`，
          空格组合式校验能过却匹配永远 False——此处转逗号绕开；
          模块层根治留作后续）。
        OR 组合（`|`）原样保留，各 OR 分支内部同样归一化。
        """
        expr = (range_expr or "").strip()
        if expr in ("", "*", "x", "X", "any"):
            expr = ">=0.0.0"

        def _pad(part: str) -> str:
            m = re.match(r"^([<>=^~]*)(\d+)(?:\.(\d+))?(?:\.(\d+))?([^,|& ]*)$", part)
            if not m:
                return part
            op, major, minor, patch, suffix = m.groups()
            return f"{op}{major}.{minor or 0}.{patch or 0}{suffix or ''}"

        or_norm = []
        for or_part in expr.split("|"):
            parts = [p for p in re.split(r"\s*,\s*|\s*&\s*|\s+", or_part.strip()) if p]
            or_norm.append(",".join(_pad(p) for p in parts))
        return PackDependency(name=name, version_range="|".join(or_norm), optional=optional)

    # ---------- publish ----------

    @staticmethod
    def _check_publishable(pack: dict) -> tuple[list[str], list[str]]:
        """发布前置校验，判据与 `pack validate` CLI 同款。

        error（阻断）：JSON 已由 _load_pack_json 保证；必需顶层字段
        （metadata/domain/workflow/quality_metrics）、metadata 8 字段、
        workflow 步骤 ID 唯一。warning（不阻断）：质量指标权重和 ≠ 1.0。
        注：schema_validator.validate_pack 是另一套更严口径（要求 metric 内嵌
        name 等，仓库正典 Pack 不满足），不作发布闸门——错位见 RESULT 记档。
        """
        errors: list[str] = []
        warnings: list[str] = []
        for field in ("metadata", "domain", "workflow", "quality_metrics"):
            if field not in pack:
                errors.append(f"缺少必需字段: {field}")
        meta = pack.get("metadata") or {}
        for field in (
            "pack_id", "pack_name", "version", "type",
            "description", "designer", "created_at", "updated_at",
        ):
            if field not in meta:
                errors.append(f"metadata 缺少必需字段: {field}")
        metrics = (pack.get("quality_metrics") or {}).get("metrics")
        if isinstance(metrics, dict) and metrics:
            total = sum(
                m.get("weight", 0) for m in metrics.values() if isinstance(m, dict)
            )
            if abs(total - 1.0) > 0.01:
                warnings.append(f"质量指标权重总和不为 1.0: {total:.3f}")
        steps = (pack.get("workflow") or {}).get("steps")
        if isinstance(steps, list):
            step_ids = [s.get("id") for s in steps if isinstance(s, dict) and "id" in s]
            if len(step_ids) != len(set(step_ids)):
                errors.append(f"workflow 步骤 ID 重复: {set(step_ids)}")
        return errors, warnings

    def publish(self, path: str, approve: bool = False) -> int:
        pack = self._load_pack_json(path)
        if pack is None:
            return 1

        errors, warnings = self._check_publishable(pack)
        for w in warnings:
            print(f"  [warning] {w}")
        for e in errors:
            print(f"  [error] {e}")
        if errors:
            print("\n✗ 校验未通过，发布中止（判据与 pack validate 同款）")
            return 1

        meta = pack.get("metadata") or {}
        version_str = str(meta.get("version", "")).strip()
        try:
            PackVersion.from_string(version_str)
        except Exception as exc:
            print(f"\n✗ 版本号不合法: {version_str!r} ({exc})")
            return 1

        deps = self._deps_from_pack(pack)
        listing = PackListing(
            pack_id=str(meta.get("pack_id") or meta.get("pack_name") or Path(path).stem),
            pack_name=str(meta.get("pack_name") or meta.get("pack_id") or Path(path).stem),
            version=version_str,
            description=str(meta.get("description", "")),
            author=str(meta.get("designer") or meta.get("author") or "unknown"),
            category=str(meta.get("category") or pack.get("domain", {}).get("name", "general")),
            tags=list(meta.get("tags") or []),
            status=PackStatus.PENDING,
            dependencies=deps,
        )
        if not self.store.create_listing(listing):
            # 同 pack_id 已在库：市场表是 pack_id 主键单行（无版本历史表），
            # 新版本走 update_listing 单行覆盖；非更高版本拒发。
            existing = self.store.get_listing(listing.pack_id)
            if existing is None:
                print("\n✗ 入库失败")
                return 1
            try:
                cur = PackVersion.from_string(str(existing.version))
                new = PackVersion.from_string(version_str)
            except Exception as exc:
                print(f"\n✗ 版本比较失败: {exc}")
                return 1
            if new.compare(cur) <= 0:
                print(
                    f"\n✗ 同 pack_id 已存在 v{existing.version}（≥ 发布版本 v{version_str}）"
                    "；请提高版本号或删旧条目"
                )
                return 1
            listing.downloads = existing.downloads
            listing.rating = existing.rating
            listing.rating_count = existing.rating_count
            if not self.store.update_listing(listing):
                print("\n✗ 版本更新失败")
                return 1
            print(
                f"\n✓ Pack 已发布（{listing.pack_id} v{existing.version} → "
                f"v{listing.version}，单行覆盖更新）"
            )
        else:
            print(f"\n✓ Pack 已发布（{listing.pack_id} v{listing.version}）")
        if deps:
            print("  依赖:")
            for d in deps:
                print(f"    - {d['name']} {d['version']}")
        if approve:
            self.api.approve_pack(listing.pack_id)
            print("  状态: approved（--approve）")
        else:
            print("  状态: pending（上架需审核，或用 --approve 直批）")
        return 0

    # ---------- install ----------

    def install(self, name_spec: str) -> int:
        name, _, range_expr = name_spec.partition("@")
        range_expr = range_expr or "*"

        packs = self.api.list_packs().get("packs", [])
        candidates = [
            p for p in packs if p.get("pack_name") == name or p.get("pack_id") == name
        ]
        if not candidates:
            print(f"\n✗ 市场中未找到 Pack: {name}")
            return 1

        def _ver(p):
            try:
                return PackVersion.from_string(str(p.get("version", "0.0.0")))
            except Exception:
                return PackVersion.from_string("0.0.0")

        candidates.sort(key=_ver)
        chosen = None
        for p in reversed(candidates):
            if self._mk_dep(name, range_expr).is_compatible_with(str(p.get("version"))):
                chosen = p
                break
        if chosen is None:
            print(f"\n✗ 无版本满足约束 {name}@{range_expr}（可用: "
                  f"{', '.join(str(p.get('version')) for p in candidates)}）")
            return 1

        pack_id = str(chosen.get("pack_id"))
        version = str(chosen.get("version"))
        print(f"\n解析: {pack_id} v{version}（约束 {range_expr}）")

        listing = self.store.get_listing(pack_id)
        deps = list(getattr(listing, "dependencies", []) or [])
        if not deps:
            # 市场表无 dependencies 列（store 层不持久化依赖）——按既有边界
            # 「市场存元数据，正文以 packs/ 为准」，从本地正文 JSON 补依赖图。
            for body in sorted(self.packs_root.rglob(f"{pack_id}.json")):
                try:
                    body_pack = json.loads(body.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                deps = self._deps_from_pack(body_pack)
                if deps:
                    print(f"  依赖来源: {body}（市场库不存依赖）")
                    break
        root = DependencyNode(pack_id=pack_id, version=version)
        for d in deps:
            root.add_dependency(
                self._mk_dep(
                    str(d.get("name")),
                    str(d.get("version", "*")),
                    optional=bool(d.get("optional", False)),
                )
            )
        for d in deps:
            self.resolver.register_version(str(d.get("name")), str(d.get("version", "1.0.0")).lstrip(">=<^~* ") or "1.0.0")

        order = self.resolver.get_install_order(root) if deps else [pack_id]
        conflicts = self.resolver.detect_conflicts([root]) if deps else []
        if deps:
            print(f"  安装顺序: {' → '.join(order)}")
        if conflicts:
            print("  ⚠ 依赖冲突:")
            for c in conflicts:
                print(f"    - {c}")
        for d in deps:
            if not d.get("optional") and not self.resolver.check_compatibility(
                self._mk_dep(str(d.get("name")), str(d.get("version", "*"))),
                str(d.get("version", "")).lstrip(">=<^~* ") or "1.0.0",
            ):
                print(f"    ⚠ {d.get('name')} 当前版本不在约束 {d.get('version')} 内")

        index = self._load_index()
        index.setdefault("installed", {})[pack_id] = {
            "version": version,
            "range": range_expr,
            "dependencies": deps,
        }
        self._save_index(index)
        self.api.increment_downloads(pack_id)
        print(f"  ✓ 已登记到 {self.index_path}（下载计数 +1）")
        print("  注: 市场库只存元数据；Pack 正文请置于 packs/ 目录（examples/ 或 templates/）")
        return 0

    # ---------- upgrade ----------

    def upgrade(self, name: str) -> int:
        index = self._load_index()
        installed = index.get("installed", {})
        match_id = next(
            (pid for pid in installed if pid == name or pid.endswith(name)), None
        )
        if match_id is None:
            print(f"\n✗ 本地索引未安装: {name}（先 pack install）")
            return 1
        current = str(installed[match_id].get("version"))
        print(f"\n已装: {match_id} v{current}")

        packs = self.api.list_packs().get("packs", [])
        mine = [p for p in packs if p.get("pack_id") == match_id]
        if not mine:
            print("✗ 市场中未找到该 Pack，无法比对")
            return 1
        latest = max(mine, key=lambda p: PackVersion.from_string(str(p.get("version", "0.0.0"))))
        latest_v = str(latest.get("version"))
        print(f"市场最新: v{latest_v}")

        cur, lat = PackVersion.from_string(current), PackVersion.from_string(latest_v)
        if lat.compare(cur) <= 0:
            print("✓ 已是最新（或本地更新），无需升级")
            return 0

        breaking = lat.major != cur.major
        if breaking:
            print(f"⚠ 升级到 v{latest_v} 是主版本变更（{cur} → {lat}），可能含破坏性变更")
        # 与已装其它 Pack 的依赖约束做一次冲突扫描
        repars: list[DependencyNode] = []
        for pid, info in installed.items():
            node = DependencyNode(pack_id=pid, version=str(info.get("version")))
            for d in info.get("dependencies", []) or []:
                node.add_dependency(
                    self._mk_dep(
                        str(d.get("name")),
                        str(d.get("version", "*")),
                        optional=bool(d.get("optional", False)),
                    )
                )
            repars.append(node)
        conflicts = self.resolver.detect_conflicts(repars)
        if conflicts:
            print("  ⚠ 与已装 Pack 的依赖约束存在冲突:")
            for c in conflicts:
                print(f"    - {c}")
            print(f"建议: 先解决冲突再升；或保持 v{current}")
            return 1

        index["installed"][match_id]["version"] = latest_v
        self._save_index(index)
        print(f"✓ 升级完成: {match_id} v{current} → v{latest_v}")
        return 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Pack 市场管理 (publish/install/upgrade)")
    parser.add_argument("--db", default="data/packs.db", help="市场库路径")
    parser.add_argument("--packs-root", default="packs", help="本地 packs 目录")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pub = sub.add_parser("publish", help="发布 Pack（校验 + SemVer + 入库）")
    p_pub.add_argument("--path", required=True, help="Pack JSON 文件")
    p_pub.add_argument("--approve", action="store_true", help="直接批准上架")

    p_ins = sub.add_parser("install", help="安装 Pack（解析依赖 + 登记索引）")
    p_ins.add_argument("name", help="Pack 名称或 id，可带 @版本范围（如 demo@^1.0.0）")

    p_up = sub.add_parser("upgrade", help="升级 Pack（对比最新 + 冲突扫描）")
    p_up.add_argument("name", help="已安装的 Pack 名称或 id")

    args = parser.parse_args()
    cli = PackMarketCLI(db_path=args.db, packs_root=args.packs_root)
    if args.cmd == "publish":
        return cli.publish(args.path, approve=args.approve)
    elif args.cmd == "install":
        return cli.install(args.name)
    return cli.upgrade(args.name)


if __name__ == "__main__":
    sys.exit(main())
