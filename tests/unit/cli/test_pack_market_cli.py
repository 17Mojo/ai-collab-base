"""
Pack Market CLI Tests（publish / install / upgrade）

约定对齐 tests/unit/cli/test_pack_import_cli.py：
mock 边界在模块内名字（PackMarketAPI/PackMarketStore/DependencyResolver），
PackListing/PackDependency/PackVersion 等纯数据/逻辑类用真实现。
"""

import json
from unittest.mock import MagicMock, patch

from ai_collab.pack.market import PackStatus


def _pack_dict(pack_id="demo-pack", version="1.2.0", deps=None):
    """最小 Pack JSON 结构（满足 pack validate 同款发布闸门）"""
    return {
        "metadata": {
            "pack_id": pack_id,
            "pack_name": "Demo Pack",
            "version": version,
            "type": "content",
            "description": "demo pack",
            "designer": "tester",
            "created_at": "2026-11-05",
            "updated_at": "2026-11-05",
            "category": "general",
            "tags": ["demo"],
        },
        "domain": {},
        "workflow": {"steps": [{"id": "s1"}, {"id": "s2"}]},
        "quality_metrics": {"metrics": {"m1": {"weight": 1.0}}},
        "dependencies": deps or [],
    }


class TestPackMarketCLIInit:
    """构造函数接线"""

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_init(self, mock_api_class, mock_store_class, mock_resolver_class):
        from ai_collab.cli.pack_market import PackMarketCLI

        cli = PackMarketCLI(db_path="data/packs.db", packs_root="packs")

        mock_api_class.assert_called_once_with("data/packs.db")
        mock_store_class.assert_called_once_with("data/packs.db")
        mock_resolver_class.assert_called_once_with()
        assert cli.index_path.name == ".packs-index.json"
        assert cli.index_path.parent.name == "packs"


class TestPackMarketCLIMkDep:
    """_mk_dep 归一化（* 通配 / 部分版本补零 / AND 空格转逗号）"""

    def test_wildcard_matches_everything(self):
        from ai_collab.cli.pack_market import PackMarketCLI

        for expr in ("*", "", "x", "X", "any"):
            dep = PackMarketCLI._mk_dep("x", expr)
            assert dep.version_range == ">=0.0.0"
            assert dep.is_compatible_with("1.2.0")
            assert dep.is_compatible_with("9.9.9")

    def test_partial_version_padded(self):
        from ai_collab.cli.pack_market import PackMarketCLI

        dep = PackMarketCLI._mk_dep("x", "^1.0")
        assert dep.version_range == "^1.0.0"
        assert dep.is_compatible_with("1.2.0")
        assert not dep.is_compatible_with("2.0.0")

        dep2 = PackMarketCLI._mk_dep("x", ">=2")
        assert dep2.version_range == ">=2.0.0"
        assert dep2.is_compatible_with("2.1.0")

    def test_exact_version_unchanged(self):
        from ai_collab.cli.pack_market import PackMarketCLI

        dep = PackMarketCLI._mk_dep("x", "1.2.3")
        assert dep.version_range == "1.2.3"
        assert dep.is_compatible_with("1.2.3")
        assert not dep.is_compatible_with("1.2.4")

    def test_space_and_combo_normalized_to_comma(self):
        """dependency.py 检查路径只认 ','/'&'；空格 AND 必须转逗号否则永远 False"""
        from ai_collab.cli.pack_market import PackMarketCLI

        dep = PackMarketCLI._mk_dep("x", ">=1.0.0 <2.0.0")
        assert dep.version_range == ">=1.0.0,<2.0.0"
        assert dep.is_compatible_with("1.5.0")
        assert not dep.is_compatible_with("2.0.0")

    def test_or_combo_preserved(self):
        from ai_collab.cli.pack_market import PackMarketCLI

        dep = PackMarketCLI._mk_dep("x", "^1.0.0 | ^2.0.0")
        assert dep.version_range == "^1.0.0|^2.0.0"
        assert dep.is_compatible_with("1.5.0")
        assert dep.is_compatible_with("2.1.0")
        assert not dep.is_compatible_with("3.0.0")

    def test_optional_flag(self):
        from ai_collab.cli.pack_market import PackMarketCLI

        assert PackMarketCLI._mk_dep("x", "*", optional=True).optional is True
        assert PackMarketCLI._mk_dep("x", "*").optional is False


