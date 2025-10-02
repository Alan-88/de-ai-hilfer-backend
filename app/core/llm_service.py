import hashlib
import uuid
from typing import Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai_adapter.llm_router import LLMRouter
from ai_adapter.schemas import AssistantInternalMessage, TextBlock
from app.db import models
from app.schemas.dictionary import AnalyzeRequest

# =================================================================================
# 性能优化：LLM响应缓存
# =================================================================================

# LLM响应缓存，避免重复调用
_llm_response_cache: Dict[str, str] = {}
_max_llm_cache_size = 500  # 最大缓存条目数


def get_cache_key(prompt: str, message: str, use_tools: bool = False) -> str:
    """生成缓存键"""
    content = f"{prompt}:{message}:{use_tools}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_llm_response(cache_key: str) -> Optional[str]:
    """获取缓存的LLM响应"""
    return _llm_response_cache.get(cache_key)


def cache_llm_response(cache_key: str, response: str) -> None:
    """缓存LLM响应"""
    # 如果缓存过大，清理一半
    if len(_llm_response_cache) > _max_llm_cache_size:
        keys_to_remove = list(_llm_response_cache.keys())[: _max_llm_cache_size // 2]
        for key in keys_to_remove:
            del _llm_response_cache[key]

    _llm_response_cache[cache_key] = response


# 词汇表缓存，避免重复查询
_vocabulary_cache: Optional[Tuple[str, float]] = None  # (vocabulary_list, timestamp)
_vocabulary_cache_ttl = 300  # 5分钟缓存时间


def get_cached_vocabulary(db: Session) -> str:
    """获取缓存的词汇表"""
    import time

    global _vocabulary_cache

    current_time = time.time()
    if _vocabulary_cache is None or current_time - _vocabulary_cache[1] > _vocabulary_cache_ttl:

        # 重新查询词汇表
        vocabulary_list_tuples = db.query(models.KnowledgeEntry.query_text).all()
        vocabulary_list = ", ".join([item[0] for item in vocabulary_list_tuples])
        _vocabulary_cache = (vocabulary_list, current_time)

    return _vocabulary_cache[0]


# =================================================================================
# 1. LLMRouter 单例管理
# =================================================================================


class LLMRouterSingleton:
    """
    使用单例模式来管理 LLMRouter 实例，确保在整个应用中只有一个实例。
    """

    _instance: Optional[LLMRouter] = None

    def initialize(self):
        if self._instance is None:
            print("--- 正在初始化 LLMRouter 实例... ---")
            self._instance = LLMRouter(config_path="config.yaml")
        else:
            print("--- LLMRouter 实例已存在，跳过初始化。---")

    def get_instance(self) -> LLMRouter:
        if self._instance is None:
            raise RuntimeError("LLMRouter has not been initialized. Call 'initialize()' first.")
        return self._instance


llm_router_instance = LLMRouterSingleton()


def get_llm_router() -> LLMRouter:
    """
    FastAPI dependency that provides the global LLMRouter instance.
    """
    return llm_router_instance.get_instance()


# =================================================================================
# 2. 通用LLM服务调用函数
# =================================================================================


async def call_llm_service(
    llm_router: LLMRouter,
    system_prompt: str,
    user_message: str,
    use_tools: bool = False,  # 【修复】增加 use_tools 参数
    use_cache: bool = True,  # 新增：是否使用缓存
) -> str:
    """
    一个通用的、用于调用LLM服务的辅助函数。
    它封装了创建会话、运行和解析结果的逻辑。
    性能优化：添加了响应缓存机制。
    """
    # 检查缓存
    if use_cache:
        cache_key = get_cache_key(system_prompt, user_message, use_tools)
        cached_response = get_cached_llm_response(cache_key)
        if cached_response:
            print("--- [缓存命中] 使用缓存的LLM响应 ---")
            return cached_response

    session_id = str(uuid.uuid4())
    session = llm_router.get_session(session_id, system_prompt_override=system_prompt)

    # 【修复】根据 use_tools 参数决定是否启用 "database" 标签的工具
    enabled_tags = ["database"] if use_tools else []

    # 【修复】使用更健壮的 async for 循环来驱动异步生成器
    async for _ in session.run(message=user_message, enabled_tags=enabled_tags):
        pass

    last_message = session.conversation_history[-1]
    response_text = ""
    if isinstance(last_message, AssistantInternalMessage):
        response_text = " ".join(
            block.text for block in last_message.content if isinstance(block, TextBlock)
        ).strip()

    if not response_text:
        raise HTTPException(
            status_code=500, detail="LLM service failed to generate a valid response."
        )

    # 缓存响应
    if use_cache:
        cache_llm_response(cache_key, response_text)

    return response_text


async def get_or_create_knowledge_entry(
    query_text: str,
    request: AnalyzeRequest,
    llm_router: LLMRouter,
    db: Session,
    analysis_prompt_template: str,  # 接收格式化前的模板
) -> models.KnowledgeEntry:
    """
    V3.2: 一个智能的辅助函数，用于获取或创建知识条目。
    如果条目已存在，则直接返回；如果不存在，则获取当前词汇表，调用AI分析并创建。
    性能优化：使用缓存的词汇表和LLM响应缓存。
    """
    entry = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.query_text == query_text)
        .first()
    )
    if entry:
        print(f"--- 内部获取: 知识条目 '{query_text}' 已存在 ---")
        return entry

    print(f"--- 内部创建: 知识条目 '{query_text}' 不存在，准备调用AI分析 ---")

    # 1. 使用缓存的词汇表获取当前知识库中的所有原型词汇
    vocabulary_list = get_cached_vocabulary(db)

    # 2. 格式化 Prompt
    analysis_prompt = analysis_prompt_template.format(
        vocabulary_list=vocabulary_list or "知识库为空"
    )

    # 3. 调用LLM服务，并启用数据库工具，使用缓存
    # 【诊断】打印最终发送给 AI 进行分析的 system_prompt
    # print(f"--- [诊断] 准备调用分析模型，System Prompt 为:\n---\n{analysis_prompt}\n---")
    analysis_markdown = await call_llm_service(
        llm_router, analysis_prompt, query_text, use_tools=True, use_cache=True
    )

    # 4. 创建新条目并存入数据库
    new_entry = models.KnowledgeEntry(
        query_text=query_text,
        entry_type=request.entry_type,
        analysis_markdown=analysis_markdown,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    # 5. 清除词汇表缓存，因为添加了新条目
    global _vocabulary_cache
    _vocabulary_cache = None

    print(f"--- 新知识条目 '{query_text}' 已创建并存入数据库 ---")

    return new_entry
