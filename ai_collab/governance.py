"""治理覆盖层：账本互斥原子写入、合并提交登记、覆盖率判定、门禁输入契约、开工检查。

设计契约见 openspec/changes/restore-governance-enforcement/design.md。

本模块刻意只依赖标准库与仓库内的普通文件，不读取任何 Agent 平台配置、不识别
会话或模型身份。事实源是磁盘，门禁与执行主体解耦 —— 这是「多会话 + 多模型」
能取代编排框架而不必重写工单系统的前提。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

# 决策总闸：2026-11-15 翻闸（Phase 4）。观测期证据见 tasks.md 的 E7 / E8
# 与验收场景 A1-A5；改回 False 可回到决策冻结态。
# 不使用 CLI 旋钮，避免误传误用。
COVERAGE_IN_DECISION = True

# 登记表必须与启用改动同 commit 落盘（spec D2），所以不能放 logs/：
# .gitignore:39 的 `logs/` 没有取反规则，且 git 不允许重新包含被排除目录下的文件。
LEDGER_REL = "collaboration/governance/governance-ledger.jsonl"
OBSERVE_REL = "logs/governance_coverage_observe.jsonl"
STATE_REL = "logs/collaboration_state.json"
ACK_BRIDGE_REL = "logs/agent_ack_bridge_state.json"
RECEIPT_REL = "logs/agent_receipt_state.json"

MANAGED_LEDGERS = (STATE_REL, ACK_BRIDGE_REL, RECEIPT_REL)
LEDGER_FILENAMES = (
    "collaboration_state.json",
    "agent_ack_bridge_state.json",
    "agent_receipt_state.json",
)
# 唯一允许直接写上述账本的文件（它们使用本模块的互斥原子入口）。
ALLOWED_STATE_WRITERS = {"ai_collab/state_manager.py", "ai_collab/governance.py"}
# 直接落盘的通用写函数；用它们写受管账本即视为绕过统一入口。
FORBIDDEN_WRITE_CALLS = frozenset({"write_text", "write_json", "_write_json", "dump", "save", "open"})
# 统一入口本身：这些调用就是互斥原子写入，不算绕过。
UNIFIED_WRITE_CALLS = frozenset(
    {"locked_json_update", "append_jsonl", "atomic_write_json", "_atomic_write_json", "merge_state_write"}
)

LEDGER_DIR_REL = "collaboration/governance"

REQUIRED_READS = (
    "collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md",
    "collaboration/COLLABORATION_GUIDELINES.md",
    "collaboration/PROTOCOL.md",
    "rules/AI-COLLABORATION-STANDARDS.md",
)

T = TypeVar("T")


class GovernanceError(ValueError):
    """治理事实源不可用或声明不合法。"""


# --------------------------------------------------------------------------
# 统一 IO：跨进程互斥 + 锁内重读 + 原子替换
# --------------------------------------------------------------------------
def lock_path_for(target: Path) -> Path:
    """与 state_manager._file_lock 共用同一套锁文件命名（realpath 归一化）。"""
    return Path(f"{os.path.realpath(target)}.lock")


@contextmanager
def file_lock(
    target: Path,
    *,
    timeout_sec: float = 5.0,
    stale_sec: float = 120.0,
    poll_interval: float = 0.05,
) -> Iterator[None]:
    """通过 lock 文件提供跨进程互斥；锁只保护「读-改-写」临界区。"""
    lock_file = lock_path_for(target)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    fd: int | None = None
    token = uuid.uuid4().hex

    while True:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{token}|{os.getpid()}|{datetime.now().isoformat()}\n".encode())
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock_file) > stale_sec:
                    os.remove(lock_file)
                    continue
            except FileNotFoundError:
                continue
            if time.time() - start >= timeout_sec:
                raise TimeoutError(f"获取文件锁超时: {lock_file}") from None
            time.sleep(poll_interval)

    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            if lock_file.exists():
                if lock_file.read_text(encoding="utf-8")[:128].startswith(f"{token}|"):
                    lock_file.unlink()
        except (FileNotFoundError, OSError):
            pass


def atomic_write_json(target: Path, payload: Any) -> None:
    """mkstemp + fsync + os.replace；中断不会留下半截文件。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".gov_tmp_", suffix=".json", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_json(target: Path, default: Any) -> Any:
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _read_json_strict(target: Path, default: Any) -> Any:
    """受管账本已损坏时拒绝覆盖，避免把半截文件静默重置成空账本。"""
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GovernanceError(f"账本内容损坏，拒绝覆盖: {target}: {exc}") from exc


