# 前端集成指南 - 德语词根词缀功能

## 📋 概述

后端已新增德语词根词缀查询功能，前端现在可以支持对德语前缀（如 "ver-", "un-"）和后缀（如 "-heit", "-keit"）的智能分析。本指南详细说明前端如何集成这些新功能。

## 🎯 核心变化

### API 接口变化
- **统一接口**：无需为词缀创建新的 API 端点
- **智能推断**：后端自动识别查询类型（单词/前缀/后缀）
- **简化调用**：前端只需发送 `query_text`，无需关心类型判断

### 支持的查询类型
| 类型 | 示例 | 说明 |
|------|------|------|
| 单词 | `haus`, `gehen`, `beispiel` | 传统单词查询 |
| 短语 | `aufstehen`, `nach Hause gehen` | 多词短语 |
| 前缀 | `ver-`, `un-`, `aus-`, `be-` | 以 `-` 结尾 |
| 后缀 | `-heit`, `-keit`, `-lich`, `-bar` | 以 `-` 开头 |

## 🔧 API 接口详情

### 1. 分析接口 `/api/v1/analyze`

#### 请求格式
```typescript
interface AnalyzeRequest {
  query_text: string;           // 必需：查询文本
  entry_type?: 'word' | 'phrase' | 'prefix' | 'suffix';  // 可选：强制指定类型
}
```

#### 响应格式
```typescript
interface AnalyzeResponse {
  id: string;                   // 条目唯一ID
  query_text: string;           // 原始查询文本
  entry_type: string;           // 条目类型（word/phrase/prefix/suffix）
  content: string;              // 分析内容（Markdown格式）
  aliases: string[];            // 别名列表
  follow_up_questions: FollowUpItem[];  // 追问问题
  source: 'generated' | 'database';     // 来源
  created_at: string;           // 创建时间
  updated_at: string;           // 更新时间
}

interface FollowUpItem {
  id: string;
  question: string;
  answer: string;
}
```

#### 调用示例

**推荐方式 - 自动推断**
```javascript
const analyzeWord = async (query: string) => {
  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query_text: query  // 后端自动推断类型
    })
  });
  
  return await response.json();
};

// 使用示例
const result1 = await analyzeWord('ver-');    // 自动识别为前缀
const result2 = await analyzeWord('haus');    // 自动识别为单词
const result3 = await analyzeWord('-keit');   // 自动识别为后缀
```

**手动指定类型**
```javascript
const analyzeWithForcedType = async (query: string, type: string) => {
  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query_text: query,
      entry_type: type  // 强制指定类型
    })
  });
  
  return await response.json();
};

// 使用示例
const result = await analyzeWithForcedType('ver-', 'prefix');
```

### 2. 建议接口 `/api/v1/suggestions`

#### 请求格式
```typescript
interface IntelligentSearchRequest {
  query: string;                // 查询文本
  limit?: number;               // 返回结果数量限制（默认10）
  entry_type?: string;          // 可选：过滤特定类型
}
```

#### 响应格式
```typescript
interface SuggestionResponse {
  query: string;                // 原始查询
  suggestions: SuggestionItem[]; // 建议列表
  total: number;                // 总数量
}

interface SuggestionItem {
  id: string;
  query_text: string;           // 建议文本
  entry_type: string;           // 条目类型
  content_preview: string;      // 内容预览
  relevance_score?: number;     // 相关性评分
}
```

#### 调用示例
```javascript
const getSuggestions = async (query: string) => {
  const response = await fetch('/api/v1/suggestions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      limit: 10
    })
  });
  
  return await response.json();
};

// 词缀查询会返回相关单词示例
const prefixSuggestions = await getSuggestions('ver-');  // 返回包含 ver- 的单词
const suffixSuggestions = await getSuggestions('-keit'); // 返回包含 -keit 的单词
```

## 🎨 前端实现建议

### 1. 输入组件优化

#### 智能提示
```typescript
// 在输入框中提供类型提示
const getInputPlaceholder = (inputValue: string) => {
  if (inputValue.endsWith('-')) {
    return '检测到前缀，将分析构词法...';
  } else if (inputValue.startsWith('-') && inputValue.length > 1) {
    return '检测到后缀，将分析构词法...';
  } else {
    return '输入德语单词、前缀或后缀...';
  }
};
```

