# De-AI-Hilfer-Backend 设计图文档

本文档包含De-AI-Hilfer-Backend项目的四种核心设计图，为前端开发和系统维护提供可视化指导。

## 1. 系统架构图

```mermaid
graph TB
    subgraph "客户端层"
        WEB[Web前端]
        MOBILE[移动端]
        API_CLIENT[API客户端]
    end

    subgraph "API网关层"
        NGINX[Nginx反向代理]
        RATE_LIMIT[限流中间件]
        AUTH[认证中间件]
    end

    subgraph "应用层 - FastAPI"
        subgraph "API端点层"
            ENDPOINTS[app/api/v1/endpoints.py]
        end
        
        subgraph "业务逻辑层"
            SERVICES[app/api/v1/services.py]
            MANAGEMENT[app/api/v1/management.py]
        end
        
        subgraph "核心服务层"
            LLM_SERVICE[app/core/llm_service.py]
            CONFIG[app/core/config.py]
            PERFORMANCE[app/core/performance.py]
        end
    end

    subgraph "AI适配器层"
        LLM_ROUTER[ai_adapter/llm_router.py]
        GEMINI_ADAPTER[Gemini适配器]
        OPENAI_ADAPTER[OpenAI适配器]
        OLLAMA_ADAPTER[Ollama适配器]
        TOOL_MANAGER[ai_adapter/tool_manager.py]
    end

    subgraph "数据层"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis缓存)]
        MIGRATIONS[Alembic迁移]
    end

    subgraph "外部AI服务"
        GEMINI_API[Google Gemini API]
        OPENAI_API[OpenAI API]
        OLLAMA_LOCAL[本地Ollama服务]
    end

    %% 连接关系
    WEB --> NGINX
    MOBILE --> NGINX
    API_CLIENT --> NGINX
    
    NGINX --> RATE_LIMIT
    RATE_LIMIT --> AUTH
    AUTH --> ENDPOINTS
    
    ENDPOINTS --> SERVICES
    ENDPOINTS --> MANAGEMENT
    SERVICES --> LLM_SERVICE
    MANAGEMENT --> LLM_SERVICE
    
    LLM_SERVICE --> LLM_ROUTER
    LLM_ROUTER --> GEMINI_ADAPTER
    LLM_ROUTER --> OPENAI_ADAPTER
    LLM_ROUTER --> OLLAMA_ADAPTER
    
    TOOL_MANAGER --> LLM_ROUTER
    
    GEMINI_ADAPTER --> GEMINI_API
    OPENAI_ADAPTER --> OPENAI_API
    OLLAMA_ADAPTER --> OLLAMA_LOCAL
    
    SERVICES --> POSTGRES
    SERVICES --> REDIS
    MANAGEMENT --> POSTGRES
    
    MIGRATIONS --> POSTGRES

    %% 样式定义
    classDef clientLayer fill:#e1f5fe
    classDef gatewayLayer fill:#f3e5f5
    classDef applicationLayer fill:#e8f5e8
    classDef aiLayer fill:#fff3e0
    classDef dataLayer fill:#fce4ec
    classDef externalLayer fill:#f1f8e9
    
    class WEB,MOBILE,API_CLIENT clientLayer
    class NGINX,RATE_LIMIT,AUTH gatewayLayer
    class ENDPOINTS,SERVICES,MANAGEMENT,LLM_SERVICE,CONFIG,PERFORMANCE applicationLayer
    class LLM_ROUTER,GEMINI_ADAPTER,OPENAI_ADAPTER,OLLAMA_ADAPTER,TOOL_MANAGER aiLayer
    class POSTGRES,REDIS,MIGRATIONS dataLayer
    class GEMINI_API,OPENAI_API,OLLAMA_LOCAL externalLayer
```

### 架构说明

**分层设计原则**：
- **客户端层**：支持多种前端接入方式
- **API网关层**：提供统一的入口和安全控制
- **应用层**：基于FastAPI的分层架构，职责清晰
- **AI适配器层**：统一的AI服务接口，支持多模型
- **数据层**：PostgreSQL主存储 + Redis缓存
- **外部服务**：集成多种AI服务提供商

**核心特性**：
- 单例模式的LLM服务管理
- 智能的AI模型路由和降级
- 完整的缓存策略
- 异步处理支持

## 2. API流程图

