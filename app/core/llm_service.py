from typing import Optional, List
import uuid
from fastapi import HTTPException
from ai_adapter.llm_router import LLMRouter, ChatSession
from app.db import models
from sqlalchemy.orm import Session
from app.schemas.dictionary import AnalyzeRequest
from ai_adapter.schemas import AssistantInternalMessage, TextBlock

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
            self._instance = LLMRouter(config_path='config.yaml')
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
    use_tools: bool = False # 【修复】增加 use_tools 参数
) -> str:
    """
    一个通用的、用于调用LLM服务的辅助函数。
    它封装了创建会话、运行和解析结果的逻辑。
    """
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
        raise HTTPException(status_code=500, detail="LLM service failed to generate a valid response.")
        
    return response_text

async def get_or_create_knowledge_entry(
    query_text: str,
    request: AnalyzeRequest,
    llm_router: LLMRouter,
    db: Session,
    analysis_prompt_template: str # 接收格式化前的模板
) -> models.KnowledgeEntry:
    """
    V3.1: 一个智能的辅助函数，用于获取或创建知识条目。
    如果条目已存在，则直接返回；如果不存在，则获取当前词汇表，调用AI分析并创建。
    """
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.query_text == query_text).first()
    if entry:
        print(f"--- 内部获取: 知识条目 '{query_text}' 已存在 ---")
        return entry
    
    print(f"--- 内部创建: 知识条目 '{query_text}' 不存在，准备调用AI分析 ---")
    
    # 1. 获取当前知识库中的所有原型词汇
    vocabulary_list_tuples = db.query(models.KnowledgeEntry.query_text).all()
    vocabulary_list = ", ".join([item[0] for item in vocabulary_list_tuples])
    
    # 2. 格式化 Prompt
    analysis_prompt = analysis_prompt_template.format(vocabulary_list=vocabulary_list or "知识库为空")
    
    # 3. 调用LLM服务，并启用数据库工具
    # 【诊断】打印最终发送给 AI 进行分析的 system_prompt
    # print(f"--- [诊断] 准备调用分析模型，System Prompt 为:\n---\n{analysis_prompt}\n---")
    analysis_markdown = await call_llm_service(llm_router, analysis_prompt, query_text, use_tools=True)
    
    # 4. 创建新条目并存入数据库
    new_entry = models.KnowledgeEntry(
        query_text=query_text,
        entry_type=request.entry_type,
        analysis_markdown=analysis_markdown
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    print(f"--- 新知识条目 '{query_text}' 已创建并存入数据库 ---")
    
    return new_entry

