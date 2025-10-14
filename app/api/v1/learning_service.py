"""
学习模块服务层 V2：包含基于每日动态队列的间隔重复算法
"""

import datetime
import json
import re
import random
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date 

from ai_adapter.llm_router import LLMRouter
from app.core.llm_service import call_llm_service
from app.db import models

# ==============================================================================
# V3 - 二元记忆方案配置 (Dual-Memory System Configuration)
# ==============================================================================

# --- 当日任务管理器配置 ---
GRADUATION_THRESHOLD = 10
QUALITY_SCORE_MAP = {5: 6, 4: 4, 3: 2, 2: -3, 1: -5, 0: -7}
DIFFICULTY_DISCOUNT_MAP = {5: 4, 4: 3, 3: 2}
MAX_DAILY_REPS = 5

# --- 长线重复调度器配置 ---
SMOOTH_INTERVAL_LADDER = [1, 2, 4, 7, 15]


# ==============================================================================
# V3 - 新增的辅助函数 (New Helper Functions for V3)
# ==============================================================================

def calculate_weighted_quality(qualities: List[int]) -> float:
    """
    根据当日所有评分历史，计算加权综合分，用于长线调度。
    """
    if not qualities:
        return 0
    if len(qualities) == 1:
        return float(qualities[0])
    
    first_quality = float(qualities[0])
    rest_qualities = [float(q) for q in qualities[1:]]
    
    weighted_score = (first_quality * 0.5) + (sum(rest_qualities) / len(rest_qualities) * 0.5)
    return weighted_score

# ==============================================================================
# 核心服务 (Core Service Logic) - 已根据审查报告修复
# ==============================================================================

# --- 算法常量 (保留) ---
ACTIVE_POOL_SIZE = 7

def get_learning_day() -> datetime.date:
    """
    【修复 4】统一"学习日"的计算方式，定义为服务器时间的凌晨4点。
    所有与日期相关的操作都应调用此函数，确保一致性。
    """
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).date()

def _generate_daily_queue(db: Session, limit_new_words: int) -> List[Dict[str, Any]]:
    """
    生成每日学习队列 (已根据审查报告修复)
    """
    today = get_learning_day()

    # 1. 获取到期复习的单词
    review_progress = (
        db.query(models.LearningProgress)
        .filter(cast(models.LearningProgress.next_review_at, Date) <= today)
        .all()
    )

    # 2. 获取尚未学习的新词
    new_word_ids_in_progress = {p.entry_id for p in review_progress}
    num_new_words_needed = limit_new_words
    
    new_entries = []
    if num_new_words_needed > 0:
         new_entries = (
            db.query(models.KnowledgeEntry)  # 【修复 1】模型名称: KnowledgeEntry
            .outerjoin(models.LearningProgress, models.KnowledgeEntry.id == models.LearningProgress.entry_id)
            .filter(models.LearningProgress.entry_id.is_(None)) # 【修复 2】查询语法: .is_(None)
            .limit(num_new_words_needed)
            .all()
        )

    queue = []
    # 添加复习单词到队列
    for progress in review_progress:
        queue.append({"entry_id": progress.entry_id})

    # 添加新单词到队列
    for entry in new_entries:
        if entry.id not in new_word_ids_in_progress:
             queue.append({"entry_id": entry.id}) # 【修复 1】字段名: entry.id
        
    random.shuffle(queue)
    return queue


def get_learning_session_service_v2(
    db: Session,
    daily_session: Dict[str, Any],
    limit_new_words: int = 5
) -> Dict[str, Any]:
    """
    获取学习会话 (已根据审查报告修复)
    """
    if not daily_session.get("queue"):
        new_queue = _generate_daily_queue(db, limit_new_words)
        daily_session["queue"] = new_queue
        daily_session["word_stats"] = {}
        daily_session["initial_count"] = len(new_queue)
        daily_session["last_shown_entry_id"] = None
    
    active_queue = [
        word_data for word_data in daily_session["queue"]
        if not daily_session.get("word_stats", {}).get(word_data["entry_id"], {}).get("completed_today", False)
    ]

    if not active_queue:
        daily_session.clear() # 清空会话
        return { "current_word": None, "completed_count": daily_session.get("initial_count", 0), "total_count": daily_session.get("initial_count", 0), "is_completed": True }

    last_id = daily_session.get("last_shown_entry_id")
    candidate_pool = [word for word in active_queue if word["entry_id"] != last_id]
    
    if not candidate_pool:
        candidate_pool = active_queue

    focus_pool = candidate_pool[:ACTIVE_POOL_SIZE]
    current_word_data = random.choice(focus_pool)
    daily_session["last_shown_entry_id"] = current_word_data["entry_id"]

    entry = db.query(models.KnowledgeEntry).get(current_word_data["entry_id"]) # 【修复 1】模型名称

    # 【修复 5】增加错误处理
    if not entry:
        # 如果数据库中找不到该词，则从队列中移除并尝试获取下一个
        daily_session["queue"] = [w for w in daily_session["queue"] if w["entry_id"] != current_word_data["entry_id"]]
        return get_learning_session_service_v2(db, daily_session, limit_new_words)

    # --- 【核心修复】---
    # 重新获取 progress 和当日统计数据，以构建完整的前端对象
    progress = db.query(models.LearningProgress).filter_by(entry_id=entry.id).first()
    stats = daily_session.get("word_stats", {}).get(entry.id, {"repetitions": 0})
    
    # 估算一个 repetitions_left 用于显示
    # 例如：如果一个词需要10分毕业，当前2分，大概还需要(10-2)/4=2次左右
    estimated_reps_left = max(1, round((GRADUATION_THRESHOLD - stats.get("mastery_score", 0)) / 4))

    current_word_for_frontend = {
        "entry_id": entry.id,
        "query_text": entry.query_text,
        "analysis_markdown": entry.analysis_markdown,
        "repetitions_left": estimated_reps_left, # 修复：添加估算的剩余次数
        "progress": progress # 修复：添加 progress 对象
    }
    
    completed_count = daily_session["initial_count"] - len(active_queue)

    return {
        "current_word": current_word_for_frontend,
        "completed_count": completed_count,
        "total_count": daily_session["initial_count"],
        "is_completed": False,
    }