def locked_json_update(target: Path, default: Any, mutate: Callable[[Any], T]) -> tuple[Any, T]:
    """在同一把锁内完成「读取最新内容 → 修改 → 原子写回」。"""
    with file_lock(target):
        payload = _read_json_strict(target, default)
        result = mutate(payload)
        atomic_write_json(target, payload)
    return payload, result


def merge_state_write(target: Path, state: dict[str, Any], *, default: Any = None) -> dict[str, Any]:
    """兼容层：调用方已经算好整份状态时，把它合并进锁内最新账本。

    保留并发方新增的键；`tasks` / `patches` 这类以 ID 为键的字典逐条合并，
    不整体替换，避免把别人刚写入的记录抹掉。写入仍在统一互斥原子入口内完成，
    且以锁内重读的最新内容为准。
    """

    def mutate(latest: Any) -> None:
        if not isinstance(latest, dict):
            return
        for key, value in state.items():
            if key in ("tasks", "patches") and isinstance(value, dict):
                existing = latest.get(key)
                merged = dict(existing) if isinstance(existing, dict) else {}
                merged.update(value)
                latest[key] = merged
            else:
                latest[key] = value

    payload, _ = locked_json_update(target, default if default is not None else {}, mutate)
    return payload


def append_jsonl(target: Path, record: dict[str, Any]) -> None:
    """append-only 写入；同样加锁，避免多执行主体并发追加交错。"""
    with file_lock(target):
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def is_managed_ledger(path: Path | str) -> bool:
    """按文件名判定受管账本；用于运行时守卫，覆盖拼接出来的动态路径。"""
    return Path(path).name in LEDGER_FILENAMES


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _strings(node: ast.AST) -> set[str]:
    return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _mentions_ledger(node: ast.AST, symbols: set[str]) -> bool:
    if any(fname in text for text in _strings(node) for fname in LEDGER_FILENAMES):
        return True
    return bool(_names(node) & symbols)


def _has_ledger_attr(node: ast.AST, attrs: set[str]) -> bool:
    return any(isinstance(sub, ast.Attribute) and sub.attr in attrs for sub in ast.walk(node))


def _is_ledger_literal(node: ast.AST) -> bool:
    return any(fname in text for text in _strings(node) for fname in LEDGER_FILENAMES)


