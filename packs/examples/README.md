# packs/examples — 能跑的示例包

这个目录的准入标准只有一条：**包能被仓库自己的校验器判为 VALID**。

```bash
# 从仓库根目录，逐个数验证
for f in packs/examples/*.json; do
  python -c "
from ai_collab.pack.schema_validator import validate_pack
r = validate_pack('$f')
print(('VALID  ' if r.is_valid else 'INVALID'), '$f')
"
done
```

全绿才算合格。这里放的是**照着能改、改完能跑**的东西，不是结构参考。

## 当前内容

| 文件 | 步骤 | 说明 |
|---|---|---|
| `external-user-smoke.json` | 1 | 冒烟自检包：一句提示词、零输入，用来确认「装好了、能跑通」 |
| `xiaohongshu_knowledge_creator.json` | 8 | 小红书知识型博主内容生产，完整业务场景，7 个 AI 步骤都有真实 `prompt_template` |

## 不是示例的包在哪

结构性参考（有 `workflow.steps` 骨架但**没有 `prompt_template`**，跑起来只会产出空对象）在
[`../templates/`](../templates/)。那些不能当「照着写」的范本用，见该目录 README 的警告。

## 历史

2026-11-03 之前本目录有 17 个包，其中 15 个是无 `prompt_template` 的空壳，
`validate_pack` 通过率 2/17。空壳已移入 `packs/templates/`，本目录只留可运行包，
使「examples」这个名字与磁盘内容一致。
