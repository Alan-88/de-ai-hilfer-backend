# API 文档

## 概述

De-AI-Hilfer-Backend 提供了一套完整的 RESTful API，用于德语学习智能分析和管理。本文档详细描述了所有可用的 API 端点、请求格式、响应格式和使用示例。

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json`
- **认证方式**: 暂无（后续版本将添加JWT认证）

## API 端点列表

### 🔍 查询端点

#### 获取最近查询的条目
- **端点**: `GET /recent`
- **描述**: 获取最近成功查询的知识条目列表，包含预览文本
- **响应**: `RecentItem[]`

**示例请求**:
\`\`\`bash
curl -X GET "http://localhost:8000/api/v1/recent"
\`\`\`

**示例响应**:
\`\`\`json
[
  {
    "query_text": "Haus",
    "preview": "n. 房子；住宅；家庭"
  },
  {
    "query_text": "gehen",
    "preview": "v. 去；走；进行"
  }
]
\`\`\`

#### 获取所有条目
- **端点**: `GET /all`
- **描述**: 获取知识库中的所有条目，按字母顺序排序
- **响应**: `RecentItem[]`

#### 获取搜索建议
- **端点**: `GET /suggestions`
- **参数**: `q` (query) - 搜索关键词
- **描述**: 根据输入提供智能搜索建议
- **响应**: `DBSuggestion[]`

**示例请求**:
\`\`\`bash
curl -X GET "http://localhost:8000/api/v1/suggestions?q=haus"
\`\`\`

### 🧠 分析端点

#### 分析德语单词
- **端点**: `POST /analyze`
- **描述**: 对德语单词进行详细的语法和语义分析
- **请求体**: `AnalyzeRequest`
- **响应**: `AnalyzeResponse`

**请求体示例**:
\`\`\`json
{
  "query_text": "Haus",
  "entry_type": "WORD"
}
\`\`\`

**响应示例**:
\`\`\`json
{
  "entry_id": 1,
  "query_text": "Haus",
  "analysis_markdown": "# Haus\n\n## 核心释义 (Bedeutung)\n\n* **n.** 房子；住宅；家庭\n\n## 语法信息 (Grammatik)\n\n### 词性 (Wortart)\n- **名词 (Substantiv)**\n\n### 变格 (Deklination)\n| 格格 | 单数 | 复数 |\n|------|------|------|\n| 主格 (Nominativ) | das Haus | die Häuser |\n| 属格 (Genitiv) | des Hauses | der Häuser |\n| 与格 (Dativ) | dem Haus | den Häusern |\n| 宾格 (Akkusativ) | das Haus | die Häuser |\n\n### 性别 (Genus)\n- **中性 (Neutrum)**\n\n## 使用示例 (Verwendungsbeispiele)\n\n1. **Das Haus ist groß.** - 房子很大。\n2. **Ich gehe nach Hause.** - 我回家。\n3. **Das Haus der Familie.** - 家庭的房子。\n\n## 相关词汇 (Verwandte Wörter)\n\n- **häuslich** - 家庭的，家用的\n- **häuslich** - 像家一样的\n- **Haushalt** - 家庭，家务\n\n## 词源 (Etymologie)\n\n来源于古高地德语 \"hūs\"，意为房屋、住所。",
  "source": "generated",
  "follow_ups": []
}
\`\`\`

#### 智能搜索
- **端点**: `POST /intelligent-search`
- **描述**: 基于用户的模糊输入和提示，使用AI推断最可能的德语单词
- **请求体**: `IntelligentSearchRequest`
- **响应**: `AnalyzeResponse`

**请求体示例**:
\`\`\`json
{
  "term": "haus",
  "hint": "building where people live"
}
\`\`\`

### 📚 知识库管理端点

#### 创建追问
- **端点**: `POST /follow-up`
- **描述**: 为指定的知识条目创建追问并生成AI回答
- **请求体**: `FollowUpCreateRequest`
- **响应**: `FollowUpItem`

**请求体示例**:
\`\`\`json
{
  "entry_id": 1,
  "question": "Haus这个词在口语中有什么特殊用法吗？"
}
\`\`\`

**响应示例**:
\`\`\`json
{
  "id": 1,
  "question": "Haus这个词在口语中有什么特殊用法吗？",
  "answer": "在德语口语中，'Haus'确实有一些特殊用法：\n\n1. **固定搭配**：\n   - 'zu Hause gehen'（回家）\n   - 'im Haus sein'（在家）\n   - 'auf dem Haus stehen'（站在房子上）\n\n2. **引申义**：\n   - 可以指代家庭或家族（'das ganze Haus'）\n   - 在商业语境中指代公司（'das Haus Siemens'）\n\n3. **口语化表达**：\n   - 'Haus und Hof' - 指代整个家业\n   - 'Hausmädchen' - 女管家（历史用法）\n\n这些用法在日常对话中非常常见。",
  "timestamp": "2025-10-02T12:00:00Z"
}
\`\`\`

#### 重新生成分析
- **端点**: `POST /regenerate/{entry_id}`
- **描述**: 重新生成指定知识条目的AI分析内容
- **参数**: `entry_id` (path) - 条目ID
- **响应**: `AnalyzeResponse`

#### 删除条目
- **端点**: `DELETE /entries/{entry_id}`
- **描述**: 从数据库中删除指定的知识条目及其相关数据
- **参数**: `entry_id` (path) - 条目ID
- **响应**: `{"message": "成功删除知识条目 'Haus'"}`

#### 创建别名
- **端点**: `POST /alias`
- **描述**: 为指定的知识条目创建别名，支持多种查询方式
- **请求体**: `AliasCreateRequest`
- **响应**: `{"message": "成功将别名 '家' 关联到 'Haus'。"}`

**请求体示例**:
\`\`\`json
{
  "entry_query_text": "Haus",
  "alias_text": "家"
}
\`\`\`

### 🗄️ 数据库管理端点

#### 导出数据库
- **端点**: `GET /export`
- **描述**: 使用pg_dump工具导出完整的PostgreSQL数据库作为SQL备份文件
- **响应**: 文件下载（SQL格式）

#### 导入数据库
- **端点**: `POST /import`
- **描述**: 从SQL备份文件恢复PostgreSQL数据库，支持文件上传和文件路径两种方式
- **请求体**: `DatabaseImportRequest` (JSON) 或 `backup_file` (文件上传)
- **响应**: `{"message": "数据库从 backup.sql 恢复成功！新数据已生效。"}`

#### 系统状态检查
- **端点**: `GET /status`
- **描述**: 检查后端服务和数据库连接的健康状态
- **响应**: `{"status": "ok", "db_status": "ok"}`

## 预览功能

### V3.8 智能感知预览系统

从v3.8.0版本开始，系统引入了智能感知预览功能，能够自动识别查询内容的类型（单词或词缀）并生成相应的预览文本。

#### 功能特性

1. **智能类型识别**
   - 自动识别词缀格式（包含Präfix、Suffix、Vorsilbe、Nachsilbe等关键词）
   - 自动识别单词格式（传统的词性+释义格式）

2. **三层处理机制**
   - **词缀优先**：专门为词缀设计的正则表达式匹配
   - **单词回退**：传统的单词格式解析逻辑
   - **通用兜底**：确保总能生成可读预览的备用方案

3. **预览格式示例**

   **词缀预览格式**：
   ```
   Präfix: 表示动作的完成、结果...
   Suffix: 表示小称、亲切...
   ```

   **单词预览格式**：
   ```
   n. 房子；住宅；家庭; v. 去；走；进行
   ```

#### 技术实现

预览提取函数 `get_preview_from_analysis` 采用以下处理流程：

```python
def get_preview_from_analysis(analysis: str) -> str:
    """
    【V3.8 智能感知版】从完整的Markdown分析中智能提取预览。
    能够区分单词和词缀，并为它们生成合适的预览。
    """
    try:
        # 方案1: 尝试匹配词缀格式
        affix_pattern = r"\*\s*\*\*(Präfix|Suffix|Vorsilbe|Nachsilbe)[^ ]*\*\*\s*\*\*(.*?)\*\*"
        affix_match = re.search(affix_pattern, analysis, re.IGNORECASE)
        if affix_match:
            affix_type = affix_match.group(1).strip()
            affix_meaning = affix_match.group(2).strip().split("\n")[0]
            preview = f"{affix_type}: {affix_meaning}"
            return (preview[:70] + "...") if len(preview) > 70 else preview

        # 方案2: 单词格式回退
        # [传统单词匹配逻辑]
        
        # 方案3: 通用备用方案
        # [通用文本提取逻辑]
    except Exception as e:
        # 错误处理
        pass
