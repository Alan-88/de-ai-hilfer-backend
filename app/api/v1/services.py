"""
API服务层：包含业务逻辑和辅助函数
"""

import json
import re
import traceback
from typing import Deque, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from ai_adapter.llm_router import LLMRouter
from app.core.errors import ErrorMessages
from app.core.llm_service import (
    call_llm_service,
    get_or_create_knowledge_entry,
)
from app.core.performance import (
    monitor_performance,
    record_cache_hit,
    record_cache_miss,
)
from app.db import models
from app.schemas.dictionary import (
    AnalyzeRequest,
    AnalyzeResponse,
    DBSuggestion,
    FollowUpItem,
    RecentItem,
    EntryType, # 导入新的枚举
)

# =================================================================================
# 性能优化：缓存和查询优化
# =================================================================================

# 全局缓存字典，用于存储预览文本的缓存
_preview_cache: Dict[str, str] = {}
_max_cache_size = 1000  # 最大缓存条目数


@monitor_performance("get_cached_preview")
def get_cached_preview(analysis_markdown: str) -> str:
    """获取缓存的预览文本，如果不存在则计算并缓存"""
    if analysis_markdown in _preview_cache:
        record_cache_hit("preview_cache")
        return _preview_cache[analysis_markdown]

    record_cache_miss("preview_cache")

    # 如果缓存过大，清理一半
    if len(_preview_cache) > _max_cache_size:
        keys_to_remove = list(_preview_cache.keys())[: _max_cache_size // 2]
        for key in keys_to_remove:
            del _preview_cache[key]

    # 计算并缓存预览
    preview = get_preview_from_analysis(analysis_markdown)
    _preview_cache[analysis_markdown] = preview
    return preview


def optimize_query_with_cache(db: Session, query_text: str) -> Optional[models.KnowledgeEntry]:
    """优化的查询函数，使用更高效的查询方式"""
    # 使用更高效的查询，避免不必要的joinedload
    entry = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.query_text == query_text)
        .first()
    )

    if entry:
        # 只有在需要时才加载follow_ups
        if hasattr(entry, "_follow_ups_loaded"):
            return entry
        # 延迟加载follow_ups
        db.refresh(entry, ["follow_ups"])
        entry._follow_ups_loaded = True

    return entry


def batch_get_entries_by_ids(db: Session, entry_ids: List[int]) -> Dict[int, models.KnowledgeEntry]:
    """批量获取条目，减少数据库查询次数"""
    if not entry_ids:
        return {}

    entries = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id.in_(entry_ids)).all()

    return {entry.id: entry for entry in entries}


# =================================================================================
# 1. 核心辅助函数 (Helper Functions)
# =================================================================================


def infer_entry_type(query: str) -> EntryType:
    """
    智能推断条目类型（单词、前缀、后缀）。
    
    Args:
        query (str): 用户输入的查询文本
        
    Returns:
        EntryType: 推断出的条目类型
    """
    clean_query = query.strip('-')
    if query.endswith('-') and len(clean_query) > 0:
        return EntryType.PREFIX
    elif query.startswith('-') and len(clean_query) > 0:
        return EntryType.SUFFIX
    else:
        return EntryType.WORD  # 默认为单词


# =================================================================================
# 2. 核心辅助函数 (Helper Functions)
# =================================================================================


def get_preview_from_analysis(analysis: str) -> str:
    """
    【V3.8 智能感知版】从完整的Markdown分析中智能提取预览。
    能够区分单词和词缀，并为它们生成合适的预览。
    """
    try:
        # 方案1: 尝试匹配词缀格式 (通过关键词: Präfix, Suffix 等)
        # 格式示例: * **Präfix/Vorsilbe** **核心含义...**
        affix_pattern = r"\*\s*\*\*(Präfix|Suffix|Vorsilbe|Nachsilbe)[^ ]*\*\*\s*\*\*(.*?)\*\*"
        affix_match = re.search(affix_pattern, analysis, re.IGNORECASE)
        if affix_match:
            # 提取类型和核心含义
            affix_type = affix_match.group(1).strip()
            affix_meaning = affix_match.group(2).strip().split("\n")[0]
            # 返回一个简洁、专门为词缀设计的预览
            preview = f"{affix_type}: {affix_meaning}"
            return (preview[:70] + "...") if len(preview) > 70 else preview

        # 方案2: 如果不是词缀，则回退到单词格式匹配
        # 在 "核心释义" 区域内查找
        bedeutung_match = re.search(
            r"#### 核心释义 \(Bedeutung\)(.*?)####", analysis, re.DOTALL | re.IGNORECASE
        )
        search_area = bedeutung_match.group(1) if bedeutung_match else analysis
        
        # 匹配 `* **词性.** **释义**` 格式
        pos_pattern = r"([a-z\./]+)\.?"
        standard_pattern = r"\*\s*\*\*" + pos_pattern + r"\*\*\s*\*\*(.*?)\*\*"
        matches = re.findall(standard_pattern, search_area, re.IGNORECASE)
        
        if matches:
            preview_parts = []
            for pos, definition in matches:
                clean_pos = pos.strip().rstrip('.') + "."
                clean_def = definition.strip().split("\n")[0]
                preview_parts.append(f"{clean_pos} {clean_def}")
            return "; ".join(preview_parts)

    except Exception as e:
        print(f"--- {ErrorMessages.PREVIEW_EXTRACTION_ERROR.format(error=e)} ---")
        pass

    # 方案3: 通用备用方案，适用于任何未知格式
    # 移除Markdown标题和星号，取第一行有效内容
    lines = analysis.strip().split('\n')
    for line in lines:
        clean_line = line.strip('#* /').strip()
        if clean_line:
            return (clean_line[:70] + "...") if len(clean_line) > 70 else clean_line
    
    # 如果完全为空，返回一个默认值
    return "无法生成预览"


