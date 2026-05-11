## 1. Implementation

- [x] 1.1 为初始化配置增加 `spawnAgentGuard` 默认配置，并约定 latest/history 输出路径
- [x] 1.2 实现 `spawn_agent` 计划校验模块，覆盖 actor、单父任务、写入/只读委派、写集声明、保护路径、活跃任务冲突检查
- [x] 1.3 在 CLI 中新增可执行 guard 入口，并输出与 `workspaceGuard` 一致的允许/阻断与报告信息
- [x] 1.4 为 guard 结果写入 latest JSON + history JSONL 审计记录
- [x] 1.5 补充单元测试，覆盖允许、缺失 parent task、非 Codex actor、保护路径命中、活跃任务冲突和配置默认值
- [x] 1.6 更新相关治理文档中的运行时守卫调用口径
- [x] 1.7 将同一 guard 接入 `PreToolUse` `Agent` hook，使内部委派在工具执行前自动 preflight
- [x] 1.8 实现 hook 上下文推导，支持 runtime parent task、prompt 元数据、progress scope 回退与 read-only 推断
- [x] 1.9 补充单元测试，覆盖 hook 配置安装、自动 allow/block、保护路径阻断与 progress scope 回退
- [x] 1.10 更新治理文档，说明自动 preflight 生效方式与推荐委派元数据格式
