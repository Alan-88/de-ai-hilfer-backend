"""
服务层测试
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from collections import deque

from app.api.v1.services import (
    get_preview_from_analysis,
    check_exact_cache_match,
    perform_spell_check,
    identify_prototype_word,
    create_alias_if_needed,
    update_recent_searches,
    get_recent_entries_service,
    get_all_entries_service,
    get_suggestions_service,
    analyze_entry_service,
    get_cached_preview,
    optimize_query_with_cache,
    batch_get_entries_by_ids
)
from app.core.llm_service import get_cached_vocabulary
from app.db.models import KnowledgeEntry, EntryAlias, FollowUp
from app.schemas.dictionary import AnalyzeRequest
from ai_adapter.llm_router import LLMRouter


class TestHelperFunctions:
    """辅助函数测试"""
    
    def test_get_preview_from_analysis_standard_format(self):
        """测试从标准格式分析中提取预览"""
        analysis = """# Haus

## 核心释义 (Bedeutung)

* **n.** **房子** - 建筑物
* **n.** **家庭** - 住在同一房子里的人

## 其他信息

这是一个常用词。"""
        
        preview = get_preview_from_analysis(analysis)
        assert "n. 房子" in preview
        assert "n. 家庭" in preview
    
    def test_get_preview_from_analysis_no_standard_format(self):
        """测试从无标准格式分析中提取预览"""
        analysis = "# Haus\n\n这是一个德语单词，意思是房子。"
        
        preview = get_preview_from_analysis(analysis)
        assert preview == "Haus\n\n这是一个德语单词，意思是房子。"
    
    def test_get_preview_from_analysis_long_text(self):
        """测试长文本预览截取"""
        analysis = "# Haus\n\n" + "A" * 100
        
        preview = get_preview_from_analysis(analysis)
        assert len(preview) <= 43  # 40 + "..."
        assert preview.endswith("...")
    
    def test_update_recent_searches(self):
        """测试更新最近搜索"""
        recent_searches = deque(["word1", "word2"], maxlen=5)
        
        # 添加新词
        update_recent_searches("word3", recent_searches)
        assert list(recent_searches) == ["word3", "word1", "word2"]
        
        # 添加已存在的词
        update_recent_searches("word1", recent_searches)
        assert list(recent_searches) == ["word1", "word3", "word2"]
    
    def test_create_alias_if_needed(self, db_session: Session):
        """测试创建别名"""
        # 创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 需要创建别名
        create_alias_if_needed("das Haus", "Haus", entry.id, db_session)
        
        # 验证别名创建
        alias = db_session.query(EntryAlias).filter_by(alias_text="das Haus").first()
        assert alias is not None
        assert alias.entry_id == entry.id
        
        # 不需要创建别名（相同文本）
        create_alias_if_needed("Haus", "Haus", entry.id, db_session)
        
        # 验证没有创建重复别名
        aliases = db_session.query(EntryAlias).filter_by(entry_id=entry.id).all()
        assert len(aliases) == 1


class TestCacheFunctions:
    """缓存函数测试"""
    
    def test_get_cached_preview_first_time(self):
        """测试首次获取预览（缓存未命中）"""
        analysis = "# Haus\n\n**词性**: Nomen"
        
        preview = get_cached_preview(analysis)
        assert preview == "Haus\n\n**词性**: Nomen"
    
    def test_get_cached_preview_cached(self):
        """测试缓存命中"""
        import app.api.v1.services as services_module
        analysis = "# Haus\n\n**词性**: Nomen"
        
        # 预填充缓存 - 直接操作模块变量
        services_module._preview_cache[analysis] = "cached preview"
        
        preview = get_cached_preview(analysis)
        assert preview == "cached preview"
    
    def test_get_cached_preview_cache_cleanup(self):
        """测试缓存清理"""
        import app.api.v1.services as services_module
        
        # 填满缓存
        for i in range(1001):
            services_module._preview_cache[f"analysis_{i}"] = f"preview_{i}"
        
        # 触发清理
        get_cached_preview("new_analysis")
        
        # 验证缓存大小
        assert len(services_module._preview_cache) <= 1000
        assert "new_analysis" in services_module._preview_cache
    
    def test_optimize_query_with_cache(self, db_session: Session):
        """测试优化查询"""
        # 创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 查询
        result = optimize_query_with_cache(db_session, "Haus")
        
        assert result is not None
        assert result.query_text == "Haus"
    
    def test_batch_get_entries_by_ids(self, db_session: Session):
        """测试批量获取条目"""
        # 创建多个条目
        entries = []
        for i in range(3):
            entry = KnowledgeEntry(
                query_text=f"word{i}",
                entry_type="WORD",
                analysis_markdown=f"# word{i}"
            )
            db_session.add(entry)
            entries.append(entry)
        db_session.commit()
        
        # 刷新获取ID
        for entry in entries:
            db_session.refresh(entry)
        
        entry_ids = [entry.id for entry in entries]
        result = batch_get_entries_by_ids(db_session, entry_ids)
        
        assert len(result) == 3
        for entry_id in entry_ids:
            assert entry_id in result
            assert result[entry_id].query_text.startswith("word")


class TestDatabaseServiceFunctions:
    """数据库服务函数测试"""
    
    def test_get_recent_entries_service_empty(self, db_session: Session):
        """测试获取空最近条目"""
        recent_searches = deque()
        
        result = get_recent_entries_service(db_session, recent_searches)
        assert result == []
    
    def test_get_recent_entries_service_with_data(self, db_session: Session):
        """测试获取有数据的最近条目"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        
        recent_searches = deque(["Haus"])
        
        result = get_recent_entries_service(db_session, recent_searches)
        
        assert len(result) == 1
        assert result[0].query_text == "Haus"
        assert result[0].preview == "Haus\n\n**词性**: Nomen"
    
    def test_get_all_entries_service(self, db_session: Session):
        """测试获取所有条目"""
        # 创建多个条目
        for i in range(3):
            entry = KnowledgeEntry(
                query_text=f"word{i}",
                entry_type="WORD",
                analysis_markdown=f"# word{i}"
            )
            db_session.add(entry)
        db_session.commit()
        
        result = get_all_entries_service(db_session)
        
        assert len(result) == 3
        query_texts = [item.query_text for item in result]
        assert "word0" in query_texts
        assert "word1" in query_texts
        assert "word2" in query_texts
        
        # 验证排序
        assert query_texts == sorted(query_texts)
    
    def test_get_suggestions_service_empty_query(self, db_session: Session):
        """测试空查询的建议"""
        result = get_suggestions_service("", db_session)
        assert result == []
        
        result = get_suggestions_service("   ", db_session)
        assert result == []
    
    def test_get_suggestions_service_with_aliases(self, db_session: Session):
        """测试包含别名的建议"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        db_session.add(alias)
        db_session.commit()
        
        result = get_suggestions_service("das", db_session)
        
        assert len(result) >= 1
        assert result[0].query_text == "Haus"
        assert "↪️ das Haus" in result[0].preview
    
    def test_get_suggestions_service_with_entries(self, db_session: Session):
        """测试条目建议"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        
        result = get_suggestions_service("Ha", db_session)
        
        assert len(result) >= 1
        assert result[0].query_text == "Haus"
        assert result[0].source == "知识库"


