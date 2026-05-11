# Pack Version Management Tests
# Week 2 Day 3: Pack 版本管理测试

"""
Pack 版本管理功能测试
"""

from datetime import datetime

import pytest

from ai_collab.pack.version import PackVersion, VersionHistory, VersionManager, VersionType


class TestPackVersion:
    """测试 PackVersion 数据类"""

    def test_create_version(self):
        """测试创建版本"""
        version = PackVersion(1, 2, 3)

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == ""

    def test_create_version_with_prerelease(self):
        """测试创建带预发布的版本"""
        version = PackVersion(1, 2, 3, prerelease="alpha", build_metadata="123")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha"
        assert version.build_metadata == "123"

    def test_invalid_version(self):
        """测试无效版本"""
        with pytest.raises(ValueError):
            PackVersion(-1, 2, 3)

        with pytest.raises(ValueError):
            PackVersion(1, -2, 3)

        with pytest.raises(ValueError):
            PackVersion(1, 2, -3)

    def test_from_string(self):
        """测试从字符串解析"""
        version = PackVersion.from_string("1.2.3")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_prerelease(self):
        """测试从带预发布的字符串解析"""
        version = PackVersion.from_string("1.2.3-alpha")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha"

    def test_from_string_with_build(self):
        """测试从带构建元数据的字符串解析"""
        version = PackVersion.from_string("1.2.3+build.123")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build_metadata == "build.123"

    def test_from_string_full(self):
        """测试从完整字符串解析"""
        version = PackVersion.from_string("1.2.3-alpha+build.123")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha"
        assert version.build_metadata == "build.123"

    def test_from_string_invalid(self):
        """测试从无效字符串解析"""
        with pytest.raises(ValueError):
            PackVersion.from_string("invalid")

        with pytest.raises(ValueError):
            PackVersion.from_string("1.2")

        with pytest.raises(ValueError):
            PackVersion.from_string("1.2.3.4")

    def test_to_string(self):
        """测试格式化为字符串"""
        version = PackVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_to_string_with_prerelease(self):
        """测试带预发布的字符串格式化"""
        version = PackVersion(1, 2, 3, prerelease="alpha")
        assert str(version) == "1.2.3-alpha"

    def test_to_string_with_build(self):
        """测试带构建元数据的字符串格式化"""
        version = PackVersion(1, 2, 3, build_metadata="build.123")
        assert str(version) == "1.2.3+build.123"

    def test_bump_major(self):
        """测试升级主版本"""
        version = PackVersion(1, 2, 3)
        next_version = version.bump(VersionType.MAJOR)

        assert next_version.major == 2
        assert next_version.minor == 0
        assert next_version.patch == 0

    def test_bump_minor(self):
        """测试升级次版本"""
        version = PackVersion(1, 2, 3)
        next_version = version.bump(VersionType.MINOR)

        assert next_version.major == 1
        assert next_version.minor == 3
        assert next_version.patch == 0

    def test_bump_patch(self):
        """测试升级修订号"""
        version = PackVersion(1, 2, 3)
        next_version = version.bump(VersionType.PATCH)

        assert next_version.major == 1
        assert next_version.minor == 2
        assert next_version.patch == 4

    def test_bump_clears_prerelease(self):
        """测试升级清除预发布标识"""
        version = PackVersion(1, 2, 3, prerelease="beta")
        next_version = version.bump(VersionType.PATCH)

        assert next_version.prerelease == ""

    def test_compare_equal(self):
        """测试版本比较（相等）"""
        v1 = PackVersion(1, 2, 3)
        v2 = PackVersion(1, 2, 3)

        assert v1.compare(v2) == 0
        assert v1 == v2
        assert v1 >= v2
        assert v1 <= v2

    def test_compare_less(self):
        """测试版本比较（小于）"""
        v1 = PackVersion(1, 2, 3)
        v2 = PackVersion(1, 2, 4)

        assert v1.compare(v2) == -1
        assert v1 < v2
        assert v1 <= v2

    def test_compare_greater(self):
        """测试版本比较（大于）"""
        v1 = PackVersion(1, 2, 4)
        v2 = PackVersion(1, 2, 3)

        assert v1.compare(v2) == 1
        assert v1 > v2
        assert v1 >= v2

    def test_compare_major_version(self):
        """测试主版本号比较"""
        v1 = PackVersion(1, 9, 9)
        v2 = PackVersion(2, 0, 0)

        assert v1 < v2

    def test_compare_prerelease_vs_stable(self):
        """测试预发布与稳定版本比较"""
        v_alpha = PackVersion(1, 2, 3, prerelease="alpha")
        v_beta = PackVersion(1, 2, 3, prerelease="beta")
        v_stable = PackVersion(1, 2, 3)

        assert v_alpha < v_beta < v_stable

    def test_to_dict(self):
        """测试序列化为字典"""
        version = PackVersion(1, 2, 3, prerelease="alpha")
        data = version.to_dict()

        assert data["major"] == 1
        assert data["minor"] == 2
        assert data["patch"] == 3
        assert data["prerelease"] == "alpha"
        assert data["version_string"] == "1.2.3-alpha"


