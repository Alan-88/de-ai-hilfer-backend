"""
学习模块API端点：智能化背单词功能的REST API接口
"""

import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_adapter.llm_router import LLMRouter
from app.api.v1.learning_service import (
    add_word_to_learning_service,
    generate_dynamic_example_service,
    generate_synonym_quiz_service,
    get_learning_session_service,
    get_word_insight_service,
    update_learning_progress_service,
    get_learning_session_service_v2,
    update_learning_progress_service_v2,
)
from app.core.state import get_daily_learning_session
from app.schemas.dictionary import LearningSessionResponse, LearningProgressResponse
from app.core.llm_service import get_llm_router
from app.db import models
from app.db.session import get_db

router = APIRouter()


# =================================================================================
# 1. 学习会话管理端点
# =================================================================================


@router.get("/session", tags=["Learning"])
def get_learning_session(
    limit_new_words: int = 5,
    db: Session = Depends(get_db)
) -> Dict:
    """
    获取学习会话：包括需要复习的单词和新单词
    
    Args:
        limit_new_words (int): 新单词数量限制，默认5个
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含复习单词和新单词的学习会话数据
        
    Note:
        - 复习单词：根据间隔重复算法需要今天复习的单词
        - 新单词：从知识库中随机选择还未学习的单词
    """
    session_data = get_learning_session_service(db, limit_new_words)
    
    return {
        "review_words": [
            {
                "id": progress.id,
                "entry_id": progress.entry_id,
                "query_text": progress.entry.query_text,
                "mastery_level": progress.mastery_level,
                "review_count": progress.review_count,
                "next_review_at": progress.next_review_at.isoformat(),
                "last_reviewed_at": progress.last_reviewed_at.isoformat() if progress.last_reviewed_at else None,
                "ease_factor": progress.ease_factor,
                "interval": progress.interval,
                "preview": progress.entry.analysis_markdown[:100] + "..." if len(progress.entry.analysis_markdown) > 100 else progress.entry.analysis_markdown,
                "analysis_markdown": progress.entry.analysis_markdown
            }
            for progress in session_data["review_words"]
        ],
        "new_words": [
            {
                "id": entry.id,
                "query_text": entry.query_text,
                "entry_type": entry.entry_type,
                "preview": entry.analysis_markdown[:100] + "..." if len(entry.analysis_markdown) > 100 else entry.analysis_markdown,
                "analysis_markdown": entry.analysis_markdown
            }
            for entry in session_data["new_words"]
        ]
    }


