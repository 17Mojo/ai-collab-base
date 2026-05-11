---
task_id: TASK-W11-D2-SYSTEM-MONITORING-002
change_id: system-monitoring-and-alerting-configuration
status: completed
assignee: claude_code
reviewer: user
primary_skill: monitoring
support_skills: ["prometheus", "grafana", "alerting"]
acceptance_commands: "curl http://127.0.0.1:8000/metrics | grep prompt_pack"
created_at: 2026-04-29T09:00:00
estimated_hours: 1.5
priority: P1
depends_on: []
---

# TASK-W11-D2-SYSTEM-MONITORING-002

## 任务描述

配置系统监控和告警机制。

## 背景

系统已有 Prometheus 指标，需要完善监控和告警。

## 详细任务

### Task 1: 监控指标扩展 (40min)

**当前指标**:
- prompt_pack_http_requests_total
- prompt_pack_http_request_duration_seconds
- prompt_pack_http_exceptions_total

**新增指标**:

| 指标 | 类型 | 说明 |
|------|------|------|
| prompt_pack_execution_total | Counter | Pack 执行总数 |
| prompt_pack_execution_duration | Histogram | 执行耗时分布 |
| prompt_pack_cache_hits | Counter | 缓存命中数 |
| prompt_pack_notebooklm_queries | Counter | NotebookLM 查询数 |
| prompt_pack_active_connections | Gauge | 活跃连接数 |

---

### Task 2: 告警规则定义 (30min)

**告警规则**:

```yaml
groups:
  - name: prompt_pack_alerts
    rules:
      - alert: HighResponseTime
        expr: prompt_pack_http_request_duration_seconds > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 响应时间过高"

      - alert: HighErrorRate
        expr: rate(prompt_pack_http_exceptions_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API 错误率过高"
```

---

### Task 3: 健康检查增强 (20min)

**增强内容**:
- 内存使用检测
- 数据库连接状态
- NotebookLM 认证状态
- 缓存命中率

---

### Task 4: 监控文档 (10min)

**位置**: `docs/MONITORING_GUIDE.md`

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 新增指标可采集 | /metrics 检查 |
| 告警规则定义 | YAML 格式 |
| 健康检查增强 | /health 检查 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| local-backend/app/core/monitoring.py | 修改 |
| prometheus/alert_rules.yml | 新建 |
| docs/MONITORING_GUIDE.md | 新建 |

---

**创建时间**: 2026-04-29T09:00:00+08:00