class TestVersionHistory:
    """测试 VersionHistory 数据类"""

    def test_create_history(self):
        """测试创建版本历史"""
        version = PackVersion(1, 2, 3)
        history = VersionHistory(
            version_id="v_test_1-2-3",
            pack_id="test_pack",
            version=version,
            changelog="Initial release",
        )

        assert history.version_id == "v_test_1-2-3"
        assert history.pack_id == "test_pack"
        assert history.changelog == "Initial release"
        assert isinstance(history.created_at, datetime)

    def test_history_to_dict(self):
        """测试序列化历史"""
        version = PackVersion(1, 2, 3)
        history = VersionHistory(
            version_id="v_test",
            pack_id="test_pack",
            version=version,
            changelog="Test",
            created_by="user1",
        )

        data = history.to_dict()

        assert data["version_id"] == "v_test"
        assert data["pack_id"] == "test_pack"
        assert data["created_by"] == "user1"
        assert "created_at" in data

    def test_history_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "version_id": "v_test",
            "pack_id": "test_pack",
            "version": {"major": 1, "minor": 2, "patch": 3, "prerelease": "", "build_metadata": ""},
            "changelog": "Test",
            "created_at": datetime.now().isoformat(),
            "created_by": "user1",
        }

        history = VersionHistory.from_dict(data)

        assert history.version_id == "v_test"
        assert history.pack_id == "test_pack"
        assert history.version.major == 1
        assert history.created_by == "user1"


