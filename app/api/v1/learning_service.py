"""
学习模块服务层 V2：包含基于每日动态队列的间隔重复算法
"""

import datetime
import json
import re
import random
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from ai_adapter.llm_router import LLMRouter
from app.core.llm_service import call_llm_service
from app.db import models

# --- 算法常量 ---
NEW_WORD_REPETITIONS = 3
REVIEW_WORD_REPETITIONS = 1
FAILED_WORD_REPETITIONS = 2
ACTIVE_POOL_SIZE = 7  # 定义"聚焦学习池"的大小，7是个不错的选择

def _generate_daily_queue(db: Session, limit_new_words: int) -> List[Dict[str, Any]]:
    """
    【V4.1 - 最终版】
    - 使用“学习日”（凌晨4点）作为日期判断基准。
    - 严格只从 learning_progress 表中选取单词。
    - 根据单词的熟练度动态设置初始重复次数。
    """
    today = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).date()

    review_progress = (
        db.query(models.LearningProgress)
        .filter(func.date(models.LearningProgress.next_review_at) <= today)
        .all()
    )
    
    queue = []
    for progress in review_progress:
        # 【关键修复】根据熟练度动态设置重复次数
        repetitions = 1 # 默认为1次
        if progress.mastery_level <= 1:
            repetitions = 3 # 生词或刚学的词，重复3次
        elif progress.mastery_level <= 3:
            repetitions = 2 # 学习中的词，重复2次
        
        queue.append({
            "entry_id": progress.entry_id,
            "repetitions_left": repetitions, 
            "progress": progress
        })
        
    random.shuffle(queue)
    return queue

def get_learning_session_service_v2(
    db: Session,
    daily_session: Dict[str, Any],
    limit_new_words: int = 5
) -> Dict[str, Any]:
    """
    获取学习会话 V3 (智能选择版):
    - 引入"聚焦学习池" (Active Pool) 概念，实现局部轮换。
    - 确保单词不会连续出现。
    """
    if not daily_session.get("queue"):
        new_queue = _generate_daily_queue(db, limit_new_words)
        daily_session["queue"] = new_queue
        daily_session["initial_count"] = len(new_queue)
        daily_session["last_shown_entry_id"] = None

    active_queue = [word for word in daily_session["queue"] if word["repetitions_left"] > 0]

    if not active_queue:
        # 清空会话，以便下次可以重新开始
        daily_session["queue"] = []
        daily_session["initial_count"] = 0
        daily_session["last_shown_entry_id"] = None
        return {
            "current_word": None,
            "completed_count": daily_session.get("initial_count", 0),
            "total_count": daily_session.get("initial_count", 0),
            "is_completed": True,
        }

    # --- 智能选择算法 ---

    # 1. 过滤掉上一个单词 (避免连续重复)
    last_id = daily_session.get("last_shown_entry_id")
    candidate_pool = [word for word in active_queue if word["entry_id"] != last_id]
    
    # 如果过滤后只剩一个或没有了，就不过滤，防止卡死
    if not candidate_pool:
        candidate_pool = active_queue

    # 2. 创建"聚焦学习池" (Active Pool)
    # 优先选择重复次数更多的单词，实现对难点的聚焦
    candidate_pool.sort(key=lambda x: x["repetitions_left"], reverse=True)
    
    # 取前 N 个最需要学习的单词形成一个小的轮换池
    focus_pool = candidate_pool[:ACTIVE_POOL_SIZE]

    # 3. 从聚焦池中随机选择一个单词
    current_word_data = random.choice(focus_pool)
    
    # 4. 更新"上一个单词"的记录
    daily_session["last_shown_entry_id"] = current_word_data["entry_id"]

    # --- 后续逻辑不变 ---
    entry = db.query(models.KnowledgeEntry).get(current_word_data["entry_id"])

    current_word_for_frontend = {
        "entry_id": entry.id,
        "query_text": entry.query_text,
        "analysis_markdown": entry.analysis_markdown,
        "repetitions_left": current_word_data["repetitions_left"],
        "progress": current_word_data["progress"]
    }

    completed_count = daily_session["initial_count"] - len(set(w["entry_id"] for w in active_queue))

    return {
        "current_word": current_word_for_frontend,
        "completed_count": completed_count,
        "total_count": daily_session["initial_count"],
        "is_completed": False,
    }