class TestPackMarketCLIPublish:
    """publish：schema 校验 + SemVer + 入市场库"""

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_success_pending(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        store.create_listing.return_value = True
        mock_store_class.return_value = store

        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict()), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 0
        store.create_listing.assert_called_once()
        listing = store.create_listing.call_args[0][0]
        assert listing.pack_id == "demo-pack"
        assert listing.pack_name == "Demo Pack"
        assert listing.version == "1.2.0"
        assert listing.status == PackStatus.PENDING
        mock_api_class.return_value.approve_pack.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_approve(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        store.create_listing.return_value = True
        mock_store_class.return_value = store

        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict()), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file), approve=True)

        assert code == 0
        mock_api_class.return_value.approve_pack.assert_called_once_with("demo-pack")

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_carries_dependencies(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        store.create_listing.return_value = True
        mock_store_class.return_value = store

        deps = [{"name": "base-pack", "version": "^1.0.0", "optional": True}]
        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict(deps=deps)), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 0
        listing = store.create_listing.call_args[0][0]
        assert listing.dependencies == [
            {"name": "base-pack", "version": "^1.0.0", "optional": True}
        ]

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_validation_failure(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        """缺必需顶层字段 → 阻断（pack validate 同款 error 判据）"""
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        mock_store_class.return_value = store

        bad = _pack_dict()
        del bad["domain"]
        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(bad), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 1
        store.create_listing.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_bad_version(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        mock_store_class.return_value = store

        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict(version="not-a-version")), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 1
        store.create_listing.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_missing_file(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        mock_store_class.return_value = store

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(tmp_path / "nonexistent.json"))

        assert code == 1
        store.create_listing.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_duplicate_same_version_rejected(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        """同 pack_id 已存在 ≥ 发布版本 → 拒发（单行模型，非更高版本不覆盖）"""
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        store.create_listing.return_value = False
        existing = MagicMock()
        existing.version = "1.2.0"
        store.get_listing.return_value = existing
        mock_store_class.return_value = store

        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict(version="1.2.0")), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 1
        store.update_listing.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_publish_newer_version_updates_row(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        """同 pack_id 发更高版本 → 单行覆盖更新（保留下载/评分计数）"""
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        store.create_listing.return_value = False
        existing = MagicMock()
        existing.version = "1.2.0"
        existing.downloads = 42
        existing.rating = 4.5
        existing.rating_count = 10
        store.get_listing.return_value = existing
        store.update_listing.return_value = True
        mock_store_class.return_value = store

        pack_file = tmp_path / "demo.json"
        pack_file.write_text(json.dumps(_pack_dict(version="2.0.0")), encoding="utf-8")

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.publish(str(pack_file))

        assert code == 0
        store.update_listing.assert_called_once()
        updated = store.update_listing.call_args[0][0]
        assert updated.version == "2.0.0"
        assert updated.downloads == 42
        assert updated.rating_count == 10


class TestPackMarketCLIInstall:
    """install：选版 + 依赖解析 + 登记本地索引"""

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_success(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}
            ]
        }
        mock_api_class.return_value = api

        store = MagicMock()
        listing = MagicMock()
        listing.dependencies = []
        store.get_listing.return_value = listing
        mock_store_class.return_value = store

        packs_root = tmp_path / "packs"
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.install("demo-pack")

        assert code == 0
        api.increment_downloads.assert_called_once_with("demo-pack")
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "1.2.0"
        assert index["installed"]["demo-pack"]["range"] == "*"

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_range_selects_compatible_version(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"},
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "2.0.0"},
            ]
        }
        mock_api_class.return_value = api

        store = MagicMock()
        listing = MagicMock()
        listing.dependencies = []
        store.get_listing.return_value = listing
        mock_store_class.return_value = store

        packs_root = tmp_path / "packs"
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.install("demo-pack@^1.0")  # 部分版本归一化 ^1.0 → ^1.0.0

        assert code == 0
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "1.2.0"  # 不选 2.0.0

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_not_found(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {"packs": []}
        mock_api_class.return_value = api

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.install("ghost")

        assert code == 1
        api.increment_downloads.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_no_version_satisfies_range(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "2.0.0"}
            ]
        }
        mock_api_class.return_value = api

        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs"))
        code = cli.install("demo-pack@^1.0.0")

        assert code == 1
        api.increment_downloads.assert_not_called()

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_with_dependencies(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        """带依赖：走安装顺序 + 冲突扫描 + 索引登记 dependencies"""
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}
            ]
        }
        mock_api_class.return_value = api

        deps = [{"name": "base-pack", "version": "^1.0.0", "optional": False}]
        store = MagicMock()
        listing = MagicMock()
        listing.dependencies = deps
        store.get_listing.return_value = listing
        mock_store_class.return_value = store

        resolver = MagicMock()
        resolver.get_install_order.return_value = ["base-pack", "demo-pack"]
        resolver.detect_conflicts.return_value = []
        resolver.check_compatibility.return_value = True
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs"
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.install("demo-pack")

        assert code == 0
        resolver.get_install_order.assert_called_once()
        resolver.detect_conflicts.assert_called_once()
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["dependencies"] == deps

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_deps_from_local_body(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        """市场条目 dependencies 为空（旧库存量条目）→ 从 packs/ 正文 JSON 补依赖图兜底"""
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}
            ]
        }
        mock_api_class.return_value = api

        store = MagicMock()
        listing = MagicMock()
        listing.dependencies = []  # 市场条目无依赖记录（N17 后为存量旧条目场景）
        store.get_listing.return_value = listing
        mock_store_class.return_value = store

        resolver = MagicMock()
        resolver.get_install_order.return_value = ["base-pack", "demo-pack"]
        resolver.detect_conflicts.return_value = []
        resolver.check_compatibility.return_value = True
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs" / "examples"
        packs_root.mkdir(parents=True)
        body_deps = [{"name": "base-pack", "version": "^1.0.0", "optional": False}]
        (packs_root / "demo-pack.json").write_text(
            json.dumps(_pack_dict(deps=body_deps)), encoding="utf-8"
        )

        cli = PackMarketCLI(
            db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs")
        )
        code = cli.install("demo-pack")

        assert code == 0
        resolver.get_install_order.assert_called_once()  # 走了依赖解析路径
        index = json.loads(
            (tmp_path / "packs" / ".packs-index.json").read_text(encoding="utf-8")
        )
        assert index["installed"]["demo-pack"]["dependencies"] == body_deps

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_install_prefers_store_dependencies(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path, capsys
    ):
        """市场表 dependencies 非空 → 以市场库为准，不走正文 JSON 兜底"""
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}
            ]
        }
        mock_api_class.return_value = api

        store_deps = [{"name": "store-base", "version": "^1.0.0", "optional": False}]
        store = MagicMock()
        listing = MagicMock()
        listing.dependencies = store_deps
        store.get_listing.return_value = listing
        mock_store_class.return_value = store

        resolver = MagicMock()
        resolver.get_install_order.return_value = ["store-base", "demo-pack"]
        resolver.detect_conflicts.return_value = []
        resolver.check_compatibility.return_value = True
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs" / "examples"
        packs_root.mkdir(parents=True)
        body_deps = [{"name": "body-base", "version": "^2.0.0", "optional": False}]
        (packs_root / "demo-pack.json").write_text(
            json.dumps(_pack_dict(deps=body_deps)), encoding="utf-8"
        )

        cli = PackMarketCLI(
            db_path=str(tmp_path / "packs.db"), packs_root=str(tmp_path / "packs")
        )
        code = cli.install("demo-pack")

        assert code == 0
        out = capsys.readouterr().out
        assert "依赖来源" not in out  # 未走正文兜底
        index = json.loads(
            (tmp_path / "packs" / ".packs-index.json").read_text(encoding="utf-8")
        )
        assert index["installed"]["demo-pack"]["dependencies"] == store_deps


