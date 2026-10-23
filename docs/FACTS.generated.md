# 项目事实快照

**生成时间**: 2026-10-23T02:20:45Z
**生成方式**: scripts/gen_facts.sh（自动生成，请勿手工编辑）
**仓库路径**: /Users/raymondna/Documents/AI-collab/ai-collab-base
**仓库 HEAD**: 9c6596aed7b5fb6004d14b8ad85e62a93e25c69c
**当前分支**: feat/codearts-collab-wiring

## 1. Git 状态
```
$ git status --short --branch
## feat/codearts-collab-wiring...origin/main [ahead 39]
 M ai_collab/ack_protocol.py
 M ai_collab/cli/_cli_main.py
 M collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md
 M docs/FACTS.generated.md
 M scripts/agent_receipt_bridge.py
 M scripts/codearts_bridge_deliver.py
 M tests/unit/test_codearts_bridge_deliver.py
?? collaboration/results/RESULT-PREFIX-DERIVATION-2026-10-23.md
?? collaboration/tasks/TASK-P1-PREFIX-DERIVATION-001.md
?? tests/unit/test_ack_prefix_derivation.py
```

## 2. 最近 20 次提交
```
9c6596a chore(monitoring): 刷新终态一致性审计摘要
b104ffc chore(monitoring): 刷新自动生成摘要（事实快照 + 终态一致性审计）
e70b94c chore(memory): 记忆镜像去外部化 + 落「仓库边界」硬规则
2f72286 test(cleanup): 测试 fixture 里的外部项目路径中性化
c07cab5 docs(cleanup): 文档与指南去掉外部项目框架，保留历史事实
019332c refactor(cleanup): 删除外部项目副本目录 hermes_target/ 与其变更提案
85973f7 feat(purge): 僵尸 cron 任务清理 —— 官方删除路由 + 文件级兜底
1cb3b8c chore(monitoring): 刷新自动生成摘要（回执桥接 + 一致性审计 3/3）
61afa3f docs(result): 对齐回执桥接的结果文件契约（## 测试结论 + 验收命令逐字一致）
4f49318 chore(monitoring): 刷新自动生成摘要（干预队列已全部 resolved）
5b9160e fix(prefix): 补齐 229062d 漏改的 3 份角色前缀映射副本
e88e1c8 fix(prefix): ACK 前缀字母池不相交——codex 的 X→O，未知 provider 的 X→Z
7af5ae3 feat(bridge): 投递残留体检——僵尸 cron 任务不再沉在 kernel 里
bbfb81b chore(monitoring): 刷新自动生成摘要（干预队列已全部 resolved）
df2ddec docs(result): 补写成功交付证据与中止根因（write/task 工具带死会话）
b46a5f6 chore(memory): 同步 CodeArts 记忆镜像（2 条 feedback）并刷新监控摘要
0e8ac69 feat(hermes): CodeArts 交付 consensus_engine 移植与单测（54 用例 / 覆盖率 95%）
ce8a3b9 fix(dispatch): payload 写明工具约束 —— write/task 会把 CodeArts 会话卡死并中止
ccfceba chore(monitoring): 刷新自动生成摘要
909ddcc docs(result): 更正提交号引用
```

