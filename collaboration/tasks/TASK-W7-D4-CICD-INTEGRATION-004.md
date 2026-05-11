---
task_id: TASK-W7-D4-CICD-INTEGRATION-004
change_id: cicd-pipeline-integration
status: completed
assignee: codearts_agent
reviewer: claude_code
primary_skill: devops
support_skills: ["github_actions", "docker", "testing"]
acceptance_commands: "gh actions list && docker compose ps"
created_at: 2026-04-25T10:00:00
estimated_hours: 3.0
priority: P3
depends_on: ["TASK-W7-D1-BRANCH-REGEX-IMPL-001", "TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002"]
---

# TASK-W7-D4-CICD-INTEGRATION-004

## 任务描述

为 AI Collab System 配置 CI/CD 管道，实现自动化测试、构建和部署流程。

## 背景

当前项目无自动化 CI/CD 流程，依赖手动测试和部署。需建立标准化 Pipeline。

## 详细任务

### Task 1: GitHub Actions 配置 (60min)

**位置**: `.github/workflows/`

**创建工作流文件**:

#### 1.1 测试工作流 - `test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      backend:
        image: python:3.10
        options: --entrypoint uvicorn
        env:
          PORT: 8000
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/integration/ -v

  chrome-extension-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd chrome-extension && npm install
      - run: cd chrome-extension && npm test
```

---

#### 1.2 构建工作流 - `build.yml`

```yaml
name: Build Artifacts

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build-extension:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd chrome-extension && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: chrome-extension
          path: chrome-extension/dist/

  build-docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: ./local-backend
          tags: ai-collab-backend:latest
          push: false
```

---

#### 1.3 发布工作流 - `release.yml`

```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd chrome-extension && npm run build
      - uses: softprops/action-gh-release@v1
        with:
          files: |
            chrome-extension/dist/*.zip
            local-backend/dist/*.whl
```

---

### Task 2: Docker Compose 完善 (30min)

**位置**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./local-backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./local-backend/data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/packs.db
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  playwright:
    image: mcr.microsoft.com/playwright:v1.40.0
    volumes:
      - ./tests/playwright:/app
    command: ["npx", "playwright", "test"]
    depends_on:
      - backend
```

---

### Task 3: 质量门禁配置 (30min)

**位置**: `.github/workflows/quality-gate.yml`

```yaml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install ruff black mypy
      - run: ruff check src/
      - run: black --check src/
      - run: mypy src/

  coverage-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest --cov=src --cov-fail-under=80
```

---

### Task 4: 环境变量管理 (30min)

**位置**: `.env.example`, `local-backend/.env`

```env
# Backend
DATABASE_URL=sqlite:///data/packs.db
LOG_LEVEL=INFO
API_PORT=8000

# NotebookLM
NOTEBOOKLM_NOTEBOOK_ID=d2b04caa-257a-4aad-82b0-f58c28e0dad5

# Chrome Extension
EXTENSION_ID=your-extension-id
```

---

### Task 5: 文档更新 (30min)

**位置**: `docs/CI_CD_GUIDE.md`

内容包括:
- CI/CD 流程说明
- 工作流触发条件
- 如何添加新的测试
- 发布流程
- 常见问题排查

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| GitHub Actions 工作流创建成功 | `gh actions list` 显示工作流 |
| 测试工作流在 PR 时触发 | 创建 PR 观察 |
| 构建产物上传成功 | Actions Artifacts 查看 |
| Docker Compose 启动正常 | `docker compose ps` |
| 质量门禁阻止低质量 PR | 低覆盖率 PR 测试 |
| 文档完整 | CI_CD_GUIDE.md 验证 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `.github/workflows/test.yml` | 新建测试工作流 |
| `.github/workflows/build.yml` | 新建构建工作流 |
| `.github/workflows/release.yml` | 新建发布工作流 |
| `.github/workflows/quality-gate.yml` | 新建质量门禁 |
| `docker-compose.yml` | 完善 Docker 配置 |
| `.env.example` | 新建环境变量示例 |
| `docs/CI_CD_GUIDE.md` | 新建 CI/CD 文档 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| GitHub Actions 限流 | 构建排队 | 缓存依赖 + 并行 job |
| Docker 镜像过大 | 构建慢 | 多阶段构建 |
| 测试不稳定 | CI 失败 | 重试机制 |

**回滚方案**: 删除 `.github/workflows/` 目录

---

## 参考文档

- 测试结构: `tests/`
- Docker 配置: `local-backend/Dockerfile`
- GitHub Actions 文档: https://docs.github.com/actions

---

**创建时间**: 2026-04-25T10:00:00+08:00