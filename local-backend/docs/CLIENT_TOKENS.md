# 客户端 Token 使用文档

**创建时间**: 2026-02-28
**版本**: 1.0.0
**用途**: 双端 API 访问认证

---

## 概述

客户端 Token 用于保护双端分发模式中的敏感 API 端点。只有持有有效 Token 的客户端才能访问完整的 Pack 数据（包含 `system_prompt` 等敏感信息）。

## 初始令牌

### 1. Chrome 扩展令牌

**用途**: Chrome 扩展访问完整 Pack

```
Token: b81814a603fa90bad18558ee51a968925ad3800d648e8707119d5c6043f3a3f3
权限: ["read", "execute", "write_results"]
有效期: 永久
```

### 2. VSCode 后端令牌

**用途**: VSCode 扩展后端访问完整 Pack

```
Token: f797466f52ffe2320c71c55de789600661078cd41db8c05d76e66c1c1d8e73aa
权限: ["read", "write", "admin"]
有效期: 永久
```

### 3. 管理员令牌

**用途**: 管理员访问所有功能

```
Token: 8b99671c3b0ff746c0ee87d7965bb12693293a772b977425b86e9fb13f76cfc0
权限: ["*"]
有效期: 永久
```

## API 使用方式

### 获取元数据（无需 Token）

```bash
# 客户端仅获取元数据（不包含敏感信息）
curl http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/metadata
```

**返回内容**:
- Pack 基础信息
- 工作流定义
- 输入输出模式
- 质量指标定义（不含权重）
- 生成参数

### 获取完整 Pack（需要 Token）

```bash
# 服务端获取完整 Pack（包含敏感信息）
curl -X POST http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/full \
  -H "X-Client-Token: b81814a603fa90bad18558ee51a968925ad3800d648e8707119d5c6043f3a3f3"
```

**返回内容**:
- 所有元数据端点的内容
- ✅ `system_prompt` (敏感)
- ✅ `quality_validation_rules` (敏感)
- ✅ `optimization` 配置
- ✅ `performance_tracking` 配置
- ✅ `collaboration` 配置

## 错误响应

### 401 - 缺少 Token

```json
{
  "detail": "Missing client token. Please provide X-Client-Token header."
}
```

### 403 - 无效 Token

```json
{
  "detail": "Invalid client token"
}
```

### 403 - Token 过期

```json
{
  "detail": "Client token has expired"
}
```

## 代码示例

### Python 请求示例

```python
import requests

# 获取元数据（不需要 Token）
response = requests.get(
    'http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/metadata'
)
metadata = response.json()

# 获取完整 Pack（需要 Token）
headers = {
    'X-Client-Token': 'b81814a603fa90bad18558ee51a968925ad3800d648e8707119d5c6043f3a3f3'
}
response = requests.post(
    'http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/full',
    headers=headers
)
full_pack = response.json()
```

### JavaScript/Fetch 示例

```javascript
// 获取元数据（不需要 Token）
fetch('http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/metadata')
  .then(response => response.json())
  .then(metadata => {
    console.log('Pack metadata:', metadata);
  });

// 获取完整 Pack（需要 Token）
fetch('http://127.0.0.1:8000/api/packs/xiaohongshu-explosive-copy/full', {
  method: 'POST',
  headers: {
    'X-Client-Token': 'b81814a603fa90bad18558ee51a968925ad3800d648e8707119d5c6043f3a3f3'
  }
})
  .then(response => response.json())
  .then(fullPack => {
    console.log('Full pack including system_prompt:', fullPack);
  });
```

## 令牌管理

### 生成新令牌（Python 代码）

```python
from local_backend.app.core.client_tokens import TokenManager

manager = TokenManager()

# 生成临时令牌（24小时有效期）
token = manager.generate_token(
    client_name="temp-client",
    permissions=["read", "execute"],
    expires_hours=24
)
print(f"新令牌: {token}")
```

### 撤销令牌（Python 代码）

```python
from local_backend.app.core.client_tokens import TokenManager

manager = TokenManager()

# 撤销令牌
token = "b81814a603fa90bad18558ee51a968925ad3800d648e8707119d5c6043f3a3f3"
success = manager.revoke(token)
print(f"撤销结果: {success}")
```

### 列出所有令牌（Python 代码）

```python
from local_backend.app.core.client_tokens import TokenManager

manager = TokenManager()

# 列出活跃令牌
tokens = manager.list_tokens(include_inactive=False)
for token in tokens:
    print(f"{token['client_name']}: {token['token']}")

# 列出所有令牌（包括已撤销）
all_tokens = manager.list_tokens(include_inactive=True)
for token in all_tokens:
    status = "活跃" if token['is_active'] else "已撤销"
    print(f"{token['client_name']} ({status}): {token['token']}")
```

## 安全建议

1. **不要硬编码 Token**: 将 Token 存储在配置文件或环境变量中
2. **使用 HTTPS**: 生产环境中必须使用 HTTPS 传输 Token
3. **定期轮换**: 建议定期更换 Token（如每月一次）
4. **最小权限原则**: 只授予必要的权限
5. **监控访问日志**: 记录令牌使用情况，检测异常访问

## 常见问题

### Q: 忘记了 Token 怎么办？

A: 可以使用管理员权限生成新令牌：

```python
from local_backend.app.core.client_tokens import TokenManager

manager = TokenManager()
new_token = manager.generate_token(
    client_name="your-client-name",
    permissions=["read", "execute"]  # 根据需要配置权限
)
print(f"新令牌: {new_token}")
```

### Q: Token 泄露了怎么办？

A: 立即撤销泄露的 Token 并生成新的：

```python
from local_backend.app.core.client_tokens import TokenManager

manager = TokenManager()

# 撤销泄露的 Token
manager.revoke("leaked_token_here")

# 生成新的 Token
new_token = manager.generate_token(
    client_name="your-client-name",
    permissions=["read", "execute"]
)
print(f"新令牌: {new_token}")
```

### Q: 如何为多个客户端生成不同的 Token？

A: 为每个客户端单独生成 Token，并记录对应关系：

```python
tokens = {}
clients = ["client-1", "client-2", "client-3"]

manager = TokenManager()
for client in clients:
    token = manager.generate_token(
        client_name=client,
        permissions=["read"],
        expires_hours=24  # 可配置不同的有效期
    )
    tokens[client] = token

print("Token 映射:", tokens)
```

## 令牌存储位置

令牌数据存储在: `local-backend/data/client_tokens.json`

**⚠️ 重要**: 不要将此文件提交到版本控制系统！

确保 `.gitignore` 包含以下条目:

```
local-backend/data/*.json
!local-backend/data/.gitkeep
```

## 相关文件

- `local-backend/app/core/client_tokens.py` - 令牌管理核心实现
- `local-backend/app/api/packs.py` - API 端点（已集成 Token 验证）
- `local-backend/data/client_tokens.json` - 令牌存储文件

## 技术支持

如遇到问题，请检查:

1. Token 是否正确复制（注意前后空格）
2. Token 是否已过期（临时 Token 会过期）
3. Token 是否被撤销
4. 后端服务是否正常运行

运行以下命令检查令牌状态:

```bash
python3 local-backend/app/core/client_tokens.py
```

这将列所有活跃的 Token 及其状态。
