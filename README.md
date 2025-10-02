# De-AI-Hilfer-Backend

一个为个人德语学习生态系统提供核心后端服务的FastAPI应用。

## 项目概述

De-AI-Hilfer-Backend是一个现代化的Python后端服务，专门为德语学习者提供智能化的语言分析和管理功能。该项目集成了多种AI服务，提供德语单词的语法分析、语义解释、拼写检查等功能。

## 主要功能

### 🧠 智能德语分析
- **单词分析**：提供德语单词的详细语法和语义分析
- **拼写检查**：智能识别拼写错误并提供修正建议
- **原型识别**：识别单词的原型形式，支持变体词处理
- **上下文理解**：基于知识库提供相关的语言信息

### 📚 知识库管理
- **词条管理**：创建、更新、删除德语单词条目
- **别名系统**：为同一单词创建多个查询别名
- **追问功能**：支持对分析结果进行深入提问
- **批量操作**：支持数据库的导入导出

### 🔍 智能搜索
- **模糊搜索**：支持部分匹配的智能搜索
- **上下文提示**：基于提示信息推断最可能的单词
- **建议系统**：提供相关的搜索建议
- **历史记录**：保存和管理搜索历史

## 技术栈

### 🏗️ 核心框架
- **FastAPI**: 现代、快速的Web框架
- **SQLAlchemy**: 强大的ORM框架
- **Pydantic**: 数据验证和序列化
- **Alembic**: 数据库迁移工具

### 🤖 AI集成
- **Gemini API**: Google的AI服务
- **OpenAI API**: GPT系列模型支持
- **Ollama**: 本地AI模型支持
- **多适配器架构**: 统一的AI服务接口

### 🗄️ 数据库
- **PostgreSQL**: 生产环境数据库
- **SQLite**: 开发和测试环境
- **异步支持**: 高性能数据库操作

## 项目结构

