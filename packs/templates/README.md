# packs/templates — 结构参考（不可运行）

> **不要把这些包当示例照抄。** 它们没有 `prompt_template`，
> 每个 AI 步骤跑起来只会产出空对象，最终结果是一串 `[object Object]`。

这些文件的价值只有一个：告诉你 Pack 的 JSON **长什么样**——顶层有哪些键、
`workflow.steps` 怎么排、分支怎么连、`quality_metrics` 怎么组织。
它们是历史遗留的设计草稿，保留是为了「结构可考」，不是为了「能跑」。

## 准入标准

没有 `prompt_template`（或等价的实际提示词）的包放这里。
一旦补上真实提示词并通过 `validate_pack`，就该移进 [`../examples/`](../examples/)。

## 当前内容（15 个）

| 文件 | 步骤 | 主题 |
|---|---|---|
| `ai_collab_intro.json` | 4 | AI 协作系统介绍文案 |
| `bilibili_video_script.json` | 6 | B 站视频脚本 |
| `demo-pack.json` | 2 | 最小结构演示（无分支） |
| `douyin_video_script.json` | 6 | 抖音视频脚本 |
| `email-auto-reply.json` | 6 | 邮件自动回复 |
| `error-handling-workflow.json` | 5 | 错误处理 + 分支路由（**唯一带 `branches` 的包**） |
| `generic_content_writer.json` | 3 | 通用内容写作 |
| `tech_documentation.json` | 6 | 技术文档 |
| `test-demo.json` | 2 | 测试用最小包 |
| `travel_planner_north_guide.json` | 8 | 北方旅行攻略 |
| `weekly_report.json` | 6 | 周报生成 |
| `weibo_explosive_copy.json` | 6 | 微博爆款文案 |
| `xiaohongshu_beauty_review.json` | 6 | 小红书美妆测评 |
| `xiaohongshu_food_explore.json` | 6 | 小红书探店 |
| `zhihu_answer_optimization.json` | 6 | 知乎回答优化 |

## 谁在依赖这些文件

`packs/templates/` 不是死目录，以下位置直接读它：

- `tests/integration/test_branch_logic.py` — 读 `error-handling-workflow.json`
  验证分支目标引用与 `regex_config` 结构（**CI 会跑**）
- `tests/test_pack_mvp.py` — 读 `ai_collab_intro.json` 跑通执行器（CI 不跑，本地跑）

改文件名或挪位置时这两处必须同步，否则 CI 红。

## 历史

2026-11-03 从 `packs/examples/` 迁入。当时 17 个示例包里 15 个没有 `prompt_template`，
`validate_pack` 通过率 2/17——目录名 `examples` 与实际内容不符，故拆开。
