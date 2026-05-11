# Prompt Pack v2.0 Schema 完整指南

**版本**: 2.0  
**更新日期**: 2026-02-27  
**主要特性**: AI-Roundtable 多 AI 协同 + 智能工作流引擎  

---

## 📐 完整数据结构定义

### 1. 核心数据模型

#### PackType（Pack 类型）
```
PRODUCTIVITY    生产力工具
CREATIVE        创意生成
ANALYSIS        数据分析
BUSINESS        业务场景
EDUCATION       教育培训
CUSTOM          自定义
```

#### StepType（工作流步骤类型）
```
LOCAL           本地处理（无需 AI）
ANALYSIS        单 AI 分析
GENERATION      多 AI 生成
VALIDATION      交叉验证
FUSION          智能融合
TRACKING        发布追踪
```

#### TargetPlatform（目标平台）
```
XIAOHONGSHU     小红书
WEIBO           微博
DOUYIN          抖音
BILIBILI        B 站
GENERIC         通用平台
```

---

### 2. 主要数据类

#### PackMetadata（Pack 元数据）
```python
pack_id: str                           # Pack 唯一标识
pack_name: str                        # Pack 显示名称
version: str                          # SemVer 版本（如 2.0.0）
type: PackType                        # Pack 类型
description: str                      # 详细描述
designer: str                         # 设计者/创建者
created_at: datetime                  # 创建时间
updated_at: datetime                  # 更新时间
category: Optional[str]               # 二级分类（如：美妆、科技）
tags: List[str]                       # 标签列表
language: str                         # 语言（默认：zh）
estimated_efficiency_gain: str         # 预期效率提升（如：80%）
```

#### WorkflowStep（工作流步骤定义）
单个步骤的完整配置，包括：

```python
id: str                               # 步骤唯一标识
name: str                             # 步骤名称
type: StepType                        # 步骤类型
description: str                      # 步骤描述

# 输入输出
input_fields: List[str]               # 输入字段名称
output_field: str                     # 输出字段名称

# AI 配置
ai_models: Optional[List[str]]        # 使用的 AI 模型列表
parallel: bool                        # 是否并行执行

# 交叉验证配置
cross_review: bool                    # 是否启用交叉验证
validation_criteria: Optional[List[str]]  # 验证标准

# 融合规则
fusion_rules: Optional[Dict[str, Any]]  # 智能融合规则

# 时间配置
estimated_time: Optional[int]         # 预估执行时间（秒）

# 自动触发配置
auto_trigger: bool                    # 是否自动触发
trigger_delay: Optional[int]          # 触发延迟（秒）

# 其他配置
config: Dict[str, Any]                # 其他自定义配置
```

#### QualityMetric（质量指标）
```python
name: str                             # 指标名称
description: str                      # 指标描述
check_method: str                     # 检查方法标识
weight: float                         # 权重（0-1）
min_threshold: float                  # 最低阈值（默认：0.0）
```

#### DomainPack（领域特定配置）
```python
primary_domain: str                   # 主要领域（如：小红书运营）
secondary_domains: List[str]          # 二级领域列表
target_platforms: List[TargetPlatform]  # 目标平台
target_audience: Optional[str]        # 目标受众描述
brand_tone: Optional[str]             # 品牌调性（如：专业、活泼）
compliance_rules: List[str]           # 合规要求列表
```

#### GenerationParams（生成参数配置）
```python
# 多样性激发
diversity_enhancement: bool           # 是否增强多样性
output_versions: int                  # 输出版本数
diversity_dimensions: List[str]       # 多样性维度

# 概率/置信度
confidence_display: bool              # 是否显示置信度
critical_facts_only: bool             # 仅关键事实

# 温度参数
temperature: float                    # AI 输出温度（0-1）

# 输出格式
output_format: str                    # 输出格式（markdown、plain）
require_code_blocks: bool             # 是否需要代码块
```

#### OptimizationRules（优化规则）
```python
enabled: bool                         # 是否启用优化
strategy: str                         # 优化策略（feedback_driven/auto/manual）
auto_refine_threshold: float          # 自动优化分数阈值
periodic_review_days: int             # 定期审查周期（天）
allowed_actions: List[str]            # 允许的优化操作
```