### 2.1 智能查询API流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as FastAPI端点
    participant Auth as 认证中间件
    participant Service as 业务服务
    participant Cache as Redis缓存
    participant DB as PostgreSQL
    participant LLM as LLM服务
    participant AI as AI适配器

    Client->>API: POST /api/v1/intelligent-query
    API->>Auth: 验证请求
    Auth-->>API: 认证通过
    
    API->>Service: intelligent_query()
    
    Service->>Cache: 检查缓存
    alt 缓存命中
        Cache-->>Service: 返回缓存结果
        Service-->>API: 返回结果
    else 缓存未命中
        Service->>DB: 查询相关数据
        DB-->>Service: 返回数据
        
        Service->>LLM: process_query()
        LLM->>AI: 路由到合适的AI模型
        
        alt Gemini可用
            AI->>Gemini: 调用Gemini API
            Gemini-->>AI: 返回响应
        else OpenAI可用
            AI->>OpenAI: 调用OpenAI API
            OpenAI-->>AI: 返回响应
        else 本地Ollama
            AI->>Ollama: 调用本地服务
            Ollama-->>AI: 返回响应
        end
        
        AI-->>LLM: 返回AI响应
        LLM-->>Service: 返回处理结果
        
        Service->>Cache: 更新缓存
        Service-->>API: 返回结果
    end
    
    API-->>Client: 返回JSON响应
```

### 2.2 批量操作API流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as FastAPI端点
    participant Service as 业务服务
    participant DB as PostgreSQL
    participant LLM as LLM服务
    participant AI as AI适配器

    Client->>API: POST /api/v1/batch-process
    API->>Service: batch_process_entries()
    
    Service->>DB: 批量查询数据
    DB-->>Service: 返回数据列表
    
    loop 处理每个条目
        Service->>LLM: process_single_entry()
        LLM->>AI: 选择AI模型
        AI-->>LLM: AI响应
        LLM-->>Service: 处理结果
        
        Service->>DB: 更新单个条目
    end
    
    Service->>DB: 批量提交事务
    Service-->>API: 返回批量处理结果
    API-->>Client: 返回处理统计
```

### 2.3 数据管理API流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as FastAPI端点
    participant Management as 管理服务
    participant DB as PostgreSQL
    participant Migrations as Alembic

    Client->>API: POST /api/v1/maintenance/optimize
    API->>Management: optimize_database()
    
    Management->>DB: ANALYZE表统计
    Management->>DB: 重建索引
    Management->>DB: 清理无用数据
    
    Management->>Migrations: 检查迁移状态
    Migrations-->>Management: 返回状态信息
    
    Management->>DB: VACUUM优化
    Management-->>API: 返回优化结果
    API-->>Client: 返回优化报告
