from collections import deque
from typing import Deque

# 1. 定义队列
_recent_searches: Deque[str] = deque(maxlen=10)


# 2. 创建一个 FastAPI "dependency" 函数
def get_recent_searches() -> Deque[str]:
    """FastAPI dependency to get the recent searches deque."""
    return _recent_searches