\`\`\`
De-AI-Hilfer-Backend/
├── app/                    # 应用核心代码
│   ├── api/v1/            # API v1版本
│   │   ├── endpoints.py    # API端点定义
│   │   ├── services.py     # 业务逻辑服务
│   │   └── management.py   # 管理功能服务
│   ├── core/               # 核心模块
│   │   ├── config.py       # 配置管理
│   │   ├── errors.py       # 错误定义
│   │   ├── exceptions.py   # 异常处理
│   │   ├── llm_service.py  # LLM服务核心
│   │   ├── performance.py  # 性能监控
│   │   └── state.py        # 状态管理
│   ├── db/                 # 数据库相关
│   │   ├── models.py       # 数据模型
│   │   ├── session.py      # 数据库会话
│   │   ├── serializers.py  # 数据序列化
│   │   └── indexes.py      # 数据库索引
│   └── schemas/            # 数据模式
│       └── dictionary.py   # API数据传输对象
├── ai_adapter/            # AI适配器模块
│   ├── llm_adapters.py    # LLM适配器实现
│   ├── llm_router.py      # LLM路由器
│   ├── schemas.py         # AI数据模型
│   ├── tool_manager.py    # 工具管理
│   └── utils.py           # 工具函数
├── tests/                 # 测试代码
│   ├── test_api.py        # API测试
│   ├── test_models.py      # 模型测试
│   ├── test_services.py    # 服务测试
│   └── conftest.py        # 测试配置
├── alembic/               # 数据库迁移
├── config.yaml            # AI配置文件
├── requirements.txt        # 依赖列表
└── Dockerfile             # Docker配置
\`\`\`

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 12+ (生产环境)
- Node.js 18+ (可选，用于前端开发)

### 安装步骤

1. **克隆项目**
\`\`\`bash
git clone https://github.com/Alan-88/de-ai-hilfer-backend.git
cd de-ai-hilfer-backend
\`\`\`

2. **创建虚拟环境**
\`\`\`bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
\`\`\`

3. **安装依赖**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

4. **配置环境变量**
\`\`\`bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和AI服务密钥
\`\`\`

5. **初始化数据库**
\`\`\`bash
# 创建数据库表
alembic upgrade head
\`\`\`

6. **启动服务**
\`\`\`bash
uvicorn app.main:app --reload
\`\`\`

### Docker部署

\`\`\`bash
# 构建镜像
docker build -t de-ai-hilfer-backend .

# 运行容器
docker run -p 8000:8000 de-ai-hilfer-backend
\`\`\`

## API文档

启动服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 主要API端点

### 基础查询
- \`GET /api/v1/recent\` - 获取最近查询的条目
- \`GET /api/v1/all\` - 获取所有条目
- \`GET /api/v1/suggestions?q={term}\` - 获取搜索建议

### 核心分析
- \`POST /api/v1/analyze\` - 分析德语单词
- \`POST /api/v1/intelligent-search\` - 智能搜索

### 知识库管理
- \`POST /api/v1/follow-up\` - 创建追问
- \`POST /api/v1/alias\` - 创建别名
- \`DELETE /api/v1/entries/{id}\` - 删除条目

### 系统管理
- \`GET /api/v1/export\` - 导出数据库
- \`POST /api/v1/import\` - 导入数据库
- \`GET /api/v1/status\` - 系统状态检查

## 配置说明

### AI服务配置
在 \`config.yaml\` 中配置AI服务：

\`\`\`yaml
llm:
  default_service: "gemini"
  services:
    gemini:
      api_key: "your-gemini-api-key"
      model: "gemini-pro"
    openai:
      api_key: "your-openai-api-key"
      model: "gpt-4"
    ollama:
      base_url: "http://localhost:11434"
      model: "llama2"
\`\`\`

### 数据库配置
在 \`.env\` 文件中配置数据库：

\`\`\`
DATABASE_URL=postgresql://user:password@localhost/de_ai_hilfer
DB_ECHO=false
\`\`\`

## 开发指南

### 运行测试
\`\`\`bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
\`\`\`

### 代码质量检查
\`\`\`bash
# 代码风格检查
flake8 app/

# 代码格式化
black app/

# 类型检查
mypy app/
\`\`\`

### 数据库迁移
\`\`\`bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head
\`\`\`

## 性能优化

项目包含多种性能优化机制：

### 缓存系统
- **预览文本缓存**：避免重复计算预览文本
- **LLM响应缓存**：避免重复调用AI服务
- **词汇表缓存**：减少数据库查询

### 数据库优化
- **批量查询**：减少数据库往返次数
- **索引优化**：关键查询字段的索引
- **延迟加载**：按需加载关联数据

### 监控系统
- **性能监控**：函数执行时间监控
- **缓存统计**：缓存命中率统计
- **内存监控**：内存使用情况跟踪

## 部署指南

### 生产环境部署

1. **环境准备**
   - 配置生产数据库
   - 设置环境变量
   - 配置反向代理

2. **应用部署**
   \`\`\`bash
   # 使用Gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   
   # 或使用Docker
   docker-compose up -d
   \`\`\`

3. **监控配置**
   - 配置日志收集
   - 设置健康检查
   - 配置性能监控

### 环境变量

| 变量名 | 描述 | 默认值 | 示例 |
|--------|------|--------|------|
| \`DATABASE_URL\` | 数据库连接URL | - | \`postgresql://user:pass@localhost/db\` |
| \`DEBUG\` | 调试模式 | \`false\` | \`true\` |
| \`LOG_LEVEL\` | 日志级别 | \`INFO\` | \`DEBUG\` |
| \`CORS_ORIGINS\` | CORS允许的源 | \`["http://localhost:5173", "http://localhost"]\` | \`["https://yourdomain.com"]\` |
| \`GEMINI_API_KEY\` | Google Gemini API密钥 | - | \`AIzaSy...\` |
| \`DEEPSEEK_API_KEY\` | DeepSeek API密钥 | - | \`sk-...\` |

#### CORS配置说明

\`CORS_ORIGINS\` 环境变量支持两种格式：

**JSON数组格式（推荐）**：
\`\`\`bash
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "https://yourdomain.com"]
\`\`\`

**逗号分隔格式**：
\`\`\`bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com
\`\`\`

**不同环境的配置建议**：
- **开发环境**：允许本地开发服务器
  \`\`\`bash
  CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
  \`\`\`
- **生产环境**：仅允许正式域名
  \`\`\`bash
  CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
  \`\`\`
- **测试环境**：根据测试前端服务的具体域名配置

## 贡献指南

### 开发流程
1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request
5. 代码审查和合并

### 代码规范
- 遵循PEP 8代码风格
- 使用类型注解
- 编写单元测试
- 更新相关文档

### 提交规范
\`\`\`
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建过程或辅助工具的变动
\`\`\`

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式

- **项目维护者**: Alan
- **邮箱**: [alanwzs.lwang@gmail.com]
- **GitHub**: [https://github.com/Alan-88/de-ai-hilfer-backend]

## 📝 版本历史

### 重要标签
- `backup-main-20251002-160008`: 代码清理前的原始main分支备份
- 使用 `git checkout backup-main-20251002-160008` 可以回到清理前状态

### 主要变更
- **代码清理重构**: 业务逻辑分离、性能优化、错误处理改进
- **API路径更新**: `/recent` → `/entries/recent`, `/all` → `/entries/all`
- **新增模块**: 配置管理、性能监控、数据序列化

### 回退指南
如果需要回退到代码清理前的状态：

```bash
# 方法1: 使用标签回退（推荐）
git checkout backup-main-20251002-160008
git checkout -b restore-original-main

# 方法2: 创建新分支从标签
git checkout -b restore-main backup-main-20251002-160008

# 方法3: 查看完整历史选择回退点
git log --oneline --graph --all
git checkout <desired-commit-hash>
```

### 零上下文对话中的回退
即使在全新的对话中，大模型也能通过以下方式感知和执行回退：

1. **Git历史分析**: `git log --oneline --graph --all`
2. **标签查看**: `git tag -l`
3. **分支结构**: `git branch -a`
4. **操作日志**: `git reflog`

这些命令提供了完整的项目历史信息，让大模型能够理解项目状态并执行相应的回退操作。

## 更新日志

### v1.1.1 (2025-10-02)
- ✨ 完成代码清理和重构
- 🔧 优化性能和缓存机制
- 📚 完善文档和测试
- 🐛 修复已知问题

### v1.0.0 (2025-XX-XX)
- 🎉 初始版本发布
- 🚀 基础功能实现
- 📖 完整API文档

---

**De-AI-Hilfer-Backend** - 让德语学习更智能、更高效！ 🇩🇪
