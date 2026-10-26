#!/usr/bin/env python3
"""变异检查：改坏全局状态回收逻辑，对应守护用例必须变红。

工单 `TASK-P1-GLOBAL-STATE-GROWTH-001` 的验收标准要求「守护用例必须**反向
可验证**（把回收逻辑改坏 → 用例变红）」。只跑一遍全绿的测试证明不了任何事：
测试可能根本没测到那处代码，也可能断言写空了。

本脚本把产品代码复制到临时目录，逐条注入变异，然后跑守护用例：

- 变异必须让**指定的那条**用例报错（不是「随便哪条红」就算过）；
- 变异在工作区之外执行，不碰工作树；
- 任何一条变异「活了」（用例仍然全绿），脚本以非零码退出。

与 `chrome-extension/tests/real-machine/mutation-check.mjs` 是同一套纪律的
Python 版本。

用法：
    python3 scripts/check_global_state_reclaim_mutations.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 需要复制到临时目录的文件（守护用例要读它们；少复制会导致「假杀」或「杀不掉」）
COPY_PATHS = (
    "ai_collab",
    "tests/conftest.py",
    "tests/unit/test_state_manager_global_sync.py",
    "tests/unit/test_perf_isolation_guard.py",
    # 性能隔离守护会把性能套件整个跑一遍（在临时副本里），少复制就会「假红」
    "tests/perf",
    # 性能套件里的 longrun 用例会调起 scripts/longrun_harness.py
    "scripts/longrun_harness.py",
    "pyproject.toml",
)

GUARD_TEST = "tests/unit/test_state_manager_global_sync.py"
PERF_GUARD_TEST = "tests/unit/test_perf_isolation_guard.py"


@dataclass(frozen=True)
class Mutation:
    """一条变异：改哪段代码、改成什么、必须由哪条用例抓住。"""

    name: str
    old: str
    new: str
    expect_fail: str
    target: str = "ai_collab/state_manager.py"


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        name="回收逻辑整体失效（死条目一条不删）",
        old="            if self._global_entry_is_reclaimable(key, global_state.get(key)):",
        new="            if False:  # MUTATION",
        expect_fail="test_temp_workspace_entries_are_reclaimed_immediately",
    ),
    Mutation(
        name="临时目录不再被特殊对待（泄漏形态漏网）",
        old="        return real_path == temp_root or real_path.startswith(temp_root + os.sep)",
        new="        return False  # MUTATION",
        expect_fail="test_temp_workspace_entries_are_reclaimed_immediately",
    ),
    Mutation(
        name="宽限期失效（死条目一律立即回收）",
        old="        return self._global_entry_is_stale(value)",
        new="        return True  # MUTATION",
        expect_fail="test_dead_non_temp_workspace_is_kept_during_grace_period",
    ),
    Mutation(
        name="存在性判断恒真（什么都判成活着）",
        old="""        try:
            os.stat(path)
        except FileNotFoundError:
            return False""",
        new="""        try:
            os.stat(path)
        except FileNotFoundError:
            return True  # MUTATION""",
        expect_fail="test_temp_workspace_entries_are_reclaimed_immediately",
    ),
    Mutation(
        name="当前条目不再受保护（正在写的条目被自己删掉）",
        old="""        reclaimed: list[str] = []
        for key in list(global_state.keys()):
            if key == current_key:
                continue""",
        new="""        reclaimed: list[str] = []
        for key in list(global_state.keys()):
            if False:  # MUTATION
                continue""",
        expect_fail="test_current_workspace_entry_is_never_reclaimed",
    ),
    Mutation(
        name="条目数上限失效",
        old="        overflow = len(global_state) - GLOBAL_STATE_MAX_ENTRIES",
        new="        overflow = 0  # MUTATION",
        expect_fail="test_entry_count_cap_evicts_oldest_and_keeps_current",
    ),
    Mutation(
        name="体积上限失效",
        old="        if size <= GLOBAL_STATE_MAX_BYTES:",
        new="        if True:  # MUTATION",
        expect_fail="test_byte_cap_evicts_oldest",
    ),
    Mutation(
        name="淘汰顺序颠倒（先淘汰最新的）",
        old="        return sorted(global_state.items(), key=sort_key)",
        new="        return sorted(global_state.items(), key=sort_key, reverse=True)  # MUTATION",
        expect_fail="test_entry_count_cap_evicts_oldest_and_keeps_current",
    ),
    Mutation(
        name="条目 schema 被改（读取方的数据形状变了）",
        old='                "conflicts": self.state["conflicts"],',
        new='                "conflicts": self.state["conflicts"],\n                "extra_field": 1,  # MUTATION',
        expect_fail="test_entry_schema_is_unchanged",
    ),
    Mutation(
        name="判不出来的 key 也被回收",
        old="""        if not key or key in self._GLOBAL_UNJUDGEABLE_KEYS:
            return False""",
        new="""        if False:  # MUTATION
            return False""",
        expect_fail="test_unknown_key_is_not_reclaimed",
    ),
    Mutation(
        name="测试隔离失效（套件写进 ambient 全局文件）",
        old="""    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home""",
        new="""    pass  # MUTATION: 隔离装置被摘掉""",
        expect_fail="test_suite_does_not_write_the_ambient_global_state_file",
        target="tests/conftest.py",
    ),
)


