"""
管理端点：包含数据库管理和系统维护相关的API端点
"""

import asyncio
import datetime
import json
import os
import shutil
from typing import Optional

from fastapi import Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from starlette.background import BackgroundTask

from ai_adapter.llm_router import LLMRouter
from app.api.v1.services import (
    analyze_entry_service,
)
from app.core.config import get_database_url
from app.core.errors import ErrorMessages, HTTPStatusCodes
from app.core.llm_service import call_llm_service
from app.db import models
from app.schemas.dictionary import (
    AliasCreateRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    DatabaseImportRequest,
    FollowUpCreateRequest,
    FollowUpItem,
    IntelligentSearchRequest,
)

# =================================================================================
# 1. 追问管理 (Follow-up Management)
# =================================================================================


async def create_follow_up_service(
    request: FollowUpCreateRequest, db: Session, llm_router: LLMRouter
) -> FollowUpItem:
    """
    为指定的知识条目创建追问并生成AI回答。

    Args:
        request (FollowUpCreateRequest): 包含条目ID和问题的请求对象
        db (Session): SQLAlchemy数据库会话
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务

    Returns:
        FollowUpItem: 创建的追问项目，包含问题、回答和时间戳

    Raises:
        HTTPException: 当条目不存在时返回404，当创建失败时返回500

    Note:
        - 函数会获取条目的历史追问记录作为上下文
        - 使用知识库中的所有词汇作为参考列表
        - AI回答会基于原始分析和历史对话生成
    """
    entry = (
        db.query(models.KnowledgeEntry)
        .options(joinedload(models.KnowledgeEntry.follow_ups))
        .filter(models.KnowledgeEntry.id == request.entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail=f"ID为 {request.entry_id} 的知识条目不存在。")

    try:
        all_prototypes = db.query(models.KnowledgeEntry.query_text).all()
        vocabulary_list = [item[0] for item in all_prototypes]

        system_prompt = llm_router.config.follow_up_prompt.format(
            original_analysis=entry.analysis_markdown,
            history="\n".join([f"Q: {fu.question}\nA: {fu.answer}" for fu in entry.follow_ups]),
            vocabulary_list=", ".join(vocabulary_list),
        )

        answer_text = await call_llm_service(
            llm_router, system_prompt, request.question, use_tools=True
        )

        new_follow_up = models.FollowUp(
            entry_id=request.entry_id, question=request.question, answer=answer_text
        )
        db.add(new_follow_up)
        db.commit()
        db.refresh(new_follow_up)

        return FollowUpItem.model_validate(new_follow_up)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建追问时发生内部错误: {e}")


# =================================================================================
# 2. 条目管理 (Entry Management)
# =================================================================================


async def regenerate_entry_analysis_service(
    entry_id: int, db: Session, llm_router: LLMRouter
) -> AnalyzeResponse:
    """
    重新生成指定知识条目的AI分析内容。

    Args:
        entry_id (int): 要重新分析的知识条目ID
        db (Session): SQLAlchemy数据库会话
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务

    Returns:
        AnalyzeResponse: 更新后的分析响应，包含新的分析内容

    Raises:
        HTTPException: 当条目不存在时返回404，当重新生成失败时返回500

    Note:
        - 函数会保留原有的条目ID和查询文本
        - 使用当前知识库中的所有词汇作为参考
        - 生成的分析会覆盖原有的analysis_markdown字段
        - 返回的source标记为"generated"表示是新生成的内容
    """
    entry = (
        db.query(models.KnowledgeEntry)
        .options(joinedload(models.KnowledgeEntry.follow_ups))
        .filter(models.KnowledgeEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail=f"ID为 {entry_id} 的知识条目未找到。")

    try:
        all_prototypes = [item[0] for item in db.query(models.KnowledgeEntry.query_text).all()]
        vocabulary_list = ", ".join(all_prototypes)

        system_prompt = llm_router.config.analysis_prompt.format(
            vocabulary_list=vocabulary_list or "知识库为空"
        )

        new_analysis_text = await call_llm_service(
            llm_router, system_prompt, entry.query_text, use_tools=True
        )
        entry.analysis_markdown = new_analysis_text
        db.commit()
        db.refresh(entry)

        return AnalyzeResponse(
            entry_id=entry.id,
            query_text=entry.query_text,
            analysis_markdown=entry.analysis_markdown,
            source="generated",
            follow_ups=[FollowUpItem.model_validate(fu) for fu in entry.follow_ups],
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重新生成时发生错误: {e}")


def delete_entry_service(entry_id: int, db: Session) -> dict:
    """
    从数据库中删除指定的知识条目及其相关数据。

    Args:
        entry_id (int): 要删除的知识条目ID
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含删除成功消息的字典

    Raises:
        HTTPException: 当条目不存在时返回404，当删除失败时返回500

    Note:
        - 由于设置了级联删除，相关的追问和别名也会被自动删除
        - 删除操作不可逆，请谨慎使用
        - 返回的消息包含被删除条目的查询文本用于确认
    """
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


def create_alias_service(request: AliasCreateRequest, db: Session) -> dict:
    """
    为指定的知识条目创建别名，支持多种查询方式。

    Args:
        request (AliasCreateRequest): 包含目标条目查询文本和别名的请求对象
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含创建成功消息的字典

    Raises:
        HTTPException: 当目标条目不存在时返回404，当别名已存在时返回409

    Note:
        - 别名不能与现有的别名重复
        - 别名不能与现有的知识条目查询文本重复
        - 创建后用户可以通过别名查询到对应的知识条目
        - 支持为同一个条目创建多个别名
    """
    entry = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.query_text == request.entry_query_text)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=404, detail=f"知识条目 '{request.entry_query_text}' 不存在。"
        )

    if (
        db.query(models.EntryAlias)
        .filter(models.EntryAlias.alias_text == request.alias_text)
        .first()
    ):
        raise HTTPException(status_code=409, detail=f"'{request.alias_text}' 已作为别名存在。")

    if (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.query_text == request.alias_text)
        .first()
    ):
        raise HTTPException(
            status_code=409, detail=f"'{request.alias_text}' 已作为核心知识条目存在。"
        )

    new_alias = models.EntryAlias(alias_text=request.alias_text, entry_id=entry.id)
    db.add(new_alias)
    db.commit()

    return {"message": f"成功将别名 '{request.alias_text}' 关联到 '{request.entry_query_text}'。"}