#### PerformanceTracking（性能追踪配置）
```python
enabled: bool                         # 是否启用追踪
metrics: List[str]                    # 追踪的指标列表
retention_days: int                   # 数据保留天数
post_publish_tracking: Optional[Dict]  # 发布后追踪配置
```

#### CollaborationConfig（团队协作配置）
```python
shared_with: List[str]                # 共享用户 ID 列表
edit_permission: List[str]            # 编辑权限用户列表
use_permission: List[str]             # 使用权限用户列表
is_public: bool                       # 是否公开
```

---

### 3. 完整 Pack 对象

#### PromptPackV2（Prompt Pack v2.0 完整定义）

所有配置的集合：

```python
metadata: PackMetadata                # 元数据
domain: DomainPack                    # 领域配置
workflow: WorkflowDefinition          # 工作流定义
quality_metrics: QualityMetrics       # 质量指标
example_library: ExampleLibrary       # 示例库
generation_params: GenerationParams   # 生成参数
optimization: OptimizationRules       # 优化规则
performance_tracking: PerformanceTracking  # 性能追踪
collaboration: CollaborationConfig    # 协作配置
system_prompt: str                    # 系统提示词
quality_validation_rules: str         # 质量验证规则

# 主要方法：
def to_dict() -> Dict[str, Any]:      # 转换为字典
def from_dict(data) -> PromptPackV2:  # 从字典创建
def validate() -> bool:               # 验证完整性
```

---

## 🏭 工厂函数

### create_xiaohongshu_base()
创建小红书特定的基础 Pack 实例，包含：
- 小红书运营领域配置
- 5 个质量指标（覆盖率、创意度、准确性、吸引力、规范性）
- 基础工作流和协作配置

---

## 📚 使用示例

### 基础创建
```python
from src.ai_collab.pack.schema_v2 import PromptPackV2, create_xiaohongshu_base

# 创建小红书 Pack
pack = create_xiaohongshu_base()

# 验证结构
if pack.validate():
    print("✅ Pack 结构有效")
else:
    print("❌ Pack 结构无效")
```

### 导出为 JSON
```python
pack_dict = pack.to_dict()
import json
print(json.dumps(pack_dict, indent=2, default=str))
```

### 从 JSON 导入
```python
pack_from_json = PromptPackV2.from_dict(pack_dict)
```

---

## 🔍 关键特性

### 1. 多 AI 协同
- 支持在单个步骤中使用多个 AI 供应商
- 并行执行不同 AI 的请求
- 智能融合多个输出的结果

### 2. 质量保证
- 定义多个质量指标及其权重
- 自动验证步骤 ID 唯一性和权重合法性
- 灵活的验证标准配置

### 3. 工作流管理
- 支持 6 种不同的步骤类型
- 自动触发和延迟配置
- 交叉验证和融合规则

### 4. 性能追踪
- 执行时间统计
- 成功率追踪
- 发布后的社交指标监控

### 5. 团队协作
- 灵活的权限管理
- 公开和私有 Pack 支持
- 在线实时协作

---

## ✅ 验证规则

Pack 验证检查以下内容：

1. **基础字段**: pack_id 和 pack_name 不为空
2. **工作流**: 至少存在一个步骤
3. **步骤 ID**: 不重名，全体唯一
4. **质量权重**: 所有权重之和约等于 1.0（误差 ±0.01）

---

## 🚀 最佳实践

1. **命名规范**：使用 kebab-case（小写 + 连字符）
2. **版本管理**：遵守 SemVer（Major.Minor.Patch）
3. **权重配置**：确保质量指标权重之和为 1.0
4. **步骤设计**：明确输入输出字段名
5. **文档完整性**：提供清晰的描述和示例

---

**文件位置**: [src/ai_collab/pack/schema_v2.py](../../src/ai_collab/pack/schema_v2.py)  
**最后修复**: 2026-02-27 09:01  
**状态**: ✅ 语法验证通过，可导入使用