## 3. 远端同步状态
```
# 基于当前分支的 upstream（@{u}），不硬编码 main
unpushed(ahead of upstream)=39
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
./logs/backups
./logs/claude-code
./logs/faults
./logs/monitoring_backup
./logs/openspec_backup
./logs/playwright-results
./logs/tasks_backup
./logs/trae-ai
./logs/workspace_forensics
./memory
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
./rules/archive
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
                                {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,orchestration,dispatch,trigger,2x,receipt,run,workspace-guard,spawn-agent-guard,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack} ...

AI 协作开发系统 - Claude Code + GitHub Copilot

positional arguments:
  {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,orchestration,dispatch,trigger,2x,receipt,run,workspace-guard,spawn-agent-guard,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack}
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
    orchestration       角色编排配置（绑定状态、角色激活、快照、历史）
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
        "provider": "codearts_agent",
        "model_variant": null,
        "status": "active"
      },
      "raci_role": "R",
      "created_at": null,
      "activated_at": "2026-10-22T18:10:56.928912"
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
    "A.RUN": "AGENT_EXEC",
    "C.RUN": "AGENT_TEST",
    "X.RUN": "AGENT_ARCH",
    "custom_prefixes": {},
    "custom_allowed": true,
    "history_compatible": true
  },
  "provider_registry": {
    "claude_code": {
      "provider_name": "claude_code",
      "display_name": "Claude Code",
      "connection_status": "connected",
      "supports_sub_agent": true,
      "model_variants": [
        "opus",
        "sonnet",
        "haiku"
      ],
      "capabilities": [
        "implementation",
        "refactoring",
        "testing",
        "architecture",
        "documentation"
      ],
      "last_check": "2026-10-22T17:49:34+08:00",
      "fallback_ack_prefix": "C"
    },
    "codearts_agent": {
      "provider_name": "codearts_agent",
      "display_name": "CodeArts Agent",
      "connection_status": "detected",
      "supports_sub_agent": false,
      "model_variants": [],
      "capabilities": [
        "implementation",
        "testing",
        "documentation",
        "validation"
      ],
      "last_check": "2026-10-22T17:49:34+08:00",
      "fallback_ack_prefix": "A"
    },
    "codex": {
      "provider_name": "codex",
      "display_name": "Codex",
      "connection_status": "unavailable",
      "supports_sub_agent": false,
      "model_variants": [],
      "capabilities": [
        "architecture",
        "research",
        "implementation",
        "testing",
        "documentation"
      ],
      "last_check": "2026-10-22T17:49:34+08:00",
      "fallback_ack_prefix": "O"
    }
  },
  "runtime_policy": {
    "allow_hot_reload": true,
    "require_confirmation": true,
    "snapshot_before_change": true,
    "max_roles": 10,
    "auto_activate_dormant": false
  },
  "snapshots": [
    {
      "snapshot_id": "snap_001",
      "timestamp": "2026-10-22T18:09:15.027231",
      "trigger": "auto_before_change",
      "note": "Before activating AGENT_EXEC",
      "config_copy": {
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
              "provider": "codearts_agent",
              "model_variant": null,
              "status": "active"
            },
            "raci_role": "R",
            "created_at": null,
            "activated_at": "2026-10-22T17:49:34.107765"
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
          "A.RUN": "AGENT_EXEC",
          "X.RUN": "AGENT_ARCH",
          "C.RUN": "AGENT_TEST",
          "custom_prefixes": {},
          "custom_allowed": true,
          "history_compatible": true
        },
        "provider_registry": {
          "claude_code": {
            "provider_name": "claude_code",
            "display_name": "Claude Code",
            "connection_status": "connected",
            "supports_sub_agent": true,
            "model_variants": [
              "opus",
              "sonnet",
              "haiku"
            ],
            "capabilities": [
              "implementation",
              "refactoring",
              "testing",
              "architecture",
              "documentation"
            ],
            "fallback_ack_prefix": "C",
            "last_check": "2026-10-22T17:49:34+08:00"
          },
          "codearts_agent": {
            "provider_name": "codearts_agent",
            "display_name": "CodeArts Agent",
            "connection_status": "detected",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "implementation",
              "testing",
              "documentation",
              "validation"
            ],
            "fallback_ack_prefix": "A",
            "last_check": "2026-10-22T17:49:34+08:00"
          },
          "codex": {
            "provider_name": "codex",
            "display_name": "Codex",
            "connection_status": "unavailable",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "architecture",
              "research",
              "implementation",
              "testing",
              "documentation"
            ],
            "fallback_ack_prefix": "O",
            "last_check": "2026-10-22T17:49:34+08:00"
          }
        },
        "runtime_policy": {
          "allow_hot_reload": true,
          "require_confirmation": true,
          "snapshot_before_change": true,
          "max_roles": 10,
          "auto_activate_dormant": false
        },
        "cold_start_config": {
          "initialized_at": null,
          "initial_provider": null,
          "initial_mode": null,
          "wizard_completed": false
        }
      }
    },
    {
      "snapshot_id": "snap_002",
      "timestamp": "2026-10-22T18:10:56.853086",
      "trigger": "manual",
      "note": "prune nested snapshot copies",
      "config_copy": {
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
              "provider": "codearts_agent",
              "model_variant": null,
              "status": "active"
            },
            "raci_role": "R",
            "created_at": null,
            "activated_at": "2026-10-22T18:09:15.027321"
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
          "A.RUN": "AGENT_EXEC",
          "X.RUN": "AGENT_ARCH",
          "C.RUN": "AGENT_TEST",
          "custom_prefixes": {},
          "custom_allowed": true,
          "history_compatible": true
        },
        "provider_registry": {
          "claude_code": {
            "provider_name": "claude_code",
            "display_name": "Claude Code",
            "connection_status": "connected",
            "supports_sub_agent": true,
            "model_variants": [
              "opus",
              "sonnet",
              "haiku"
            ],
            "capabilities": [
              "implementation",
              "refactoring",
              "testing",
              "architecture",
              "documentation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "C"
          },
          "codearts_agent": {
            "provider_name": "codearts_agent",
            "display_name": "CodeArts Agent",
            "connection_status": "detected",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "implementation",
              "testing",
              "documentation",
              "validation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "A"
          },
          "codex": {
            "provider_name": "codex",
            "display_name": "Codex",
            "connection_status": "unavailable",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "architecture",
              "research",
              "implementation",
              "testing",
              "documentation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "O"
          }
        },
        "runtime_policy": {
          "allow_hot_reload": true,
          "require_confirmation": true,
          "snapshot_before_change": true,
          "max_roles": 10,
          "auto_activate_dormant": false
        },
        "cold_start_config": {
          "initialized_at": null,
          "initial_provider": null,
          "initial_mode": null,
          "wizard_completed": false
        }
      }
    },
    {
      "snapshot_id": "snap_003",
      "timestamp": "2026-10-22T18:10:56.928851",
      "trigger": "auto_before_change",
      "note": "Before activating AGENT_EXEC",
      "config_copy": {
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
              "provider": "codearts_agent",
              "model_variant": null,
              "status": "active"
            },
            "raci_role": "R",
            "created_at": null,
            "activated_at": "2026-10-22T18:09:15.027321"
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
          "A.RUN": "AGENT_EXEC",
          "X.RUN": "AGENT_ARCH",
          "C.RUN": "AGENT_TEST",
          "custom_prefixes": {},
          "custom_allowed": true,
          "history_compatible": true
        },
        "provider_registry": {
          "claude_code": {
            "provider_name": "claude_code",
            "display_name": "Claude Code",
            "connection_status": "connected",
            "supports_sub_agent": true,
            "model_variants": [
              "opus",
              "sonnet",
              "haiku"
            ],
            "capabilities": [
              "implementation",
              "refactoring",
              "testing",
              "architecture",
              "documentation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "C"
          },
          "codearts_agent": {
            "provider_name": "codearts_agent",
            "display_name": "CodeArts Agent",
            "connection_status": "detected",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "implementation",
              "testing",
              "documentation",
              "validation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "A"
          },
          "codex": {
            "provider_name": "codex",
            "display_name": "Codex",
            "connection_status": "unavailable",
            "supports_sub_agent": false,
            "model_variants": [],
            "capabilities": [
              "architecture",
              "research",
              "implementation",
              "testing",
              "documentation"
            ],
            "last_check": "2026-10-22T17:49:34+08:00",
            "fallback_ack_prefix": "O"
          }
        },
        "runtime_policy": {
          "allow_hot_reload": true,
          "require_confirmation": true,
          "snapshot_before_change": true,
          "max_roles": 10,
          "auto_activate_dormant": false
        },
        "cold_start_config": {
          "initialized_at": null,
          "initial_provider": null,
          "initial_mode": null,
          "wizard_completed": false
        }
      }
    }
  ],
  "history": [
    {
      "timestamp": "2026-09-13T20:47:46.107780",
      "event": "mode_switched",
      "details": {
        "new_mode": "multi_agent"
      }
    },
    {
      "timestamp": "2026-10-22T17:49:34+08:00",
      "event": "role_activated",
      "details": {
        "role_id": "AGENT_EXEC",
        "provider": "codearts_agent",
        "model_variant": null,
        "previous_provider": "claude_code",
        "reason": "Claude Code 与 CodeArts 共创分工：CodeArts 承接 AGENT_EXEC(R) 实现位，Claude Code 退守 AGENT_ARCH(A) 架构 + AGENT_TEST(C) 验证"
      }
    },
    {
      "timestamp": "2026-10-22T18:09:15.027316",
      "event": "snapshot_created",
      "details": {
        "snapshot_id": "snap_001",
        "trigger": "auto_before_change"
      }
    },
    {
      "timestamp": "2026-10-22T18:09:15.027330",
      "event": "role_activated",
      "details": {
        "role_id": "AGENT_EXEC",
        "provider": "codearts_agent",
        "model_variant": null
      }
    },
    {
      "timestamp": "2026-10-22T18:10:56.853138",
      "event": "snapshot_created",
      "details": {
        "snapshot_id": "snap_002",
        "trigger": "manual"
      }
    },
    {
      "timestamp": "2026-10-22T18:10:56.928908",
      "event": "snapshot_created",
      "details": {
        "snapshot_id": "snap_003",
        "trigger": "auto_before_change"
      }
    },
    {
      "timestamp": "2026-10-22T18:10:56.928917",
      "event": "role_activated",
      "details": {
        "role_id": "AGENT_EXEC",
        "provider": "codearts_agent",
        "model_variant": null
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
2840 tests collected in 0.65s
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
