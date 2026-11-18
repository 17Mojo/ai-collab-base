# 项目事实快照

**生成时间**: 2026-11-18T13:19:27Z
**生成方式**: scripts/gen_facts.sh（自动生成，请勿手工编辑）
**仓库路径**: /Users/raymondna/Documents/AI-collab/ai-collab-base
**仓库 HEAD**: a02212ae9db1f483d51878f1d851183c9508d8e6
**当前分支**: main

## 1. Git 状态
```
$ git status --short --branch
## main...origin/main
 M docs/FACTS.generated.md
```

## 2. 最近 20 次提交
```
a02212a fix(fixture): 按真机探针重建 deepseek 快照，矩阵不再指向无辜的生产代码（N50 closed）
85eeafd test(worktree): 冲突 fixture 改用 symbolic-ref，不再依赖 git 对 `-B` 的宽纵（N49 closed）
7666180 fix(governance): 修掉 mypy 3 条与 bandit 3 条新发现，关掉两个红着的阻塞门禁（N48 closed）
c1fdaae ci(lint): 锁死 ruff 版本并让阻塞 lint 门禁真正变绿（N47 closed）
7afdc4d chore(test-env): 更正「50 条环境基线失败」的归因并登记 N46
6a4171b fix(daemon): 让 --once 真实入口真的调用看门狗（N45 二次复查）
9f5bbd3 fix(orchestration): 可用性标注与审计入口可信度（关闭 N44/N45）
6fc4f47 fix(audit): 产物要求按状态分流，并补上「已 ACK 却无产物」的非终态扫描（N42 closed）
2d76a2c fix(gate): 结果文件章节契约收敛为一份判据，缺回滚不再被放行（N41 closed）
8e8d902 fix(example3): 自纠——范例三本就是 D3，我先前的 D1 判断建立在查错字段上
1337039 test(example3): 范例三端到端 ACK 流实跑并留回执，D1→D3；跑出 4 条偏差登记 N41-N44
5ae7732 test(evidence): 从 .gitignore 的 `!` 放行反推检查范围，堵住「规则写了动作漏了」
823dc69 chore: 开发日志入库、logs 目录补 ignore、DOTS 立项书与解冻裁定对齐
1e6a5a1 fix(evidence): 补齐 135 份漏 add 的真机证据，并加证据链绊线（N40 closed）
6baeb3a fix(governance): 守卫与预检共用同一份配置解析；测试结论不再隐瞒未跟踪用例（N37/N39 closed）
a77ff1d fix(governance): 门禁编号不再允许按连惯性虚构（N38 closed）
c648c15 chore(N36): 多平台执行器裁定「标注未实现」——@unwired 标记 + 文档降级 + 双向绊线
8a09c1f fix(real-machine): 登录判据不再只看输入框可见，解冻留痕不再误报（N34/N35 closed）
e571426 docs(result): 回填 D1/D2/D3 → N34/N35/N36 交叉引用（原写「建议登记」与磁盘不符）
2100e5e chore(governance): 登记合并提交 0ae0c18（豁免 wip-content-baseline-merge-2026-11-18）
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
./.arts
./.cache
./.cache/worktrees
./.cc-claude-codex
./.cc-claude-codex/snapshots
./.claude
./.claude/commands
./.claude/skills
./.codeartsdoer
./.codeartsdoer/.codebase
./.codeartsdoer/agent-team
./.codeartsdoer/agents
./.codeartsdoer/experience-reuse
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
./.ruff_cache/0.17.5
./.trae
./.trae/skills
./.vscode
./.workbuddy
./.workbuddy/memory
./.workbuddy/tmp
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
./ai_collab/resources
./chrome-extension
./chrome-extension/collaboration
./chrome-extension/dist
./chrome-extension/logs
./chrome-extension/public
./chrome-extension/src
./chrome-extension/tests
./collaboration
./collaboration/governance
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
./openspec/specs
./packs
./packs/api-design-pack
./packs/demo-pack
./packs/examples
./packs/exports
./packs/python-best-practices
./packs/templates
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
usage: __main__.py [-h] [-w WORKSPACE] [-v]
                   {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,orchestration,dispatch,trigger,2x,receipt,daily-report,run,workspace-guard,spawn-agent-guard,concurrent,governance,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack} ...

AI 协作开发系统 - Claude Code + GitHub Copilot

positional arguments:
  {activate,check,tasks,sessions,ack,ack-remediation,patches,conflicts,logs,init,clean,status,codex,controller,orchestration,dispatch,trigger,2x,receipt,daily-report,run,workspace-guard,spawn-agent-guard,concurrent,governance,hygiene,stage-source,stage-ops,stage-docs,stage-other,stage-safe,benefit,pack}
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
    daily-report        生成日报与监控摘要（operator closeout 收尾用）
    run                 标准 RUN 流程：dispatch -> receipt -> benefit
    workspace-guard     工作区门禁诊断（阈值+分域）
    spawn-agent-guard   Codex spawn_agent 前置门禁诊断
    concurrent          并发工作区守护
    governance          治理覆盖层（一致性校验 / 开工检查 / 登记表 / 覆盖率观测）
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
      "connection_status": "unavailable",
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
./chrome-extension/src/platforms/stepfun-adapter.js
./chrome-extension/src/platforms/yiyan-adapter.js
./chrome-extension/src/platforms/yuanbao-adapter.js
./chrome-extension/tests/_archive/test-adapters.js
./chrome-extension/tests/adapter-matrix/adapter-test-runner.js
./chrome-extension/tests/adapter-matrix/adapter-test-utils.js
```

## 9. 测试收集
```
$ python3 -m pytest -q --collect-only 2>&1 | tail -5

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] tests/unit/test_database_indexes.py:17: backend database not found at /Users/raymondna/Documents/AI-collab/ai-collab-base/local-backend/data/client_tokens.db
3262 tests collected in 3.17s
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
