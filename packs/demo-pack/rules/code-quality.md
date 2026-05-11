"""
演示 Pack 规则 - 代码质量检查

提供代码质量检查的提示和规则
"""

# 1. 启用静态分析
- 在提交任何代码前，确保运行 linter 和 formatter
- 对于 Python，使用 `ruff` 和 `black`
- 对于 JavaScript/TypeScript，使用 `eslint` 和 `prettier`

# 2. 编写测试
- 新功能必须包含单元测试
- 测试覆盖率至少达到 80%
- 使用 pytest 进行测试

# 3. 代码审查
- 每个 PR 需要至少一个审查
- 处理所有审查意见后再合并
- 确保 CI 通过
