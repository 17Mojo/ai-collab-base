---
name: laya 本地决策引擎服务（127.0.0.1:8421）
description: 用户本地部署的 MLX 双模型决策引擎，区别于通用对话 LLM，用于结构化决策问题（分类/打分/真伪判断）
type: reference
from: Agent
---

用户在本机部署了 **laya**（实为 jev 双模型）本地决策引擎服务，地址 `http://127.0.0.1:8421`，**不是对话模型**，而是一次前向传播回答三类结构化问题的决策引擎：

- **choice**：从多个选项中选一个（返回选项名 + 概率分布）
- **score**：按评分标准打分（返回分数 + 各级概率）
- **noul**：判断命题是否为真（返回 P(true)）

## 核心特点
- **延迟**：10-26ms（typed-decisions ~26ms / multilingual ~12ms，**0 个生成 token、不会幻觉**）
- **上下文限**：1024 token，不适合超长文档
- **不适合**：生成文本回复、开放式问答、需要长推理链

## 双模型与自动路由
- **typed-decisions**（421M，ModernBERT-large）：英文/拉丁字符路由到此
- **multilingual**（322M，mmBERT-base）：中日韩俄阿印等非拉丁字符路由到此
- **POST `/predict`** 不指定 `model` 时按输入字符类型自动路由（拉丁→typed-decisions，否则→multilingual）；可显式指定 `model="multilingual"` 绕过路由

## 启动与服务管理
- **conda 环境名**：`laya`（`conda activate laya` → `python serve.py` 启动）
- **API 文档**：浏览器打开 `http://127.0.0.1:8421/docs`（Swagger UI）
- **已加入开机自启**（macOS launchd）：`~/Library/LaunchAgents/com.laya.mlx-api.plist`，KeepAlive 崩溃自动重启
- **管理命令**：`bash service.sh status|start|stop|restart|logs|errors`
- **日志位置**：`~/.laya-mlx-api.log`（stdout）/ `~/.laya-mlx-api.err`（stderr）

## 调用示例
```python
import requests
result = requests.post("http://127.0.0.1:8421/predict", json={
    "state": "发票被重复扣款",
    "questions": {
        "dept": {"type": "choice", "instructions": "哪个部门？", "criteria": ["billing", "tech"]},
        "urgency": {"type": "score", "instructions": "紧急程度？", "criteria": ["不紧急", "尽快处理", "紧急/阻塞"]},
        "refund_requested": {"type": "noul", "instructions": "用户是否明确要求退款？"}
    }
}).json()
# result["answers"]["dept"]["choice"] / result["answers"]["urgency"]["score"] / result["answers"]["refund_requested"]["noul"]
# result["latency_ms"] ~10-26ms
```

## 典型应用场景
- 邮件/工单自动分类（部门/紧急度/风险多维度并行判断）
- 多语言客服路由（自动按语言路由到对应模型）
- 对话流实时决策（state 可以是 conversation list）
- 内容审核/安全检测
- 批量工单处理（ThreadPoolExecutor 1000 条 ≈ 3-5s）
- **作为 LLM 的前置决策层**：先用 laya 判断 `needs_llm`，复杂问题才调 Claude/GPT

## 与 127.0.0.1:1234 的关系
**两个不同服务**：
- `127.0.0.1:1234`：LM Studio / 通用对话 LLM（生成文本回复）
- `127.0.0.1:8421`：laya / 专用决策引擎（不给文本，只给概率/分类）

**How to apply:** 用户要求"分类/打分/判断真假/做决策"或提供决策选项时，优先考虑 laya；要求"生成回复/对话/长文"时，用 1234 的对话 LLM。两者可串联：laya 前置过滤 → 复杂问题转 LLM 生成。