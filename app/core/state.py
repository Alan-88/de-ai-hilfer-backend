from collections import deque
from typing import Deque, List, Dict, Any
import datetime

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

def get_daily_learning_session() -> Dict[str, Any]:
    """FastAPI dependency to get the daily learning session queue."""
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).date().isoformat()
    # 如果日期不是今天，就清空队列，强制重新生成
    if _daily_learning_session["date"] != today:
        _daily_learning_session["date"] = today
        _daily_learning_session["queue"] = []
        _daily_learning_session["initial_count"] = 0
        _daily_learning_session["last_shown_entry_id"] = None
    return _daily_learning_session
