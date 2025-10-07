# API 快速参考 - 德语词根词缀功能

## 🚀 快速开始

### 基础调用
```javascript
// 统一分析接口 - 支持单词、前缀、后缀
const response = await fetch('/api/v1/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query_text: 'ver-'  // 支持任何德语文本
  })
});
const result = await response.json();
```

## 📡 API 端点

### 1. 分析接口 `/api/v1/analyze`

**功能**: 统一分析德语单词、短语、前缀、后缀

**请求**:
```json
{
  "query_text": "ver-",           // 必需：查询文本
  "entry_type": "prefix"          // 可选：强制指定类型
}
```

**响应**:
```json
{
  "id": "uuid-string",
  "query_text": "ver-",
  "entry_type": "prefix",         // word/phrase/prefix/suffix
  "content": "# **ver-**\n\n#### 1. 类型 (Typ)\n* 前缀...",
  "aliases": ["vor-", "for-"],
  "follow_up_questions": [],
  "source": "generated",
  "created_at": "2025-10-07T21:00:00Z",
  "updated_at": "2025-10-07T21:00:00Z"
}
```

### 2. 建议接口 `/api/v1/suggestions`

**功能**: 获取相关建议，支持词缀感知

**请求**:
```json
{
  "query": "ver-",
  "limit": 10,
  "entry_type": "word"           // 可选：过滤类型
}
```

**响应**:
```json
{
  "query": "ver-",
  "suggestions": [
    {
      "id": "uuid-1",
      "query_text": "verkaufen",
      "entry_type": "word",
      "content_preview": "卖掉，出售...",
      "relevance_score": 0.95
    }
  ],
  "total": 15
}
```

## 🎯 支持的查询类型

| 类型 | 示例 | 自动识别规则 |
|------|------|-------------|
| 单词 | `haus`, `gehen` | 默认类型 |
| 短语 | `aufstehen` | 多词组合 |
| 前缀 | `ver-`, `un-`, `aus-` | 以 `-` 结尾 |
| 后缀 | `-heit`, `-keit`, `-lich` | 以 `-` 开头 |

## 💡 使用技巧

### 1. 智能推断
```javascript
// 后端自动识别类型
analyze('ver-');    // → prefix
analyze('haus');    // → word  
analyze('-keit');   // → suffix
```

### 2. 强制指定类型
```javascript
// 手动指定类型（特殊情况下使用）
analyze('ver-', { entry_type: 'prefix' });
```

### 3. 获取相关示例
```javascript
// 词缀查询会返回包含该词缀的单词
const suggestions = await getSuggestions('ver-');
// 返回: verkaufen, verlieren, verstehen...
```

## 🔧 前端集成代码

### React 组件示例
```typescript
const GermanAnalyzer = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = async (text: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_text: text })
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('分析失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="输入德语单词、前缀或后缀..."
      />
      <button onClick={() => analyze(query)}>
        {loading ? '分析中...' : '分析'}
      </button>
      
      {result && (
        <div>
          <h3>{result.query_text} ({result.entry_type})</h3>
          <div dangerouslySetInnerHTML={{ __html: result.content }} />
        </div>
      )}
    </div>
  );
};
```

### Vue 组件示例
```vue
<template>
  <div>
    <input 
      v-model="query" 
      placeholder="输入德语单词、前缀或后缀..."
    />
    <button @click="analyze" :disabled="loading">
      {{ loading ? '分析中...' : '分析' }}
    </button>
    
    <div v-if="result">
      <h3>{{ result.query_text }} ({{ result.entry_type }})</h3>
      <div v-html="result.content"></div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      query: '',
      result: null,
      loading: false
    };
  },
  methods: {
    async analyze() {
      this.loading = true;
      try {
        const response = await fetch('/api/v1/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query_text: this.query })
        });
        this.result = await response.json();
      } catch (error) {
        console.error('分析失败:', error);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

## 🎨 UI 类型指示器

### 实时类型检测
```javascript
const detectType = (input) => {
  const trimmed = input.trim();
  if (trimmed.endsWith('-') && trimmed.length > 1) return 'prefix';
  if (trimmed.startsWith('-') && trimmed.length > 1) return 'suffix';
  if (trimmed.length > 0) return 'word';
  return 'unknown';
};

// UI 显示
const TypeBadge = ({ type }) => {
  const colors = {
    word: 'blue',
    prefix: 'green', 
    suffix: 'orange',
    unknown: 'gray'
  };
  
  return (
    <span style={{ 
      backgroundColor: colors[type] || 'gray',
      color: 'white',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '12px'
    }}>
      {type}
    </span>
  );
};
```

## ⚠️ 注意事项

### 1. 错误处理
```javascript
const analyzeWithErrorHandling = async (query) => {
  try {
    const response = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: query })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('分析请求失败:', error);
    // 显示用户友好的错误信息
    alert('分析失败，请检查网络连接后重试');
    return null;
  }
};
```

### 2. 防抖处理
```javascript
// 避免频繁请求
const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

const debouncedAnalyze = debounce(analyze, 300);
```

### 3. 加载状态
```javascript
// 为不同类型设置不同的加载提示
const getLoadingMessage = (query) => {
  if (query.endsWith('-')) return '分析前缀中...';
  if (query.startsWith('-')) return '分析后缀中...';
  return '分析单词中...';
};
```

## 🧪 测试用例

### 基础功能测试
```javascript
// 测试前缀分析
const testPrefix = async () => {
  const result = await analyze('ver-');
  console.assert(result.entry_type === 'prefix');
  console.assert(result.content.includes('类型'));
};

// 测试后缀分析  
const testSuffix = async () => {
  const result = await analyze('-heit');
  console.assert(result.entry_type === 'suffix');
  console.assert(result.content.includes('含义'));
};

// 测试建议服务
const testSuggestions = async () => {
  const result = await getSuggestions('ver-');
  console.assert(result.suggestions.length > 0);
};
```

## 📞 故障排除

### 常见问题

**Q: 为什么词缀分析返回空结果？**
A: 检查输入格式，前缀应以 `-` 结尾，后缀应以 `-` 开头

**Q: 如何区分前缀和后缀？**
A: 前缀：`ver-`, `un-`（连字符在末尾）；后缀：`-heit`, `-keit`（连字符在开头）

**Q: 建议服务返回不相关结果？**
A: 词缀查询会返回包含该词缀的单词，确保词缀格式正确

### 调试技巧
```javascript
// 添加调试日志
const analyzeWithDebug = async (query) => {
  console.log(`分析查询: "${query}"`);
  console.log(`检测类型: ${detectType(query)}`);
  
  const result = await analyze(query);
  console.log(`返回类型: ${result.entry_type}`);
  console.log(`内容长度: ${result.content.length}`);
  
  return result;
};
```

---

**版本**: v1.0  
**更新**: 2025-10-07  
**支持**: 向后兼容现有功能