#### 实时类型检测
```typescript
const detectInputType = (value: string): 'word' | 'prefix' | 'suffix' | 'unknown' => {
  const trimmed = value.trim();
  if (trimmed.endsWith('-') && trimmed.length > 1) {
    return 'prefix';
  } else if (trimmed.startsWith('-') && trimmed.length > 1) {
    return 'suffix';
  } else if (trimmed.length > 0) {
    return 'word';
  }
  return 'unknown';
};

// 在 UI 中显示检测到的类型
const TypeIndicator = ({ value }: { value: string }) => {
  const type = detectInputType(value);
  const typeConfig = {
    word: { label: '单词', color: 'blue' },
    prefix: { label: '前缀', color: 'green' },
    suffix: { label: '后缀', color: 'orange' },
    unknown: { label: '未知', color: 'gray' }
  };
  
  if (type === 'unknown') return null;
  
  return (
    <span style={{ color: typeConfig[type].color }}>
      {typeConfig[type].label}
    </span>
  );
};
```

### 2. 结果展示优化

#### 词缀分析结果展示
```typescript
const AffixAnalysisDisplay = ({ response }: { response: AnalyzeResponse }) => {
  if (response.entry_type === 'prefix' || response.entry_type === 'suffix') {
    return (
      <div className="affix-analysis">
        <div className="affix-header">
          <h3>{response.query_text}</h3>
          <span className="affix-type">
            {response.entry_type === 'prefix' ? '前缀' : '后缀'}
          </span>
        </div>
        
        {/* 渲染 Markdown 内容 */}
        <div className="affix-content">
          <ReactMarkdown>{response.content}</ReactMarkdown>
        </div>
        
        {/* 显示相关单词示例 */}
        <RelatedWordsExamples affix={response.query_text} />
      </div>
    );
  }
  
  // 传统单词展示
  return <WordAnalysisDisplay response={response} />;
};
```

#### 相关单词示例组件
```typescript
const RelatedWordsExamples = ({ affix }: { affix: string }) => {
  const [examples, setExamples] = useState<SuggestionItem[]>([]);
  
  useEffect(() => {
    const loadExamples = async () => {
      try {
        const response = await getSuggestions(affix);
        setExamples(response.suggestions.slice(0, 5));
      } catch (error) {
        console.error('加载示例失败:', error);
      }
    };
    
    loadExamples();
  }, [affix]);
  
  return (
    <div className="related-examples">
      <h4>相关单词示例</h4>
      <div className="examples-grid">
        {examples.map(example => (
          <div key={example.id} className="example-item">
            <span className="example-word">{example.query_text}</span>
            <span className="example-preview">{example.content_preview}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 3. 搜索建议优化

#### 类型感知的搜索建议
```typescript
const EnhancedSearchSuggestions = ({ query }: { query: string }) => {
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    
    const loadSuggestions = async () => {
      setLoading(true);
      try {
        const response = await getSuggestions(query);
        setSuggestions(response.suggestions);
      } catch (error) {
        console.error('加载建议失败:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadSuggestions();
  }, [query]);
  
  return (
    <div className="search-suggestions">
      {loading && <div className="loading">加载中...</div>}
      {suggestions.map(suggestion => (
        <div key={suggestion.id} className="suggestion-item">
          <div className="suggestion-text">{suggestion.query_text}</div>
          <div className="suggestion-type">{suggestion.entry_type}</div>
          <div className="suggestion-preview">{suggestion.content_preview}</div>
        </div>
      ))}
    </div>
  );
};
```

## 🎯 UI/UX 设计建议

### 1. 输入界面
- **实时类型检测**：当用户输入 "ver-" 或 "-heit" 时，显示类型标签
- **智能提示**：根据输入类型显示不同的占位符文本
- **视觉反馈**：不同类型使用不同颜色标识

### 2. 结果展示
- **词缀专门布局**：为词缀分析设计专门的展示模板
- **结构化信息**：突出显示类型、含义、语法功能等关键信息
- **相关示例**：在词缀分析页面展示包含该词缀的单词

### 3. 搜索体验
- **类型过滤**：允许用户按类型筛选搜索结果
- **智能排序**：词缀查询优先显示相关单词示例
- **历史记录**：区分显示不同类型的查询历史

## 🔄 迁移指南

### 现有代码修改

#### 1. API 调用更新
```typescript
// 之前
const analyzeWord = async (word: string) => {
  // 假设之前有专门的单词分析接口
  return await fetch(`/api/v1/analyze/word/${word}`);
};

// 现在
const analyzeWord = async (query: string) => {
  return await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: query })
  });
};
```

#### 2. 类型处理更新
```typescript
// 之前可能需要前端判断类型
const getAnalysisEndpoint = (input: string) => {
  if (input.endsWith('-')) {
    return '/api/v1/analyze/prefix';
  } else if (input.startsWith('-')) {
    return '/api/v1/analyze/suffix';
  } else {
    return '/api/v1/analyze/word';
  }
};

