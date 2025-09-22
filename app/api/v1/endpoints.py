import os
import json
import re
import traceback
import datetime
import shutil
import sqlite3
from typing import Deque, List
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.state import get_recent_searches 
from app.core.llm_service import get_llm_router, call_llm_service, get_or_create_knowledge_entry
from app.schemas.dictionary import (
    RecentItem,
    AnalyzeRequest,
    AnalyzeResponse,
    SuggestionResponse,
    DBSuggestion,
    SpellCorrectionSuggestion,
    NewWordSuggestion,
    DatabaseImportRequest,
    IntelligentSearchRequest,
    AliasCreateRequest,
    FollowUpCreateRequest,
    FollowUpItem,
)
from ai_adapter.llm_router import LLMRouter
from app.db import models
from app.db.session import get_db

router = APIRouter()

# =================================================================================
# 1. 核心辅助函数 (Helper Functions)
# =================================================================================

def get_preview_from_analysis(analysis: str) -> str:
    """
    【V3.3 终极健壮版】从完整的Markdown分析中智能提取核心释义作为预览。
    能够兼容多种可能的格式，并保留词性。
    """
    try:
        # 策略 1: 匹配新版格式的列表项, e.g., "* **v.** **释义**"
        match = re.search(r"\*\s*\*\*(v\.|n\.|adj\.)\*\*\s*\*\*(.*?)\*\*", analysis, re.IGNORECASE)
        if match:
            pos = match.group(1)  # part of speech
            definition = match.group(2).strip()
            return f"{pos} {definition}"

        # 策略 2: 兼容旧格式的表格
        match = re.search(r"\|\s*\*\*核心释义\s*\(Bedeutung\)\*\*\s*\|\s*\*\*(v\.|n\.|adj\.)\*\*\s*\*\*(.*?)\*\*\s*\|", analysis, re.IGNORECASE)
        if match:
            pos = match.group(1)
            definition = match.group(2).strip()
            return f"{pos} {definition}"
        
        # 策略 3: 匹配不带粗体标记的列表项, e.g., "* v. 释义"
        match = re.search(r"^\s*\*\s*(v\.|n\.|adj\.)\s+(.*)", analysis, re.MULTILINE | re.IGNORECASE)
        if match:
            pos = match.group(1)
            definition = match.group(2).strip().split('\n')[0] # 取第一行
            return f"{pos} {definition}"

    except Exception as e:
        print(f"--- 预览提取时发生轻微错误: {e} ---")
        pass

    # 备用方案：截断文本
    fallback_preview = analysis.lstrip('#* /').strip()
    return (fallback_preview[:40] + '...') if len(fallback_preview) > 40 else fallback_preview

# =================================================================================
# 2. API 端点 (Endpoints)
# =================================================================================

@router.get("/entries/recent", response_model=List[RecentItem], tags=["Dictionary"])
def get_recent_entries(
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches)
):
    """
    获取最近成功查询的知识条目列表，包含预览。
    """
    recent_items = []
    # 遍历最近查询的单词列表
    for query in recent_searches:
        # 在数据库中查找对应的条目
        entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.query_text == query).first()
        if entry:
            # 如果找到，就创建并添加一个 RecentItem
            recent_items.append(
                RecentItem(
                    query_text=entry.query_text,
                    preview=get_preview_from_analysis(entry.analysis_markdown)
                )
            )
    
    return recent_items

@router.get("/entries/all", response_model=List[RecentItem], tags=["Dictionary"])
def get_all_entries(db: Session = Depends(get_db)):
    """
    获取知识库中的所有条目，按字母顺序排序，并包含预览。
    """
    all_entries = db.query(models.KnowledgeEntry).order_by(models.KnowledgeEntry.query_text.asc()).all()
    
    response_items = []
    for entry in all_entries:
        response_items.append(
            RecentItem(
                query_text=entry.query_text,
                preview=get_preview_from_analysis(entry.analysis_markdown)
            )
        )
    return response_items