```

#### 向后兼容性

- 完全兼容现有的单词分析格式
- 不影响现有API响应结构
- 自动适配新的词缀分析格式

#### 鲁棒性保证

- 即使AI返回意外格式，系统也能提取有效预览
- 多层错误处理机制确保系统稳定性
- 预览长度限制（70字符）确保显示效果

#### 相关API端点

以下端点的响应中包含预览文本：

- `GET /recent` - 返回 `RecentItem[]`，每个项目包含 `preview` 字段
- `GET /suggestions` - 返回 `DBSuggestion[]`，每个建议包含 `preview` 字段
- `POST /analyze` - 返回 `AnalyzeResponse`，通过内部预览提取生成

#### 预览文本结构

```json
{
  "query_text": "un-",
  "preview": "Präfix: 表示否定、相反..."
}
```

```json
{
  "query_text": "Haus",
  "preview": "n. 房子；住宅；家庭"
}
```

## 数据模型

### 请求模型

#### AnalyzeRequest
\`\`\`json
{
  "query_text": "string",      // 必需：要分析的德语单词
  "entry_type": "WORD" | "PHRASE"  // 必需：条目类型
}
\`\`\`

#### IntelligentSearchRequest
\`\`\`json
{
  "term": "string",           // 必需：搜索词
  "hint": "string"            // 可选：提示信息
}
\`\`\`

#### FollowUpCreateRequest
\`\`\`json
{
  "entry_id": "integer",        // 必需：条目ID
  "question": "string"          // 必需：问题内容
}
\`\`\`

#### AliasCreateRequest
\`\`\`json
{
  "entry_query_text": "string",  // 必需：目标条目查询文本
  "alias_text": "string"         // 必需：别名文本
}
\`\`\`

#### DatabaseImportRequest
\`\`\`json
{
  "file_path": "string"         // 必需：备份文件路径（Raycast客户端）
}
\`\`\`

### 响应模型

#### AnalyzeResponse
\`\`\`json
{
  "entry_id": "integer",           // 条目ID
  "query_text": "string",          // 查询文本
  "analysis_markdown": "string",    // 分析内容（Markdown格式）
  "source": "generated" | "知识库", // 数据来源
  "follow_ups": "FollowUpItem[]"    // 追问列表
}
\`\`\`

#### RecentItem
\`\`\`json
{
  "query_text": "string",  // 查询文本
  "preview": "string"       // 预览文本
}
\`\`\`

#### DBSuggestion
\`\`\`json
{
  "entry_id": "integer",           // 条目ID
  "query_text": "string",          // 查询文本
  "preview": "string",             // 预览文本
  "analysis_markdown": "string",    // 分析内容
  "source": "知识库",              // 数据来源
  "follow_ups": "FollowUpItem[]"    // 追问列表
}
\`\`\`

#### FollowUpItem
\`\`\`json
{
  "id": "integer",                  // 追问ID
  "question": "string",             // 问题内容
  "answer": "string",               // 回答内容
  "timestamp": "string"              // 时间戳（ISO 8601格式）
}
\`\`\`

## 错误处理

### 错误响应格式

所有错误响应都遵循统一的格式：

\`\`\`json
{
  "error": "error_code",
  "message": "错误描述",
  "status_code": 400,
  "details": {}
}
\`\`\`

### 常见错误码

| 状态码 | 错误代码 | 描述 |
|--------|----------|------|
| 400 | BAD_REQUEST | 请求参数错误 |
| 404 | NOT_FOUND | 资源未找到 |
| 409 | CONFLICT | 资源冲突 |
| 500 | INTERNAL_SERVER_ERROR | 服务器内部错误 |

### 错误示例

#### 请求参数错误
\`\`\`json
{
  "error": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "status_code": 400,
  "details": {
    "validation_errors": [
      {
        "loc": ["body", "query_text"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
\`\`\`

#### 资源未找到
\`\`\`json
{
  "error": "NOT_FOUND",
  "message": "ID为 999 的知识条目不存在。",
  "status_code": 404,
  "details": {}
}
\`\`\`

## 使用示例

### 完整的分析流程

1. **基础分析**
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Haus",
    "entry_type": "WORD"
  }'
\`\`\`

2. **添加追问**
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/follow-up" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_id": 1,
    "question": "这个词在古德语中有什么不同？"
  }'
\`\`\`

3. **创建别名**
\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/alias" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_query_text": "Haus",
    "alias_text": "家"
  }'
\`\`\`

### 智能搜索示例

\`\`\`bash
curl -X POST "http://localhost:8000/api/v1/intelligent-search" \
  -H "Content-Type: application/json" \
  -d '{
    "term": "hous",
    "hint": "building where people live"
  }'
\`\`\`

### 数据库管理

\`\`\`bash
# 导出数据库
curl -X GET "http://localhost:8000/api/v1/export" -o backup.sql

# 导入数据库
curl -X POST "http://localhost:8000/api/v1/import" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/backup.sql"
  }'
\`\`\`

## 性能考虑

### 缓存机制
- **预览文本缓存**：避免重复计算预览文本
- **LLM响应缓存**：避免重复调用AI服务
- **词汇表缓存**：减少数据库查询

### 批量操作
- **批量查询**：减少数据库往返次数
- **延迟加载**：按需加载关联数据
- **索引优化**：关键查询字段的索引

### 限制和配额
- **请求频率**：建议每秒不超过10个请求
- **响应大小**：单个响应不超过10MB
- **文件上传**：备份文件最大100MB

## 版本信息

- **当前版本**: v3.8.0
- **API版本**: v1
- **更新日期**: 2025-10-07

## 支持

如有问题或建议，请通过以下方式联系：

- **GitHub Issues**: [项目Issues页面]
- **邮件**: [your-email@example.com]
- **文档**: [完整API文档]

---

*最后更新: 2025-10-07*
