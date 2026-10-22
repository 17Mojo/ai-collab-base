---
description: 用户角色与偏好信息
from: Agent
---

# 用户信息

## 角色与职责
- **角色**: 开发者/维护者
- **职责**: AI Collaboration System 项目管理、技术债追踪、质量把控
- **团队协作模式**: Claude + Copilot 双AI协作

## 工作偏好
1. **文档追踪**: 使用 SYSTEM_METRICS_DASHBOARD.md、OWNERSHIP.md 等文档系统化追踪问题
2. **任务管理**: 使用 task ID 格式如 TASK-W11-D5-README-DOCUMENTATION-005
3. **优先级意识**: 区分高/中/低优先级问题
4. **核查习惯**: 喜欢先梳理历史会话再执行方案
5. **拆分提交**: 大型改动（如 Ruff 清理）偏好按改动类别拆分为多个聚焦的小提交（配置改动、路径迁移等各自独立），而非单次混合大提交

## 技术栈偏好
- **Python 环境**: miniforge3 (`/Users/raymondna/miniforge3/bin/python3`, Python 3.14.6) — 2026-09-19 从 anaconda3 迁移
- 后端: FastAPI + SQLite (local-first)
- 前端: Chrome Extension + VSCode Extension
- 协作: Claude Code + GitHub Copilot

## 沟通风格
- 使用中文沟通，嵌入英文技术术语
- 喜欢结构化的输出（表格、清单）
- 重视断点续接场景的核实
- **简洁指令式回复**: 反感冗长解释，偏好直接推进的指令式回复（如直接说"推进"、"继续未完成工作"）
- **追问根因**: 遇到问题时倾向于追问原因（如"为什么卡住了？"），希望 AI 解释问题根因而非仅给出解决方案

## 工作偏好 (来自系统配置)
1. **提交规范**: Conventional Commits 格式 (如 `docs(glossary): fix ...`)
2. **验证优先**: 先跑 git status / 工具命令摸底，要求「洞察 vs 真证」差异表，声明阈值/口径/分母/版本四元组
3. **术语保留**: 技术词汇保留英文原文 (grid、final、snapshot、CERTIFIED、prompt、VLM 等)
4. **命名规范**: snake_case 命名 (模块、测试、YAML 配置键)
5. **方案审慎**: 正式执行前先梳理历史会话，断点续接需重新核实