@router.get("/suggestions", response_model=SuggestionResponse, tags=["Dictionary"])
def get_suggestions(q: str, db: Session = Depends(get_db)) -> SuggestionResponse: # <-- 【修改】恢复为同步函数，移除 AI 依赖
    """
    【V3.2 纯数据库版】只从数据库中进行模糊查询，返回匹配的建议。
    """
    if not q:
        return SuggestionResponse(suggestions=[])

    suggestion_items = []
    processed_entry_ids = set()

    # 1. 模糊查询别名
    aliases = db.query(models.EntryAlias).options(
        joinedload(models.EntryAlias.entry).joinedload(models.KnowledgeEntry.follow_ups)
    ).filter(models.EntryAlias.alias_text.ilike(f"{q}%")).limit(5).all()

    for alias in aliases:
        entry = alias.entry
        if entry and entry.id not in processed_entry_ids:
            suggestion_items.append(
                DBSuggestion( # <-- 【修改】使用 DBSuggestion 模型
                    entry_id=entry.id,
                    query_text=entry.query_text,
                    preview=f"↪️ {alias.alias_text} → {get_preview_from_analysis(entry.analysis_markdown)}",
                    analysis_markdown=entry.analysis_markdown,
                    source="知识库",
                    follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
                )
            )
            processed_entry_ids.add(entry.id)

    # 2. 模糊查询知识条目
    entries = db.query(models.KnowledgeEntry).options(joinedload(models.KnowledgeEntry.follow_ups)).filter(
        models.KnowledgeEntry.query_text.ilike(f"{q}%")
    ).limit(10).all()

    for entry in entries:
        if entry.id not in processed_entry_ids:
            suggestion_items.append(
                DBSuggestion( # <-- 【修改】使用 DBSuggestion 模型
                    entry_id=entry.id,
                    query_text=entry.query_text,
                    preview=get_preview_from_analysis(entry.analysis_markdown),
                    analysis_markdown=entry.analysis_markdown,
                    source="知识库",
                    follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
                )
            )
            processed_entry_ids.add(entry.id)
    
    return SuggestionResponse(suggestions=suggestion_items)

@router.post("/analyze", response_model=AnalyzeResponse, tags=["Dictionary"])
async def analyze_entry(
    request: AnalyzeRequest,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches)
) -> AnalyzeResponse:
    query = request.query_text.strip()
    
    def update_recents(text: str):
        if text in recent_searches:
            recent_searches.remove(text)
        recent_searches.appendleft(text)

    try:
        # 1. 精确缓存检查 (知识条目表和别名表)
        entry = db.query(models.KnowledgeEntry).options(joinedload(models.KnowledgeEntry.follow_ups)).filter(models.KnowledgeEntry.query_text == query).first()
        if entry:
            update_recents(entry.query_text)
            return AnalyzeResponse(
                entry_id=entry.id,
                query_text=entry.query_text,
                analysis_markdown=entry.analysis_markdown,
                source="知识库",
                follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
            )

        alias = db.query(models.EntryAlias).options(joinedload(models.EntryAlias.entry).joinedload(models.KnowledgeEntry.follow_ups)).filter(models.EntryAlias.alias_text == query).first()
        if alias and alias.entry:
            entry = alias.entry
            update_recents(entry.query_text)
            return AnalyzeResponse(
                entry_id=entry.id,
                query_text=entry.query_text,
                analysis_markdown=entry.analysis_markdown,
                source="知识库",
                follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
            )

        # 2. 【新增】缓存未命中，先进行拼写检查
        is_correctly_spelled = True
        suggestion = None
        target_word = query
        should_create_alias = False

        spell_checker_prompt = llm_router.config.spell_checker_prompt
        response_text = await call_llm_service(llm_router, spell_checker_prompt, query)
        
        try:
            spell_data = json.loads(response_text)
            is_correctly_spelled = spell_data.get("is_correct", True)
            suggestion = spell_data.get("suggestion")
        except (json.JSONDecodeError, KeyError):
            print(f"--- [警告] 拼写检查器返回格式不规范，将 '{query}' 视为一个拼写正确的词。")

        # 3. 根据拼写检查结果进行决策
        if not is_correctly_spelled and suggestion:
            # 情况 A: 这是一个拼写错误。
            # 目标词是修正后的词，且绝不创建别名。
            print(f"--- [信息] 检测到拼写错误，将 '{query}' 修正为 '{suggestion}'。")
            target_word = suggestion
            should_create_alias = False
        else:
            # 情况 B: 这是一个拼写正确的词。
            # 现在我们才需要检查它是不是一个变体。
            identification_prompt = llm_router.config.prototype_identification_prompt
            prototype_response_text = await call_llm_service(llm_router, identification_prompt, query, use_tools=False)
            
            prototype_word = query
            try:
                cleaned_text = re.search(r'\{.*\}', prototype_response_text, re.DOTALL)
                prototype_data = json.loads(cleaned_text.group(0) if cleaned_text else "{}")
                prototype_word = prototype_data.get("prototype", query)
            except (json.JSONDecodeError, AttributeError):
                print(f"--- 警告: AI返回的原型JSON格式错误: '{prototype_response_text}'。")

            if query.lower() != prototype_word.lower():
                # B.1: 是一个合法的单词变体 (如 "ging")。
                # 目标词是原型词，并且需要为原输入创建别名。
                print(f"--- [信息] 检测到单词变体，将 '{query}' 的原型识别为 '{prototype_word}'。")
                target_word = prototype_word
                should_create_alias = True
            # B.2: 本身就是原型词，无需任何操作。

        # 4. 执行数据库操作
        analysis_prompt = llm_router.config.analysis_prompt
        entry = await get_or_create_knowledge_entry(target_word, request, llm_router, db, analysis_prompt)

        if should_create_alias:
            existing_alias = db.query(models.EntryAlias).filter(models.EntryAlias.alias_text == query).first()
            if not existing_alias:
                print(f"--- [信息] 为 '{query}' 创建指向 '{target_word}' 的别名。")
                new_alias = models.EntryAlias(alias_text=query, entry_id=entry.id)
                db.add(new_alias)
                db.commit()
        
        update_recents(entry.query_text)
        return AnalyzeResponse(
            entry_id=entry.id,
            query_text=entry.query_text,
            analysis_markdown=entry.analysis_markdown,
            source="generated", # 这里的 source 是 "generated"
            follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
        )

    except Exception as e:
        # 【诊断】打印完整的异常堆栈跟踪
        print("--- [错误] 在 analyze_entry 中捕获到未处理的异常 ---")
        traceback.print_exc()
        print("----------------------------------------------------")
        
        db.rollback()
        raise HTTPException(status_code=500, detail=f"分析时发生内部错误: {e}")


