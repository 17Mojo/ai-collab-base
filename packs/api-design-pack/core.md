# API 设计核心规范

## RESTful 设计原则

### 1. 资源命名

- **使用复数形式**: `/users` 而非 `/user`
- **使用小写字母**: `/user-profiles` 而非 `/UserProfiles`
- **使用连字符分隔**: `/user-orders` 而非 `/userOrders`
- **避免特殊字符**: 只使用字母、数字、连字符和下划线

### 2. URL 结构

```
/资源名                # 集合
/资源名/{id}           # 单个资源
/资源名/{id}/子资源名   # 子资源
```

示例:
```
GET    /users              # 获取用户列表
GET    /users/123          # 获取单个用户
GET    /users/123/orders   # 获取用户的订单
POST   /users/123/orders   # 为用户创建订单
```

### 3. HTTP 方法

| 方法 | 操作 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 查询资源 | ✅ 是 | ✅ 是 |
| POST | 创建资源 | ❌ 否 | ❌ 否 |
| PUT | 完整更新 | ✅ 是 | ❌ 否 |
| PATCH | 部分更新 | ❌ 否 | ❌ 否 |
| DELETE | 删除资源 | ✅ 是 | ❌ 否 |

### 4. 状态码

#### 成功响应
- `200 OK` - GET、PUT、PATCH 成功
- `201 Created` - POST 创建成功
- `204 No Content` - DELETE 或 PUT/PATCH 无返回内容

#### 客户端错误
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证
- `403 Forbidden` - 已认证但无权限
- `404 Not Found` - 资源不存在
- `409 Conflict` - 资源冲突
- `422 Unprocessable Entity` - 语义错误
- `429 Too Many Requests` - 请求过于频繁

#### 服务端错误
- `500 Internal Server Error` - 服务器错误
- `503 Service Unavailable` - 服务不可用

## 版本管理

### URL 版本控制
```
/api/v1/users
/api/v2/users
```

### Header 版本控制
```
Accept: application/vnd.myapi.v1+json
```

### 版本策略
- **主版本**: 不向后兼容的变更
- **次版本**: 向后兼容的功能新增
- **修订版本**: 向后兼容的问题修复

## 错误处理

### 标准错误响应格式
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "reason": "Invalid format"
    },
    "timestamp": "2026-03-02T12:00:00Z",
    "request_id": "req-123456"
  }
}
```

### 错误代码规范
- 使用 SCREAMING_SNAKE_CASE
- 描述错误类型，不描述错误位置
- 包含足够的上下文信息

## 分页处理

### 查询参数
```
GET /users?page=1&per_page=20&sort=created_at&order=desc
```

### 分页响应格式
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  },
  "links": {
    "first": "/users?page=1",
    "last": "/users?page=5",
    "prev": null,
    "next": "/users?page=2"
  }
}
```

## 过滤和搜索

### 查询参数
```
GET /users?status=active&role=admin&created_after=2026-01-01
```

### 搜索参数
```
GET /users?q=john&search_fields=name,email
```

## 关系和包含

### 嵌套资源
```
GET /users/123/orders?include=items,products
```

### 响应格式
```json
{
  "data": {
    "id": 123,
    "name": "Order #123",
    "items": [...],
    "products": [...]
  },
  "included": {}
}
```

## 安全要求

### 认证
- 使用 JWT 或 OAuth 2.0
- Token 放在 Authorization Header: `Bearer {token}`
- 实现刷新 Token 机制

### HTTPS
- 所有 API 必须使用 HTTPS
- 启用 HSTS
- 使用现代 TLS 版本

### 输入验证
- 验证所有输入参数
- 防止 SQL 注入
- 防 XSS 攻击
- 防 CSRF 攻击

### 速率限制
- 实现基于 IP 和用户的速率限制
- 返回 429 状态码
- 在响应头中包含限流信息
