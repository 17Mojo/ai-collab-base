# Web 开发编码约定

## 命名规范

### 变量命名
- 使用 camelCase: `variableName`
- 布尔值使用 is/has 前缀: `isValid`, `hasPermission`
- 常量使用 UPPER_SNAKE_CASE: `API_URL`

### 函数命名
- 使用 camelCase: `functionName()`
- 动作函数使用动词开头: `getUserData()`, `saveSettings()`
- 获取函数使用 get 前缀: `getValue()`
- 设置函数使用 set 前缀: `setValue()`

### 类命名
- 使用 PascalCase: `ClassName`
- 组件使用 PascalCase: `ComponentName`

### 文件命名
- 组件文件使用 PascalCase: `ComponentName.tsx`
- 工具函数使用 kebab-case: `utils-file.ts`
- 常量文件使用 UPPER_SNAKE_CASE: `CONSTANTS.ts`

## 代码格式化

### 缩进
- 使用 2 个空格缩进
- 不使用 Tab

### 空格
- 运算符前后加空格: `a = b + c`
- 函数参数之间加空格: `function(a, b, c)`
- 逗号后加空格: `[a, b, c]`

### 分号
- JavaScript/TypeScript 不使用分号（使用 Prettier）
- SQL 查询每行末尾使用分号

### 大括号
- K&R 风格: 左大括号与语句同行
```javascript
if (condition) {
  // code
}
```

## 注释规范

### 单行注释
```javascript
// 单行注释
```

### 多行注释
```javascript
/**
 * 多行注释
 * 用于函数说明
 */
```

### JSDoc
```javascript
/**
 * 计算两个数的和
 * @param {number} a - 第一个数
 * @param {number} b - 第二个数
 * @returns {number} 两数之和
 */
function add(a, b) {
  return a + b;
}
```

## 错误处理

### Try-Catch
```javascript
try {
  // 可能出错的代码
} catch (error) {
  console.error('Error:', error);
  // 适当的错误处理
}
```

### 错误日志
- 记录错误堆栈
- 记录错误上下文
- 使用有意义的错误消息

## Git 提交规范

### 提交消息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关
