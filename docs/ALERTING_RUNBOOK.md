# 告警响应手册 (Alerting Runbook)

本文档描述本地后端监控告警的响应流程与演练步骤。

---

## 告警响应流程（最小闭环）

1. **确认告警**：在 Prometheus / Alertmanager 中确认告警已触发，记录 alert name 与时间。
2. **初步定位**：查看 `/metrics` 与后端日志，确认是流量变化、依赖故障还是代码缺陷。
3. **缓解措施**：按下方各告警的处置步骤执行；必要时先回滚最近部署。
4. **闭环记录**：在 `collaboration/results/` 记录处理过程、根因与后续改进项。
5. **复盘**：将新增的防护措施补入规则与测试。

---

## 错误率告警演练

**关联告警**: `PromptPackApiErrorRateWarning`

**触发条件**: `prompt_pack_http_requests_total` 5xx 比例 > 0.05（持续 10m）

**演练步骤**:
1. 注入故障：临时让 `/api/health` 返回 500。
2. 观察指标：确认 `prompt_pack_http_requests_total{status="5xx"}` 上升。
3. 确认告警在预期窗口内触发。
4. 恢复服务并确认告警自动解除。
5. 记录演练时间线与结果。

---

## 延迟告警演练

**关联告警**: `PromptPackApiLatencyP95Warning`

**触发条件**: `prompt_pack_http_request_duration_seconds_bucket` P95 > 0.25（持续 5m）

**演练步骤**:
1. 注入延迟：在 API 处理链路中加入固定 sleep。
2. 观察 P95 指标上升。
3. 确认告警触发。
4. 移除延迟并确认告警解除。
5. 记录演练结论。

---

## 失败比例告警演练

**关联告警**: `PromptPackPackApiFailureRatioWarning`

**触发条件**: Pack API 失败比例 > 0.15（持续 2m）

**演练步骤**:
1. 注入失败：让 Pack API 对特定请求返回错误。
2. 观察失败比例指标。
3. 确认告警触发。
4. 恢复并确认解除。
5. 记录演练结论。

---

## 异常突增告警演练

**关联告警**: 异常突增（`prompt_pack_http_exceptions_total` 短时激增）

**触发条件**: `prompt_pack_http_exceptions_total` 速率 > 0.30（持续 2m）

**演练步骤**:
1. 注入异常：构造触发未捕获异常的请求。
2. 观察异常计数突增。
3. 确认告警触发。
4. 修复并确认解除。
5. 记录演练结论。

---

## 常见告警速查

| 告警 | 严重度 | 首要动作 |
|------|--------|----------|
| PromptPackApiErrorRateWarning | warning | 检查最近部署与依赖 |
| PromptPackApiLatencyP95Warning | warning | 检查 DB 与外部调用 |
| PromptPackPackApiFailureRatioWarning | warning | 检查 Pack 数据与校验逻辑 |

---

**维护者**: AI Collab Team
**最后更新**: 2026-09-13
