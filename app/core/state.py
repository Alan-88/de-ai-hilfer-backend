from collections import deque
from typing import Deque, List, Dict, Any
from datetime import date, datetime, timezone, timedelta

# --- 原有代码 ---
_recent_searches: Deque[str] = deque(maxlen=10)

def get_recent_searches() -> Deque[str]:
    """FastAPI dependency to get the recent searches deque."""
    return _recent_searches

# --- 新增代码 ---
# 用于存储每日学习队列和其状态
_daily_learning_session: Dict[str, Any] = {
    "date": None,
    "queue": [],
    "initial_count": 0,
    "last_shown_entry_id": None,  # 新增此行
}

def get_learning_day() -> date:
    """获取当前学习日（以UTC+4为基准，即柏林时间上午6点）"""
    return (datetime.now(timezone.utc) + timedelta(hours=4)).date()

def get_daily_learning_session() -> Dict[str, Any]:
    """FastAPI dependency to get the daily learning session queue."""
    today = get_learning_day()
    
    # 【核心修复】使用 .get() 方法安全地访问 'date' 键
    # 无论 _daily_learning_session 是否为空或缺少 'date' 键，都不会报错
    if _daily_learning_session.get("date") != today:
        _daily_learning_session.clear()
        _daily_learning_session["date"] = today
        # 初始化或重置会话的其他状态
        _daily_learning_session["queue"] = []
        _daily_learning_session["word_stats"] = {}
        _daily_learning_session["initial_count"] = 0
        _daily_learning_session["last_shown_entry_id"] = None

    return _daily_learning_session
