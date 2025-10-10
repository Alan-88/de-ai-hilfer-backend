"""
学习模块服务层：包含间隔重复算法和学习相关业务逻辑
"""

import datetime
import json
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from ai_adapter.llm_router import LLMRouter
from app.core.llm_service import call_llm_service
from app.db import models


def update_learning_progress_service(progress: models.LearningProgress, quality: int, db: Session):
    """
    基于 SuperMemo-2 (SM-2) 简化算法，更新一个单词的学习进度。
    quality: 0-5 的记忆质量评分。
    """
    if quality < 3:
        # 记忆失败，重置学习周期
        progress.mastery_level = 0
        progress.interval = 1
        # 对 ease_factor 进行惩罚
        if quality == 2: # 看了提示才记起
            progress.ease_factor = max(1.3, progress.ease_factor - 0.15)
        else: # 完全忘记
            progress.ease_factor = max(1.3, progress.ease_factor - 0.20)
    else:
        # 记忆成功
        progress.mastery_level += 1
        if progress.mastery_level == 1:
            progress.interval = 1
        elif progress.mastery_level == 2:
            progress.interval = 6
        else:
            progress.interval = round(progress.interval * progress.ease_factor)
        
        # 根据记忆质量微调 ease_factor
        progress.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if progress.ease_factor < 1.3:
            progress.ease_factor = 1.3
            
    progress.review_count += 1
    progress.last_reviewed_at = datetime.datetime.utcnow()
    progress.next_review_at = progress.last_reviewed_at + datetime.timedelta(days=progress.interval)
    
    db.add(progress)
    db.commit()
    return progress


def get_learning_session_service(db: Session, limit_new_words: int = 5) -> dict:
    """
    获取学习会话：包括需要复习的单词和新单词
    """
    today = datetime.datetime.utcnow()
    
    # 获取需要复习的单词
    review_words = (
        db.query(models.LearningProgress)
        .filter(models.LearningProgress.next_review_at <= today)
        .join(models.KnowledgeEntry)
        .all()
    )
    
    # 获取新单词（还没有学习进度的单词）
    # 修复：获取所有已有学习进度的单词ID，而不是仅仅复习单词
    all_learned_progress = db.query(models.LearningProgress.entry_id).all()
    all_learned_entry_ids = {progress.entry_id for progress in all_learned_progress}
    
    new_words = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.id.notin_(all_learned_entry_ids))
        .filter(models.KnowledgeEntry.entry_type == 'WORD')
        .limit(limit_new_words)
        .all()
    )
    
    # 为新单词创建学习进度记录，确保前端可以正常提交复习结果
    new_words_with_progress = []
    for word in new_words:
        # 创建学习进度记录
        new_progress = models.LearningProgress(
            entry_id=word.id,
            next_review_at=datetime.datetime.utcnow()  # 立即可学习
        )
        db.add(new_progress)
        db.commit()
        db.refresh(new_progress)
        
        # 将新单词包装成与复习单词相同的数据结构
        new_words_with_progress.append(new_progress)
    
    return {
        "review_words": review_words,
        "new_words": new_words_with_progress  # 返回带有学习进度记录的新单词
    }


def add_word_to_learning_service(entry_id: int, db: Session) -> models.LearningProgress:
    """
    将单词添加到学习计划
    """
    # 检查是否已经存在学习进度
    existing_progress = (
        db.query(models.LearningProgress)
        .filter(models.LearningProgress.entry_id == entry_id)
        .first()
    )
    
    if existing_progress:
        return existing_progress
    
    # 创建新的学习进度记录
    new_progress = models.LearningProgress(
        entry_id=entry_id,
        next_review_at=datetime.datetime.utcnow()  # 立即可学习
    )
    
    db.add(new_progress)
    db.commit()
    db.refresh(new_progress)
    
    return new_progress


def get_word_insight_service(entry_id: int, db: Session) -> Optional[str]:
    """
    获取单词的"深度解析"部分用于提示
    """
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        return None
    
    # 使用正则表达式提取"深度解析 (Einblicke)"部分
    insight_pattern = r"#### 🧐 深度解析 \(Einblicke\)(.*?)(?=####|\Z)"
    match = re.search(insight_pattern, entry.analysis_markdown, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return None


async def generate_dynamic_example_service(entry_id: int, llm_router: LLMRouter, db: Session) -> dict:
    """
    AI动态生成例句
    """
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("单词不存在")
    
    prompt = llm_router.config.dynamic_example_sentence_prompt
    response_text = await call_llm_service(llm_router, prompt, entry.query_text)
    
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        raise ValueError("AI返回的例句格式错误")


async def generate_synonym_quiz_service(entry_id: int, llm_router: LLMRouter, db: Session) -> dict:
    """
    AI生成同义词辨析选择题
    """
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("单词不存在")
    
    # 提取核心释义用于出题
    core_meaning_pattern = r"\*\s*\*\*[nv\./adj\.]*\*\*\s*\*\*(.*?)\*\*"
    meaning_match = re.search(core_meaning_pattern, entry.analysis_markdown, re.IGNORECASE)
    core_meaning = meaning_match.group(1).strip() if meaning_match else entry.query_text
    
    word_details = f"单词: {entry.query_text}\n核心释义: {core_meaning}"
    
    prompt = llm_router.config.dynamic_synonym_quiz_prompt.format(word_details=word_details)
    response_text = await call_llm_service(llm_router, prompt)
    
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        raise ValueError("AI返回的题目格式错误")
