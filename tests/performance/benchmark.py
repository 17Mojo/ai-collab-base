#!/usr/bin/env python3
"""
性能基准测试脚本

测试目标：
- API 响应时间 < 50ms
- NotebookLM 缓存命中率 > 30%
- Extension 加载时间 < 500ms
"""

import json
import statistics
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def benchmark_api_endpoints(base_url: str = "http://127.0.0.1:8000") -> dict:
    """
    测试 API 端点响应时间

    目标：所有端点 < 50ms
    """
    import urllib.request

    endpoints = [
        ("/health", "健康检查"),
        ("/api/packs", "获取 Pack 列表"),
        ("/api/packs/ai_collab_intro", "获取单个 Pack"),
        ("/metrics", "Prometheus Metrics"),
    ]

    results = []
    all_passed = True

    print("\n=== API 端点性能测试 ===")

    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        times: list[float] = []

        # 测试 5 次
        for i in range(5):
            try:
                start = time.time()
                urllib.request.urlopen(url, timeout=5)
                elapsed = (time.time() - start) * 1000  # 转换为毫秒
                times.append(elapsed)
            except Exception as e:
                print(f"  ❌ {description}: 请求失败 - {e}")
                all_passed = False

        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)

            passed = avg_time < 50
            status = "✅" if passed else "❌"

            print(f"  {status} {description}: avg={avg_time:.2f}ms, min={min_time:.2f}ms, max={max_time:.2f}ms")

            results.append({
                "endpoint": endpoint,
                "description": description,
                "avg_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time,
                "passed": passed,
                "target": 50,
            })

            if not passed:
                all_passed = False

    return {
        "test_name": "API Endpoint Performance",
        "passed": all_passed,
        "target": "< 50ms average",
        "results": results,
    }


def benchmark_notebooklm_cache() -> dict:
    """
    测试 NotebookLM 缓存性能

    目标：缓存命中 > 30%，相似问题匹配有效
    """
    import importlib.util

    cache_path = Path(__file__).parent.parent.parent / "local-backend" / "app" / "core" / "notebooklm_cache.py"
    spec = importlib.util.spec_from_file_location("notebooklm_cache", cache_path)
    if spec is None or spec.loader is None:
        return {"test_name": "NotebookLM Cache", "passed": False, "error": "无法加载模块"}

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    NotebookLMCache = module.NotebookLMCache

    print("\n=== NotebookLM 缓存性能测试 ===")

    cache = NotebookLMCache(
        default_ttl=3600,
        similarity_threshold=0.85,
        max_entries=100,
    )

    # 模拟查询
    test_questions = [
        "什么是 AI 协作系统?",
        "AI 协作系统是什么?",
        "如何使用 Prompt Pack?",
        "Prompt Pack 怎么用?",
        "Chrome Extension 如何安装?",
        "安装 Chrome Extension 的方法?",
        "什么是 AI 协作系统?",  # 重复查询
        "AI 协作系统架构是怎样的?",
    ]

    hits = 0
    misses = 0

    for question in test_questions:
        cached = cache.get_similar(question)
        if cached:
            hits += 1
            cache.record_query(hit=True)
        else:
            misses += 1
            cache.record_query(hit=False)
            # 模拟缓存新答案
            cache.cache_answer(question, f"关于 {question} 的回答...", ["doc1.pdf"])

    stats = cache.get_stats()
    hit_rate = float(stats["hit_rate"].replace("%", ""))

    passed = hit_rate >= 30
    status = "✅" if passed else "❌"

    print(f"  {status} 缓存命中率: {stats['hit_rate']} (目标 > 30%)")
    print(f"  {status} 相似匹配: {stats['similarity_matches']} 次")
    print(f"  {status} 缓存条目: {stats['total_entries']}")
    print(f"  预估时间节省: {stats['time_saved_ms']:.0f}ms")

    return {
        "test_name": "NotebookLM Cache",
        "passed": passed,
        "target": "> 30% hit rate",
        "hit_rate": hit_rate,
        "total_queries": stats["total_queries"],
        "cache_hits": stats["cache_hits"],
        "similarity_matches": stats["similarity_matches"],
        "time_saved_ms": stats["time_saved_ms"],
    }


def benchmark_extension_load_time(extension_dir: str = "chrome-extension") -> dict:
    """
    测试 Extension 加载时间（模拟）

    目标：< 500ms

    实际测试需要浏览器环境，这里估算文件大小
    """
    print("\n=== Extension 加载时间测试（模拟） ===")

    ext_path = Path(__file__).parent.parent.parent / extension_dir

    # 计算文件大小
    total_size = 0
    file_count = 0

    for f in ext_path.rglob("*"):
        if f.is_file() and not f.name.endswith((".map", ".test.js")):
            total_size += f.stat().st_size
            file_count += 1

    # 估算加载时间：每 KB 约 1ms（本地加载）
    estimated_time = total_size / 1024 * 1

    passed = estimated_time < 500
    status = "✅" if passed else "❌"

    print(f"  {status} 文件总数: {file_count}")
    print(f"  {status} 总大小: {total_size / 1024:.2f} KB")
    print(f"  {status} 估算加载时间: {estimated_time:.2f}ms (目标 < 500ms)")

    return {
        "test_name": "Extension Load Time",
        "passed": passed,
        "target": "< 500ms",
        "total_files": file_count,
        "total_size_kb": total_size / 1024,
        "estimated_load_ms": estimated_time,
    }


def run_all_benchmarks() -> dict:
    """运行所有基准测试"""
    print("=" * 60)
    print("AI Collab System 性能基准测试")
    print("=" * 60)

    results = []

    # 1. API 端点测试
    try:
        api_result = benchmark_api_endpoints()
        results.append(api_result)
    except Exception as e:
        print(f"  ❌ API 测试失败: {e}")
        results.append({"test_name": "API Endpoint Performance", "passed": False, "error": str(e)})

    # 2. NotebookLM 缓存测试
    try:
        cache_result = benchmark_notebooklm_cache()
        results.append(cache_result)
    except Exception as e:
        print(f"  ❌ NotebookLM 缓存测试失败: {e}")
        results.append({"test_name": "NotebookLM Cache", "passed": False, "error": str(e)})

    # 3. Extension 加载测试
    try:
        ext_result = benchmark_extension_load_time()
        results.append(ext_result)
    except Exception as e:
        print(f"  ❌ Extension 加载测试失败: {e}")
        results.append({"test_name": "Extension Load Time", "passed": False, "error": str(e)})

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)

    for r in results:
        status = "✅ PASS" if r.get("passed") else "❌ FAIL"
        print(f"  {status}: {r['test_name']}")

    print(f"\n总计: {passed_count}/{total_count} 通过")

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": total_count,
        "passed_tests": passed_count,
        "pass_rate": f"{(passed_count / total_count * 100):.0f}%",
        "results": results,
    }


def save_results(results: dict, output_file: str = "collaboration/results/PERFORMANCE_BENCHMARK_2026-04-29.json"):
    """保存测试结果"""
    output_path = Path(__file__).parent.parent.parent / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_path}")


if __name__ == "__main__":
    results = run_all_benchmarks()
    save_results(results)