def check_exact_cache_match(query: str, db: Session) -> Optional[models.KnowledgeEntry]:
    """
    检查精确缓存匹配（知识条目表和别名表）
    """
    # 1. 检查知识条目表
    entry = (
        db.query(models.KnowledgeEntry)
        .options(joinedload(models.KnowledgeEntry.follow_ups))
        .filter(models.KnowledgeEntry.query_text == query)
        .first()
    )
    if entry:
        return entry

    # 2. 检查别名表
    alias = (
        db.query(models.EntryAlias)
        .options(joinedload(models.EntryAlias.entry).joinedload(models.KnowledgeEntry.follow_ups))
        .filter(models.EntryAlias.alias_text == query)
        .first()
    )
    if alias and alias.entry:
        return alias.entry

    return None


async def perform_spell_check(query: str, llm_router: LLMRouter) -> tuple[bool, Optional[str]]:
    """
    执行拼写检查，返回(是否拼写正确, 建议)
    """
    spell_checker_prompt = llm_router.config.spell_checker_prompt
    response_text = await call_llm_service(llm_router, spell_checker_prompt, query)

    try:
        spell_data = json.loads(response_text)
        is_correctly_spelled = spell_data.get("is_correct", True)
        suggestion = spell_data.get("suggestion")
        return is_correctly_spelled, suggestion
    except (json.JSONDecodeError, KeyError):
        print(f"--- {ErrorMessages.SPELL_CHECK_WARNING.format(query=query)} ---")
        return True, None


async def identify_prototype_word(query: str, llm_router: LLMRouter) -> str:
    """
    识别原型单词，返回原型词
    """
    identification_prompt = llm_router.config.prototype_identification_prompt
    prototype_response_text = await call_llm_service(
        llm_router, identification_prompt, query, use_tools=False
    )

    prototype_word = query
    try:
        cleaned_text = re.search(r"\{.*\}", prototype_response_text, re.DOTALL)
        prototype_data = json.loads(cleaned_text.group(0) if cleaned_text else "{}")
        prototype_word = prototype_data.get("prototype", query)
    except (json.JSONDecodeError, AttributeError):
        error_msg = ErrorMessages.PROTOTYPE_JSON_ERROR.format(
            prototype_response_text=prototype_response_text
        )
        print(f"--- {error_msg} ---")

    return prototype_word


def create_alias_if_needed(query: str, target_word: str, entry_id: int, db: Session) -> None:
    """
    如果需要，为查询词创建别名
    """
    if query.lower() != target_word.lower():
        existing_alias = (
            db.query(models.EntryAlias).filter(models.EntryAlias.alias_text == query).first()
        )
        if not existing_alias:
            print(f"--- [信息] 为 '{query}' 创建指向 '{target_word}' 的别名。")
            new_alias = models.EntryAlias(alias_text=query, entry_id=entry_id)
            db.add(new_alias)
            db.commit()


def update_recent_searches(query: str, recent_searches: Deque[str]) -> None:
    """
    更新最近搜索列表
    """
    if query in recent_searches:
        recent_searches.remove(query)
    recent_searches.appendleft(query)


# =================================================================================
# 2. 数据库服务函数 (Database Service Functions)
# =================================================================================


@monitor_performance("get_recent_entries_service")
def get_recent_entries_service(db: Session, recent_searches: Deque[str]) -> list[RecentItem]:
    """
    获取最近成功查询的知识条目列表，包含预览。
    性能优化：使用批量查询和缓存预览。
    """
    if not recent_searches:
        return []

    # 批量查询所有需要的条目
    entries = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.query_text.in_(list(recent_searches)))
        .all()
    )

    # 创建查询到条目的映射
    entry_map = {entry.query_text: entry for entry in entries}

    recent_items = []
    for query in recent_searches:
        entry = entry_map.get(query)
        if entry:
            # 使用缓存的预览
            recent_items.append(
                RecentItem(
                    query_text=entry.query_text,
                    preview=get_cached_preview(entry.analysis_markdown),
                )
            )

    return recent_items


