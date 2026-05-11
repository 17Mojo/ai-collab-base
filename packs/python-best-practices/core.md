# Python 核心最佳实践

## 代码风格

### 遵循 PEP 8

- 使用 4 个空格缩进（不要用 Tab）
- 每行最多 79 个字符
- 类与顶层函数之间用两个空行分隔
- 方法之间用一个空行分隔
- 在同一行不要放多个语句
- 使用两个空格在赋值运算符周围

```python
# ✅ 好的示例
class User:
    """用户类"""

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def get_info(self) -> dict:
        """获取用户信息"""
        return {"name": self.name, "age": self.age}
```

### 使用类型提示

```python
from typing import List, Dict, Optional, Tuple

def process_data(
    items: List[Dict[str, int]],
    threshold: int,
) -> Tuple[List[str], Dict[str, int]]:
    """处理数据列表"""
    filtered = [item["name"] for item in items if item["value"] > threshold]
    summary = {item["name"]: item["value"] for item in items}
    return filtered, summary
```

### 使用文档字符串

```python
def calculate_grade(score: int, max_score: int = 100) -> str:
    """计算成绩等级.

    Args:
        score: 获得的分数
        max_score: 最高分数（默认为 100）

    Returns:
        成绩等级（A、B、C、D 或 F）

    Raises:
        ValueError: 当 score 为负数或大于 max_score 时

    Examples:
        >>> calculate_grade(85)
        'B'
    """
    percentage = (score / max_score) * 100

    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    else:
        return "F"
```

## 性能优化

### 使用生成器

```python
# ❌ 低效：使用列表
def get_even_numbers(n: int) -> List[int]:
    """获取 0 到 n 之间的所有偶数"""
    return [i for i in range(n) if i % 2 == 0]

# ✅ 高效：使用生成器
def get_even_numbers_gen(n: int):
    """生成 0 到 n 之间的所有偶数"""
    for i in range(n):
        if i % 2 == 0:
            yield i
```

### 使用列表推导式

```python
# ❌ 低效：使用循环
result = []
for item in items:
    if item["value"] > 10:
        result.append(item["price"] * 1.1)

# ✅ 高效：使用列表推导式
result = [item["price"] * 1.1 for item in items if item["value"] > 10]
```

### 使用字典和集合查找

```python
# ❌ 低效：列表查找（O(n)）
items = {"apple", "banana", "orange"}
if "apple" in items:
    pass

# ✅ 高效：集合查找（O(1)）
items = {"apple", "banana", "orange"}
if "apple" in items:
    pass
```

### 避免全局变量

```python
# ❌ 避免使用全局变量
counter = 0

def increment():
    global counter
    counter += 1

# ✅ 使用类或闭包
class Counter:
    """计数器类"""

    def __init__(self):
        self.counter = 0

    def increment(self):
        """递增计数"""
        self.counter += 1
```

### 使用缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n: int) -> int:
    """计算斐波那契数列（带缓存）"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

## 异常处理

### 捕获特定异常

```python
# ❌ 避免：捕获所有异常
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ 推荐：捕获特定异常
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except KeyError as e:
    logger.error(f"Key not found: {e}")
```

### 使用 finally 清理资源

```python
def process_file(filename: str):
    """处理文件"""
    file = None
    try:
        file = open(filename, 'r')
        content = file.read()
        return content
    finally:
        if file is not None:
            file.close()
```

### 使用 context manager

```python
# ✅ 最佳实践
def process_file(filename: str):
    """处理文件（使用 with）"""
    with open(filename, 'r') as file:
        content = file.read()
    return content
```

### 自定义异常

```python
class UserNotFoundError(Exception):
    """用户未找到异常"""

    pass

def get_user(user_id: int) -> dict:
    """获取用户"""
    user = find_user(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user
```

## 安全实践

### 输入验证

```python
def create_user(name: str, age: int, email: str) -> dict:
    """创建用户"""
    # 验证参数
    if not name or not isinstance(name, str) or len(name) > 100:
        raise ValueError("Invalid name")

    if not isinstance(age, int) or age < 0 or age > 150:
        raise ValueError("Invalid age")

    if not email or '@' not in email:
        raise ValueError("Invalid email")

    return {"name": name, "age": age, "email": email}
```

### 避免使用 eval

```python
# ❌ 危险
def evaluate_expression(expr: str) -> Any:
    return eval(expr)

# ✅ 安全
import ast

def evaluate_expression(expr: str) -> Any:
    """安全地求值表达式（仅支持字面量）"""
    return ast.literal_eval(expr)
```

### 使用安全的字符串格式化

```python
# ❌ 不安全（可能导致注入）
query = f"SELECT * FROM users WHERE name = '{user_name}'"

# ✅ 安全（使用参数化查询）
cursor.execute("SELECT * FROM users WHERE name = %s", (user_name,))
```

### 敏感数据处理

```python
# ❌ 不要记录敏感信息
logger.info(f"User password: {password}")

# ✅ 记录哈希值或掩码
import hashlib

password_hash = hashlib.sha256(password.encode()).hexdigest()
logger.info(f"User password hash: {password_hash}")
```

## 测试要求

### 单元测试覆盖率

- 目标覆盖率: ≥ 80%
- 每个公共方法都要有测试
- 测试边界条件和异常情况

### 使用 pytest

```python
import pytest

def test_calculate_grade():
    """测试计算成绩"""
    assert calculate_grade(90, 100) == "A"
    assert calculate_grade(80, 100) == "B"
    assert calculate_grade(70, 100) == "C"
    assert calculate_grade(60, 100) == "D"
    assert calculate_grade(50, 100) == "F"

def test_calculate_grade_invalid():
    """测试无效输入"""
    with pytest.raises(ValueError):
        calculate_grade(-10)

    with pytest.raises(ValueError):
        calculate_grade(110)
```

### 使用 fixtures

```python
@pytest.fixture
def sample_data():
    """测试数据 fixture"""
    return [
        {"name": "Alice", "score": 85},
        {"name": "Bob", "score": 92},
        {"name": "Charlie", "score": 78},
    ]

def test_process_data(sample_data):
    """测试数据处理"""
    names, summary = process_data(sample_data, threshold=80)
    assert "Bob" in names
    assert summary["Alice"]["score"] == 85
```

### Mock 外部依赖

```python
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_external_service():
    """模拟外部服务"""
    with patch('myapp.services.ExternalService') as mock:
        mock.return_value.get_data.return_value = {"status": "ok"}
        yield mock

def test_external_call(mock_external_service):
    """测试外部调用"""
    result = call_external_service()
    assert result["status"] == "ok"
```

## 代码组织

### 使用包和模块

```
project_name/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── user.py
├── services/
│   ├── __init__.py
│   └── user_service.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

### 避免循环导入

```python
# models/user.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.user_service import UserService

class User:
    """用户类"""
    def get_service(self) -> 'UserService':
        """获取服务（延迟导入）"""
        from services.user_service import UserService
        return UserService()
```

### 使用相对导入

```python
# 在包内部使用相对导入
from .user import User
from ..utils.helpers import format_name
```