# =================================================================================
# 3. 高级搜索 (Intelligent Search)
# =================================================================================


async def intelligent_search_service(
    request: IntelligentSearchRequest,
    llm_router: LLMRouter,
    db: Session,
    recent_searches,
) -> AnalyzeResponse:
    """
    基于用户的模糊输入和提示，使用AI推断最可能的德语单词并返回详细分析。

    Args:
        request (IntelligentSearchRequest): 包含搜索词和提示的请求对象
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务
        db (Session): SQLAlchemy数据库会话
        recent_searches: 最近搜索列表，用于更新搜索历史

    Returns:
        AnalyzeResponse: 推断单词的完整分析响应

    Raises:
        HTTPException: 当AI推理失败时返回404，当响应无效时返回500

    Note:
        - 使用AI模型根据用户的输入和提示推断最可能的单词
        - 复用analyze_entry_service的逻辑确保一致性
        - 支持模糊搜索和上下文提示
        - 自动更新最近搜索历史
    """
    try:
        # 1. 准备给 AI 的输入
        intelligent_search_prompt = llm_router.config.intelligent_search_prompt
        # 将用户的输入构造成一个 JSON 字符串，作为 user_message
        user_input_json = json.dumps({"term": request.term, "hint": request.hint})

        # 2. 调用 AI 进行推理
        response_text = await call_llm_service(
            llm_router, intelligent_search_prompt, user_input_json
        )

        deduced_word = ""
        try:
            # 3. 解析 AI 返回的结果
            response_data = json.loads(response_text)
            deduced_word = response_data.get("result")
            if not deduced_word:
                raise HTTPException(
                    status_code=HTTPStatusCodes.NOT_FOUND,
                    detail=ErrorMessages.AI_INFERENCE_FAILED,
                )
        except (json.JSONDecodeError, KeyError):
            raise HTTPException(
                status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
                detail=ErrorMessages.AI_RESPONSE_INVALID.format(response_text=response_text),
            )

        # 4. 【核心】复用现有的 analyze_entry 逻辑！
        # 我们创建一个新的 AnalyzeRequest 对象，然后"假装"用户是直接查询这个推断出的单词
        new_request = AnalyzeRequest(query_text=deduced_word, entry_type="WORD")
        return await analyze_entry_service(new_request, llm_router, db, recent_searches)

    except HTTPException as http_exc:
        # 直接将 analyze_entry 中可能抛出的拼写错误等异常传递出去
        raise http_exc
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"高级查询时发生内部错误: {e}")