@monitor_performance("get_all_entries_service")
def get_all_entries_service(db: Session) -> list[RecentItem]:
    """
    获取知识库中的所有条目，按字母顺序排序，并包含预览。
    性能优化：使用缓存预览和批量处理。
    """
    # 只查询必要的字段，减少内存使用
    all_entries = (
        db.query(
            models.KnowledgeEntry.id,
            models.KnowledgeEntry.query_text,
            models.KnowledgeEntry.analysis_markdown,
        )
        .order_by(models.KnowledgeEntry.query_text.asc())
        .all()
    )

    response_items = []
    for entry in all_entries:
        response_items.append(
            RecentItem(
                entry_id=entry.id,
                query_text=entry.query_text,
                preview=get_cached_preview(entry.analysis_markdown),
            )
        )
    return response_items


@monitor_performance("get_suggestions_service")
def get_suggestions_service(q: str, db: Session) -> list[DBSuggestion]:
    """
    【V3.4 词缀感知版】优化的建议查询。
    - 如果输入是词缀 (如 'ver-' 或 '-keit')，则同时返回词缀本身和包含该词缀的单词。
    - 否则，执行常规的别名和单词查询。
    """
    query = q.strip()
    if not query or len(query) < 2:
        return []

    suggestion_items = []
    processed_entry_ids = set()

    # =====================================================================
    # 1. 新增：词缀查询的专属处理逻辑
    # =====================================================================
    # 使用统一的推断逻辑确定条目类型
    entry_type = infer_entry_type(query)
    
    if entry_type in [EntryType.PREFIX, EntryType.SUFFIX]:
        clean_query = query.strip('-')
        is_prefix = entry_type == EntryType.PREFIX
        is_suffix = entry_type == EntryType.SUFFIX
        # 步骤 A: 精确查找词缀条目本身，并置于列表顶部
        affix_entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.query_text == query).first()
        if affix_entry:
            suggestion_items.append(
                DBSuggestion(
                    entry_id=affix_entry.id,
                    query_text=affix_entry.query_text,
                    preview=get_cached_preview(affix_entry.analysis_markdown),
                    analysis_markdown=affix_entry.analysis_markdown,
                    source="知识库",
                    follow_ups=[],  # 稍后批量加载
                )
            )
            processed_entry_ids.add(affix_entry.id)

        # 步骤 B: 模糊查找包含该词缀的单词作为示例
        if is_prefix:
            pattern = f"{clean_query}%"
        else:  # is_suffix
            pattern = f"%{clean_query}"
        
        # 只查找单词类型的条目作为示例
        example_words = (
            db.query(models.KnowledgeEntry)
            .filter(
                models.KnowledgeEntry.query_text.ilike(pattern),
                models.KnowledgeEntry.id.notin_(processed_entry_ids),
                models.KnowledgeEntry.entry_type == 'WORD' 
            )
            .limit(10)
            .all()
        )

        for word in example_words:
            suggestion_items.append(
                DBSuggestion(
                    entry_id=word.id,
                    query_text=word.query_text,
                    preview=get_cached_preview(word.analysis_markdown),
                    analysis_markdown=word.analysis_markdown,
                    source="知识库",
                    follow_ups=[], # 稍后批量加载
                )
            )
            processed_entry_ids.add(word.id)

    # =====================================================================
    # 2. 保留：常规单词和别名的查询逻辑
    # =====================================================================
    else:
        # 步骤 A: 模糊查询别名
        alias_query = (
            db.query(
                models.EntryAlias.alias_text,
                models.KnowledgeEntry.query_text,
                models.KnowledgeEntry.analysis_markdown,
                models.KnowledgeEntry.id.label("entry_id"),
            )
            .join(models.KnowledgeEntry, models.EntryAlias.entry_id == models.KnowledgeEntry.id)
            .filter(
                models.EntryAlias.alias_text.ilike(f"{query}%"),
                models.EntryAlias.entry_id.notin_(processed_entry_ids)
            )
            .limit(5)
            .all()
        )
        for alias_data in alias_query:
            if alias_data.entry_id not in processed_entry_ids:
                preview = f"↪️ {alias_data.alias_text} → {get_cached_preview(alias_data.analysis_markdown)}"
                suggestion_items.append(
                    DBSuggestion(
                        entry_id=alias_data.entry_id,
                        query_text=alias_data.query_text,
                        preview=preview,
                        analysis_markdown=alias_data.analysis_markdown,
                        source="知识库",
                        follow_ups=[],
                    )
                )
                processed_entry_ids.add(alias_data.entry_id)

        # 步骤 B: 模糊查询知识条目
        entry_query = (
            db.query(models.KnowledgeEntry)
            .filter(
                models.KnowledgeEntry.query_text.ilike(f"{query}%"),
                models.KnowledgeEntry.id.notin_(processed_entry_ids),
            )
            .limit(10)
            .all()
        )
        for entry_data in entry_query:
            if entry_data.id not in processed_entry_ids:
                suggestion_items.append(
                    DBSuggestion(
                        entry_id=entry_data.id,
                        query_text=entry_data.query_text,
                        preview=get_cached_preview(entry_data.analysis_markdown),
                        analysis_markdown=entry_data.analysis_markdown,
                        source="知识库",
                        follow_ups=[],
                    )
                )
                processed_entry_ids.add(entry_data.id)

    # =====================================================================
    # 3. 统一处理：为所有建议批量加载追问信息（性能优化）
    # =====================================================================
    entry_ids_to_load = {s.entry_id for s in suggestion_items}
    if entry_ids_to_load:
        follow_ups_query = (
            db.query(models.FollowUp).filter(models.FollowUp.entry_id.in_(entry_ids_to_load)).all()
        )
        follow_ups_map = {}
        for fu in follow_ups_query:
            if fu.entry_id not in follow_ups_map:
                follow_ups_map[fu.entry_id] = []
            follow_ups_map[fu.entry_id].append(FollowUpItem.model_validate(fu))
        
        for suggestion in suggestion_items:
            suggestion.follow_ups = follow_ups_map.get(suggestion.entry_id, [])

    return suggestion_items


