---
task_id: TASK-W7-D3-XHS-STUDIO-DELIVERABLES-003
change_id: xiaohongshu-studio-deliverables-generation
status: completed
assignee: claude_code
reviewer: user
primary_skill: notebooklm
support_skills: ["content_generation", "deliverables_management"]
acceptance_commands: "ls deliverables/xhs-guide/*.m4a deliverables/xhs-guide/*.mp4 deliverables/xhs-guide/*.pdf"
created_at: 2026-04-25T10:00:00
estimated_hours: 1.5
priority: P2
depends_on: ["TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002"]
---

# TASK-W7-D3-XHS-STUDIO-DELIVERABLES-003

## 任务描述

为小红书创作指南场景生成 Studio 多模态交付物（Audio + Video + Slides），并按交付物管理规范存放。

## 背景

北方旅游攻略场景已完成 Studio 产物生成（94MB），小红书创作指南场景待生成。

## 详细任务

### Task 1: 确认知识源 (10min)

**位置**: `knowledge-sources/xiaohongshu_knowledge_creator_guide.md`

**验证**:
- 文件存在且内容完整
- NotebookLM Source ID: `b83da83a-5578-4b92-b22b-b4bdb7e9dfb5`
- Notebook ID: `d2b04caa-257a-4aad-82b0-f58c28e0dad5`

---

### Task 2: 创建交付物目录 (10min)

**命令**:

```bash
mkdir -p deliverables/xhs-guide
```

**目录结构**:

```
deliverables/xhs-guide/
├── README.md
├── metadata.json
├── xhs-guide-audio.m4a
├── xhs-guide-video.mp4
└── xhs-guide-slides.pdf
```

---

### Task 3: 生成 Studio 产物 (60min)

**命令**:

```bash
# Audio 播客
nlm audio create d2b04caa-257a-4aad-82b0-f58c28e0dad5 \
  --format deep_dive \
  --language zh-CN \
  --focus "小红书知识型博主创作指南"

# Video 视频
nlm video create d2b04caa-257a-4aad-82b0-f58c28e0dad5 \
  --language zh-CN \
  --focus "小红书创作技巧"

# Slides 幻灯片
nlm slides create d2b04caa-257a-4aad-82b0-f58c28e0dad5 \
  --format detailed_deck \
  --language zh-CN \
  --focus "知识型博主内容创作方法"
```

---

### Task 4: 下载产物 (20min)

**命令**:

```bash
# 下载 Audio
nlm download audio d2b04caa-... --id {audio_artifact_id} --output deliverables/xhs-guide/xhs-guide-audio.m4a

# 下载 Video
nlm download video d2b04caa-... --id {video_artifact_id} --output deliverables/xhs-guide/xhs-guide-video.mp4

# 下载 Slides
nlm download slide-deck d2b04caa-... --id {slides_artifact_id} --output deliverables/xhs-guide/xhs-guide-slides.pdf
```

---

### Task 5: 创建元数据文件 (10min)

**位置**: `deliverables/xhs-guide/metadata.json`

```json
{
  "scene_id": "xhs-guide",
  "scene_name": "小红书创作指南",
  "pack_id": "xhs-knowledge-creator-v2",
  "created_at": "2026-04-25",
  "knowledge_source": {
    "file": "xiaohongshu_knowledge_creator_guide.md",
    "path": "knowledge-sources/xiaohongshu_knowledge_creator_guide.md",
    "notebooklm_source_id": "b83da83a-5578-4b92-b22b-b4bdb7e9dfb5"
  },
  "studio_artifacts": [
    {
      "type": "audio",
      "artifact_id": "{audio_id}",
      "file": "xhs-guide-audio.m4a",
      "size_mb": 0,
      "format": "deep_dive",
      "language": "zh-CN",
      "focus": "小红书知识型博主创作指南"
    },
    {
      "type": "video",
      "artifact_id": "{video_id}",
      "file": "xhs-guide-video.mp4",
      "size_mb": 0,
      "language": "zh-CN",
      "focus": "小红书创作技巧"
    },
    {
      "type": "slide_deck",
      "artifact_id": "{slides_id}",
      "file": "xhs-guide-slides.pdf",
      "size_mb": 0,
      "pages": 0,
      "format": "detailed_deck",
      "language": "zh-CN",
      "focus": "知识型博主内容创作方法"
    }
  ],
  "notebook_id": "d2b04caa-257a-4aad-82b0-f58c28e0dad5",
  "total_size_mb": 0,
  "status": "completed"
}
```

---

### Task 6: 创建 README (10min)

**位置**: `deliverables/xhs-guide/README.md`

参照 `deliverables/travel-guide/README.md` 格式。

---

### Task 7: 更新总索引 (10min)

**位置**: `deliverables/index.md`

更新小红书创作指南场景状态为 "完成"。

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| Audio 文件存在且 > 10MB | `ls -la` + `file` 命令 |
| Video 文件存在且 > 10MB | `ls -la` + `file` 命令 |
| Slides 文件存在且 > 5MB | `ls -la` + `file` 命令 |
| metadata.json 包含正确 Artifact IDs | JSON 格式验证 |
| README.md 包含生成/下载命令 | 文件内容检查 |
| deliverables/index.md 已更新 | 状态为 ✅ |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `deliverables/xhs-guide/` | 新建目录 |
| `deliverables/xhs-guide/xhs-guide-audio.m4a` | 下载产物 |
| `deliverables/xhs-guide/xhs-guide-video.mp4` | 下载产物 |
| `deliverables/xhs-guide/xhs-guide-slides.pdf` | 下载产物 |
| `deliverables/xhs-guide/metadata.json` | 新建元数据 |
| `deliverables/xhs-guide/README.md` | 新建说明 |
| `deliverables/index.md` | 更新索引 |

---

## 风险/回滚

| 飆险 | 影响 | 缓解 |
|------|------|------|
| NotebookLM 认证过期 | 生成失败 | 先检查认证状态 |
| 生成超时 | 产物丢失 | 增加超时时间 |
| 下载失败 | 文件不完整 | 重试下载 |

**回滚方案**: 删除 `deliverables/xhs-guide/` 目录

---

## 参考文档

- 北方旅游攻略交付物: `deliverables/travel-guide/`
- 交付物管理规范: `deliverables/DELIVERABLES_MANAGEMENT_SPEC.md`
- Studio 融合测试报告: `collaboration/results/STUDIO_FUSION_TEST_2026-04-25.md`

---

**创建时间**: 2026-04-25T10:00:00+08:00