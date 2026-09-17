# User Guide

**Version**: 1.0.0
**Last Updated**: 2026-09-14

This guide covers installation, configuration, and usage of ai-collab-base.

## Quick Start

```bash
git clone https://github.com/17Mojo/ai-collab-base.git
cd ai-collab-base
pip install -r requirements.txt
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 20+
- Chrome (latest stable)

### Backend

```bash
cd local-backend
pip install -r requirements.txt
# Or
docker-compose up
```

### Chrome Extension

1. Open chrome://extensions/
2. Enable Developer mode
3. Click Load unpacked
4. Select the chrome-extension/ directory

## Configuration

### Backend

Edit local-backend/.env (copy from .env.example):
- DATABASE_URL
- API_KEYS
- LOG_LEVEL

### Extension

1. Click extension icon in Chrome
2. Open Settings
3. Configure:
   - Backend URL
   - Default platform
   - Auto-execute settings

## Using the Chrome Extension

### Workflow

1. Navigate to AI platform (Claude, ChatGPT, etc.)
2. Click extension icon
3. Select a Pack
4. Click Execute
5. Extension auto-fills, submits, captures result

### Supported Platforms

11+ platforms: ChatGPT, Claude, Gemini, Kimi,
Tongyi, Zhipu, Wenxin, Tencent Yuanbao, LongCat, Doubao, DeepSeek

## Using the Backend API

### Start

```bash
cd local-backend
python -m uvicorn app.main:app --reload --port 8000
```

### Endpoints

- GET /api/health - Health check
- GET /api/packs - List packs
- POST /api/packs/{id}/execute - Execute a pack
- GET /api/packs/{id}/metadata - Get metadata

### Authentication

Uses Personal Access Tokens via X-Client-Token header.

## Pack Workflows

### Structure

A Pack is JSON defining:
- metadata: ID, name, version
- workflow: Steps with types
- branches: Conditional logic
- quality_metrics: Evaluation criteria

### Example

See packs/examples/email-auto-reply.json.

### Creating Custom Packs

1. Copy existing pack
2. Modify workflow steps
3. Test in dev mode
4. Add to packs/custom/

## Troubleshooting

### Backend will not start

- python --version (must be 3.10+)
- pip list | grep fastapi
- lsof -i :8000

### Extension not loading

- Chrome version (88+)
- Developer mode enabled
- All files in chrome-extension/

### Test failures

```bash
python -m pytest tests/unit/ -v --tb=short
```

### CI issues

See docs/ALERTING_RUNBOOK.md.

## Getting Help

- GitHub Issues: https://github.com/17Mojo/ai-collab-base/issues
- Documentation: docs/
- Workflows: .github/workflows/

## See Also

- CHANGELOG.md
- ARCHITECTURE.md
- README.md
