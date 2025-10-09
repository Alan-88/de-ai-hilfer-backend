# 前端集成指南 - 智能化背单词模块

## 📋 概述

本文档为前端开发者提供智能化背单词模块的完整集成指南，包括API接口说明、数据流程、UI组件设计和最佳实践。

**版本**: v4.0.0  
**更新日期**: 2025-10-09  
**兼容性**: De-AI-Hilfer Backend v4.0.0+

## 🎯 功能特性

### 核心学习流程
- **间隔重复系统 (SRS)**: 基于SuperMemo-2算法的科学记忆
- **二次机会学习**: 人性化的提示机制，深度记忆
- **多维学习模式**: 卡片、拼写、选择题三种模式
- **AI动态生成**: 实时生成例句和智能题目

### 学习体验设计
- **渐进式学习**: 新词与复习词智能配比
- **自适应难度**: 根据用户表现调整学习内容
- **即时反馈**: 实时的学习效果评估
- **进度可视化**: 清晰的学习统计和成就系统

## 🔌 API接口详解

### 基础配置
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1'
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}` // 如果需要认证
}
```

### 1. 获取学习会话
```javascript
// GET /api/v1/learning/session
async function getLearningSession() {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/session`, {
      method: 'GET',
      headers
    })
    const data = await response.json()
    
    // 响应格式:
    // {
    //   "new_words": [...],
    //   "review_words": [...],
    //   "total_count": 10,
    //   "new_count": 3,
    //   "review_count": 7
    // }
    
    return data
  } catch (error) {
    console.error('获取学习会话失败:', error)
    throw error
  }
}
```

### 2. 添加单词到学习计划
```javascript
// POST /api/v1/learning/add/{entry_id}
async function addWordToLearning(entryId) {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/add/${entryId}`, {
      method: 'POST',
      headers
    })
    
    if (!response.ok) {
      throw new Error('添加单词失败')
    }
    
    return await response.json()
  } catch (error) {
    console.error('添加单词失败:', error)
    throw error
  }
}
```

### 3. 提交复习结果
```javascript
// POST /api/v1/learning/review/{entry_id}
async function submitReview(entryId, quality) {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/review/${entryId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ quality }) // quality: 0-5
    })
    
    if (!response.ok) {
      throw new Error('提交复习失败')
    }
    
    return await response.json()
  } catch (error) {
    console.error('提交复习失败:', error)
    throw error
  }
}
```

### 4. 获取深度解析提示
```javascript
// GET /api/v1/learning/insight/{entry_id}
async function getInsightHint(entryId) {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/insight/${entryId}`, {
      method: 'GET',
      headers
    })
    
    const data = await response.json()
    
    // 响应格式:
    // {
    //   "insight": "深度解析内容..."
    // }
    
    return data
  } catch (error) {
    console.error('获取提示失败:', error)
    throw error
  }
}
```

### 5. AI生成例句
```javascript
// POST /api/v1/learning/generate-example/{entry_id}
async function generateExample(entryId) {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/generate-example/${entryId}`, {
      method: 'POST',
      headers
    })
    
    const data = await response.json()
    
    // 响应格式:
    // {
    //   "sentence": "德语例句",
    //   "translation": "中文翻译"
    // }
    
    return data
  } catch (error) {
    console.error('生成例句失败:', error)
    throw error
  }
}
```

### 6. AI生成智能题目
```javascript
// POST /api/v1/learning/generate-quiz/{entry_id}
async function generateQuiz(entryId) {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/generate-quiz/${entryId}`, {
      method: 'POST',
      headers
    })
    
    const data = await response.json()
    
    // 响应格式:
    // {
    //   "question": "题目文本____",
    //   "options": ["选项A", "选项B", "选项C", "选项D"],
    //   "answer": "正确选项"
    // }
    
    return data
  } catch (error) {
    console.error('生成题目失败:', error)
    throw error
  }
}
```

### 7. 获取学习统计
```javascript
// GET /api/v1/learning/stats
async function getLearningStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/learning/stats`, {
      method: 'GET',
      headers
    })
    
    const data = await response.json()
    
    // 响应格式:
    // {
    //   "total_words": 150,
    //   "learned_today": 10,
    //   "reviewed_today": 25,
    //   "streak_days": 7,
    //   "mastery_distribution": {
    //     "new": 20,
    //     "learning": 80,
    //     "review": 40,
    //     "mature": 10
    //   }
    // }
    
    return data
  } catch (error) {
    console.error('获取统计失败:', error)
    throw error
  }
}
```

## 🎨 UI组件设计

### 1. 学习会话组件
```jsx
// LearningSession.jsx
import React, { useState, useEffect } from 'react'

const LearningSession = () => {
  const [session, setSession] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadLearningSession()
  }, [])

  const loadLearningSession = async () => {
    try {
      const data = await getLearningSession()
      setSession(data)
    } catch (error) {
      // 错误处理
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>加载中...</div>
  if (!session || session.total_count === 0) return <div>今日学习已完成！</div>

  const currentWord = session.new_words.length > 0 
    ? session.new_words[0] 
    : session.review_words[currentIndex - session.new_words.length]

  return (
    <div className="learning-session">
      <ProgressIndicator 
        current={currentIndex + 1}
        total={session.total_count}
        newCount={session.new_count}
      />
      <WordCard word={currentWord} />
    </div>
  )
}
```

