# 项目事实快照

**生成时间**: 2026-10-22T07:56:32Z
**生成方式**: scripts/gen_facts.sh（自动生成，请勿手工编辑）
**仓库路径**: /Users/raymondna/Documents/AI-collab/ai-collab-base
**仓库 HEAD**: 3ae6ccad351e779028cb1f6f39d1552ef11b6117
**当前分支**: refactor/slimming-2026-09-20

## 1. Git 状态
```
$ git status --short --branch
## refactor/slimming-2026-09-20...origin/refactor/slimming-2026-09-20
 M collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md
D  docs/FACTS_2026-10-21_193044.md
 M pyproject.toml
 M scripts/gen_facts.sh
?? docs/FACTS.generated.md
```

## 2. 最近 20 次提交
```
3ae6cca fix(hermes): 修复 consensus_engine 语法错误与 IntegrationMode 假枚举
01f67c2 fix(ci): 修复 test.yml 的 ruff 步骤，恢复被遮蔽的覆盖率门禁
157cb2c fix(test): 消除新增测试文件的 lint 回归，使 ruff 错误数回到 main 基线
b27cbc1 test(pack): 为 pack 执行测试补真实断言，清零 return-not-none 警告
9590f0b fix(laya-client): 校验响应 JSON 类型，清零 mypy 最后一个错误
fd0f556 chore(scripts): 新增 gen_facts.sh 生成项目事实快照
048bffa fix(test): 隔离模板库测试写入目录，消除仓库根目录污染
50da6c8 test(context): 补强 enhanced_query 路径与 state_manager P2 覆盖率缺口
56f0cf2 test(adapter): 新增 16 个单元测试覆盖适配器契约与 NotebookLM 集成
e0a7d2c feat(pack): 新增 ReviewWorkflow 数据类支持 AI-Pair 审查模式
61e6b07 test(laya-client): 新增 27 个单元测试覆盖自动路由与错误分层
23518e2 feat(laya-client): 新增 Laya MLX API 同步客户端
b679b0d test(concurrent-guard): 新增 23 个单元测试含冲突样本回归
952a855 feat(concurrent-guard): 新增并发工作区守护服务层
4a6aa18 docs(protocol): 新增第十四章并发工作区安全及设计文档
672f496 chore: harden .gitignore against regenerated artifacts
3aed955 chore: clean root-level artifacts and archive pack exports
9e0c8b7 chore(extension): archive 36 one-off debug scripts (4,643 lines)
8191c6b docs: replace obsolete `python3 -m src.cli` references
6030087 chore: remove dead src/ directory (3,564 lines)
```

## 3. 远端同步状态
```
# 基于当前分支的 upstream（@{u}），不硬编码 main
unpushed(ahead of upstream)=0
behind(upstream ahead of us)=0
```

## 4. 目录树（2 层）
```
.
./.cc-claude-codex
./.cc-claude-codex/snapshots
./.claude
./.codeartsdoer
./.codeartsdoer/.codebase
./.codeartsdoer/agent-team
./.codeartsdoer/agents
./.codeartsdoer/mcp
./.codeartsdoer/rule
./.codeartsdoer/skills
./.codeartsdoer/temp
./.mypy_cache
./.mypy_cache/3.10
./.ruff_cache
./.ruff_cache/0.16.2
./.ruff_cache/0.16.8
./.ruff_cache/0.17.1
./.trae
./.trae/skills
./.vscode
./ai_collab
./ai_collab/adapters
./ai_collab/cli
./ai_collab/config
./ai_collab/context
./ai_collab/engines
./ai_collab/hooks
./ai_collab/integrations
./ai_collab/pack
./ai_collab/prompt_pack
./ai_collab/quality
./ai_collab/resources
./ai_collab/skills
./ai_collab/workflow
./chrome-extension
./chrome-extension/collaboration
./chrome-extension/dist
./chrome-extension/logs
./chrome-extension/public
./chrome-extension/src
./chrome-extension/tests
./collaboration
./collaboration/guides
./collaboration/handoff
./collaboration/monitoring
./collaboration/results
./collaboration/scripts
./collaboration/skills
./collaboration/tasks
./config
./data
./docs
./hermes_target
./hermes_target/hermes_agent
./hermes_target/openclaw-mac
./htmlcov_total
./local-backend
./local-backend/app
./local-backend/collaboration
./local-backend/data
./local-backend/docs
./local-backend/local-backend
./local-backend/logs
./local-backend/monitoring
./logs
./logs/api
./logs/claude-code
./logs/faults
./logs/monitoring_backup
./logs/openspec_backup
./logs/playwright-results
./logs/tasks_backup
./logs/trae-ai
./notifications
./notifications/handoffs
./openspec
./openspec/changes
./packs
./packs/api-design-pack
./packs/demo-pack
./packs/examples
./packs/exports
./packs/python-best-practices
./packs/web-dev-pack
./products
./products/vscode-extension
./rules
./scripts
./src
./src/ai_collab_system.egg-info
./tests
./tests/data
./tests/e2e
./tests/integration
./tests/logs
./tests/perf
./tests/performance
./tests/playwright
./tests/security
./tests/uat
./tests/unit
```