class TestAnalysisService:
    """分析服务测试"""
    
    def test_check_exact_cache_match_entry(self, db_session: Session):
        """测试精确缓存匹配（条目）"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        
        result = check_exact_cache_match("Haus", db_session)
        
        assert result is not None
        assert result.query_text == "Haus"
    
    def test_check_exact_cache_match_alias(self, db_session: Session):
        """测试精确缓存匹配（别名）"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        db_session.add(alias)
        db_session.commit()
        
        result = check_exact_cache_match("das Haus", db_session)
        
        assert result is not None
        assert result.query_text == "Haus"
    
    def test_check_exact_cache_match_not_found(self, db_session: Session):
        """测试精确缓存匹配（未找到）"""
        result = check_exact_cache_match("nonexistent", db_session)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_perform_spell_check_success(self):
        """测试拼写检查成功"""
        mock_llm_router = Mock()
        mock_llm_router.config.spell_checker_prompt = "spell check prompt"
        
        with patch('app.api.v1.services.call_llm_service') as mock_call:
            mock_call.return_value = '{"is_correct": true, "suggestion": null}'
            
            is_correct, suggestion = await perform_spell_check("Haus", mock_llm_router)
            
            assert is_correct is True
            assert suggestion is None
    
    @pytest.mark.asyncio
    async def test_perform_spell_check_correction(self):
        """测试拼写检查修正"""
        mock_llm_router = Mock()
        mock_llm_router.config.spell_checker_prompt = "spell check prompt"
        
        with patch('app.api.v1.services.call_llm_service') as mock_call:
            mock_call.return_value = '{"is_correct": false, "suggestion": "Haus"}'
            
            is_correct, suggestion = await perform_spell_check("Haus", mock_llm_router)
            
            assert is_correct is False
            assert suggestion == "Haus"
    
    @pytest.mark.asyncio
    async def test_perform_spell_check_error(self):
        """测试拼写检查错误"""
        mock_llm_router = Mock()
        mock_llm_router.config.spell_checker_prompt = "spell check prompt"
        
        with patch('app.api.v1.services.call_llm_service') as mock_call:
            mock_call.return_value = "invalid json"
            
            is_correct, suggestion = await perform_spell_check("Haus", mock_llm_router)
            
            assert is_correct is True  # 默认值
            assert suggestion is None
    
    @pytest.mark.asyncio
    async def test_identify_prototype_word_success(self):
        """测试原型词识别成功"""
        mock_llm_router = Mock()
        mock_llm_router.config.prototype_identification_prompt = "prototype prompt"
        
        with patch('app.api.v1.services.call_llm_service') as mock_call:
            mock_call.return_value = '{"prototype": "Haus"}'
            
            prototype = await identify_prototype_word("Häuser", mock_llm_router)
            
            assert prototype == "Haus"
    
    @pytest.mark.asyncio
    async def test_identify_prototype_word_error(self):
        """测试原型词识别错误"""
        mock_llm_router = Mock()
        mock_llm_router.config.prototype_identification_prompt = "prototype prompt"
        
        with patch('app.api.v1.services.call_llm_service') as mock_call:
            mock_call.return_value = "invalid json"
            
            prototype = await identify_prototype_word("Häuser", mock_llm_router)
            
            assert prototype == "Häuser"  # 返回原词
    
    @pytest.mark.asyncio
    async def test_analyze_entry_service_cache_hit(self, db_session: Session):
        """测试分析条目服务（缓存命中）"""
        # 创建条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        
        # 创建后续问题
        follow_up = FollowUp(
            entry_id=entry.id,
            question="复数形式？",
            answer="Häuser"
        )
        db_session.add(follow_up)
        db_session.commit()
        
        request = AnalyzeRequest(query_text="Haus")
        recent_searches = deque()
        
        with patch('app.api.v1.services.get_llm_router') as mock_router:
            mock_llm_router = Mock()
            mock_router.return_value = mock_llm_router
            
            result = await analyze_entry_service(request, mock_llm_router, db_session, recent_searches)
            
            assert result.entry_id == entry.id
            assert result.query_text == "Haus"
            assert result.source == "知识库"
            assert len(result.follow_ups) == 1
            assert result.follow_ups[0].question == "复数形式？"
    
    @pytest.mark.asyncio
    async def test_analyze_entry_service_cache_miss(self, db_session: Session):
        """测试分析条目服务（缓存未命中）"""
        request = AnalyzeRequest(query_text="Haus")
        recent_searches = deque()
        
        with patch('app.api.v1.services.get_llm_router') as mock_router, \
             patch('app.api.v1.services.get_or_create_knowledge_entry') as mock_create:
            
            mock_llm_router = Mock()
            mock_router.return_value = mock_llm_router
            
            # 模拟创建的条目
            mock_entry = Mock()
            mock_entry.id = 1
            mock_entry.query_text = "Haus"
            mock_entry.analysis_markdown = "# Haus"
            mock_entry.follow_ups = []
            mock_create.return_value = mock_entry
            
            # 模拟拼写检查
            with patch('app.api.v1.services.perform_spell_check') as mock_spell, \
                 patch('app.api.v1.services.identify_prototype_word') as mock_prototype:
                
                mock_spell.return_value = (True, None)
                mock_prototype.return_value = "Haus"
                
                result = await analyze_entry_service(request, mock_llm_router, db_session, recent_searches)
                
                assert result.entry_id == 1
                assert result.query_text == "Haus"
                assert result.source == "generated"