def _is_path_expr(node: ast.AST, symbols: set[str]) -> bool:
    """只认「返回路径」的表达式。

    关键：`read_json(workspace / ... / collaboration_state.json, ...)` 的返回值是
    **数据**而不是路径，不能因为参数里有账本名就把 `state` 染成账本符号。
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
        return _is_ledger_literal(node) or bool(_names(node) & symbols)
    if isinstance(node, ast.Call):
        return _call_name(node) in {"Path", "joinpath", "resolve"} and (
            _is_ledger_literal(node) or bool(_names(node) & symbols)
        )
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return any(fname in node.value for fname in LEDGER_FILENAMES)
    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
        return bool(_names(node) & symbols)
    return False


def _base_symbols(tree: ast.Module) -> tuple[set[str], set[str]]:
    """模块级常量与 argparse 默认值：全文件有效。"""
    symbols: set[str] = set()
    attrs: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            if not _is_ledger_literal(node.value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id != "_":
                    symbols.add(target.id)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "add_argument":
            option = next(
                (a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)),
                "",
            )
            default = next((kw.value for kw in node.keywords if kw.arg == "default"), None)
            if option.startswith("--") and default is not None and _is_ledger_literal(default):
                attrs.add(option[2:].replace("-", "_"))
    return symbols, attrs


def _collect_scopes(tree: ast.Module) -> list[list[ast.AST]]:
    """把每个节点归到最内层函数作用域；模块级单独一组。

    同名局部变量在不同函数里可以指向完全不同的文件，符号集合必须按作用域隔离：
    agent_dispatch_bridge.py 的 `state_file` 在读函数里是受管账本、在写函数里
    是 dispatch 账本，按文件合并符号会把后者误报成绕过写入。
    """
    scopes: list[list[ast.AST]] = []
    module_nodes: list[ast.AST] = []

    def visit(node: ast.AST, current: list[ast.AST]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            own: list[ast.AST] = [node]
            scopes.append(own)
            for child in ast.iter_child_nodes(node):
                visit(child, own)
            return
        current.append(node)
        for child in ast.iter_child_nodes(node):
            visit(child, current)

    for child in ast.iter_child_nodes(tree):
        visit(child, module_nodes)
    scopes.insert(0, module_nodes)
    return scopes


def _scope_symbols(nodes: list[ast.AST], base: set[str]) -> set[str]:
    """单个作用域内「指向受管账本」的符号：参数默认值 + 路径赋值不动点。"""
    symbols = set(base)
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            pairs = list(zip(a.args[-len(a.defaults) :] if a.defaults else [], a.defaults, strict=False))
            pairs += [(arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults, strict=False) if d is not None]
            for arg, default in pairs:
                if _mentions_ledger(default, symbols):
                    symbols.add(arg.arg)

    for _ in range(4):
        before = set(symbols)
        for node in nodes:
            targets: list[ast.expr] = []
            value: ast.AST | None = None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            if value is None:
                continue
            from_loader = isinstance(value, ast.Call) and _call_name(value) == "load_ack_bridge_state"
            if not from_loader and not _is_path_expr(value, symbols):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id != "_":
                    symbols.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)) and from_loader and target.elts:
                    # load_ack_bridge_state() 首位返回账本路径；其余位置不标记。
                    first = target.elts[0]
                    if isinstance(first, ast.Name) and first.id != "_":
                        symbols.add(first.id)
        if symbols == before:
            break
    return symbols


def _scan_file(source: Path, rel: str) -> list[str]:
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    base, attrs = _base_symbols(tree)
    hits: set[str] = set()
    for nodes in _collect_scopes(tree):
        symbols = _scope_symbols(nodes, base)
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in UNIFIED_WRITE_CALLS or name not in FORBIDDEN_WRITE_CALLS:
                continue
            if name == "open":
                mode = (
                    node.args[1]
                    if len(node.args) > 1
                    else next((kw.value for kw in node.keywords if kw.arg == "mode"), None)
                )
                writable = mode is not None and any(
                    isinstance(c, ast.Constant) and isinstance(c.value, str) and any(ch in c.value for ch in "wax+")
                    for c in ast.walk(mode)
                )
                if not writable:
                    continue
            probes: list[ast.AST] = []
            if isinstance(node.func, ast.Attribute):
                # path.write_text(content) / json.dump(data, handle)：接收者才是路径，
                # 第一个参数是内容，不能拿它做账本判定。
                probes.append(node.func.value)
            elif node.args:
                probes.append(node.args[0])
            if any(_mentions_ledger(p, symbols) or _has_ledger_attr(p, attrs) for p in probes):
                hits.add(f"{rel}:{node.lineno}:{name}()")
    return sorted(hits)


def find_direct_state_writes(workspace: Path) -> list[str]:
    """AST 确定性扫描 ai_collab/ 与 scripts/，点名绕过统一入口的直写路径。"""
    hits: list[str] = []
    for root in ("ai_collab", "scripts"):
        base = workspace / root
        if not base.is_dir():
            continue
        for source in sorted(base.rglob("*.py")):
            rel = source.relative_to(workspace).as_posix()
            if rel in ALLOWED_STATE_WRITERS or "__pycache__" in rel:
                continue
            hits.extend(_scan_file(source, rel))
    return sorted(hits)


def check_direct_writes(workspace: Path) -> dict[str, Any]:
    """供 CLI 使用：命中即 pass=False，调用方据此非零退出。"""
    hits = find_direct_state_writes(workspace)
    return {"pass": not hits, "checked": len(hits), "hits": hits}


# --------------------------------------------------------------------------
# 治理登记表
# --------------------------------------------------------------------------
def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _is_commit(workspace: Path, sha: str) -> bool:
    if not sha or len(sha) < 7:
        return False
    return _git(workspace, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def load_ledger(workspace: Path) -> tuple[list[dict[str, Any]], str | None]:
    """严格读取登记表：缺失、空文件、任一非法行都返回错误，不静默当作「无未登记项」。"""
    path = workspace / LEDGER_REL
    if not path.exists():
        return [], f"登记表缺失: {LEDGER_REL}"
    rows: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            return [], f"登记表第 {lineno} 行无法解析: {exc.msg}"
        if not isinstance(item, dict) or not item.get("kind"):
            return [], f"登记表第 {lineno} 行缺少 kind"
        rows.append(item)
    if not rows:
        return [], f"登记表为空: {LEDGER_REL}"
    return rows, None


def enforced_from(workspace: Path) -> tuple[str | None, str | None]:
    rows, error = load_ledger(workspace)
    if error:
        return None, error
    markers = [r for r in rows if r.get("kind") == "enforcement"]
    if len(markers) != 1:
        return None, f"生效边界声明必须为且仅为 1 条，实际 {len(markers)} 条"
    sha = str(markers[0].get("commit_sha") or "").strip()
    if not _is_commit(workspace, sha):
        return None, f"生效边界不是合法 commit: {sha!r}"
    return sha, None


def declare_enforcement(workspace: Path, commit_sha: str, reason: str, declared_by: str) -> dict[str, Any]:
    if not _is_commit(workspace, commit_sha):
        raise GovernanceError(f"生效边界不是合法 commit: {commit_sha!r}")
    if len(reason.strip()) < 10:
        raise GovernanceError("理由至少需要 10 个字符")
    rows, _ = load_ledger(workspace)
    if any(r.get("kind") == "enforcement" for r in rows):
        raise GovernanceError("生效边界已声明，不得改写")
    record = {
        "kind": "enforcement",
        "commit_sha": commit_sha,
        "reason": reason.strip(),
        "declared_at": datetime.now().isoformat(),
        "declared_by": declared_by,
    }
    append_jsonl(workspace / LEDGER_REL, record)
    return record


def declare_commit(
    workspace: Path,
    *,
    commit_sha: str,
    change_id: str = "",
    exemption: str = "",
    reason: str,
    declared_by: str,
) -> dict[str, Any]:
    sha = commit_sha.strip()
    if not _is_commit(workspace, sha):
        raise GovernanceError(f"不是合法 commit: {sha!r}")
    if bool(change_id) == bool(exemption):
        raise GovernanceError("必须且只能提供 change_id 或 exemption 之一")
    if len(reason.strip()) < 10:
        raise GovernanceError("理由至少需要 10 个字符")
    record = {
        "kind": "commit",
        "commit_sha": sha,
        "change_id": change_id.strip(),
        "exemption": exemption.strip(),
        "reason": reason.strip(),
        "declared_at": datetime.now().isoformat(),
        "declared_by": declared_by,
    }
    append_jsonl(workspace / LEDGER_REL, record)
    return record


def compute_coverage(workspace: Path) -> dict[str, Any]:
    """生效边界之后的合并提交集合，减去已登记集合。"""
    boundary, error = enforced_from(workspace)
    if error:
        return {"available": False, "error": error, "gaps": [], "merge_count": 0}
    rows, _ = load_ledger(workspace)
    declared = {str(r.get("commit_sha") or "") for r in rows if r.get("kind") == "commit"}
    result = _git(workspace, "rev-list", "--merges", f"{boundary}..HEAD")
    if result.returncode != 0:
        return {"available": False, "error": f"无法枚举合并提交: {result.stderr.strip()}", "gaps": [], "merge_count": 0}
    merges = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    gaps = [sha for sha in merges if sha not in declared]
    return {
        "available": True,
        "error": None,
        "boundary": boundary,
        "merge_count": len(merges),
        "declared_count": len(declared),
        "gaps": gaps,
    }


def evaluate_coverage(workspace: Path, base_report: dict[str, Any]) -> dict[str, Any]:
    """观测期只落盘假想判定；翻闸后才让覆盖率失败影响退出码。

    观测记录必须可复核：输入摘要、当前结论、假想结论、两者是否一致缺一不可。
    """
    coverage = compute_coverage(workspace)
    would_fail = (not coverage["available"]) or bool(coverage["gaps"])
    base_invalid = int(base_report.get("invalid_count", 0) or 0)
    base_valid = bool(base_report.get("valid", False))
    base_fail = (not base_valid) or base_invalid > 0
    current_fail = (base_fail or would_fail) if COVERAGE_IN_DECISION else base_fail
    hypothetical_fail = base_fail or would_fail
    record = {
        "observed_at": datetime.now().isoformat(),
        "decision_enabled": COVERAGE_IN_DECISION,
        "base_invalid_count": base_invalid,
        "base_valid": base_valid,
        "coverage_available": coverage["available"],
        "coverage_error": coverage.get("error"),
        "gap_count": len(coverage["gaps"]),
        "gaps": coverage["gaps"][:10],
        "would_fail": would_fail,
        "applied": COVERAGE_IN_DECISION and would_fail,
        "input_summary": {
            "invalid_count": base_invalid,
            "valid": base_valid,
            "coverage_available": coverage["available"],
            "boundary": coverage.get("boundary"),
            "merge_count": coverage.get("merge_count", 0),
            "gap_count": len(coverage["gaps"]),
        },
        "current_conclusion": {"fail": current_fail},
        "hypothetical_conclusion": {"fail": hypothetical_fail},
        "differs": current_fail != hypothetical_fail,
    }
    append_jsonl(workspace / OBSERVE_REL, record)
    return {"coverage": coverage, "would_fail": would_fail, "applied": record["applied"], "observe": record}


# --------------------------------------------------------------------------
# 门禁输入契约与开工检查
# --------------------------------------------------------------------------
def input_contract_complete(expected_branch: Any, baseline_commit: Any, watch_paths: Any) -> bool:
    """三个硬门禁输入均有值才算装备完成；不臆造默认值。"""
    return bool(expected_branch) and bool(baseline_commit) and bool(watch_paths)


def guard_input_report(workspace: Path) -> dict[str, Any]:
    config_path = workspace / ".vscode" / "ai-collab.json"
    config = read_json(config_path, {})
    guard = config.get("concurrentGuard") if isinstance(config, dict) else {}
    guard = guard if isinstance(guard, dict) else {}
    expected = guard.get("expectedBranch")
    baseline = guard.get("baselineCommit")
    watch = guard.get("watchPaths")
    missing = [
        name
        for name, value in (("expectedBranch", expected), ("baselineCommit", baseline), ("watchPaths", watch))
        if not value
    ]
    return {
        "complete": input_contract_complete(expected, baseline, watch),
        "missing": missing,
    }


def preflight(workspace: Path) -> dict[str, Any]:
    """开工前一次机器检查：五项可判定结论 + 总 PASS/FAIL。"""
    checks: list[dict[str, Any]] = []

    session_path = workspace / ".ai_collab_session.json"
    session = read_json(session_path, {})
    acknowledged = session.get("required_reads_acknowledged") if isinstance(session, dict) else None
    reads = set(acknowledged) if isinstance(acknowledged, list) else set()
    missing_reads = [p for p in REQUIRED_READS if p not in reads]
    checks.append(
        {
            "name": "必读清单声明",
            "pass": not missing_reads,
            "detail": "齐全" if not missing_reads else f"缺: {missing_reads}",
        }
    )

    state = read_json(workspace / STATE_REL, {})
    last_updated = str(state.get("last_updated") or "") if isinstance(state, dict) else ""
    checks.append(
        {"name": "状态机时效", "pass": bool(last_updated), "detail": last_updated or "状态文件缺失或无 last_updated"}
    )

    guard = guard_input_report(workspace)
    checks.append(
        {
            "name": "门禁输入完整性",
            "pass": guard["complete"],
            "detail": "三个输入齐全" if guard["complete"] else f"未装备，缺: {guard['missing']}",
        }
    )

    coverage = compute_coverage(workspace)
    coverage_ok = coverage["available"] and not coverage["gaps"]
    checks.append(
        {
            "name": "HEAD 治理登记",
            "pass": coverage_ok,
            "detail": coverage.get("error")
            or f"边界后合并提交 {coverage['merge_count']} 个，未登记 {len(coverage['gaps'])} 个",
        }
    )

    ack_state = read_json(workspace / ACK_BRIDGE_REL, {})
    items = ack_state.get("items") if isinstance(ack_state, dict) else {}
    explicit = [
        tid
        for tid, item in (items or {}).items()
        if isinstance(item, dict) and str(item.get("source") or "").startswith(("cli-ack", "chat-ack"))
    ]
    checks.append(
        {"name": "显式 ACK 证据", "pass": bool(explicit), "detail": f"{len(explicit)} 条" if explicit else "无显式 ACK"}
    )

    return {"checks": checks, "pass": all(c["pass"] for c in checks)}