```

## 3. 数据库ER图

```mermaid
erDiagram
    KNOWLEDGE_ENTRY {
        int id PK
        string word
        string word_type
        jsonb definition
        jsonb examples
        jsonb grammar_info
        jsonb context_info
        string difficulty_level
        string source
        string created_at
        string updated_at
        boolean is_active
        jsonb metadata
    }
    
    ENTRY_ALIAS {
        int id PK
        int entry_id FK
        string alias
        string alias_type
        string created_at
        boolean is_primary
    }
    
    FOLLOW_UP {
        int id PK
        int entry_id FK
        string question
        string answer
        string question_type
        string difficulty_level
        int priority
        string created_at
        string updated_at
        boolean is_active
        jsonb metadata
    }
    
    LEARNING_PROGRESS {
        int id PK
        int entry_id FK
        string user_id
        string mastery_level
        int review_count
        string last_reviewed
        string next_review
        jsonb performance_data
        string created_at
        string updated_at
    }
    
    AI_INTERACTION_LOG {
        int id PK
        string session_id
        string user_id
        int entry_id FK
        string interaction_type
        jsonb request_data
        jsonb response_data
        string ai_model_used
        float response_time
        string created_at
        boolean is_successful
    }
    
    %% 关系定义
    KNOWLEDGE_ENTRY ||--o{ ENTRY_ALIAS : "has"
    KNOWLEDGE_ENTRY ||--o{ FOLLOW_UP : "generates"
    KNOWLEDGE_ENTRY ||--o{ LEARNING_PROGRESS : "tracks"
    KNOWLEDGE_ENTRY ||--o{ AI_INTERACTION_LOG : "involves"
    
    %% 索引标记
    KNOWLEDGE_ENTRY {
        index idx_word_type (word, word_type)
        index idx_difficulty (difficulty_level)
        index idx_source (source)
        index idx_active (is_active)
        index idx_created (created_at)
    }
    
    ENTRY_ALIAS {
        index idx_entry_alias (entry_id, alias)
        index idx_alias_type (alias_type)
        index idx_primary (is_primary)
    }
    
    FOLLOW_UP {
        index idx_entry_followup (entry_id, question_type)
        index idx_priority (priority)
        index idx_difficulty (difficulty_level)
        index idx_active (is_active)
    }
    
    LEARNING_PROGRESS {
        index idx_user_entry (user_id, entry_id)
        index idx_mastery (mastery_level)
        index idx_next_review (next_review)
        index idx_updated (updated_at)
    }
    
    AI_INTERACTION_LOG {
        index idx_session (session_id)
        index idx_user_session (user_id, session_id)
        index idx_entry_interaction (entry_id, interaction_type)
        index idx_created (created_at)
        index idx_model (ai_model_used)
    }
```

### 数据模型说明

**核心表结构**：

1. **KNOWLEDGE_ENTRY**：知识条目主表
   - 存储德语单词、短语的核心信息
   - 支持JSONB格式的灵活数据结构
   - 包含难度等级、来源等元数据

2. **ENTRY_ALIAS**：别名表
   - 支持一词多义和变体形式
   - 区分主别名和次别名

3. **FOLLOW_UP**：追问表
   - 存储相关的练习题和测试
   - 支持多种题型和难度分级

4. **LEARNING_PROGRESS**：学习进度表
   - 跟踪用户学习状态
   - 支持间隔重复算法

5. **AI_INTERACTION_LOG**：AI交互日志表
   - 记录所有AI服务调用
   - 支持性能分析和优化

**索引策略**：
- 复合索引优化常用查询
- 时间索引支持数据分析
- 类型索引支持分类查询

## 4. 部署架构图

### 4.1 生产环境部署架构

```mermaid
graph TB
    subgraph "负载均衡层"
        LB[负载均衡器]
        SSL[SSL终端]
    end

    subgraph "Web服务层"
        NGINX1[Nginx 1]
        NGINX2[Nginx 2]
    end

    subgraph "应用服务层"
        API1[FastAPI实例 1]
        API2[FastAPI实例 2]
        API3[FastAPI实例 3]
    end

    subgraph "缓存层"
        REDIS_MASTER[Redis主节点]
        REDIS_SLAVE1[Redis从节点 1]
        REDIS_SLAVE2[Redis从节点 2]
    end

    subgraph "数据库层"
        PG_MASTER[(PostgreSQL主库)]
        PG_SLAVE1[(PostgreSQL从库 1)]
        PG_SLAVE2[(PostgreSQL从库 2)]
    end

    subgraph "监控层"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ALERTMANAGER[AlertManager]
    end

    subgraph "日志层"
        ELASTICSEARCH[Elasticsearch]
        KIBANA[Kibana]
        LOGSTASH[Logstash]
    end

    subgraph "外部服务"
        GEMINI_API[Google Gemini]
        OPENAI_API[OpenAI]
        OLLAMA_CLUSTER[Ollama集群]
    end

    %% 连接关系
    LB --> SSL
    SSL --> NGINX1
    SSL --> NGINX2
    
    NGINX1 --> API1
    NGINX1 --> API2
    NGINX2 --> API2
    NGINX2 --> API3
    
    API1 --> REDIS_MASTER
    API2 --> REDIS_MASTER
    API3 --> REDIS_MASTER
    
    REDIS_MASTER --> REDIS_SLAVE1
    REDIS_MASTER --> REDIS_SLAVE2
    
    API1 --> PG_MASTER
    API2 --> PG_MASTER
    API3 --> PG_MASTER
    
    PG_MASTER --> PG_SLAVE1
    PG_MASTER --> PG_SLAVE2
    
    API1 --> GEMINI_API
    API2 --> OPENAI_API
    API3 --> OLLAMA_CLUSTER
    
    PROMETHEUS --> API1
    PROMETHEUS --> API2
    PROMETHEUS --> API3
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERTMANAGER
    
    API1 --> LOGSTASH
    API2 --> LOGSTASH
    API3 --> LOGSTASH
    LOGSTASH --> ELASTICSEARCH
    ELASTICSEARCH --> KIBANA

    %% 样式定义
    classDef loadBalancer fill:#ffeb3b
    classDef webService fill:#4caf50
    classDef appService fill:#2196f3
    classDef cache fill:#ff9800
    classDef database fill:#9c27b0
    classDef monitoring fill:#f44336
    classDef logging fill:#795548
    classDef external fill:#607d8b
    
    class LB,SSL loadBalancer
    class NGINX1,NGINX2 webService
    class API1,API2,API3 appService
    class REDIS_MASTER,REDIS_SLAVE1,REDIS_SLAVE2 cache
    class PG_MASTER,PG_SLAVE1,PG_SLAVE2 database
    class PROMETHEUS,GRAFANA,ALERTMANAGER monitoring
    class ELASTICSEARCH,KIBANA,LOGSTASH logging
    class GEMINI_API,OPENAI_API,OLLAMA_CLUSTER external
```

### 4.2 开发环境部署架构

```mermaid
graph TB
    subgraph "开发机"
        DEV_NGINX[Nginx开发服务器]
        DEV_API[FastAPI开发服务器]
        DEV_REDIS[Redis开发实例]
        DEV_PG[(PostgreSQL开发库)]
        DEV_OLLAMA[本地Ollama]
    end

    subgraph "开发工具"
        DOCKER[Docker Compose]
        TEST[测试环境]
        DOCS[文档服务]
    end

    subgraph "版本控制"
        GIT[Git仓库]
        CI[CI/CD流水线]
    end

    %% 连接关系
    DEV_NGINX --> DEV_API
    DEV_API --> DEV_REDIS
    DEV_API --> DEV_PG
    DEV_API --> DEV_OLLAMA
    
    DOCKER --> DEV_NGINX
    DOCKER --> DEV_API
    DOCKER --> DEV_REDIS
    DOCKER --> DEV_PG
    DOCKER --> DEV_OLLAMA
    
    TEST --> DEV_API
    DOCS --> DEV_API
    
    GIT --> CI
    CI --> DOCKER

    %% 样式定义
    classDef development fill:#e3f2fd
    classDef tools fill:#f1f8e9
    classDef versionControl fill:#fff3e0
    
    class DEV_NGINX,DEV_API,DEV_REDIS,DEV_PG,DEV_OLLAMA development
    class DOCKER,TEST,DOCS tools
    class GIT,CI versionControl
```

### 4.3 容器化部署配置

```yaml
# docker-compose.yml 示例
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
  
  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/de_ai_hilfer
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=de_ai_hilfer
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
  
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

## 5. 前端开发指导

### 5.1 API调用示例

```javascript
// 智能查询API
const intelligentQuery = async (query) => {
  const response = await fetch('/api/v1/intelligent-query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query })
  });
  
  return await response.json();
};

// 批量处理API
const batchProcess = async (entries, options) => {
  const response = await fetch('/api/v1/batch-process', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      entries,
      options 
    })
  });
  
  return await response.json();
};
```

### 5.2 错误处理策略

```javascript
// 统一错误处理
const handleApiError = (error) => {
  if (error.status === 429) {
    // 限流错误，实现重试机制
    return retryWithBackoff(request);
  } else if (error.status >= 500) {
    // 服务器错误，显示友好提示
    showErrorMessage('服务暂时不可用，请稍后重试');
  } else {
    // 客户端错误，显示具体错误信息
    showErrorMessage(error.message);
  }
};
```

### 5.3 缓存策略

```javascript
// 前端缓存实现
class ApiCache {
  constructor(ttl = 300000) { // 5分钟TTL
    this.cache = new Map();
    this.ttl = ttl;
  }
  
  async get(key, fetcher) {
    const cached = this.cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < this.ttl) {
      return cached.data;
    }
    
    const data = await fetcher();
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
    
    return data;
  }
}
```

## 6. 性能优化建议

### 6.1 前端优化
- 实现请求去重和缓存
- 使用虚拟滚动处理大量数据
- 实现懒加载和预加载策略
- 优化Bundle大小

### 6.2 API调用优化
- 批量请求合并
- 实现指数退避重试
- 使用WebSocket处理实时更新
- 合理设置超时时间

### 6.3 数据传输优化
- 启用gzip压缩
- 使用分页和过滤
- 实现增量更新
- 优化JSON结构

---

## 总结

这套设计图提供了De-AI-Hilfer-Backend项目的完整技术视图：

1. **系统架构图**：展示了清晰的分层架构和模块关系
2. **API流程图**：详细说明了请求处理流程
3. **数据库ER图**：完整的数据模型和关系设计
4. **部署架构图**：生产环境和开发环境的部署方案

这些设计图为前端开发团队提供了：
- 清晰的API调用逻辑
- 完整的数据结构理解
- 合理的错误处理策略
- 有效的性能优化方案

建议前端开发团队基于这些设计图进行开发，并与后端团队保持密切沟通，确保系统的一致性和可维护性。