### 2. 单词卡片组件
```jsx
// WordCard.jsx
const WordCard = ({ word }) => {
  const [isFlipped, setIsFlipped] = useState(false)
  const [showInsight, setShowInsight] = useState(false)
  const [insight, setInsight] = useState(null)

  const handleForget = async () => {
    // 显示深度解析提示
    if (!insight) {
      const data = await getInsightHint(word.id)
      setInsight(data.insight)
    }
    setShowInsight(true)
  }

  const handleQualityRating = async (quality) => {
    await submitReview(word.id, quality)
    // 移动到下一个单词
  }

  return (
    <div className={`word-card ${isFlipped ? 'flipped' : ''}`}>
      {!showInsight ? (
        <div className="card-front">
          <h2>{word.word}</h2>
          <div className="word-type">{word.word_type}</div>
          <button onClick={() => setIsFlipped(true)}>查看答案</button>
          <button onClick={handleForget}>忘记了</button>
        </div>
      ) : (
        <div className="insight-view">
          <h3>深度解析</h3>
          <p>{insight}</p>
          <button onClick={() => setShowInsight(false)}>继续</button>
        </div>
      )}
      
      {isFlipped && !showInsight && (
        <div className="card-back">
          <h3>{word.translation}</h3>
          <p>{word.definition}</p>
          <QualityRating onSelect={handleQualityRating} />
        </div>
      )}
    </div>
  )
}
```

### 3. 质量评分组件
```jsx
// QualityRating.jsx
const QualityRating = ({ onSelect }) => {
  const options = [
    { value: 0, label: '完全忘记', color: '#ff4444' },
    { value: 1, label: '忘记', color: '#ff6644' },
    { value: 2, label: '困难', color: '#ffaa44' },
    { value: 3, label: '掌握', color: '#44ff44' },
    { value: 4, label: '容易', color: '#44ffaa' },
    { value: 5, label: '太简单', color: '#44ffff' }
  ]

  return (
    <div className="quality-rating">
      <p>记忆程度如何？</p>
      <div className="rating-buttons">
        {options.map(option => (
          <button
            key={option.value}
            onClick={() => onSelect(option.value)}
            style={{ backgroundColor: option.color }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
```

## 🔄 学习流程设计

### 1. 主学习流程
```
开始学习 → 获取会话 → 显示单词 → 用户交互 → 评分 → 更新进度 → 下一个单词
```

### 2. "二次机会"流程
```
用户点击"忘记了" → 显示深度解析 → 用户回忆 → 再次评分 → 区分处理
```

### 3. AI增强流程
```
显示单词 → 请求AI例句 → 显示例句 → 请求AI题目 → 显示题目 → 用户答题
```

## 📊 数据状态管理

### Redux Store结构
```javascript
const learningSlice = createSlice({
  name: 'learning',
  initialState: {
    currentSession: null,
    currentIndex: 0,
    stats: null,
    loading: false,
    error: null
  },
  reducers: {
    setSession: (state, action) => {
      state.currentSession = action.payload
    },
    nextWord: (state) => {
      state.currentIndex += 1
    },
    updateStats: (state, action) => {
      state.stats = action.payload
    }
  }
})
```

### 本地存储
```javascript
// 保存学习进度
const saveProgress = (progress) => {
  localStorage.setItem('learningProgress', JSON.stringify(progress))
}

// 恢复学习进度
const loadProgress = () => {
  const saved = localStorage.getItem('learningProgress')
  return saved ? JSON.parse(saved) : null
}
```

## 🎯 最佳实践

### 1. 错误处理
- 网络请求失败时显示友好的错误信息
- 提供重试机制
- 记录错误日志用于调试

### 2. 性能优化
- 预加载下一个单词的内容
- 缓存AI生成的内容
- 使用虚拟滚动处理长列表

### 3. 用户体验
- 添加键盘快捷键支持
- 提供学习进度动画
- 实现离线学习模式

### 4. 响应式设计
- 适配移动端和桌面端
- 优化触摸交互
- 考虑不同屏幕尺寸

## 🧪 测试建议

### 1. 单元测试
```javascript
// 测试API调用
describe('Learning API', () => {
  test('should get learning session', async () => {
    const data = await getLearningSession()
    expect(data).toHaveProperty('new_words')
    expect(data).toHaveProperty('review_words')
  })
})
```

### 2. 集成测试
- 测试完整的学习流程
- 测试错误处理机制
- 测试组件交互

### 3. E2E测试
- 使用Cypress测试完整用户旅程
- 测试不同学习模式
- 测试AI功能集成

## 🚀 部署注意事项

### 1. 环境配置
```javascript
const config = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api/v1'
  },
  production: {
    API_BASE_URL: 'https://api.de-ai-hilfer.com/api/v1'
  }
}
```

### 2. 构建优化
- 代码分割减少初始加载时间
- 图片压缩和懒加载
- 使用CDN加速静态资源

## 📱 移动端特殊考虑

### 1. 触摸交互
- 滑动翻页
- 长按显示菜单
- 手势识别

### 2. 离线支持
- Service Worker缓存
- 本地数据库存储
- 同步机制

### 3. 推送通知
- 学习提醒
- 成就通知
- 复习提醒

---

## 📞 技术支持

如果在集成过程中遇到问题，请：
1. 检查API文档确认接口格式
2. 查看浏览器控制台错误信息
3. 联系后端开发团队
4. 参考项目GitHub Issues

**文档维护**: 本文档将随API更新而同步更新，请定期检查最新版本。