## 5. Python 模块行数 Top 40
```
```

## 6. CLI 实际入口
```
$ ls -d src ai_collab 2>&1
ai_collab
src
$ python3 -m ai_collab.cli --help
usage: python3 -m ai_collab.cli [-h] [-w WORKSPACE] [-v]
                                {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,dispatch,trigger,2x,receipt,run,workspace-guard,spawn-agent-guard,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack} ...

AI 协作开发系统 - Claude Code + GitHub Copilot

positional arguments:
  {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,dispatch,trigger,2x,receipt,run,workspace-guard,spawn-agent-guard,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack}
                        命令
    activate            激活 AI 协作系统
    check               检查文件冲突
    tasks               任务管理
    sessions            会话注册表与控制面基线
    ack                 输出标准 ACK 协议行
    ack-remediation     审计并标记历史非显式 ACK bridge 残留
    patches             Patch 管理
    conflicts           冲突管理
    logs                日志管理
    init                初始化项目
    clean               清理旧日志
    status              显示系统状态
    codex               CC Claude Codex 集成
    controller          工单控制器（常驻轮询）
    dispatch            自动派单桥接（生成 Agent 执行指令包）
    trigger             暗语触发派单（2X DISPATCH）
    2x                  极简派单入口：2x claude/codearts/codex/all
    receipt             自动回执桥接（testing -> completed）
    run                 标准 RUN 流程：dispatch -> receipt -> benefit
    workspace-guard     工作区门禁诊断（阈值+分域）
    spawn-agent-guard   Codex spawn_agent 前置门禁诊断
    hygiene             工作区/暂存区自动治理（可一次执行或轮询）
    stage-source        按 source 域安全暂存（替代 git add .）
    stage-ops           按 ops 域安全暂存（results/monitoring/logs）
    stage-docs          按 docs 域安全暂存（文档/研究/规范）
    stage-other         按 other 域安全暂存（其余残留变更）
    stage-safe          一键分域安全暂存（默认 ops->docs->other，先预览再执行）
    benefit             自动化收益看板（>3 目标追踪）
    pack                Prompt Pack 管理

options:
  -h, --help            show this help message and exit
  -w, --workspace WORKSPACE
                        工作区路径
  -v, --version         show program's version number and exit

示例:
  # 激活 Claude Code
  ai-collab activate --ai claude

  # 检查文件冲突
  ai-collab check --ai claude --files src/api.ts

  # 初始化项目
  ai-collab init

  # 查看系统状态
  ai-collab status

  # 查看活跃任务
  ai-collab tasks list --status active

  # 极简派单
  ai-collab 2x claude
  ai-collab 2x codearts
  ai-collab 2x all

  # Prompt Pack 版本管理
  ai-collab pack bump --name demo-pack --type patch
  ai-collab pack history --name demo-pack

  # 兼容性检查
```

