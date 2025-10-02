"""
性能监控和优化模块
提供性能分析、监控和优化建议
"""

import functools
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

# 性能统计数据
performance_stats = {
    "query_times": defaultdict(list),
    "cache_hits": defaultdict(int),
    "cache_misses": defaultdict(int),
    "function_calls": defaultdict(int),
    "total_queries": 0,
    "slow_queries": [],
    "memory_usage": deque(maxlen=100),
}

# 线程安全的锁
_stats_lock = threading.Lock()


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self._record_performance()

    def _record_performance(self):
        """记录性能数据"""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time

            with _stats_lock:
                performance_stats["query_times"][self.name].append(duration)
                performance_stats["function_calls"][self.name] += 1
                performance_stats["total_queries"] += 1

                # 记录慢查询（超过1秒）
                if duration > 1.0:
                    performance_stats["slow_queries"].append(
                        {
                            "name": self.name,
                            "duration": duration,
                            "timestamp": time.time(),
                        }
                    )

    @property
    def duration(self) -> Optional[float]:
        """获取执行时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def monitor_performance(name: str):
    """性能监控装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceMonitor(name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def record_cache_hit(cache_name: str):
    """记录缓存命中"""
    with _stats_lock:
        performance_stats["cache_hits"][cache_name] += 1


def record_cache_miss(cache_name: str):
    """记录缓存未命中"""
    with _stats_lock:
        performance_stats["cache_misses"][cache_name] += 1


def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    with _stats_lock:
        report = {
            "summary": {
                "total_queries": performance_stats["total_queries"],
                "total_functions": len(performance_stats["function_calls"]),
                "slow_queries_count": len(performance_stats["slow_queries"]),
            },
            "query_performance": {},
            "cache_performance": {},
            "slow_queries": performance_stats["slow_queries"][-10:],  # 最近10个慢查询
            "recommendations": [],
        }

        # 查询性能统计
        for name, times in performance_stats["query_times"].items():
            if times:
                report["query_performance"][name] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_time": sum(times),
                }

        # 缓存性能统计
        all_cache_names = set(performance_stats["cache_hits"].keys()) | set(
            performance_stats["cache_misses"].keys()
        )
        for cache_name in all_cache_names:
            hits = performance_stats["cache_hits"].get(cache_name, 0)
            misses = performance_stats["cache_misses"].get(cache_name, 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0

            report["cache_performance"][cache_name] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": f"{hit_rate:.2f}%",
            }

        # 生成优化建议
        report["recommendations"] = _generate_recommendations(report)

        return report


def _generate_recommendations(report: Dict[str, Any]) -> List[str]:
    """生成性能优化建议"""
    recommendations = []

    # 检查慢查询
    if report["summary"]["slow_queries_count"] > 0:
        recommendations.append(
            f"发现 {report['summary']['slow_queries_count']} 个慢查询，建议优化查询逻辑或添加索引"
        )

    # 检查缓存命中率
    for cache_name, stats in report["cache_performance"].items():
        hit_rate = float(stats["hit_rate"].rstrip("%"))
        if hit_rate < 50:
            recommendations.append(
                f"缓存 '{cache_name}' 命中率较低 ({stats['hit_rate']})，建议调整缓存策略"
            )

    # 检查查询性能
    for name, stats in report["query_performance"].items():
        if stats["avg_time"] > 0.5:
            recommendations.append(
                f"函数 '{name}' 平均执行时间较长 ({stats['avg_time']:.3f}s)，建议优化"
            )

    # 检查总查询量
    if report["summary"]["total_queries"] > 1000:
        recommendations.append("查询量较大，建议考虑添加更多缓存或优化数据库连接池")

    if not recommendations:
        recommendations.append("性能表现良好，无明显优化建议")

    return recommendations


def reset_performance_stats():
    """重置性能统计"""
    with _stats_lock:
        performance_stats["query_times"].clear()
        performance_stats["cache_hits"].clear()
        performance_stats["cache_misses"].clear()
        performance_stats["function_calls"].clear()
        performance_stats["total_queries"] = 0
        performance_stats["slow_queries"].clear()
        performance_stats["memory_usage"].clear()


def log_memory_usage():
    """记录内存使用情况"""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        with _stats_lock:
            performance_stats["memory_usage"].append(
                {
                    "rss": memory_info.rss,
                    "vms": memory_info.vms,
                    "timestamp": time.time(),
                }
            )
    except ImportError:
        # psutil 未安装，跳过内存监控
        pass


def get_memory_trend() -> Dict[str, Any]:
    """获取内存使用趋势"""
    with _stats_lock:
        memory_data = list(performance_stats["memory_usage"])

        if not memory_data:
            return {"status": "no_data"}

        rss_values = [m["rss"] for m in memory_data]
        vms_values = [m["vms"] for m in memory_data]

        return {
            "current_rss": rss_values[-1] if rss_values else 0,
            "current_vms": vms_values[-1] if vms_values else 0,
            "avg_rss": sum(rss_values) / len(rss_values) if rss_values else 0,
            "avg_vms": sum(vms_values) / len(vms_values) if vms_values else 0,
            "max_rss": max(rss_values) if rss_values else 0,
            "max_vms": max(vms_values) if vms_values else 0,
            "samples": len(memory_data),
        }


# 性能优化建议模板
OPTIMIZATION_TIPS = """
性能优化建议：

1. 数据库优化：
   - 为频繁查询的字段添加索引
   - 使用批量查询替代循环查询
   - 避免N+1查询问题
   - 使用连接池管理数据库连接

2. 缓存优化：
   - 缓存频繁访问的数据
   - 设置合适的缓存过期时间
   - 使用多级缓存策略
   - 监控缓存命中率

3. 代码优化：
   - 减少不必要的计算
   - 使用生成器处理大数据集
   - 避免重复的函数调用
   - 优化算法复杂度

4. 内存优化：
   - 及时释放不需要的对象
   - 使用内存分析工具检测内存泄漏
   - 优化数据结构
   - 控制缓存大小

5. 并发优化：
   - 使用异步处理提高并发能力
   - 合理使用线程池
   - 避免锁竞争
   - 优化I/O操作
"""
