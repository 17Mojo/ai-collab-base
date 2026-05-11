---
task_id: TASK-W10-D4-CICD-OPTIMIZATION-004
change_id: github-actions-workflow-optimization
status: completed
assignee: claude_code
reviewer: user
primary_skill: cicd
support_skills: ["github_actions", "yaml", "testing"]
acceptance_commands: "ls .github/workflows/*.yml | wc -l"
created_at: 2026-04-28T09:00:00
estimated_hours: 1.5
priority: P2
depends_on: []
---

# TASK-W10-D4-CICD-OPTIMIZATION-004

## 任务描述

优化 GitHub Actions 工作流配置。

## 背景

当前 CI/CD 工作流需要完善和优化。

## 详细任务

### Task 1: 现有工作流检查 (20min)

**检查项**:

```bash
ls .github/workflows/*.yml
```

| 工作流 | 状态 |
|--------|------|
| backend-test.yml | 需检查 |
| extension-test.yml | 需创建 |
| pack-validate.yml | 需创建 |

---

### Task 2: Extension 测试工作流 (30min)

**新建**: `.github/workflows/extension-test.yml`

```yaml
name: Chrome Extension Tests

on:
  push:
    paths:
      - 'chrome-extension/**'
  pull_request:
    paths:
      - 'chrome-extension/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Run Adapter Tests
        run: |
          cd chrome-extension/tests
          node test-adapters.js
          node test-branch-executor.js

      - name: Run Branch Tests
        run: node chrome-extension/tests/test-branch-execution-real.js
```

---

### Task 3: Pack 验证工作流 (20min)

**新建**: `.github/workflows/pack-validate.yml`

```yaml
name: Pack Validation

on:
  push:
    paths:
      - 'packs/**/*.json'
  pull_request:
    paths:
      - 'packs/**/*.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate Pack JSONs
        run: |
          for pack in packs/examples/*.json; do
            python -c "import json; json.load(open('$pack'))"
            echo "✅ $pack valid"
          done
```

---

### Task 4: 性能测试工作流 (20min)

**新建**: `.github/workflows/performance-test.yml`

```yaml
name: Performance Benchmark

on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Run Performance Tests
        run: |
          python -m pytest tests/performance/ -v
```

---

### Task 5: 工作流验证 (20min)

**验证项**:
- YAML 格式正确
- 依赖安装正确
- 测试命令正确

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 5+ 工作流配置 | ls 统计 |
| YAML 格式正确 | yamllint |
| 测试覆盖完整 | workflow 内容 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| .github/workflows/extension-test.yml | 新建 |
| .github/workflows/pack-validate.yml | 新建 |
| .github/workflows/performance-test.yml | 新建 |
| collaboration/results/CICD_RESULT.md | 新建 |

---

**创建时间**: 2026-04-28T09:00:00+08:00