@router.post("/follow-ups", response_model=FollowUpItem, tags=["Dictionary"])
async def create_follow_up(
    request: FollowUpCreateRequest,
    db: Session = Depends(get_db),
    llm_router: LLMRouter = Depends(get_llm_router)
):
    entry = db.query(models.KnowledgeEntry).options(joinedload(models.KnowledgeEntry.follow_ups)).filter(models.KnowledgeEntry.id == request.entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"ID为 {request.entry_id} 的知识条目不存在。")

    try:
        all_prototypes = db.query(models.KnowledgeEntry.query_text).all()
        vocabulary_list = [item[0] for item in all_prototypes]
        
        system_prompt = llm_router.config.follow_up_prompt.format(
            original_analysis=entry.analysis_markdown,
            history="\n".join([f"Q: {fu.question}\nA: {fu.answer}" for fu in entry.follow_ups]),
            vocabulary_list=", ".join(vocabulary_list)
        )
        
        answer_text = await call_llm_service(llm_router, system_prompt, request.question, use_tools=True)
        
        new_follow_up = models.FollowUp(
            entry_id=request.entry_id,
            question=request.question,
            answer=answer_text
        )
        db.add(new_follow_up)
        db.commit()
        db.refresh(new_follow_up)
        
        return FollowUpItem.model_validate(new_follow_up)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建追问时发生内部错误: {e}")


# =================================================================================
# 3. 管理端点 (Management Endpoints)
# =================================================================================

@router.post("/entries/{entry_id}/regenerate", response_model=AnalyzeResponse, tags=["Management"])
async def regenerate_entry_analysis(entry_id: int, db: Session = Depends(get_db), llm_router: LLMRouter = Depends(get_llm_router)):
    entry = db.query(models.KnowledgeEntry).options(joinedload(models.KnowledgeEntry.follow_ups)).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"ID为 {entry_id} 的知识条目未找到。")

    try:
        all_prototypes = [item[0] for item in db.query(models.KnowledgeEntry.query_text).all()]
        vocabulary_list = ", ".join(all_prototypes)
        
        system_prompt = llm_router.config.analysis_prompt.format(
            vocabulary_list=vocabulary_list or "知识库为空"
        )
        
        new_analysis_text = await call_llm_service(llm_router, system_prompt, entry.query_text, use_tools=True)
        entry.analysis_markdown = new_analysis_text
        db.commit()
        db.refresh(entry)
        
        return AnalyzeResponse(
            entry_id=entry.id,
            query_text=entry.query_text,
            analysis_markdown=entry.analysis_markdown,
            source="generated",
            follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重新生成时发生错误: {e}")


@router.delete("/entries/{entry_id}", status_code=200, tags=["Management"])
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"ID为 {entry_id} 的知识条目未找到。")
    
    try:
        query_text = entry.query_text
        db.delete(entry)
        db.commit()
        return {"message": f"成功删除知识条目 '{query_text}'"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除时发生错误: {e}")

@router.post("/aliases", status_code=201, tags=["Management"])
def create_alias(request: AliasCreateRequest, db: Session = Depends(get_db)):
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.query_text == request.entry_query_text).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"知识条目 '{request.entry_query_text}' 不存在。")
    
    if db.query(models.EntryAlias).filter(models.EntryAlias.alias_text == request.alias_text).first():
        raise HTTPException(status_code=409, detail=f"'{request.alias_text}' 已作为别名存在。")
    
    if db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.query_text == request.alias_text).first():
        raise HTTPException(status_code=409, detail=f"'{request.alias_text}' 已作为核心知识条目存在。")

    new_alias = models.EntryAlias(alias_text=request.alias_text, entry_id=entry.id)
    db.add(new_alias)
    db.commit()

    return {"message": f"成功将别名 '{request.alias_text}' 关联到 '{request.entry_query_text}'。"}

