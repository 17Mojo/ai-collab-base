# Implementation Tasks

## Phase 0: 准备工作

- [ ] 0.1 确认 ai-collab-base 源代码可用
- [ ] 0.2 创建 Hermes 目标目录结构
- [ ] 0.3 备份当前 Hermes 配置和代码

## Phase 1: P0 - consensus_engine 移植（优先级最高）

### 1.1 代码移植

- [ ] 1.1.1 复制 `consensus_engine.py` 到 Hermes `engines/`
- [ ] 1.1.2 适配 Hermes 配置格式（providers → models）
- [ ] 1.1.3 添加 Hermes 日志集成
- [ ] 1.1.4 创建 `engines/__init__.py` 导出

### 1.2 配置修改

- [ ] 1.2.1 在 `config.yaml` 添加 `engines` 配置段
- [ ] 1.2.2 配置并发参数（max_concurrent=5, timeout=60）
- [ ] 1.2.3 配置 fallback 策略

### 1.3 集成到 ai-media-analysis

- [ ] 1.3.1 修改 `ai-media-analysis-report.py` 使用 consensus_engine
- [ ] 1.3.2 替换串行洞察生成为并行
- [ ] 1.3.3 添加超时和重试逻辑

### 1.4 测试与验收

- [ ] 1.4.1 编写单元测试 `test_consensus_engine.py`
- [ ] 1.4.2 执行验收命令：`pytest tests/unit/hermes/test_consensus_engine.py -v --cov`
- [ ] 1.4.3 性能基准测试：延迟 < 串行/3
- [ ] 1.4.4 创建 RESULT 文件

## Phase 2: P1 - state_manager 移植

### 2.1 代码移植

- [ ] 2.1.1 复制 `state_manager.py` 到 Hermes `core/`
- [ ] 2.1.2 适配 Hermes 任务格式
- [ ] 2.1.3 实现文件锁机制
- [ ] 2.1.4 实现 checkpoint 备份

### 2.2 状态机集成

- [ ] 2.2.1 定义 ai-media-analysis 任务状态流转
- [ ] 2.2.2 实现心跳超时检测
- [ ] 2.2.3 实现冲突检测

### 2.3 长任务支持

- [ ] 2.3.1 修改 smart-report-scheduler.sh 使用状态管理
- [ ] 2.3.2 实现断点续传
- [ ] 2.3.3 实现失败重试单个阶段

### 2.4 测试与验收

- [ ] 2.4.1 编写单元测试 `test_state_manager.py`
- [ ] 2.4.2 测试状态流转正确性
- [ ] 2.4.3 测试 checkpoint 备份
- [ ] 2.4.4 测试冲突检测
- [ ] 2.4.5 创建 RESULT 文件

## Phase 3: P1 - notification 移植

### 3.1 代码移植

- [ ] 3.1.1 复制 `notification.py` 到 Hermes `messaging/`
- [ ] 3.1.2 实现 broadcast/@mention/direct 三种模式
- [ ] 3.1.3 集成到 Hermes → OpenClaw 通信

### 3.2 集成

- [ ] 3.2.1 修改飞书推送使用 notification 模块
- [ ] 3.2.2 实现 Hermes 通知 OpenClaw 任务状态

### 3.3 测试与验收

- [ ] 3.3.1 编写单元测试 `test_notification.py`
- [ ] 3.3.2 测试三种通知模式
- [ ] 3.3.3 创建 RESULT 文件

## Phase 4: P2 - intervention_queue 移植

### 4.1 代码移植

- [ ] 4.1.1 复制 `intervention_queue.py` 到 Hermes `queue/`
- [ ] 4.1.2 适配 Hermes 干预格式
- [ ] 4.1.3 实现摘要生成

### 4.2 集成

- [ ] 4.2.1 修改质量评估低分时触发干预
- [ ] 4.2.2 实现 operator 干预接口

### 4.3 测试与验收

- [ ] 4.3.1 编写单元测试 `test_intervention_queue.py`
- [ ] 4.3.2 测试干预持久化
- [ ] 4.3.3 创建 RESULT 文件

## Phase 5: P2 - dispatch_trigger 移植

### 5.1 代码移植

- [ ] 5.1.1 复制 `dispatch_trigger.py` 到 OpenClaw `scheduler/`
- [ ] 5.1.2 实现 Payload 生成

### 5.2 集成

- [ ] 5.2.1 修改 crontab 使用 dispatch_trigger
- [ ] 5.2.2 实现任务派发到 Hermes

### 5.3 测试与验收

- [ ] 5.3.1 编写单元测试 `test_dispatch_trigger.py`
- [ ] 5.3.2 测试 Payload 生成正确性
- [ ] 5.3.3 创建 RESULT 文件

## Phase 6: 收尾

- [ ] 6.1 更新 Hermes 文档 (MEMORY.md, SOUL.md)
- [ ] 6.2 更新 OpenClaw 文档 (ROLE.md, ROADMAP.md)
- [ ] 6.3 性能对比报告
- [ ] 6.4 归档 OpenSpec Change