def _copy_workspace(dest: Path) -> None:
    for rel in COPY_PATHS:
        source = PROJECT_ROOT / rel
        if not source.exists():
            raise SystemExit(f"缺少待复制的文件：{rel}")
        target = dest / rel
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def _run_guard(workspace: Path) -> tuple[int, str]:
    # 被守护子进程必须**自己**有一个隔离的 HOME：
    # 守护用例里有一条是「测试套件不得写进 ambient 全局文件」，而「ambient」
    # 是按子进程启动时的 HOME 算出来的。若透传开发机的 HOME，隔离装置一旦
    # 被变异破坏，守护就会往**开发机的真实全局文件**里写——守护自己成了
    # 污染源。这里给它一个临时 HOME：变异破坏隔离时，守护仍然会变红，
    # 但受影响的只是临时目录。
    fake_home = workspace / ".mutation-fake-home"
    fake_home.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["PYTHONPATH"] = str(workspace)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            GUARD_TEST,
            PERF_GUARD_TEST,
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    survivors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="global-state-mutation-") as tmp:
        workspace = Path(tmp)
        _copy_workspace(workspace)

        # 基线：未变异时守护必须全绿，否则「变异让用例变红」这件事没有意义
        code, output = _run_guard(workspace)
        if code != 0:
            print("基线不绿——未变异时守护用例就有问题，先修守护：\n")
            print(output[-4000:])
            return 2

        for mutation in MUTATIONS:
            target = workspace / mutation.target
            original = target.read_text(encoding="utf-8")
            if mutation.old not in original:
                print(f"❌ 变异落点失效：{mutation.name}")
                print(f"   在 {mutation.target} 里找不到这段代码：\n{mutation.old}")
                survivors.append(mutation.name)
                continue
            target.write_text(original.replace(mutation.old, mutation.new, 1), encoding="utf-8")
            try:
                code, output = _run_guard(workspace)
            finally:
                target.write_text(original, encoding="utf-8")

            killed = code != 0 and mutation.expect_fail in output
            if killed:
                print(f"✅ 被杀死：{mutation.name} → {mutation.expect_fail}")
            else:
                print(f"❌ 变异存活：{mutation.name}")
                print(f"   期望由 {mutation.expect_fail} 抓住，但该用例没报错")
                survivors.append(mutation.name)

    print()
    if survivors:
        print(f"有 {len(survivors)} 条变异存活：")
        for name in survivors:
            print(f"  - {name}")
        return 1
    print(f"全部 {len(MUTATIONS)} 条变异都被杀死。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