# =================================================================================
# 4. 数据库管理 (Database Management)
# =================================================================================


async def export_database_service():
    """
    使用pg_dump工具导出完整的PostgreSQL数据库作为SQL备份文件。

    Returns:
        FileResponse: 包含数据库备份的SQL文件，通过后台任务自动清理临时文件

    Raises:
        HTTPException: 当数据库URL未设置时返回500，当pg_dump不存在时返回500，当备份失败时返回500

    Note:
        - 使用--clean和--if-exists选项确保恢复时能正确处理现有对象
        - 备份文件名包含时间戳便于管理
        - 使用FastAPI的BackgroundTask机制自动清理临时文件
        - 临时文件存储在/tmp目录下
        - 支持Render环境的网络连接数据库
    """
    db_url = get_database_url()
    if not db_url:
        raise HTTPException(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.DATABASE_URL_NOT_SET,
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    temp_backup_path = f"/tmp/de_ai_hilfer_backup_{timestamp}.sql"

    # 解析数据库URL以获取连接参数
    import urllib.parse
    
    try:
        parsed_url = urllib.parse.urlparse(db_url)
        
        # 调试信息
        print(f"--- [调试] 数据库URL: {db_url} ---")
        print(f"--- [调试] 解析结果: hostname={parsed_url.hostname}, port={parsed_url.port}, username={parsed_url.username}, dbname={parsed_url.path} ---")
        
        # 检查数据库类型
        if db_url.startswith("sqlite://"):
            # SQLite数据库备份
            print("--- [调试] 检测到SQLite数据库，使用文件复制方式备份 ---")
            import shutil
            sqlite_db_path = parsed_url.path  # 获取SQLite数据库文件路径
            if not sqlite_db_path or not os.path.exists(sqlite_db_path):
                raise HTTPException(
                    status_code=500,
                    detail=f"SQLite数据库文件不存在: {sqlite_db_path}"
                )
            
            # 直接复制SQLite数据库文件
            shutil.copy2(sqlite_db_path, temp_backup_path)
            
            # 定义清理函数
            def cleanup():
                print(f"--- [后台任务] 清理临时备份文件: {temp_backup_path} ---")
                os.remove(temp_backup_path)

            cleanup_task = BackgroundTask(cleanup)
            
            return FileResponse(
                path=temp_backup_path,
                filename=os.path.basename(temp_backup_path),
                media_type="application/sql",
                background=cleanup_task,
            )
        
        # PostgreSQL数据库备份
        elif db_url.startswith("postgresql://"):
            print("--- [调试] 检测到PostgreSQL数据库，使用pg_dump备份 ---")
            
            # 构建pg_dump命令参数
            dbname = parsed_url.path.lstrip('/') if parsed_url.path else ""
            if not dbname:
                raise HTTPException(
                    status_code=500,
                    detail="数据库URL中未指定数据库名"
                )
            
            # 验证所有参数都不为None
            if not parsed_url.hostname:
                raise HTTPException(status_code=500, detail="数据库URL中未指定主机名")
            if not parsed_url.username:
                raise HTTPException(status_code=500, detail="数据库URL中未指定用户名")
            
            command = [
                "pg_dump",
                "--clean",
                "--if-exists",
                "--no-password",  # 避免密码提示
                "--host", parsed_url.hostname,
                "--port", str(parsed_url.port or 5432),
                "--username", parsed_url.username,
                "--dbname", dbname,
                "-f", temp_backup_path,
            ]
            
            print(f"--- [调试] pg_dump命令: {' '.join(command)} ---")
            
            # 设置密码环境变量
            env = os.environ.copy()
            if parsed_url.password:
                env["PGPASSWORD"] = parsed_url.password
            
            # 执行pg_dump命令
            try:
                process = await asyncio.create_subprocess_exec(
                    *command, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE,
                    env=env  # 传递包含密码的环境变量
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_message = stderr.decode().strip()
                    print(f"--- [错误] pg_dump 执行失败: {error_message} ---")
                    # 如果 pg_dump 失败，也要清理可能创建的空文件
                    if os.path.exists(temp_backup_path):
                        os.remove(temp_backup_path)
                    raise HTTPException(status_code=500, detail=f"数据库备份失败: {error_message}")

                # 定义一个清理函数
                def cleanup():
                    print(f"--- [后台任务] 清理临时备份文件: {temp_backup_path} ---")
                    os.remove(temp_backup_path)

                # 将清理函数包装成一个 BackgroundTask
                cleanup_task = BackgroundTask(cleanup)

                # 将 background task 传递给 FileResponse
                return FileResponse(
                    path=temp_backup_path,
                    filename=os.path.basename(temp_backup_path),
                    media_type="application/sql",
                    background=cleanup_task,
                )

            except FileNotFoundError:
                raise HTTPException(
                    status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
                    detail=ErrorMessages.PG_DUMP_NOT_FOUND,
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"不支持的数据库类型: {db_url.split('://')[0]}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"解析数据库URL失败: {str(e)}"
        )



async def import_database_service(
    request: Optional[DatabaseImportRequest] = Body(None),
    backup_file: Optional[UploadFile] = File(None),
):
    """
    从SQL备份文件恢复PostgreSQL数据库，支持多种输入方式。

    Args:
        request (Optional[DatabaseImportRequest]): 包含文件路径的JSON请求（Raycast客户端）
        backup_file (Optional[UploadFile]): 上传的SQL文件（Web客户端）

    Returns:
        dict: 包含恢复成功消息的字典

    Raises:
        HTTPException: 当数据库URL未设置时返回500，当文件不存在时返回404，当文件类型无效时返回400，当psql不存在时返回500，当恢复失败时返回500

    Note:
        - 支持两种模式：文件上传（Web）和文件路径（Raycast）
        - 使用临时文件确保安全性，避免直接操作原始文件
        - 在finally块中确保临时文件被正确清理
        - 恢复过程会覆盖现有数据，请谨慎使用
    """
    db_url = get_database_url()
    if not db_url:
        raise HTTPException(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.DATABASE_URL_NOT_SET,
        )

    timestamp = datetime.datetime.now().timestamp()
    temp_sql_path = f"/tmp/temp_import_{timestamp}.sql"
    source_description = ""  # 用于日志记录

    try:
        # --- 【逻辑恢复】模式一：处理文件上传 (Web 客户端) ---
        if backup_file:
            source_description = f"uploaded file '{backup_file.filename}'"
            if not backup_file.filename or not backup_file.filename.endswith(".sql"):
                raise HTTPException(
                    status_code=HTTPStatusCodes.BAD_REQUEST,
                    detail=ErrorMessages.INVALID_FILE_TYPE,
                )

            # 将上传的文件内容写入临时文件
            with open(temp_sql_path, "wb") as buffer:
                shutil.copyfileobj(backup_file.file, buffer)

        # --- 【逻辑恢复】模式二：处理文件路径 (Raycast 客户端) ---
        elif request and request.file_path:
            source_description = f"file path '{request.file_path}'"
            if not os.path.exists(request.file_path):
                raise HTTPException(
                    status_code=HTTPStatusCodes.NOT_FOUND,
                    detail=ErrorMessages.FILE_NOT_FOUND.format(file_path=request.file_path),
                )
            if not request.file_path.endswith(".sql"):
                raise HTTPException(
                    status_code=HTTPStatusCodes.BAD_REQUEST,
                    detail=ErrorMessages.INVALID_FILE_EXTENSION,
                )

            # 为了安全，我们先复制再操作
            shutil.copyfile(request.file_path, temp_sql_path)

        # --- 如果两种模式都没有匹配，则报错 ---
        else:
            raise HTTPException(
                status_code=HTTPStatusCodes.BAD_REQUEST,
                detail=ErrorMessages.FILE_REQUIRED,
            )

        # --- 统一的 psql 执行逻辑 ---
        print(f"--- [数据库导入] 开始从 {source_description} 恢复...")
        
        # 解析数据库URL以获取连接参数（与导出逻辑保持一致）
        import urllib.parse
        
        try:
            parsed_url = urllib.parse.urlparse(db_url)
            
            # 构建psql命令参数
            dbname = parsed_url.path.lstrip('/') if parsed_url.path else ""
            if not dbname:
                raise HTTPException(
                    status_code=500,
                    detail="数据库URL中未指定数据库名"
                )
            
            command = [
                "psql",
                "--no-password",  # 避免密码提示
                "--host", parsed_url.hostname,
                "--port", str(parsed_url.port or 5432),
                "--username", parsed_url.username,
                "--dbname", dbname,
                "-f", temp_sql_path,
            ]
            
            # 设置密码环境变量
            env = os.environ.copy()
            if parsed_url.password:
                env["PGPASSWORD"] = parsed_url.password
                
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"解析数据库URL失败: {str(e)}"
            )

        process = await asyncio.create_subprocess_exec(
            *command, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE,
            env=env  # 传递包含密码的环境变量
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode().strip()
            print(f"--- [错误] psql 执行失败: {error_message} ---")
            raise HTTPException(status_code=500, detail=f"数据库恢复失败: {error_message}")

        return {"message": f"数据库从 {source_description} 恢复成功！新数据已生效。"}

    except FileNotFoundError:
        raise HTTPException(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.PSQL_NOT_FOUND,
        )
    except Exception as e:
        if isinstance(e, HTTPException):  # 直接重新抛出已知的 HTTP 异常
            raise e
        raise HTTPException(status_code=500, detail=f"恢复数据库时发生未知错误: {str(e)}")
    finally:
        if backup_file:
            backup_file.file.close()
        if os.path.exists(temp_sql_path):
            os.remove(temp_sql_path)


# =================================================================================
# 5. 系统状态 (System Status)
# =================================================================================


def get_server_status_service(db: Session) -> dict:
    """
    检查后端服务和数据库连接的健康状态。

    Args:
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含服务状态和数据库状态的字典

    Raises:
        HTTPException: 当数据库连接失败时返回503

    Note:
        - 执行简单的SELECT 1查询来验证数据库连接
        - 如果数据库连接正常，返回{"status": "ok", "db_status": "ok"}
        - 用于负载均衡器健康检查和监控系统
    """
    try:
        from sqlalchemy import text

        # 执行一个最简单的SQL查询来唤醒或检查数据库
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db_status": "ok"}
    except Exception as e:
        # 如果数据库连接失败，这个接口会报错
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")
