---
task_id: TASK-NLM-STUDIO-VIDEO-001
change_id: add-video-overview-generation
status: completed
assignee: claude
reviewer: claude
primary_skill: notebooklm-studio
support_skills: ["playwright", "automation"]
created_at: 2026-04-28T14:15:00+08:00
estimated_hours: 0.5
priority: P2
---

# TASK-NLM-STUDIO-VIDEO-001

## 任务描述

为 research-sequence-diagram 项目补充 Video Overview 生成。

## 背景

NotebookLM Studio 产物已生成：
- ✅ Audio Overview: research-sequence-diagram-audio.m4a (46MB)
- ✅ Slides: research-sequence-diagram-slides.pdf (14MB)
- ❌ Video Overview: 未生成（预留目录已创建）

## 当前任务

### 1. Video Overview 生成验证 (20min)

**目标**: 验证 NotebookLM Video Overview 是否可自动下载

**验证点**:
- [ ] NotebookLM 视频概览按钮是否可用
- [ ] Video 生成时间预估
- [ ] Video 输出格式 (.mp4?)
- [ ] Video 文件大小预估

### 2. 自动化执行 (10min)

**条件**: 验证通过后执行

**执行命令**:
```bash
# Playwright 自动化流程（参考 Audio/Slides）
# 1. 打开 NotebookLM 笔记本
# 2. 点击 Studio > 视频概览
# 3. 等待生成完成
# 4. 下载 .mp4 文件
# 5. 移动到 video/ 目录
```

### 3. 更新元数据 (5min)

**目标**: 更新 metadata.json 添加 video artifact

**更新内容**:
```json
{
  "type": "video",
  "artifact_id": "notebooklm-video-001",
  "file": "research-sequence-diagram-video.mp4",
  "size_mb": "待测量",
  "format": "video_overview",
  "language": "zh-CN"
}
```

## 验收标准

- ✅ Video 文件生成并保存到 video/ 目录
- ✅ metadata.json 包含 video artifact 信息
- ✅ 文件命名符合规范: {scene-id}-video.mp4

## NotebookLM 笔记本

- URL: https://notebooklm.google.com/notebook/eb5b6f8f-83d7-41de-b15f-bcba4e9ccfdc
- ID: eb5b6f8f-83d7-41de-b15f-bcba4e9ccfdc
- 知识源: knowledge-source.md

## 参考文档

- [NotebookLM Studio 自动化总结](../../docs/NOTEBOOKLM_STUDIO_AUTOMATION_SUMMARY_2026-04-28.md)
- [Audio/Slides 生成经验](../../deliverables/research-sequence-diagram/metadata.json)

## 优先级说明

**P2**: 非阻塞任务，可后续补充。当前项目已有 Audio + Slides，基本功能完整。