class TestPackMarketCLIUpgrade:
    """upgrade：版本对比 + 依赖冲突扫描"""

    def _write_index(self, packs_root, installed):
        packs_root.mkdir(parents=True, exist_ok=True)
        (packs_root / ".packs-index.json").write_text(
            json.dumps({"version": "1.0.0", "installed": installed}), encoding="utf-8"
        )

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_upgrade_not_installed(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        packs_root = tmp_path / "packs"
        self._write_index(packs_root, {})
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.upgrade("demo-pack")

        assert code == 1

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_upgrade_already_latest(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}
            ]
        }
        mock_api_class.return_value = api

        packs_root = tmp_path / "packs"
        self._write_index(packs_root, {"demo-pack": {"version": "1.2.0", "dependencies": []}})
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.upgrade("demo-pack")

        assert code == 0
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "1.2.0"

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_upgrade_minor_success(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"},
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.5.0"},
            ]
        }
        mock_api_class.return_value = api

        resolver = MagicMock()
        resolver.detect_conflicts.return_value = []
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs"
        self._write_index(packs_root, {"demo-pack": {"version": "1.2.0", "dependencies": []}})
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.upgrade("demo-pack")

        assert code == 0
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "1.5.0"

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_upgrade_major_conflict_blocks(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path, capsys
    ):
        """主版本变更仍可升，但冲突扫描命中时阻断且索引不动"""
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "2.0.0"}
            ]
        }
        mock_api_class.return_value = api

        resolver = MagicMock()
        resolver.detect_conflicts.return_value = [{"conflict": "base-pack"}]
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs"
        self._write_index(
            packs_root,
            {
                "demo-pack": {
                    "version": "1.2.0",
                    "dependencies": [{"name": "base-pack", "version": "^1.0.0"}],
                }
            },
        )
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.upgrade("demo-pack")

        assert code == 1
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "1.2.0"  # 未升
        out = capsys.readouterr().out
        assert "主版本变更" in out  # 破坏性变更提示

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_upgrade_major_clean_passes(
        self, mock_api_class, mock_store_class, mock_resolver_class, tmp_path, capsys
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [
                {"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "2.0.0"}
            ]
        }
        mock_api_class.return_value = api

        resolver = MagicMock()
        resolver.detect_conflicts.return_value = []
        mock_resolver_class.return_value = resolver

        packs_root = tmp_path / "packs"
        self._write_index(packs_root, {"demo-pack": {"version": "1.2.0", "dependencies": []}})
        cli = PackMarketCLI(db_path=str(tmp_path / "packs.db"), packs_root=str(packs_root))
        code = cli.upgrade("demo-pack")

        assert code == 0
        index = json.loads((packs_root / ".packs-index.json").read_text(encoding="utf-8"))
        assert index["installed"]["demo-pack"]["version"] == "2.0.0"
        out = capsys.readouterr().out
        assert "主版本变更" in out


class TestPackMarketCLIHistory:
    """history：pack_versions 版本历史查询"""

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_history_lists_versions(
        self, mock_api_class, mock_store_class, mock_resolver_class, capsys
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        store = MagicMock()
        listing = MagicMock()
        listing.pack_id = "demo-pack"
        store.get_listing.return_value = listing
        store.list_versions.return_value = [
            {
                "version": "1.0.0",
                "status": "pending",
                "dependencies": [],
                "archived_at": "2026-11-05T10:00:00",
            },
            {
                "version": "2.0.0",
                "status": "approved",
                "dependencies": [{"name": "base", "version": "^1.0.0"}],
                "archived_at": "2026-11-05T11:00:00",
            },
        ]
        mock_store_class.return_value = store

        cli = PackMarketCLI(db_path="x.db", packs_root="packs")
        code = cli.history("demo-pack")

        assert code == 0
        store.list_versions.assert_called_once_with("demo-pack")
        out = capsys.readouterr().out
        assert "v1.0.0" in out and "v2.0.0" in out
        assert "base" in out  # 依赖明细

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_history_unknown_pack_returns_1(
        self, mock_api_class, mock_store_class, mock_resolver_class, capsys
    ):
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {"packs": []}
        mock_api_class.return_value = api

        store = MagicMock()
        store.get_listing.return_value = None
        store.list_versions.return_value = []
        mock_store_class.return_value = store

        cli = PackMarketCLI(db_path="x.db", packs_root="packs")
        code = cli.history("nope")

        assert code == 1
        assert "无版本历史" in capsys.readouterr().out

    @patch("ai_collab.cli.pack_market.DependencyResolver")
    @patch("ai_collab.cli.pack_market.PackMarketStore")
    @patch("ai_collab.cli.pack_market.PackMarketAPI")
    def test_history_resolves_pack_name_to_id(
        self, mock_api_class, mock_store_class, mock_resolver_class
    ):
        """pack_name 传入 → 经市场当前条目反查 pack_id 再查历史"""
        from ai_collab.cli.pack_market import PackMarketCLI

        api = MagicMock()
        api.list_packs.return_value = {
            "packs": [{"pack_id": "demo-pack", "pack_name": "Demo Pack", "version": "1.2.0"}]
        }
        mock_api_class.return_value = api

        store = MagicMock()
        store.get_listing.return_value = None  # 按名字直接查 id 查不到
        store.list_versions.return_value = [
            {"version": "1.2.0", "status": "pending", "dependencies": [], "archived_at": "t"}
        ]
        mock_store_class.return_value = store

        cli = PackMarketCLI(db_path="x.db", packs_root="packs")
        code = cli.history("Demo Pack")

        assert code == 0
        store.list_versions.assert_called_once_with("demo-pack")


class TestPackMarketCLIMain:
    """main() 参数解析（返回码约定对齐 pack_import.main）"""

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_publish(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.publish.return_value = 0
        mock_cli_class.return_value = cli

        with patch(
            "sys.argv",
            ["pack_market.py", "publish", "--path", "demo.json", "--approve"],
        ):
            code = main()

        assert code == 0
        cli.publish.assert_called_once_with("demo.json", approve=True)

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_publish_without_approve(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.publish.return_value = 0
        mock_cli_class.return_value = cli

        with patch("sys.argv", ["pack_market.py", "publish", "--path", "demo.json"]):
            code = main()

        assert code == 0
        cli.publish.assert_called_once_with("demo.json", approve=False)

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_install(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.install.return_value = 0
        mock_cli_class.return_value = cli

        with patch("sys.argv", ["pack_market.py", "install", "demo@^1.0.0"]):
            code = main()

        assert code == 0
        cli.install.assert_called_once_with("demo@^1.0.0")

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_upgrade(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.upgrade.return_value = 1
        mock_cli_class.return_value = cli

        with patch("sys.argv", ["pack_market.py", "upgrade", "demo"]):
            code = main()

        assert code == 1
        cli.upgrade.assert_called_once_with("demo")

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_custom_db_and_root(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.install.return_value = 0
        mock_cli_class.return_value = cli

        with patch(
            "sys.argv",
            ["pack_market.py", "--db", "x.db", "--packs-root", "p", "install", "demo"],
        ):
            main()

        mock_cli_class.assert_called_once_with(db_path="x.db", packs_root="p")

    @patch("ai_collab.cli.pack_market.PackMarketCLI")
    def test_main_history(self, mock_cli_class):
        from ai_collab.cli.pack_market import main

        cli = MagicMock()
        cli.history.return_value = 0
        mock_cli_class.return_value = cli

        with patch("sys.argv", ["pack_market.py", "history", "demo"]):
            code = main()

        assert code == 0
        cli.history.assert_called_once_with("demo")