# =================================================================================
# 3. 核心分析函数 (Core Analysis Functions)
# =================================================================================


async def analyze_entry_service(
    request: AnalyzeRequest,
    llm_router: LLMRouter,
    db: Session,
    recent_searches: Deque[str],
) -> AnalyzeResponse:
    """
    【V2 - 统一版】分析德语条目（包括单词、词缀等），提供详细的语法和语义分析。
    """
    query = request.query_text.strip()
    
    # 使用智能推断逻辑确定条目类型（如果用户没有明确指定）
    entry_type = request.entry_type if request.entry_type else infer_entry_type(query)

    try:
        # 1. 精确缓存检查 (所有类型的条目共用)
        entry = check_exact_cache_match(query, db)
        if entry:
            update_recent_searches(entry.query_text, recent_searches)
            return AnalyzeResponse(
                entry_id=entry.id,
                query_text=entry.query_text,
                analysis_markdown=entry.analysis_markdown,
                source="知识库",
                follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups],
            )

        # 2. 根据条目类型，执行不同的处理逻辑
        # ============ 词缀处理逻辑 (PREFIX/SUFFIX) ============
        if entry_type in [EntryType.PREFIX, EntryType.SUFFIX]:
            print(f"--- [信息] 检测到词缀分析请求: '{query}' ({entry_type})。")
            
            # 为词缀选择专用的提示词
            analysis_prompt = llm_router.config.affix_analysis_prompt
            
            # 【核心】复用 get_or_create_knowledge_entry，但传入不同的提示词
            entry = await get_or_create_knowledge_entry(
                query, request, llm_router, db, analysis_prompt
            )

        # ============ 单词处理逻辑 (WORD/PHRASE) ============
        else:
            # 2.1. 缓存未命中，先进行拼写检查
            is_correctly_spelled, suggestion = await perform_spell_check(query, llm_router)
            target_word = query
            should_create_alias = False

            # 2.2. 根据拼写检查结果进行决策
            if not is_correctly_spelled and suggestion:
                print(f"--- [信息] 检测到拼写错误，将 '{query}' 修正为 '{suggestion}'。")
                target_word = suggestion
                should_create_alias = False
            else:
                prototype_word = await identify_prototype_word(query, llm_router)
                if query.lower() != prototype_word.lower():
                    print(f"--- [信息] 检测到单词变体，将 '{query}' 的原型识别为 '{prototype_word}'。")
                    target_word = prototype_word
                    should_create_alias = True

            # 2.3. 执行数据库操作 (使用单词分析的提示词)
            analysis_prompt = llm_router.config.analysis_prompt
            entry = await get_or_create_knowledge_entry(
                target_word, request, llm_router, db, analysis_prompt
            )

            # 2.4. 如果需要，创建别名
            if should_create_alias:
                create_alias_if_needed(query, target_word, entry.id, db)

        # 3. 统一返回结果
        update_recent_searches(entry.query_text, recent_searches)
        return AnalyzeResponse(
            entry_id=entry.id,
            query_text=entry.query_text,
            analysis_markdown=entry.analysis_markdown,
            source="generated",
            follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups],
        )

    except Exception as e:
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"分析时发生内部错误: {e}")
