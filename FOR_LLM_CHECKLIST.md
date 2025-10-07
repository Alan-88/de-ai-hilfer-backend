# 给大模型的文件清单 - 前端开发

当您需要大模型协助前端开发时，请提供以下**具体文件**和**关键信息**：

## 🗂️ 项目信息
- **项目根目录**: `/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend`
- **项目名称**: De-AI-Hilfer-Backend (德语学习智能助手后端)
- **文档目录**: `/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/docs/`

## 🌐 部署平台信息
- **后端服务**: Render (FastAPI后端)
- **Web前端**: Vercel (React应用)
- **数据库**: Neon (PostgreSQL数据库)
- **Raycast前端**: Raycast (原生应用)

### 可用的MCP调试工具
根据部署平台，大模型可以使用以下MCP工具进行调试：
- **Render MCP**: 查看后端日志、部署状态、性能指标
- **Vercel MCP**: 检查前端部署、构建日志、性能分析
- **Neon MCP**: 数据库查询、性能优化、架构管理
- **GitHub MCP**: 代码管理、CI/CD状态、问题跟踪

## 📁 必须提供的文件（按重要性排序）

### 1. 核心文档文件
```
📄 README.md                    # 项目概述和快速开始
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/README.md

📄 docs/ 目录下的所有文档        # 最新项目文档
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/docs/
   包含：API文档、前端指南、设计图表等
```

### 2. 后端核心代码文件
```
📄 app/api/v1/endpoints.py      # API端点定义
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/api/v1/endpoints.py

📄 app/api/v1/services.py       # 业务逻辑
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/api/v1/services.py

📄 app/schemas/dictionary.py    # 数据传输对象
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/schemas/dictionary.py

📄 app/db/models.py             # 数据库模型
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/db/models.py
```

### 3. 配置文件
```
📄 config.yaml                  # AI服务配置
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/config.yaml

📄 requirements.txt             # Python依赖
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/requirements.txt
```

## 🎯 必须提供的关键信息

### 项目基本信息（3句话）
```
我正在开发De-AI-Hilfer德语学习应用的前端。
后端是FastAPI，提供智能德语分析API。
技术栈：React + TypeScript + Tailwind CSS。
```

### 当前需求（1-2句话）
```
我需要实现[具体功能，如：搜索组件、词条详情页]。
请基于提供的API文档给出代码实现。
```

## 🚀 完整的给大模型提示模板

```
我正在开发De-AI-Hilfer德语学习应用的前端，需要你的帮助。

【项目背景】
德语学习智能助手，后端使用FastAPI提供智能德语分析功能。
前端技术栈：React + TypeScript + Tailwind CSS。

【当前需求】
我需要实现[搜索组件/词条详情页/学习进度页面等具体功能]。

【请参考以下文件】
1. README.md - 项目概述
2. docs/ 目录下的所有文档 - 最新项目文档和API说明
3. app/api/v1/endpoints.py - API端点
4. app/schemas/dictionary.py - 数据结构

请提供具体的React组件代码实现。
```

## 📋 快速检查清单

在向大模型求助前，确认已准备：

- [ ] README.md
- [ ] docs/ 目录（包含所有最新文档）
- [ ] app/api/v1/endpoints.py
- [ ] app/schemas/dictionary.py
- [ ] config.yaml
- [ ] 3句话项目背景
- [ ] 1-2句话具体需求

## 🤖 给大模型的自动化指令

如果您是大模型，请按以下步骤自动读取项目文件：

### 第一步：读取核心文档
```bash
# 使用filesystem MCP读取以下文件：
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/README.md")

# 读取docs目录下的所有文档
list_directory("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/docs/")
# 然后读取docs目录下的所有.md文件
```

### 第二步：读取核心代码文件
```bash
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/api/v1/endpoints.py")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/api/v1/services.py")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/schemas/dictionary.py")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/app/db/models.py")
```

### 第三步：读取配置文件
```bash
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/config.yaml")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/requirements.txt")
```

### 第四步：分析项目并等待用户需求
读取完所有文件后，分析项目架构和API接口，特别注意docs目录中的最新文档内容，然后等待用户提出具体的前端开发需求。

### 第五步：MCP调试工具准备（可选）
如果需要调试或检查部署状态，可以使用以下MCP工具：

```bash
# Render - 后端服务调试
list_services                    # 列出所有服务
get_service(service_id)          # 获取服务详情
list_logs(service_id)            # 查看服务日志
get_metrics(service_id)           # 获取性能指标

# Vercel - 前端部署调试
list_projects()                  # 列出项目
get_project(project_id)          # 获取项目详情
list_deployments(project_id)     # 查看部署历史
get_deployment_build_logs(id)    # 查看构建日志

# Neon - 数据库调试
list_postgres_instances()        # 列出数据库实例
get_postgres(postgres_id)        # 获取数据库详情
run_sql(postgres_id, sql)        # 执行SQL查询
list_slow_queries(postgres_id)   # 查看慢查询

# GitHub - 代码管理
list_commits(owner, repo)        # 查看提交历史
list_issues(owner, repo)         # 查看问题列表
create_issue(owner, repo, data)  # 创建新问题
```

## 💡 使用建议

1. **对于用户**：只需提供这个checklist文件，大模型会自动读取所有需要的文件
2. **对于大模型**：按照上述自动化指令，使用filesystem MCP工具读取所有文件
3. **重点关注docs目录**：这里包含最新的项目文档和API说明
4. **明确具体需求**：不要说"帮我开发前端"，要说"帮我实现搜索组件"
5. **引用具体API**：提到需要使用的具体API端点

## 📂 docs目录说明

docs目录包含项目的所有最新文档：
- **API文档**: 详细的API接口说明
- **前端指南**: 前端开发专门指导
- **设计文档**: 系统架构和设计说明
- **部署指南**: 部署和运维相关文档
- **其他文档**: 项目相关的其他说明文档

大模型会自动读取docs目录下的所有文档，确保获取最新的项目信息。

---

**总结**：用户只需提供这一个checklist文件，大模型就能自动获取所有必要信息，包括docs目录中的最新文档，并提供准确的前端开发帮助。

**特点**：
- 通用型设计，不需要频繁更新
- 通过docs目录自动获取最新信息
- 自动化文件读取流程
- 适用于项目的任何发展阶段
