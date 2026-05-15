# Menu 技能定义

此文件定义 `/menu` 技能的实现规范，用于 AI Collab Base 项目的动态配置管理。

---

## 技能概述

**技能名称**: `menu`  
**调用方式**: `/menu`  
**功能**: 常态化配置服务，随时调整 Agent 角色绑定、命令映射、工作模式等

---

## 技能入口

当用户输入 `/menu` 时，系统执行以下流程：

### 1. 检测 Orchestration 配置状态

```
检测 config/agent-orchestration.json 存在性
    ├─ 不存在 → 提示冷启动 → 执行 cold-start 流程
    └─ 存在但 binding_status == uninitialized → 提示冷启动
    └─ 存在且已初始化 → 显示主菜单
```

### 2. 显示主菜单

```
┌─────────────────────────────────────────────────────┐
│  ⚙️  AI Collab Base - 控制面板                       │
│                                                     │
│  当前状态: {startup_mode} ({active_providers})       │
│  角色数: {total_roles} ({active_roles} 活跃)         │
│                                                     │
│  ────────────────────────────────────────────────  │
│  [1] 角色管理                                       │
│  [2] Agent 绑定                                     │
│  [3] 命令配置                                       │
│  [4] 工作模式切换                                    │
│  [5] 快照与回滚                                     │
│  [6] 导出/导入                                      │
│  [7] 检测 Agent 服务商                              │
│  [8] 查看历史                                       │
│  [0] 退出                                          │
└─────────────────────────────────────────────────────┘
```

---

## 子功能实现

### [1] 角色管理

**CLI 命令映射**:
```bash
python3 -m src.cli orchestration roles list
python3 -m src.cli orchestration roles add --role-id AGENT_PERF --display-name "性能优化师" --duties "性能测试" "负载分析"
python3 -m src.cli orchestration roles activate --role-id AGENT_PERF --provider gemini_cli
python3 -m src.cli orchestration roles deactivate --role-id AGENT_PERF
```

**交互流程**:
1. 显示当前角色列表
2. 用户选择操作（新增/编辑/激活/休眠）
3. 执行对应 CLI 命令
4. 显示执行结果
5. 返回主菜单

---

### [2] Agent 绑定

**CLI 命令映射**:
```bash
python3 -m src.cli orchestration bind
python3 -m src.cli orchestration roles activate --role-id <ID> --provider <PROVIDER> --model-variant <VARIANT>
```

**SubAgent 模式说明**:
- 仅当 provider 支持 SubAgent（如 Claude Code）时显示 model_variant 选项
- 可选变体: opus、sonnet、haiku
- 每个角色可独立指定变体

---

### [3] 命令配置

**CLI 命令映射**:
```bash
# 查看当前映射
python3 -m src.cli orchestration status

# 自定义命令需通过配置文件编辑
# 或使用 CLI 快捷方式（待实现）
```

**命令重定义流程**:
1. 显示当前命令映射（A.RUN, X.RUN, C.RUN）
2. 用户输入要重定义的命令前缀
3. 用户选择目标角色
4. 更新 command_prefixes 配置
5. history 记录 command_redefined 事件

---

### [4] 工作模式切换

**模式类型**:
- `single_agent`: 单 Agent 承担所有活跃角色
- `sub_agent`: 单 Agent 内部模型变体分工
- `multi_agent`: 多 Agent 服务商协作

**切换流程**:
1. 显示当前模式
2. 列出可选模式及其前置条件
3. 验证前置条件（如 multi_agent 需至少 2 个可用服务商）
4. 用户确认切换
5. 创建快照（auto_before_change）
6. 执行模式切换
7. 更新 startup_mode 配置

---

### [5] 快照与回滚

**CLI 命令映射**:
```bash
python3 -m src.cli orchestration snapshot list
python3 -m src.cli orchestration snapshot create --note "备份说明"
python3 -m src.cli orchestration snapshot rollback --snapshot-id snap_001
```

**快照触发类型**:
- `manual`: 用户手动创建
- `auto_before_change`: 变更前自动创建
- `mode_switch`: 模式切换时创建
- `cold_start`: 冷启动时创建

---

### [6] 导出/导入

**导出流程**:
1. 用户指定导出文件路径
2. 选择导出范围（完整配置 / 仅角色 / 仅命令）
3. 系统生成 JSON 文件
4. 显示导出成功信息

