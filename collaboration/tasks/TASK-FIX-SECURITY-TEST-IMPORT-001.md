# 任务: 修复安全测试导入问题

**任务ID**: TASK-FIX-SECURITY-TEST-IMPORT-001
**创建时间**: 2026-02-28T17:00:00+08:00
**优先级**: P1 (高)
**创建者**: CodeArts Agent (技术合伙人)

---

## 问题描述

**发现的问题**:
- 安全测试全部跳过 (17 个测试)
- 原因: `local_backend` 模块导入失败
- 根本原因: 目录名为 `local-backend` (带连字符),不符合 Python 模块命名规范

**影响范围**:
- 17 个安全测试无法运行
- 安全功能无法验证
- 测试覆盖率降低

---

## 解决方案

**方案 1: 重命名目录** (推荐)
- 将 `local-backend` 重命名为 `local_backend`
- 更新所有引用该路径的配置文件
- 优点: 符合 Python 规范,一劳永逸
- 缺点: 需要更新多处引用

**方案 2: 修改导入路径**
- 在测试文件中使用 `sys.path` 添加路径
- 使用 `importlib` 动态导入
- 优点: 不需要重命名目录
- 缺点: 不符合 Python 规范,维护困难

**推荐方案**: 方案 1 (重命名目录)

---

## 执行步骤

### 步骤 1: 检查影响范围
```bash
# 查找所有引用 local-backend 的文件
grep -r "local-backend" --include="*.py" --include="*.md" --include="*.json" --include="*.yml" --include="*.yaml"
```

### 步骤 2: 重命名目录
```bash
mv local-backend local_backend
```

### 步骤 3: 更新所有引用
需要更新的文件可能包括:
- `docker-compose.yml`
- `Dockerfile`
- `README.md`
- `docs/` 下的文档
- 测试文件
- 配置文件

### 步骤 4: 验证修复
```bash
# 运行安全测试
python3 -m pytest tests/security/test_security_functions.py -v

# 运行所有测试
python3 -m pytest tests/ -v
```

---

## 验证标准

- [ ] 安全测试可以正常运行 (不再跳过)
- [ ] 所有测试通过
- [ ] 没有破坏现有功能
- [ ] 文档和配置已更新

---

## 分配建议

**建议分配给**: `codex` 或 `claude_code`

**理由**:
- 这是一个代码修改任务
- 需要修改多个文件
- 需要验证测试通过

**预计耗时**: 30-60 分钟

---

## 备注

这是技术合伙人主动发现并协调解决的问题。请责任 AI 接收任务后立即执行,并在完成后提交结果文件。
