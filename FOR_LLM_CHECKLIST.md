# 给大模型的文件清单 - 前端开发

当您需要大模型协助前端开发时，请提供以下**具体文件**和**关键信息**：

## 🗂️ 项目信息
- **项目根目录**: `/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend`
- **项目名称**: De-AI-Hilfer-Backend (德语学习智能助手后端)

## 📁 必须提供的文件（按重要性排序）

### 1. 核心文档文件
```
📄 README.md                    # 项目概述和快速开始
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/README.md

📄 API_DOCUMENTATION.md         # API接口详细说明
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/API_DOCUMENTATION.md

📄 DESIGN_DIAGRAMS.md           # 系统架构图和流程图
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/DESIGN_DIAGRAMS.md
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

📄 .env                         # 环境变量（敏感信息可隐藏）
   路径: /Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/.env
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
2. API_DOCUMENTATION.md - API接口说明
3. DESIGN_DIAGRAMS.md - 系统架构图
4. app/api/v1/endpoints.py - API端点
5. app/schemas/dictionary.py - 数据结构

【重点关注的API】
- POST /api/v1/intelligent-query (智能查询)
- GET /api/v1/suggestions?q={term} (搜索建议)
- POST /api/v1/follow-up (创建追问)

请提供具体的React组件代码实现。
```

## 📋 快速检查清单

在向大模型求助前，确认已准备：

- [ ] README.md
- [ ] API_DOCUMENTATION.md  
- [ ] DESIGN_DIAGRAMS.md
- [ ] app/api/v1/endpoints.py
- [ ] app/schemas/dictionary.py
- [ ] config.yaml
- [ ] 3句话项目背景
- [ ] 1-2句话具体需求

## 🤖 给大模型的自动化指令

如果您是大模型，请按以下步骤自动读取项目文件：

### 第一步：读取核心文档文件
```bash
# 使用filesystem MCP读取以下文件：
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/README.md")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/API_DOCUMENTATION.md")
read_text_file("/Users/alan/Programming/De-AI-Hilfer-Project/De-AI-Hilfer-Backend/DESIGN_DIAGRAMS.md")
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
读取完所有文件后，分析项目架构和API接口，然后等待用户提出具体的前端开发需求。

## 💡 使用建议

1. **对于用户**：只需提供这个checklist文件，大模型会自动读取所有需要的文件
2. **对于大模型**：按照上述自动化指令，使用filesystem MCP工具读取所有文件
3. **重点关注API文档**：这是前端开发最核心的参考资料
4. **明确具体需求**：不要说"帮我开发前端"，要说"帮我实现搜索组件"
5. **引用具体API**：提到需要使用的具体API端点

---

**总结**：用户只需提供这一个checklist文件，大模型就能自动获取所有必要信息并提供准确的前端开发帮助。