## 7. 角色编排配置
```
$ cat config/agent-orchestration.json
{
  "version": "2.0.0",
  "binding_status": "active",
  "startup_mode": "multi_agent",
  "roles": {
    "AGENT_EXEC": {
      "role_id": "AGENT_EXEC",
      "display_name": "主执行者",
      "duties": [
        "代码实现",
        "重构",
        "Bug修复"
      ],
      "required_capabilities": [
        "implementation",
        "refactoring"
      ],
      "binding": {
        "provider": "claude_code",
        "model_variant": "sonnet",
        "status": "active"
      },
      "raci_role": "R",
      "created_at": null,
      "activated_at": "2026-09-13T20:47:46.107765"
    },
    "AGENT_ARCH": {
      "role_id": "AGENT_ARCH",
      "display_name": "架构师",
      "duties": [
        "架构设计",
        "技术选型",
        "代码审查"
      ],
      "required_capabilities": [
        "architecture",
        "design"
      ],
      "binding": {
        "provider": "claude_code",
        "model_variant": "sonnet",
        "status": "active"
      },
      "raci_role": "A",
      "created_at": null,
      "activated_at": "2026-09-13T20:47:46.107773"
    },
    "AGENT_TEST": {
      "role_id": "AGENT_TEST",
      "display_name": "测试验证",
      "duties": [
        "单元测试",
        "集成测试",
        "质量保证"
      ],
      "required_capabilities": [
        "testing",
        "validation"
      ],
      "binding": {
        "provider": "claude_code",
        "model_variant": "sonnet",
        "status": "active"
      },
      "raci_role": "C",
      "created_at": null,
      "activated_at": "2026-09-13T20:47:46.107774"
    }
  },
  "command_prefixes": {
    "A.RUN": "AGENT_ARCH",
    "X.RUN": "AGENT_EXEC",
    "C.RUN": "AGENT_TEST",
    "custom_prefixes": {},
    "custom_allowed": true,
    "history_compatible": true
  },
  "provider_registry": {},
  "runtime_policy": {
    "allow_hot_reload": true,
    "require_confirmation": true,
    "snapshot_before_change": true,
    "max_roles": 10,
    "auto_activate_dormant": false
  },
  "snapshots": [],
  "history": [
    {
      "timestamp": "2026-09-13T20:47:46.107780",
      "event": "mode_switched",
      "details": {
        "new_mode": "multi_agent"
      }
    }
  ],
  "cold_start_config": {
    "initialized_at": null,
    "initial_provider": null,
    "initial_mode": null,
    "wizard_completed": false
  }
}```

## 8. Chrome 适配器
```
./chrome-extension/src/platforms/adapter-utils.js
./chrome-extension/src/platforms/adapter.js
./chrome-extension/src/platforms/chatglm-adapter.js
./chrome-extension/src/platforms/chatgpt-adapter.js
./chrome-extension/src/platforms/claude-adapter.js
./chrome-extension/src/platforms/deepseek-adapter.js
./chrome-extension/src/platforms/gemini-adapter.js
./chrome-extension/src/platforms/kimi-adapter.js
./chrome-extension/src/platforms/longcat-adapter.js
./chrome-extension/src/platforms/qianwen-adapter.js
./chrome-extension/src/platforms/yiyan-adapter.js
./chrome-extension/src/platforms/yuanbao-adapter.js
./chrome-extension/tests/_archive/test-adapters.js
./chrome-extension/tests/adapter-matrix/adapter-test-runner.js
./chrome-extension/tests/adapter-matrix/adapter-test-utils.js
```

## 9. 测试收集
```
$ python3 -m pytest -q --collect-only 2>&1 | tail -5
tests/unit/test_workspace_guard_extra.py::test_module_exports

=========================== short test summary info ============================
SKIPPED [1] tests/unit/test_database_indexes.py:17: backend database not found at /Users/raymondna/Documents/AI-collab/ai-collab-base/local-backend/data/client_tokens.db
2665 tests collected in 0.81s
```

## 10. 活跃任务
```
$ python3 -m ai_collab.cli tasks list 2>&1
============================================================
AI 协作系统 - 任务管理
============================================================

任务列表 (active, 0 个):
  无任务
```

## 11. 关键路径存在性
```
EXISTS  ARCHITECTURE.md
EXISTS  CLAUDE.md
EXISTS  README.md
EXISTS  docs/ARCHAEOLOGY_CODE_INVENTORY.md
EXISTS  collaboration/PROTOCOL.md
EXISTS  collaboration/results
EXISTS  openspec
EXISTS  local-backend
EXISTS  chrome-extension
EXISTS  packs
EXISTS  tests/unit
EXISTS  pyproject.toml
EXISTS  requirements.txt
```

## 12. 最大的 20 个文件
```
```