class TestLLMVocabularyCache:
    """LLM词汇缓存测试"""
    
    def test_get_cached_vocabulary_first_time(self, db_session: Session):
        """测试首次获取词汇表（缓存未命中）"""
        # 创建测试数据
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        
        # 清除缓存
        import app.core.llm_service as llm_service
        llm_service._vocabulary_cache = None
        
        result = get_cached_vocabulary(db_session)
        
        assert result is not None
        assert "Haus" in result
        assert llm_service._vocabulary_cache is not None
        assert llm_service._vocabulary_cache[1] > 0  # timestamp > 0
    
    def test_get_cached_vocabulary_cache_hit(self, db_session: Session):
        """测试缓存命中"""
        import app.core.llm_service as llm_service
        
        # 预填充缓存
        cached_vocabulary = "Haus\nAuto\n"
        llm_service._vocabulary_cache = (cached_vocabulary, time.time())
        
        result = get_cached_vocabulary(db_session)
        
        assert result == cached_vocabulary
    
    def test_get_cached_vocabulary_cache_expired(self, db_session: Session):
        """测试缓存过期"""
        # 创建测试数据
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus"
        )
        db_session.add(entry)
        db_session.commit()
        
        import app.core.llm_service as llm_service
        
        # 设置过期的缓存
        llm_service._vocabulary_cache = ("old cache", time.time() - 4000)  # 超过1小时
        
        result = get_cached_vocabulary(db_session)
        
        assert result != "old cache"
        assert "Haus" in result
    
    def test_get_cached_vocabulary_empty_database(self, db_session: Session):
        """测试空数据库"""
        import app.core.llm_service as llm_service
        
        # 清除缓存
        llm_service._vocabulary_cache = None
        
        result = get_cached_vocabulary(db_session)
        
        assert result == ""


class TestServiceErrorHandling:
    """服务错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_entry_service_exception(self, db_session: Session):
        """测试分析条目服务异常处理"""
        request = AnalyzeRequest(query_text="Haus")
        recent_searches = deque()
        
        with patch('app.api.v1.services.get_llm_router') as mock_router:
            mock_llm_router = Mock()
            mock_llm_router.config.analysis_prompt = "analysis prompt"
            mock_router.return_value = mock_llm_router
            
            # 模拟异常
            with patch('app.api.v1.services.check_exact_cache_match', side_effect=Exception("测试异常")):
                with pytest.raises(Exception):
                    await analyze_entry_service(request, mock_llm_router, db_session, recent_searches)