# ==============================================================================
# 【核心修改】替换 update_learning_progress_service_v2
# ==============================================================================

def update_learning_progress_service_v2(
    entry_id: int, 
    quality: int, 
    db: Session, 
    daily_session: Dict[str, Any]
):
    """
    【V3 - 最终版】更新学习进度，采用二元记忆方案。
    """
    # --- 1. 初始化 & 更新当日会话数据 ---
    stats = daily_session.setdefault('word_stats', {}).setdefault(entry_id, {
        "qualities": [], "repetitions": 0, "completed_today": False, 
        "mastery_score": 0, "is_difficult": False
    })
    stats['qualities'].append(quality)
    stats['repetitions'] += 1
    
    # --- 2. 当日任务管理器：计算“当日掌握积分” ---
    score_change = 0
    if stats['is_difficult']:
        score_change = DIFFICULTY_DISCOUNT_MAP.get(quality, QUALITY_SCORE_MAP.get(quality, 0))
    else:
        score_change = QUALITY_SCORE_MAP.get(quality, 0)
    stats['mastery_score'] = max(0, stats['mastery_score'] + score_change)

    # --- 3. 当日任务管理器：应用“初见宽容” & 更新困难词状态 ---
    if not stats['is_difficult'] and quality < 3:
        fail_count = sum(1 for q in stats['qualities'] if q < 3)
        if fail_count > 1:
            stats['is_difficult'] = True

    # --- 4. 当日任务管理器：判断当日任务是否完成 ---
    task_completed = False
    if stats['mastery_score'] >= GRADUATION_THRESHOLD:
        task_completed = True
    elif stats['repetitions'] >= MAX_DAILY_REPS:
        task_completed = True
    stats['completed_today'] = task_completed

    # --- 5. 获取或创建数据库对象 ---
    progress = db.query(models.LearningProgress).filter_by(entry_id=entry_id).first()
    if not progress:
        progress = models.LearningProgress(entry_id=entry_id, ease_factor=2.5)
        db.add(progress)

    today = get_learning_day() # 【修复 4】统一日期计算

    # --- 6. 长线重复调度器：如果任务完成，则规划未来 ---
    if task_completed:
        final_quality = calculate_weighted_quality(stats['qualities'])
        
        is_punished = False
        if stats['repetitions'] >= MAX_DAILY_REPS and stats['mastery_score'] < GRADUATION_THRESHOLD:
            if stats['mastery_score'] < 7:
                 progress.ease_factor = max(1.3, progress.ease_factor - 0.4)
                 progress.mastery_level = 0
            else:
                 progress.ease_factor = max(1.3, progress.ease_factor - 0.2)
            is_punished = True

        if is_punished and progress.mastery_level == 0:
            progress.next_review_at = today + datetime.timedelta(days=1)
        else:
            current_mastery = progress.mastery_level or 0
            if current_mastery < len(SMOOTH_INTERVAL_LADDER):
                progress.interval = SMOOTH_INTERVAL_LADDER[current_mastery]
            else:
                progress.interval = round((progress.interval or 1) * (progress.ease_factor or 2.5))
            
            progress.mastery_level = (progress.mastery_level or 0) + 1
            
            new_ef = (progress.ease_factor or 2.5) + (0.1 - (5 - final_quality) * (0.08 + (5 - final_quality) * 0.02))
            progress.ease_factor = max(1.3, new_ef)
            progress.next_review_at = today + datetime.timedelta(days=progress.interval)
    else:
        progress.next_review_at = today
    
    # --- 7. 收尾工作 ---
    progress.last_reviewed_at = today
    if progress.review_count is None:
        progress.review_count = 0
    progress.review_count += 1
    db.commit()
    db.refresh(progress)

    # 返回当日统计数据，与你现有的前端更兼容
    return {
        "entry_id": progress.entry_id,
        "mastery_level": progress.mastery_level,
        "next_review_at": progress.next_review_at.isoformat(),
        "daily_stats": stats # 把当日的详细情况也返回
    }

# ==============================================================================
# 其他原有函数 (保持不变)
# ==============================================================================

def update_learning_progress_service(progress: models.LearningProgress, quality: int, db: Session):
    # ... 此处是你提供的原有代码，完全没有改动 ...
    if quality < 3:
        progress.mastery_level = 0
        progress.interval = 0
        if quality == 2:
            progress.ease_factor = max(1.3, progress.ease_factor - 0.15)
        else:
            progress.ease_factor = max(1.3, progress.ease_factor - 0.20)
    else:
        progress.mastery_level += 1
        if progress.mastery_level == 1:
            progress.interval = 1
        elif progress.mastery_level == 2:
            progress.interval = 6
        else:
            progress.interval = round(progress.interval * progress.ease_factor)
        progress.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if progress.ease_factor < 1.3:
            progress.ease_factor = 1.3
    progress.review_count += 1
    progress.last_reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    progress.next_review_at = progress.last_reviewed_at + datetime.timedelta(days=progress.interval)
    db.add(progress)
    db.commit()
    return progress

# ... (后面所有其他函数 get_learning_session_service, add_word_to_learning_service 等都完全保留，此处省略以节约篇幅) ...
# 请将你本地文件里该函数之后的所有内容，都原封不动地保留在下面。

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
