"""
API端点：重构后的简洁端点定义
"""

from typing import Deque, List, Optional

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from ai_adapter.llm_router import LLMRouter

# 导入管理层
from app.api.v1.management import (
    create_alias_service,
    create_follow_up_service,
    delete_entry_service,
    export_database_service,
    get_server_status_service,
    import_database_service,
    intelligent_search_service,
    regenerate_entry_analysis_service,
)

# 导入服务层
from app.api.v1.services import (
    analyze_entry_service,
    get_all_entries_service,
    get_recent_entries_service,
    get_suggestions_service,
)
from app.core.llm_service import get_llm_router
from app.core.state import get_recent_searches
from app.db.session import get_db
from app.schemas.dictionary import (
    AliasCreateRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    DatabaseImportRequest,
    FollowUpCreateRequest,
    FollowUpItem,
    IntelligentSearchRequest,
    RecentItem,
    SuggestionResponse,
)

router = APIRouter()

# =================================================================================
# 1. 基础查询端点 (Basic Query Endpoints)
# =================================================================================


@router.get("/entries/recent", response_model=List[RecentItem], tags=["Dictionary"])
def get_recent_entries(
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches),
):
    """
    获取最近成功查询的知识条目列表，按查询时间倒序排列。

    Args:
        db (Session): SQLAlchemy数据库会话
        recent_searches (Deque[str]): 最近搜索的查询文本队列

    Returns:
        List[RecentItem]: 最近查询的条目列表，每个条目包含查询文本和预览

    Note:
        - 只返回在数据库中实际存在的条目
        - 预览内容从分析结果中智能提取核心释义
        - 用于用户快速访问最近查询的单词
    """
    return get_recent_entries_service(db, recent_searches)


@router.get("/entries/all", response_model=List[RecentItem], tags=["Dictionary"])
def get_all_entries(db: Session = Depends(get_db)):
    """
    获取知识库中的所有条目，按字母顺序排序。

    Args:
        db (Session): SQLAlchemy数据库会话

    Returns:
        List[RecentItem]: 所有知识条目的列表，按查询文本字母顺序排列

    Note:
        - 包含所有已存储的知识条目
        - 每个条目都包含从分析中提取的预览信息
        - 适用于浏览整个知识库内容
    """
    return get_all_entries_service(db)


@router.get("/suggestions", response_model=SuggestionResponse, tags=["Dictionary"])
def get_suggestions(q: str, db: Session = Depends(get_db)) -> SuggestionResponse:
    """
    基于查询前缀提供智能建议，支持别名和知识条目的模糊匹配。

    Args:
        q (str): 查询前缀，用于匹配建议
        db (Session): SQLAlchemy数据库会话

    Returns:
        SuggestionResponse: 包含匹配建议列表的响应对象

    Note:
        - 优先匹配别名，并在前面显示↪️符号标识
        - 同时匹配知识条目的查询文本
        - 限制返回数量以避免响应过大
        - 每个建议都包含预览和追问信息
    """
    suggestions = get_suggestions_service(q, db)
    return SuggestionResponse(suggestions=suggestions)


# =================================================================================
# 2. 核心分析端点 (Core Analysis Endpoints)
# =================================================================================


@router.post("/analyze", response_model=AnalyzeResponse, tags=["Dictionary"])
async def analyze_entry(
    request: AnalyzeRequest,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches),
) -> AnalyzeResponse:
    """
    分析德语单词条目，提供详细的语法和语义分析。

    Args:
        request (AnalyzeRequest): 包含查询文本和条目类型的请求对象
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务
        db (Session): SQLAlchemy数据库会话
        recent_searches (Deque[str]): 最近搜索队列，用于更新搜索历史

    Returns:
        AnalyzeResponse: 包含详细分析的响应对象

    Note:
        - 支持缓存机制，已存在的条目直接返回
        - 自动进行拼写检查和原型词识别
        - 为单词变体自动创建别名
        - 分析结果包含词性、释义、例句等完整信息
    """
    return await analyze_entry_service(request, llm_router, db, recent_searches)


# =================================================================================
# 3. 追问管理端点 (Follow-up Management Endpoints)
# =================================================================================


@router.post("/follow-ups", response_model=FollowUpItem, tags=["Dictionary"])
async def create_follow_up(
    request: FollowUpCreateRequest,
    db: Session = Depends(get_db),
    llm_router: LLMRouter = Depends(get_llm_router),
):
    """
    为指定的知识条目创建追问并生成AI回答。

    Args:
        request (FollowUpCreateRequest): 包含条目ID和问题的请求对象
        db (Session): SQLAlchemy数据库会话
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务

    Returns:
        FollowUpItem: 创建的追问项目，包含问题、回答和时间戳

    Note:
        - AI回答会基于原始分析和历史追问记录生成
        - 支持连续对话，上下文会传递给AI
        - 追问与原条目关联，可通过条目ID访问
    """
    return await create_follow_up_service(request, db, llm_router)


# =================================================================================
# 4. 管理端点 (Management Endpoints)
# =================================================================================