def update_learning_progress_service_v2(
    entry_id: int, 
    quality: int, 
    db: Session, 
    daily_session: Dict[str, Any]
):
    """
    更新学习进度 V2:
    - 更新每日队列中的重复次数。
    - 异步更新数据库中的 SRS 数据。
    """
    # 1. 更新内存中的每日队列
    word_in_queue = next((word for word in daily_session["queue"] if word["entry_id"] == entry_id), None)
    
    if not word_in_queue:
        raise ValueError("单词不在当前学习会话中")

    if quality < 3:
        # 如果答错了，增加重复次数
        word_in_queue["repetitions_left"] += FAILED_WORD_REPETITIONS
    elif quality < 4:
        word_in_queue["repetitions_left"] = max(0, word_in_queue["repetitions_left"] - 1)
    else:
        word_in_queue["repetitions_left"] = max(0, word_in_queue["repetitions_left"] - 2)
        
    # 2. 更新数据库中的核心 SRS 数据
    progress = (
        db.query(models.LearningProgress)
        .filter(models.LearningProgress.entry_id == entry_id)
        .first()
    )
    
    # 如果是新词，先创建 LearningProgress 记录
    if not progress:
        progress = models.LearningProgress(entry_id=entry_id)
        db.add(progress)
    
    # 沿用之前的 SM-2 算法更新 SRS 核心数据
    if quality < 3:
        progress.mastery_level = 0
        progress.interval = 0 
        progress.ease_factor = max(1.3, progress.ease_factor - (0.20 if quality < 2 else 0.15))
    else:
        if progress.mastery_level == 0:
            progress.interval = 1
        elif progress.mastery_level == 1:
            progress.interval = 6
        else:
            progress.interval = round(progress.interval * progress.ease_factor)
        
        progress.mastery_level += 1
        progress.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if progress.ease_factor < 1.3:
            progress.ease_factor = 1.3
            
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).date()
    progress.review_count += 1
    progress.last_reviewed_at = today
    progress.next_review_at = progress.last_reviewed_at + datetime.timedelta(days=progress.interval)
    
    db.commit()
    db.refresh(progress)
    
    # 更新内存队列中的 progress 对象
    word_in_queue["progress"] = progress

    return progress

# --- 保留原有的其他服务函数 ---

def update_learning_progress_service(progress: models.LearningProgress, quality: int, db: Session):
    """
    基于 SuperMemo-2 (SM-2) 简化算法，更新一个单词的学习进度。
    quality: 0-5 的记忆质量评分。
    """
    if quality < 3:
        # 记忆失败，重置学习周期
        progress.mastery_level = 0
        progress.interval = 0  # 立即需要再次复习
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
    progress.last_reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    progress.next_review_at = progress.last_reviewed_at + datetime.timedelta(days=progress.interval)
    
    db.add(progress)
    db.commit()
    return progress


def get_learning_session_service(db: Session, limit_new_words: int = 5) -> dict:
    """
    获取学习会话：包括需要复习的单词和新单词
    修复：只返回用户明确添加到学习计划的单词
    """
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).date()
    
    # 获取需要复习的单词（用户已添加到学习计划的单词）
    review_words = (
        db.query(models.LearningProgress)
        .filter(models.LearningProgress.next_review_at <= today)
        .join(models.KnowledgeEntry)
        .all()
    )
    
    # 修复：不再自动从未学习的单词中获取新词
    # 新单词应该只通过用户明确调用 /add/{entry_id} 接口添加
    # 这样确保只有用户选择的单词才会进入学习列表
    
    new_words_with_progress = []  # 空列表，等待用户主动添加单词
    
    return {
        "review_words": review_words,
        "new_words": new_words_with_progress
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
        next_review_at=datetime.datetime.now(datetime.timezone.utc)  # 立即可学习
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
