#!/usr/bin/env python3
"""测试 Prompt Pack 中期功能的 CLI 演示"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def demonstrate_version_management():
    """演示版本管理"""
    print("=" * 60)
    print("版本管理功能演示")
    print("=" * 60)

    from ai_collab.prompt_pack.version import PackVersion, VersionBumpType

    # 版本解析
    v = PackVersion.parse("1.2.3")
    print(f"\n✅ 解析版本: {v}")

    # 版本升级
    print(f"\n  * 主版本升级: {v} → {v.bump(VersionBumpType.MAJOR)}")
    print(f"  * 次版本升级: {v} → {v.bump(VersionBumpType.MINOR)}")
    print(f"  * 修订版本升级: {v} → {v.bump(VersionBumpType.PATCH)}")

    # 版本比较
    v2 = PackVersion.parse("1.5.0")
    comparison = v.compare_to(v2)
    print(f"\n✅ 版本比较: {v} vs {v2} → {comparison} (0=相等, -1=v<v2, 1=v>v2)")


def demonstrate_compatibility():
    """演示兼容性检查"""
    print("\n" + "=" * 60)
    print("兼容性检查功能演示")
    print("=" * 60)

    from ai_collab.prompt_pack.compatibility import CompatibilityChecker

    checker = CompatibilityChecker()

    # 模拟破坏性变更
    source = PackVersion.parse("1.0.0")
    target = PackVersion.parse("2.0.0")
    breaking_changes = [
        "Removed old_field from manifest",
        "Changed API endpoint format",
        "Default behavior changed",
    ]

    print(f"\n✅ 检查兼容性: {source} → {target}")
    report = checker.check_compatibility(source, target, breaking_changes)

    print(f"  * 状态: {report.status.value}")
    print(f"  * 问题数: {len(report.issues)}")
    compatible = report.is_compatible()
    print(f"  * 是否兼容: {('是' if compatible else '否')}")
    if report.summary:
        print(f"  * 摘要: {report.summary}")


def demonstrate_store():
    """演示 Pack 商店"""
    print("\n" + "=" * 60)
    print("Pack 商店功能演示")
    print("=" * 60)

    from ai_collab.prompt_pack.store import PackSortType, create_pack_store

    store_engine = create_pack_store()

    # 列出所有 Pack
    all_packs = store_engine.get_all_packs()
    print(f"\n✅ 所有 Pack ({len(all_packs)} 个):")
    for pack in all_packs:
        print(f"  * {pack.name} (v{pack.version}) - {pack.description}")

    # 搜索 Pack
    print("\n✅ 搜索 'web':")
    results = store_engine.search("web", PackSortType.POPULARITY, limit=3)
    for pack in results:
        print(f"  * {pack.name} (评分: {pack.rating}, 下载: {pack.downloads})")

    # 获取热门 Pack
    print("\n✅ 热门 Pack (前3):")
    trending = store_engine.get_trending_packs(limit=3)
    for pack in trending:
        print(f"  * {pack.name} (下载: {pack.downloads})")


def demonstrate_rating():
    """演示评分系统"""
    print("\n" + "=" * 60)
    print("评分系统功能演示")
    print("=" * 60)

    from ai_collab.prompt_pack.rating import create_rating_system

    rating_system = create_rating_system()

    # 获取现有评价
    for pack_name in ["web-dev-pack", "api-design-pack", "python-best-practices"]:
        try:
            rating_system.get_reviews(pack_name)
            summary = rating_system.get_rating_summary(pack_name)

            if summary.total_reviews > 0:
                print(f"\n✅ {pack_name}:")
                print(f"  * 平均评分: {summary.average_rating:.1f}/5.0")
                print(f"  * 评价总数: {summary.total_reviews}")
                print(f"  * 评分分布: {summary.rating_distribution}")
            else:
                print(f"\n✅ {pack_name}: 暂无评价")

        except FileNotFoundError:
            print(f"\nℹ️  {pack_name}: (未发现)")


def demonstrate_sharing():
    """演示权限管理"""
    print("\n" + "=" * 60)
    print("权限管理功能演示")
    print("=" * 60)

    from ai_collab.prompt_pack.sharing import create_permission_manager

    perm_mgr = create_permission_manager()

    # 检查公开状态
    for pack_name in ["web-dev-pack", "api-design-pack", "python-best-practices"]:
        try:
            perm_info = perm_mgr.get_user_permissions(pack_name, "default")

            print(f"\n✅ {pack_name} (用户: {perm_info['user']}):")
            print(f"  * 是所有者: {perm_info['is_owner']}")
            print(f"  * 读取权限: {perm_info['has_read']}")
            print(f"  * 写入权限: {perm_info['has_write']}")
            print(f"  * 管理权限: {perm_info['has_admin']}")
            if perm_info.get("permission_level"):
                print(f"  * 权限级别: {perm_info['permission_level']}")
        except FileNotFoundError:
            print(f"\nℹ️  {pack_name}: (未找到)")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Prompt Pack 中期功能 CLI 演示")
    print("=" * 60)

    try:
        demonstrate_version_management()
        demonstrate_compatibility()
        demonstrate_store()
        demonstrate_rating()
        demonstrate_sharing()

        print("\n" + "=" * 60)
        print("所有功能演示完成！")
        print("=" * 60)
        print("\n提示: 实际使用时，这些功能可以通过以下方式集成到 ai-collab CLI:")
        print("  * python-collab pack version bump --name web-dev-pack --type minor")
        print("  * ai-collab pack store search --query 'web'")
        print("  * ai-collab pack rate --name web-dev-pack --score 5")
        print("  * ai-collab pack share --name web-dev-pack --user alice --level write")
        print("\n")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