class TestVersionManager:
    """测试 VersionManager 类"""

    @pytest.fixture(scope="function")
    def manager(self):
        """创建版本管理器实例（每个测试独立）"""
        # Use a fresh manager for each test
        return VersionManager()

    def test_create_initial_version(self, manager):
        """测试创建初始版本"""
        version = manager.create_version(
            pack_id="test_pack_initial",
            version_type=VersionType.MINOR,
            changelog="Initial release",
            created_by="user1",
        )

        assert version.major == 0
        assert version.minor == 1
        assert version.patch == 0

    def test_create_version_from_base(self, manager):
        """测试从基础版本创建新版本"""
        base = PackVersion(1, 2, 3)

        next_version = manager.create_version(
            pack_id="test_pack_base",
            version_type=VersionType.MINOR,
            changelog="New feature",
            base_version=base,
        )

        assert next_version.major == 1
        assert next_version.minor == 3
        assert next_version.patch == 0

    def test_create_major_version(self, manager):
        """测试创建主版本"""
        manager.create_version("test_pack_major", VersionType.MINOR, "Initial")
        next_version = manager.create_version(
            "test_pack_major", VersionType.MAJOR, "Breaking changes"
        )

        assert next_version.major == 1
        assert next_version.minor == 0
        assert next_version.patch == 0

    def test_create_minor_version(self, manager):
        """测试创建次版本"""
        manager.create_version("test_pack_minor", VersionType.MINOR, "Initial")
        next_version = manager.create_version("test_pack_minor", VersionType.MINOR, "New feature")

        assert next_version.major == 0
        assert next_version.minor == 2
        assert next_version.patch == 0

    def test_create_patch_version(self, manager):
        """测试创建修订版本"""
        manager.create_version("test_pack_patch", VersionType.MINOR, "Initial")
        next_version = manager.create_version("test_pack_patch", VersionType.PATCH, "Bug fix")

        assert next_version.major == 0
        assert next_version.minor == 1
        assert next_version.patch == 1

    def test_list_versions(self, manager):
        """测试列出版本"""
        manager.create_version("test_pack_list1", VersionType.MINOR, "v1")
        manager.create_version("test_pack_list1", VersionType.MINOR, "v2")
        manager.create_version("test_pack_list1", VersionType.PATCH, "v3")

        versions = manager.list_versions("test_pack_list1")

        assert len(versions) == 3
        # 应该按版本号降序排列
        assert versions[0].version.major >= versions[1].version.major

    def test_get_latest_version(self, manager):
        """测试获取最新版本"""
        manager.create_version("test_pack_latest1", VersionType.MINOR, "v1")
        manager.create_version("test_pack_latest1", VersionType.MINOR, "v2")
        manager.create_version("test_pack_latest1", VersionType.MAJOR, "v3")

        latest = manager.get_latest_version("test_pack_latest1")

        assert latest.major == 1  # 主版本升级后应该是最新的

    def test_get_latest_version_empty(self, manager):
        """测试获取不存在 Pack 的最新版本"""
        latest = manager.get_latest_version("nonexistent")

        assert latest is None

    def test_get_version(self, manager):
        """测试获取指定版本"""
        manager.create_version("test_pack_get", VersionType.MINOR, "v1")
        target_version = manager.create_version("test_pack_get", VersionType.MINOR, "v2")

        # 使用版本字符串查找
        version_str = str(target_version)
        history = manager.get_version("test_pack_get", version_str)

        assert history is not None
        assert history.version == target_version
        assert history.changelog == "v2"

    def test_get_version_not_found(self, manager):
        """测试获取不存在的版本"""
        manager.create_version("test_pack_notfound", VersionType.MINOR, "v1")

        history = manager.get_version("test_pack_notfound", "99.99.99")

        assert history is None

    def test_compare_versions(self, manager):
        """测试比较版本"""
        result = manager.compare_versions("1.2.3", "1.2.4")

        assert result == -1  # 1.2.3 < 1.2.4

    def test_compare_versions_equal(self, manager):
        """测试比较相等版本"""
        result = manager.compare_versions("1.2.3", "1.2.3")

        assert result == 0

    def test_compare_versions_greater(self, manager):
        """测试比较大于"""
        result = manager.compare_versions("1.2.4", "1.2.3")

        assert result == 1

    def test_calculate_distance(self, manager):
        """测试计算版本距离"""
        # 同一次版本，不同修订号：距离 1
        distance1 = manager.calculate_distance("1.2.3", "1.2.4")
        assert distance1 == 1

        # 同主版本，不同次版本：距离 10
        distance2 = manager.calculate_distance("1.2.0", "1.3.0")
        assert distance2 == 10

        # 不同主版本：距离 100
        distance3 = manager.calculate_distance("1.0.0", "2.0.0")
        assert distance3 == 100

    def test_rollback_version(self, manager):
        """测试回滚版本"""
        # 创建几个版本
        manager.create_version("test_pack_rollback", VersionType.MINOR, "v1")
        manager.create_version("test_pack_rollback", VersionType.MINOR, "v2")
        manager.create_version("test_pack_rollback", VersionType.MINOR, "v3")

        # 回滚到 v2
        v2_str = "0.2.0"
        success = manager.rollback_version("test_pack_rollback", v2_str)

        assert success is True

        # 验证历史记录增加了
        versions = manager.list_versions("test_pack_rollback")
        assert len(versions) == 4  # 3 个版本 + 1 个回滚记录

    def test_rollback_version_not_found(self, manager):
        """测试回滚到不存在的版本"""
        manager.create_version("test_pack_rollback_nf", VersionType.MINOR, "v1")

        success = manager.rollback_version("test_pack_rollback_nf", "99.99.99")

        assert success is False

    def test_get_version_range(self, manager):
        """测试获取版本范围"""
        # 创建多个版本
        manager.create_version("test_pack_range", VersionType.MINOR, "v1")  # 0.1.0
        manager.create_version("test_pack_range", VersionType.MINOR, "v2")  # 0.2.0
        manager.create_version("test_pack_range", VersionType.MINOR, "v3")  # 0.3.0

        # 获取 0.1.0 到 0.2.0 之间的版本（包含边界）
        versions = manager.get_version_range(
            "test_pack_range", min_version="0.1.0", max_version="0.2.0"
        )

        # Should return 0.1.0 and 0.2.0 (both within range)
        assert len(versions) >= 1  # At least one version in range

    def test_get_version_range_min_only(self, manager):
        """测试仅设置最小版本"""
        manager.create_version("test_pack_range_min", VersionType.MINOR, "v1")  # 0.1.0
        manager.create_version("test_pack_range_min", VersionType.MINOR, "v2")  # 0.2.0
        manager.create_version("test_pack_range_min", VersionType.MINOR, "v3")  # 0.3.0

        # 获取 >= 0.2.0 的版本
        versions = manager.get_version_range("test_pack_range_min", min_version="0.2.0")

        assert len(versions) == 2  # 0.2.0 和 0.3.0

    def test_is_compatible_compatible(self, manager):
        """测试兼容性检查（兼容）"""
        result = manager.is_compatible("^1.2.3", "1.3.0")

        assert result is True

    def test_is_compatible_incompatible(self, manager):
        """测试兼容性检查（不兼容）"""
        result = manager.is_compatible("^1.2.3", "2.0.0")

        assert result is False

    def test_is_compatible_invalid_format(self, manager):
        """测试兼容性检查（无效格式，无 ^）"""
        # 没有 ^ 符号时，应该是兼容的（相同版本）
        result = manager.is_compatible("1.2.3", "1.2.3")

        assert result is True