// 现在统一使用一个接口
const analyze = async (input: string) => {
  return await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: input })
  });
};
```

### 新功能集成

#### 1. 添加词缀类型支持
```typescript
// 在类型定义中添加
type EntryType = 'word' | 'phrase' | 'prefix' | 'suffix';

interface AnalysisResult {
  // ... 现有字段
  entry_type: EntryType;
}

// 在组件中处理新类型
const renderAnalysisResult = (result: AnalysisResult) => {
  switch (result.entry_type) {
    case 'prefix':
    case 'suffix':
      return <AffixAnalysis result={result} />;
    case 'word':
    case 'phrase':
    default:
      return <WordAnalysis result={result} />;
  }
};
```

#### 2. 更新搜索逻辑
```typescript
// 在搜索组件中支持词缀查询
const handleSearch = async (query: string) => {
  // 无需判断类型，直接发送查询
  const result = await analyze(query);
  
  // 根据返回的类型选择展示方式
  if (result.entry_type === 'prefix' || result.entry_type === 'suffix') {
    // 显示词缀分析结果
    showAffixAnalysis(result);
  } else {
    // 显示传统单词分析结果
    showWordAnalysis(result);
  }
};
```

## 🧪 测试建议

### 1. 功能测试用例
```typescript
describe('词根词缀功能测试', () => {
  test('前缀分析', async () => {
    const result = await analyze('ver-');
    expect(result.entry_type).toBe('prefix');
    expect(result.content).toContain('类型');
    expect(result.content).toContain('含义');
  });
  
  test('后缀分析', async () => {
    const result = await analyze('-heit');
    expect(result.entry_type).toBe('suffix');
    expect(result.content).toContain('语法功能');
  });
  
  test('单词分析', async () => {
    const result = await analyze('haus');
    expect(result.entry_type).toBe('word');
  });
  
  test('建议服务', async () => {
    const suggestions = await getSuggestions('ver-');
    expect(suggestions.suggestions).toHaveLength.greaterThan(0);
    suggestions.suggestions.forEach(s => {
      expect(s.query_text).toContain('ver');
    });
  });
});
```

### 2. 集成测试
- 测试完整的用户流程：输入 → 分析 → 展示
- 测试不同输入类型的正确识别
- 测试建议服务的词缀感知功能
- 测试错误处理和边界情况

## 🚀 部署注意事项

### 1. 向后兼容性
- 现有的单词查询功能完全不受影响
- 前端可以逐步集成新功能，无需一次性修改所有代码

### 2. 性能考虑
- 词缀分析可能比单词分析稍慢，建议添加加载状态
- 建议服务已优化，但大量词缀查询时仍需注意缓存

### 3. 错误处理
```typescript
const analyzeWithErrorHandling = async (query: string) => {
  try {
    const response = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: query })
    });
    
    if (!response.ok) {
      throw new Error(`分析失败: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('分析请求失败:', error);
    // 显示用户友好的错误信息
    showError('分析失败，请稍后重试');
    return null;
  }
};
```

## 📞 技术支持

如果在集成过程中遇到问题，请：
1. 检查网络请求的格式和参数
2. 查看浏览器控制台的错误信息
3. 确认后端服务正常运行
4. 参考本文档的示例代码

---

**更新时间**: 2025-10-07  
**版本**: v1.0  
**兼容性**: 向后兼容现有功能