@router.post("/intelligent_search", response_model=AnalyzeResponse, tags=["Dictionary"])
async def intelligent_search(
    request: IntelligentSearchRequest,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches)
):
    """
    【V3.2 高级查询】根据用户的模糊输入和提示，推断出最可能的单词并返回其分析。
    """
    try:
        # 1. 准备给 AI 的输入
        intelligent_search_prompt = llm_router.config.intelligent_search_prompt
        # 将用户的输入构造成一个 JSON 字符串，作为 user_message
        user_input_json = json.dumps({"term": request.term, "hint": request.hint})
        
        # 2. 调用 AI 进行推理
        response_text = await call_llm_service(llm_router, intelligent_search_prompt, user_input_json)
        
        deduced_word = ""
        try:
            # 3. 解析 AI 返回的结果
            response_data = json.loads(response_text)
            deduced_word = response_data.get("result")
            if not deduced_word:
                raise HTTPException(status_code=404, detail="AI 未能推断出有效的目标单词。")
        except (json.JSONDecodeError, KeyError):
            raise HTTPException(status_code=500, detail=f"AI 返回了无法解析的格式: {response_text}")

        # 4. 【核心】复用现有的 analyze_entry 逻辑！
        # 我们创建一个新的 AnalyzeRequest 对象，然后“假装”用户是直接查询这个推断出的单词
        new_request = AnalyzeRequest(query_text=deduced_word, entry_type="WORD")
        return await analyze_entry(new_request, llm_router, db, recent_searches)

    except HTTPException as http_exc:
        # 直接将 analyze_entry 中可能抛出的拼写错误等异常传递出去
        raise http_exc
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"高级查询时发生内部错误: {e}")
    
@router.get("/database/export", tags=["Management"])
def export_database():
    """
    导出整个 SQLite 数据库文件作为备份。
    """
    db_path = "word_entries.db" # 数据库文件相对于项目根目录的路径
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件未找到。")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"de_ai_hilfer_backup_{timestamp}.db"

    return FileResponse(
        path=db_path,
        filename=filename, # 指定下载时显示的文件名
        media_type="application/x-sqlite3" # 指定文件的 MIME 类型
    )

@router.post("/database/import", tags=["Management"])
def import_database(request: DatabaseImportRequest):
    """
    用用户提供的备份文件恢复整个 SQLite 数据库。
    """
    backup_path = request.file_path
    current_db_path = "word_entries.db"
    temp_db_path = "temp_import_validation.db"

    # 1. 路径和文件存在性检查
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail=f"文件未找到: {backup_path}")
    if not os.path.isfile(backup_path):
        raise HTTPException(status_code=400, detail="提供的路径不是一个文件。")

    try:
        # 2. 复制到临时位置进行安全验证
        shutil.copyfile(backup_path, temp_db_path)

        # 3. 验证临时文件
        try:
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            # 检查核心表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('knowledge_entries', 'entry_aliases', 'follow_ups');")
            tables = cursor.fetchall()
            if len(tables) < 3:
                raise ValueError("备份文件缺少核心数据表，不是一个有效的备份。")
            conn.close()
        except (sqlite3.DatabaseError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"备份文件验证失败: {e}")

        # 4. 【核心操作】替换数据库文件
        # 注意：在生产环境中，这里需要关闭所有现有连接。
        # 对于本地应用，提示用户重启是最安全、最简单的方式。
        shutil.move(temp_db_path, current_db_path)

        return {"message": "数据库恢复成功！请完全重启 Raycast (通过 Command + Q) 以加载新的知识库。"}

    except Exception as e:
        # 确保在出错时清理临时文件
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        raise HTTPException(status_code=500, detail=f"恢复数据库时发生未知错误: {e}")
    finally:
        # 确保在任何情况下都尝试清理临时文件
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)