@router.post(
    "/entries/{entry_id}/regenerate",
    response_model=AnalyzeResponse,
    tags=["Management"],
)
async def regenerate_entry_analysis(
    entry_id: int,
    db: Session = Depends(get_db),
    llm_router: LLMRouter = Depends(get_llm_router),
):
    """
    重新生成指定知识条目的AI分析内容。

    Args:
        entry_id (int): 要重新分析的知识条目ID
        db (Session): SQLAlchemy数据库会话
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务

    Returns:
        AnalyzeResponse: 更新后的分析响应，包含新的分析内容

    Note:
        - 保留原有的条目ID和查询文本
        - 使用当前知识库词汇重新生成分析
        - 适用于改进分析质量或修复错误内容
        - 新分析会覆盖原有的analysis_markdown字段
    """
    return await regenerate_entry_analysis_service(entry_id, db, llm_router)


@router.delete("/entries/{entry_id}", status_code=200, tags=["Management"])
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    从数据库中删除指定的知识条目及其相关数据。

    Args:
        entry_id (int): 要删除的知识条目ID
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含删除成功消息的字典

    Note:
        - 由于级联删除，相关的追问和别名也会被自动删除
        - 删除操作不可逆，请谨慎使用
        - 返回消息包含被删除条目的查询文本用于确认
    """
    return delete_entry_service(entry_id, db)


@router.post("/aliases", status_code=201, tags=["Management"])
def create_alias(request: AliasCreateRequest, db: Session = Depends(get_db)):
    """
    为指定的知识条目创建别名，支持多种查询方式。

    Args:
        request (AliasCreateRequest): 包含目标条目查询文本和别名的请求对象
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含创建成功消息的字典

    Note:
        - 别名不能与现有的别名或知识条目重复
        - 创建后用户可以通过别名查询到对应的知识条目
        - 支持为同一个条目创建多个别名
        - 返回201状态码表示资源创建成功
    """
    return create_alias_service(request, db)


@router.post("/intelligent_search", response_model=AnalyzeResponse, tags=["Dictionary"])
async def intelligent_search(
    request: IntelligentSearchRequest,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db),
    recent_searches: Deque[str] = Depends(get_recent_searches),
):
    """
    基于用户的模糊输入和提示，使用AI推断最可能的德语单词并返回详细分析。

    Args:
        request (IntelligentSearchRequest): 包含搜索词和提示的请求对象
        llm_router (LLMRouter): LLM路由器实例，用于调用AI服务
        db (Session): SQLAlchemy数据库会话
        recent_searches (Deque[str]): 最近搜索队列，用于更新搜索历史

    Returns:
        AnalyzeResponse: 推断单词的完整分析响应

    Note:
        - 使用AI模型根据用户的输入和提示推断最可能的单词
        - 支持模糊搜索和上下文提示
        - 复用analyze_entry的逻辑确保一致性
        - 自动更新最近搜索历史
    """
    return await intelligent_search_service(request, llm_router, db, recent_searches)


@router.get("/database/export", tags=["Management"])
async def export_database():
    """
    导出完整的PostgreSQL数据库作为SQL备份文件。

    Returns:
        FileResponse: 包含数据库备份的SQL文件，通过后台任务自动清理临时文件

    Note:
        - 使用pg_dump工具导出完整数据库结构
        - 备份文件名包含时间戳便于管理
        - 使用后台任务自动清理临时文件
        - 适用于数据备份和迁移
    """
    return await export_database_service()


@router.post("/database/import", tags=["Management"])
async def import_database(
    request: Optional[DatabaseImportRequest] = None,
    backup_file: Optional[UploadFile] = None,
):
    """
    从SQL备份文件恢复PostgreSQL数据库，支持多种输入方式。

    Args:
        request (Optional[DatabaseImportRequest]): 包含文件路径的JSON请求（Raycast客户端）
        backup_file (Optional[UploadFile]): 上传的SQL文件（Web客户端）

    Returns:
        dict: 包含恢复成功消息的字典

    Note:
        - 支持两种模式：文件上传（Web）和文件路径（Raycast）
        - 恢复过程会覆盖现有数据，请谨慎使用
        - 使用临时文件确保安全性
        - 适用于数据迁移和灾难恢复
    """
    return await import_database_service(request, backup_file)


@router.get("/status", tags=["Health Check"])
def get_server_status(db: Session = Depends(get_db)):
    """
    检查后端服务和数据库连接的健康状态。

    Args:
        db (Session): SQLAlchemy数据库会话

    Returns:
        dict: 包含服务状态和数据库状态的字典

    Note:
        - 执行简单的数据库查询验证连接状态
        - 用于负载均衡器健康检查和监控系统
        - 如果数据库连接正常，返回{"status": "ok", "db_status": "ok"}
        - 响应时间快，适合频繁调用
    """
    return get_server_status_service(db)


@router.get("/debug/cors", tags=["Debug"])
def debug_cors():
    """
    调试CORS配置，显示当前允许的源。

    Returns:
        dict: 包含当前CORS配置信息的字典

    Note:
        - 仅用于调试目的
        - 显示当前配置的允许源列表
        - 帮助诊断CORS相关问题
    """
    from app.core.config import settings
    return {
        "cors_origins": settings.api.cors_origins,
        "environment": settings.environment
    }