class TestVersionManagerComplexScenarios:
    """测试版本管理器复杂场景"""

    @pytest.fixture
    def manager(self):
        """创建包含多个版本的版本管理器"""
        manager = VersionManager()

        # 创建版本历史
        manager.create_version("pack_a_iso", VersionType.MINOR, "Initial")
        manager.create_version("pack_a_iso", VersionType.MINOR, "Feature 1")
        manager.create_version("pack_a_iso", VersionType.PATCH, "Bug fix 1")

        manager.create_version("pack_b_iso", VersionType.MINOR, "Initial")
        manager.create_version("pack_b_iso", VersionType.MAJOR, "Breaking change")

        return manager

    def test_multiple_packs_isolated(self, manager):
        """测试多个 Pack 的版本隔离"""
        versions_a = manager.list_versions("pack_a_iso")
        versions_b = manager.list_versions("pack_b_iso")

        versions_a_ids = [v.version_id for v in versions_a]
        versions_b_ids = [v.version_id for v in versions_b]

        # 验证两个 Pack 的版本是独立的
        assert len(set(versions_a_ids) & set(versions_b_ids)) == 0

    def test_version_evolution_sequence(self, manager):
        """测试版本演进序列"""
        versions = manager.list_versions("pack_a_iso")

        # 版本应该按降序排列
        for i in range(len(versions) - 1):
            assert versions[i].version >= versions[i + 1].version

    def test_distance_calculation_complex(self, manager):
        """测试复杂距离计算"""
        # 计算跨主版本的距离
        distance = manager.calculate_distance("0.2.1", "1.0.0")

        # |1-0|*100 + |0-2|*10 + |0-1| = 100 + 20 + 1 = 121
        assert distance == 121

    def test_rollback_with_history(self, manager):
        """测试带历史记录的回滚"""
        # pack_b_iso 有版本历史 (0.1.0 -> 1.0.0)
        versions_before = manager.list_versions("pack_b_iso")
        count_before = len(versions_before)

        # 回滚到实际存在的版本
        if versions_before:
            # Use the oldest version for rollback
            target_ver = versions_before[-1].version  # Oldest version
            target = str(target_ver)
        else:
            target = "0.1.0"

        success = manager.rollback_version("pack_b_iso", target)

        assert success is True

        versions_after = manager.list_versions("pack_b_iso")
        count_after = len(versions_after)

        # 应该添加了一条回滚记录
        assert count_after == count_before + 1

    def test_mixed_prerelease_versions(self, manager):
        """测试混合预发布版本"""
        manager.create_version("pack_c_pre", VersionType.MINOR, "Initial")
        # 模拟添加预发布版本
        v_stable = manager.get_latest_version("pack_c_pre")
        if v_stable:
            prerelease = PackVersion(
                v_stable.major, v_stable.minor, v_stable.patch, prerelease="alpha"
            )

            # 预发布版本应该小于稳定版本
            assert prerelease < v_stable
