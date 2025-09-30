import os
import json
import re
import traceback
import datetime
import shutil
import sqlite3
import asyncio
from starlette.background import BackgroundTask
from typing import Deque, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

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
    【V3.4 词性扩展版】从完整的Markdown分析中智能提取核心释义作为预览。
    能够兼容多种可能的格式，并保留词性。
    """
    try:
        # 【修改】将 'adv.' (副词) 添加到正则表达式中
        part_of_speech_pattern = r"(v\.|n\.|adj\.|adv\.)"

        # 策略 1: 匹配新版格式的列表项, e.g., "* **v.** **释义**"
        # 使用了上面定义的扩展模式
        match = re.search(r"\*\s*\*\*" + part_of_speech_pattern + r"\*\*\s*\*\*(.*?)\*\*", analysis, re.IGNORECASE)
        if match:
            pos = match.group(1)  # part of speech
            definition = match.group(2).strip()
            return f"{pos} {definition}"

        # 策略 2: 兼容旧格式的表格
        # 同样使用扩展模式
        match = re.search(r"\|\s*\*\*核心释义\s*\(Bedeutung\)\*\*\s*\|\s*\*\*" + part_of_speech_pattern + r"\*\*\s*\*\*(.*?)\*\*\s*\|", analysis, re.IGNORECASE)
        if match:
            pos = match.group(1)
            definition = match.group(2).strip()
            return f"{pos} {definition}"
        
        # 策略 3: 匹配不带粗体标记的列表项, e.g., "* v. 释义"
        # 同样使用扩展模式
        match = re.search(r"^\s*\*\s*" + part_of_speech_pattern + r"\s+(.*)", analysis, re.MULTILINE | re.IGNORECASE)
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
async def export_database():
    """
    【V2.1 健壮版】使用 pg_dump 导出整个 PostgreSQL 数据库作为备份。
    使用后台任务来确保临时文件在响应发送后被清理。
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL 环境变量未设置。")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    temp_backup_path = f"/tmp/de_ai_hilfer_backup_{timestamp}.sql"

    command = ["pg_dump", "--clean", "--if-exists", "-d", db_url, "-f", temp_backup_path]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode().strip()
            print(f"--- [错误] pg_dump 执行失败: {error_message} ---")
            # 【改进】如果 pg_dump 失败，也要清理可能创建的空文件
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
            raise HTTPException(status_code=500, detail=f"数据库备份失败: {error_message}")
        
        # --- 【核心修复】 ---
        # 1. 定义一个清理函数
        def cleanup():
            print(f"--- [后台任务] 清理临时备份文件: {temp_backup_path} ---")
            os.remove(temp_backup_path)

        # 2. 将清理函数包装成一个 BackgroundTask
        cleanup_task = BackgroundTask(cleanup)

        # 3. 将 background task 传递给 FileResponse
        return FileResponse(
            path=temp_backup_path,
            filename=os.path.basename(temp_backup_path),
            media_type="application/sql",
            background=cleanup_task  # <-- 在这里传入任务
        )

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="服务器错误: 'pg_dump' 命令未找到。请确保 PostgreSQL 客户端工具已安装在后端环境中。")
    except Exception as e:
        # 如果在 FileResponse 创建前就发生异常，也需要清理
        if os.path.exists(temp_backup_path):
            os.remove(temp_backup_path)
        raise HTTPException(status_code=500, detail=f"创建备份时发生未知错误: {str(e)}")
    # 【修改】移除了 'finally' 块，因为清理逻辑已经交给了 BackgroundTask


@router.post("/database/import", tags=["Management"])
async def import_database(
    request: Optional[DatabaseImportRequest] = Body(None), # 【修正】使用 Body(None) 明确接收 JSON 体
    backup_file: Optional[UploadFile] = File(None)       # 【修正】同时支持文件上传
):
    """
    【V2.1 终极兼容版】从 .sql 文件恢复 PostgreSQL 数据库。
    - Web 端: 直接上传 .sql 文件 (backup_file)。
    - Raycast 端: 传递包含 .sql 文件路径的 JSON (request)。
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL 环境变量未设置。")

    timestamp = datetime.datetime.now().timestamp()
    temp_sql_path = f"/tmp/temp_import_{timestamp}.sql"
    source_description = "" # 用于日志记录

    try:
        # --- 【逻辑恢复】模式一：处理文件上传 (Web 客户端) ---
        if backup_file:
            source_description = f"uploaded file '{backup_file.filename}'"
            if not backup_file.filename or not backup_file.filename.endswith('.sql'):
                raise HTTPException(status_code=400, detail="请上传一个有效的 .sql 数据库备份文件。")
            
            # 将上传的文件内容写入临时文件
            with open(temp_sql_path, "wb") as buffer:
                shutil.copyfileobj(backup_file.file, buffer)

        # --- 【逻辑恢复】模式二：处理文件路径 (Raycast 客户端) ---
        elif request and request.file_path:
            source_description = f"file path '{request.file_path}'"
            if not os.path.exists(request.file_path):
                raise HTTPException(status_code=404, detail=f"文件未找到: {request.file_path}")
            if not request.file_path.endswith('.sql'):
                 raise HTTPException(status_code=400, detail="提供的路径不是一个 .sql 文件。")

            # 为了安全，我们先复制再操作
            shutil.copyfile(request.file_path, temp_sql_path)
        
        # --- 如果两种模式都没有匹配，则报错 ---
        else:
            raise HTTPException(status_code=400, detail="必须通过文件上传或文件路径提供一个 .sql 备份文件。")

        # --- 统一的 psql 执行逻辑 ---
        print(f"--- [数据库导入] 开始从 {source_description} 恢复...")
        command = ["psql", "-d", db_url, "-f", temp_sql_path]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode().strip()
            print(f"--- [错误] psql 执行失败: {error_message} ---")
            raise HTTPException(status_code=500, detail=f"数据库恢复失败: {error_message}")
            
        return {"message": f"数据库从 {source_description} 恢复成功！新数据已生效。"}

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="服务器错误: 'psql' 命令未找到。请确保 PostgreSQL 客户端工具已安装在后端环境中。")
    except Exception as e:
        if isinstance(e, HTTPException): # 直接重新抛出已知的 HTTP 异常
            raise e
        raise HTTPException(status_code=500, detail=f"恢复数据库时发生未知错误: {str(e)}")
    finally:
        if backup_file:
            backup_file.file.close()
        if os.path.exists(temp_sql_path):
            os.remove(temp_sql_path)

@router.get("/status", tags=["Health Check"])
def get_server_status(db: Session = Depends(get_db)):
    """
    检查后端服务和数据库的健康状态。
    """
    try:
        # 执行一个最简单的SQL查询来唤醒或检查数据库
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db_status": "ok"}
    except Exception as e:
        # 如果数据库连接失败，这个接口会报错
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")