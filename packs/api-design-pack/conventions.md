# Python 代码规范

## 命名约定

### 模块名
- 使用小写字母
- 使用下划线分隔: `user_service.py`
- 避免与标准库名冲突

### 类名
- 使用 Pascal Case: `UserService`
- 首字母大写
- 每个单词首字母大写

### 函数名
- 使用 snake_case: `get_user_data()`
- 小写字母开头
- 单词间用下划线分隔

### 常量名
- 使用 UPPER_SNAKE_CASE: `MAX_RETRIES`
- 全大写
- 单词间用下划线分隔

### 私有成员
- 前导单下划线: `_internal_method`
- 表示内部使用

### 私有类成员
- 前导双下划线: `__private_attribute`
- 触发名称改写

## 类型提示

### 函数类型提示
```python
def get_user(user_id: int) -> dict:
    """获取用户信息"""
    pass
```

### 可选类型
```python
from typing import Optional

def find_user(name: str) -> Optional[dict]:
    """查找用户，可能不存在"""
    pass
```

### 泛型类型
```python
from typing import List, Dict

def process_items(items: List[int]) -> Dict[str, int]:
    """处理项目列表"""
    pass
```

## 文档字符串

### Google 风格
```python
def calculate_discount(price: float, rate: float) -> float:
    """计算折扣后的价格。

    Args:
        price: 原始价格
        rate: 折扣率（0-1 之间的小数）

    Returns:
        折扣后的价格

    Raises:
        ValueError: 当 rate 不在 0-1 之间时

    Examples:
        >>> calculate_discount(100.0, 0.1)
        90.0
    """
```

### 类文档字符串
```python
class UserRepository:
    """用户数据仓库类。

    负责用户数据的持久化和查询操作。

    Attributes:
        db_session: 数据库会话对象
    """
```

## 异常处理

### 不要过度捕获
```python
# ❌ 避免
try:
    do_something()
except Exception:
    pass

# ✅ 推荐
try:
    do_something()
except SpecificError as e:
    logger.error(f"Error: {e}")
    raise
```

### 使用 finally 清理资源
```python
try:
    file = open('data.txt', 'r')
    content = file.read()
finally:
    file.close()
```

### 使用 with 语句
```python
# ✅ 最佳实践
with open('data.txt', 'r') as file:
    content = file.read()
```

## 代码质量

### 遵循 PEP 8
- 使用 `flake8` 检查
- 限制单行长度为 79 字符
- 使用 4 个空格缩进

### 使用 `black` 格式化
```bash
pip install black
black .
```

### 使用 `isort` 整理导入
```bash
pip install isort
isort .
```

### 使用类型检查
```bash
pip install mypy
mypy .
```

## 性能优化

### 使用生成器
```python
# ❌ 低效
def get_all_items():
    items = []
    for item in large_dataset:
        items.append(process(item))
    return items

# ✅ 高效
def get_all_items():
    for item in large_dataset:
        yield process(item)
```

### 避免不必要的全局变量
- 全局变量会增加内存使用
- 影响代码可测试性

### 使用缓存
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(x):
    """缓存结果"""
    return complex_calculation(x)
```

## 安全最佳实践

### 避免 eval
```python
# ❌ 危险
result = eval(user_input)

# ✅ 安全
import ast
result = ast.literal_eval(user_input)
```

### 验证输入
```python
def update_user(user_id: int, data: dict) -> bool:
    """更新用户信息"""
    # 验证 user_id
    if user_id <= 0:
        raise ValueError("Invalid user_id")

    # 验证 data
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")
```

### 使用参数化查询
```python
# ❌ 不安全
cursor.execute(f"SELECT * FROM users WHERE name = '{user_name}'")

# ✅ 安全
cursor.execute("SELECT * FROM users WHERE name = %s", (user_name,))
```

## 测试要求

### 单元测试
- 使用 pytest
- 每个功能都要有测试
- 测试覆盖率 ≥ 80%

### 测试命名
```python
def test_calcuate_discount_with_valid_rate():
    """测试有效折扣率"""
    result = calculate_discount(100.0, 0.1)
    assert result == 90.0
```

### 使用 fixtures
```python
@pytest.fixture
def sample_user():
    """创建测试用户"""
    return {"id": 1, "name": "Test User"}

def test_user_creation(sample_user):
    """测试用户创建"""
    assert sample_user["name"] == "Test User"
```

## 导入规范

### 按类别组织导入
```python
# 1. 标准库
import os
import sys
from typing import List

# 2. 第三方库
import requests
from flask import Flask

# 3. 本地导入
from . import utils
from .models import User
```

### 避免循环导入
- 使用 type hints 延迟导入
- 重新组织代码结构

### 导入顺序
- 标准库
- 第三方库
- 本地导入
- 每个类别之间用空行分隔