**导入流程**:
1. 用户提供配置文件路径
2. 选择合并策略（完全替换 / 增量合并 / 仅导入角色）
3. 验证配置格式（对照 schema）
4. 执行导入
5. 显示导入结果

---

### [7] 检测 Agent 服务商

**CLI 命令映射**:
```bash
python3 -m src.cli orchestration detect
```

**检测结果展示**:
```
检测结果:
  ✓ Claude Code [connected] (支持 SubAgent)
  ✓ Codex CLI [detected]
  ✗ Gemini CLI [unavailable]
  ✗ CodeArts Agent [unavailable]
```

---

### [8] 查看历史

**CLI 命令映射**:
```bash
python3 -m src.cli orchestration history --limit 20
```

**事件类型**:
- `cold_start`: 冷启动完成
- `role_added`: 新增角色
- `role_activated`: 激活角色
- `command_redefined`: 重定义命令
- `mode_switched`: 模式切换
- `snapshot_created`: 创建快照
- `rollback_executed`: 回滚执行
- `provider_connected`: 接入服务商
- `provider_disconnected`: 断开服务商

---

## 快捷参数支持

用户可直接输入带参数的命令：

| 快捷命令 | 功能 |
|---------|------|
| `/menu roles` | 直接进入角色管理 |
| `/menu bind` | 直接进入绑定管理 |
| `/menu detect` | 直接检测服务商 |
| `/menu status` | 显示当前状态摘要 |
| `/menu history` | 查看变更历史 |
| `/menu export <path>` | 导出配置到指定路径 |
| `/menu rollback <id>` | 回滚到指定快照 |

---

## 实现优先级

### P0 - 核心功能（必需）
- [1] 角色管理（list/activate/deactivate）
- [2] Agent 绑定（bind/activate）
- [7] 检测服务商

### P1 - 增强功能
- [3] 命令配置（重定义）
- [4] 工作模式切换
- [5] 快照与回滚

### P2 - 辅助功能
- [6] 导出/导入
- [8] 查看历史详情
- 快捷参数完整支持

---

## 技能实现方式

**方案 A: CLI 包装**
- 技能内部调用 `python3 -m src.cli orchestration ...` 命令
- 解析命令输出并格式化显示
- 适用于 VSCode Extension 环境

**方案 B: Python API 调用**
- 技能内部直接调用 `ai_collab.orchestration` 模块
- 无需通过 CLI 中间层
- 适用于 Claude Code 直接执行环境

**推荐**: 方案 B，直接 API 调用更高效

---

## 示例代码（方案 B）

```python
from ai_collab.orchestration import get_orchestration_config, OrchestrationConfig

def menu_skill(args: str = ""):
    """执行 /menu 技能"""
    workspace = os.getcwd()
    config = get_orchestration_config(workspace)
    
    if not args:
        # 显示主菜单
        show_main_menu(config)
    elif args == "roles":
        show_roles_menu(config)
    elif args == "bind":
        show_bind_menu(config)
    elif args == "detect":
        run_detect(config)
    elif args.startswith("export"):
        export_config(config, args.split()[1] if len(args.split()) > 1 else None)
    else:
        print(f"未知参数: {args}")
        print("可用参数: roles, bind, detect, status, history, export, rollback")

def show_main_menu(config: OrchestrationConfig):
    """显示主菜单"""
    print("⚙️  AI Collab Base - 控制面板")
    print(f"当前状态: {config.config.get('startup_mode', '未设置')}")
    print(f"绑定状态: {config.get_binding_status().value}")
    
    active_roles = [r for r in config.roles.values() if r.is_active()]
    print(f"角色数: {len(config.roles)} ({len(active_roles)} 活跃)")
    
    print("\n[1] 角色管理  [2] Agent 绑定  [3] 命令配置")
    print("[4] 模式切换  [5] 快照回滚   [6] 导出导入")
    print("[7] 检测服务商  [8] 查看历史  [0] 退出")
```

---

## 配置文件引用

- 主配置: `config/agent-orchestration.json`
- 模板: `config/agent-orchestration.template.json`
- Schema: `config/agent-orchestration.schema.json`
- 交互规范: `collaboration/guides/MENU_INTERACTION_SPEC.md`

---

**更新时间**: 2026-05-15
**状态**: 技能定义草案