@router.post("/add/{entry_id}", status_code=201, tags=["Learning"])
def add_word_to_learning(
    entry_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    将单词添加到学习计划
    
    Args:
        entry_id (int): 知识条目ID
        db (Session): 数据库会话
        
    Returns:
        Dict: 创建成功的学习进度信息
        
    Note:
        - 如果单词已在学习计划中，返回现有进度
        - 如果单词不存在，返回404错误
    """
    # 检查单词是否存在
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="单词不存在")
    
    progress = add_word_to_learning_service(entry_id, db)
    
    return {
        "id": progress.id,
        "entry_id": progress.entry_id,
        "query_text": progress.entry.query_text,
        "mastery_level": progress.mastery_level,
        "review_count": progress.review_count,
        "next_review_at": progress.next_review_at.isoformat(),
        "ease_factor": progress.ease_factor,
        "interval": progress.interval,
        "message": "单词已添加到学习计划"
    }


# =================================================================================
# 2. 复习和进度管理端点
# =================================================================================


@router.post("/review/{entry_id}", tags=["Learning"])
def submit_review_result(
    entry_id: int,
    quality: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    提交复习结果，更新学习进度
    
    Args:
        entry_id (int): 知识条目ID
        quality (int): 记忆质量评分 (0-5)
            0: 完全忘记
            1: 忘记，但有印象
            2: 看了提示才记起
            3: 记起来了，但困难
            4: 记起来了，有点困难
            5: 完全掌握
        db (Session): 数据库会话
        
    Returns:
        Dict: 更新后的学习进度信息
        
    Note:
        - 使用SuperMemo-2算法计算下次复习时间
        - 根据记忆质量调整难度系数
    """
    if not 0 <= quality <= 5:
        raise HTTPException(status_code=400, detail="质量评分必须在0-5之间")
    
    progress = db.query(models.LearningProgress).filter(models.LearningProgress.entry_id == entry_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="学习进度不存在")
    
    updated_progress = update_learning_progress_service(progress, quality, db)
    
    return {
        "id": updated_progress.id,
        "entry_id": updated_progress.entry_id,
        "query_text": updated_progress.entry.query_text,
        "mastery_level": updated_progress.mastery_level,
        "review_count": updated_progress.review_count,
        "next_review_at": updated_progress.next_review_at.isoformat(),
        "last_reviewed_at": updated_progress.last_reviewed_at.isoformat() if updated_progress.last_reviewed_at else None,
        "ease_factor": updated_progress.ease_factor,
        "interval": updated_progress.interval,
        "message": "复习进度已更新"
    }


@router.get("/insight/{entry_id}", tags=["Learning"])
def get_word_insight(
    entry_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    获取单词的"深度解析"提示内容
    
    Args:
        entry_id (int): 知识条目ID
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含深度解析内容的响应
        
    Note:
        - 用于"二次机会"学习流程
        - 当用户忘记单词时提供提示
    """
    insight = get_word_insight_service(entry_id, db)
    if insight is None:
        raise HTTPException(status_code=404, detail="单词不存在或没有深度解析内容")
    
    return {
        "entry_id": entry_id,
        "insight": insight
    }


# =================================================================================
# 3. AI动态生成端点
# =================================================================================


@router.post("/generate-example/{entry_id}", tags=["Learning"])
async def generate_dynamic_example(
    entry_id: int,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db)
) -> Dict:
    """
    AI动态生成例句
    
    Args:
        entry_id (int): 知识条目ID
        llm_router (LLMRouter): LLM路由器
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含德语例句和中文翻译的响应
        
    Note:
        - 例句符合B1水平
        - 适合日常使用场景
    """
    try:
        example = await generate_dynamic_example_service(entry_id, llm_router, db)
        return {
            "entry_id": entry_id,
            "sentence": example.get("sentence"),
            "translation": example.get("translation")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成例句失败: {str(e)}")


@router.post("/generate-quiz/{entry_id}", tags=["Learning"])
async def generate_synonym_quiz(
    entry_id: int,
    llm_router: LLMRouter = Depends(get_llm_router),
    db: Session = Depends(get_db)
) -> Dict:
    """
    AI生成同义词辨析选择题
    
    Args:
        entry_id (int): 知识条目ID
        llm_router (LLMRouter): LLM路由器
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含选择题题目、选项和答案的响应
        
    Note:
        - 基于词汇网络生成高质量题目
        - 包含3个干扰项
        - 适合语法和词汇辨析练习
    """
    try:
        quiz = await generate_synonym_quiz_service(entry_id, llm_router, db)
        return {
            "entry_id": entry_id,
            "question": quiz.get("question"),
            "options": quiz.get("options"),
            "answer": quiz.get("answer")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成题目失败: {str(e)}")


# =================================================================================
# 4. 学习统计端点
# =================================================================================


@router.get("/progress", tags=["Learning"])
def get_learning_progress(db: Session = Depends(get_db)) -> Dict:
    """
    获取所有单词的学习进度信息
    
    Args:
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含所有学习进度信息的响应
        
    Note:
        - 用于词库管理中判断单词学习状态
        - 返回entry_id到学习进度的映射
    """
    progress_list = db.query(models.LearningProgress).all()
    
    progress_map = {}
    for progress in progress_list:
        progress_map[progress.entry_id] = {
            "id": progress.id,
            "entry_id": progress.entry_id,
            "mastery_level": progress.mastery_level,
            "review_count": progress.review_count,
            "next_review_at": progress.next_review_at.isoformat(),
            "last_reviewed_at": progress.last_reviewed_at.isoformat() if progress.last_reviewed_at else None,
            "ease_factor": progress.ease_factor,
            "interval": progress.interval
        }
    
    return {
        "progress": progress_map
    }


@router.get("/stats", tags=["Learning"])
def get_learning_stats(db: Session = Depends(get_db)) -> Dict:
    """
    获取学习统计信息
    
    Args:
        db (Session): 数据库会话
        
    Returns:
        Dict: 包含各种学习统计数据的响应
        
    Note:
        - 包括总学习单词数、复习统计、掌握等级分布等
    """
    total_learning = db.query(models.LearningProgress).count()
    
    # 按掌握等级统计
    mastery_stats = db.query(
        models.LearningProgress.mastery_level,
        func.count(models.LearningProgress.id).label('count')
    ).group_by(models.LearningProgress.mastery_level).all()
    
    # 今日需要复习的数量
    today = datetime.datetime.utcnow()
    due_today = db.query(models.LearningProgress).filter(
        models.LearningProgress.next_review_at <= today
    ).count()
    
    # 平均难度系数
    avg_ease_factor = db.query(
        func.avg(models.LearningProgress.ease_factor)
    ).scalar() or 0
    
    return {
        "total_words": total_learning,
        "due_today": due_today,
        "average_ease_factor": round(avg_ease_factor, 2),
        "mastery_distribution": [
            {"level": level, "count": count}
            for level, count in mastery_stats
        ]
    }


# =================================================================================
# 5. 学习模块 V2 - 每日动态学习队列
# =================================================================================


@router.get("/session/v2", response_model=LearningSessionResponse, tags=["Learning V2"])
def get_learning_session_v2(
    limit_new_words: int = 5,
    db: Session = Depends(get_db),
    daily_session: Dict[str, Any] = Depends(get_daily_learning_session)
):
    """
    获取学习会话 V2: 从每日动态队列中获取一个单词及当前进度。
    """
    session_data = get_learning_session_service_v2(db, daily_session, limit_new_words)
    return session_data


@router.post("/review/v2/{entry_id}", response_model=LearningProgressResponse, tags=["Learning V2"])
def submit_review_result_v2(
    entry_id: int,
    quality: int,
    db: Session = Depends(get_db),
    daily_session: Dict[str, Any] = Depends(get_daily_learning_session)
):
    """
    提交复习结果 V2: 更新每日队列和核心SRS数据。
    """
    if not 0 <= quality <= 5:
        raise HTTPException(status_code=400, detail="质量评分必须在0-5之间")
    
    try:
        updated_progress = update_learning_progress_service_v2(entry_id, quality, db, daily_session)
        return updated_progress
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
