# 项目文档结构整理

## 📁 当前文档结构（已实施）

### 根目录文件（3个关键文件）
```
项目根目录/
├── FOR_LLM_CHECKLIST.md         # 🤖 AI检查清单（通用型，不随项目更新）
├── DOCUMENTATION_STRUCTURE.md   # 📋 文档结构说明（本文档）
└── progress.md                  # 📈 项目进度跟踪
```

### docs/core/ 目录（5个核心文档）
```
docs/core/
├── README.md                    # 📖 项目介绍（主要文档）
├── API_DOCUMENTATION.md         # 🔌 API文档（主要文档）
├── FRONTEND_DEVELOPMENT_GUIDE.md # 🎨 前端指南（主要文档）
├── DEPLOYMENT_GUIDE.md          # 🚀 部署指南（主要文档）
└── DESIGN_DIAGRAMS.md           # 🏗️ 设计文档（支持文档）
```

### docs/archive/ 目录（4个归档文档）
```
docs/archive/
├── AFFIX_FEATURE_SUMMARY_CHANGE.md      # 词缀功能开发总结
├── API_QUICK_REFERENCE_CHANGE.md       # API快速参考变更
├── FRONTEND_INTEGRATION_GUIDE_CHANGE.md # 前端集成指南变更
└── DOCUMENTATION_UPDATE_SUMMARY.md     # 文档更新总结
```

## 🎯 文件用途说明

### 根目录文件

#### 1. FOR_LLM_CHECKLIST.md
**用途**: 给大模型的通用检查清单，包含项目信息、部署平台、MCP调试工具
**特点**: 
- 通用型设计，不随项目更新而改变
- 通过docs目录自动获取最新信息
- 包含完整的开发环境指导

#### 2. DOCUMENTATION_STRUCTURE.md
**用途**: 文档结构说明和维护指南
**内容**: 文件用途、更新规则、维护责任
**更新频率**: 文档结构变更时

#### 3. progress.md
**用途**: 项目进度跟踪和开发历史
**内容**: 功能开发状态、技术实现、版本历史
**更新频率**: 功能完成时

### 核心文档（docs/core/）

#### 4. README.md
**用途**: 项目主要说明文档，面向所有用户和开发者
**内容**: 项目概述、主要功能、快速开始、技术栈
**更新频率**: 功能重大更新时

#### 5. API_DOCUMENTATION.md
**用途**: 详细的API接口文档，面向前端开发者
**内容**: 所有API端点的详细说明、请求/响应格式、示例
**更新频率**: API变更时

#### 6. FRONTEND_DEVELOPMENT_GUIDE.md
**用途**: 前端开发指南，给大模型的核心信息
**内容**: 前端技术栈、API调用封装、最佳实践、开发工作流
**更新频率**: 前端技术或API变更时

#### 7. DEPLOYMENT_GUIDE.md
**用途**: 部署指南，面向运维和开发者
**内容**: 环境配置、部署步骤、监控、故障排除
**更新频率**: 部署流程变更时

#### 8. DESIGN_DIAGRAMS.md
**用途**: 系统设计图和架构说明
**内容**: 架构图、流程图、设计决策
**更新频率**: 架构重大变更时

### 归档文档（docs/archive/）

#### 9-12. 临时变更文档
**用途**: 开发过程中的详细变更记录
**状态**: 已归档，不再更新
- `AFFIX_FEATURE_SUMMARY_CHANGE.md` - 词缀功能开发完整记录
- `API_QUICK_REFERENCE_CHANGE.md` - API变更记录
- `FRONTEND_INTEGRATION_GUIDE_CHANGE.md` - 前端集成变更
- `DOCUMENTATION_UPDATE_SUMMARY.md` - 文档更新总结

## 🔄 更新规则

### 核心文档更新原则：
1. **及时更新**: 功能变更时立即更新对应文档
2. **保持一致**: 所有文档风格和格式保持一致
3. **版本控制**: 重要更新在文档中标注版本和日期
4. **交叉引用**: 文档间保持适当的交叉引用

### 临时文档处理原则：
1. **及时清理**: 功能集成完成后删除临时文档
2. **归档保存**: 重要的临时文档移到 archive 目录
3. **命名规范**: 临时文档使用 `_CHANGE` 或 `_DRAFT` 后缀

## 📝 文档维护责任

### 开发者负责：
- API_DOCUMENTATION.md（API变更时）
- progress.md（功能开发进度）

### 架构师负责：
- README.md（项目概述）
- DESIGN_DIAGRAMS.md（架构设计）

### 前端开发者负责：
- FRONTEND_DEVELOPMENT_GUIDE.md（前端集成）

### 运维负责：
- DEPLOYMENT_GUIDE.md（部署流程）

### 项目经理负责：
- FOR_LLM_CHECKLIST.md（开发规范）
- 文档结构维护和清理

---

**建议执行时间**: 立即清理临时文档
**维护周期**: 每月检查文档结构和更新状态
**责任人**: 项目经理协调各角色维护
