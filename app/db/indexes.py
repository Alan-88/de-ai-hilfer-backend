"""
数据库索引优化模块
为提升查询性能而创建的索引定义
"""

from sqlalchemy import Index

from app.db import models

# 定义性能优化索引
PERFORMANCE_INDEXES = [
    # 知识条目表的索引
    Index("idx_knowledge_entries_query_text", models.KnowledgeEntry.query_text),
    Index("idx_knowledge_entries_entry_type", models.KnowledgeEntry.entry_type),
    Index("idx_knowledge_entries_timestamp", models.KnowledgeEntry.timestamp),
    Index(
        "idx_knowledge_entries_query_type",
        models.KnowledgeEntry.query_text,
        models.KnowledgeEntry.entry_type,
    ),
    # 别名表的索引
    Index("idx_entry_aliases_alias_text", models.EntryAlias.alias_text),
    Index("idx_entry_aliases_entry_id", models.EntryAlias.entry_id),
    Index(
        "idx_entry_aliases_alias_entry",
        models.EntryAlias.alias_text,
        models.EntryAlias.entry_id,
    ),
    # 追问表的索引
    Index("idx_follow_ups_entry_id", models.FollowUp.entry_id),
    Index("idx_follow_ups_timestamp", models.FollowUp.timestamp),
    Index("idx_follow_ups_entry_time", models.FollowUp.entry_id, models.FollowUp.timestamp),
]


def create_performance_indexes():
    """创建所有性能优化索引"""
    print("--- 开始创建性能优化索引 ---")

    for index in PERFORMANCE_INDEXES:
        try:
            index.create(bind=models.Base.metadata.bind)
            print(f"--- 创建索引: {index.name} ---")
        except Exception as e:
            print(f"--- 索引 {index.name} 可能已存在或创建失败: {e} ---")

    print("--- 性能优化索引创建完成 ---")


def drop_performance_indexes():
    """删除所有性能优化索引（用于测试或重建）"""
    print("--- 开始删除性能优化索引 ---")

    for index in PERFORMANCE_INDEXES:
        try:
            index.drop(bind=models.Base.metadata.bind)
            print(f"--- 删除索引: {index.name} ---")
        except Exception as e:
            print(f"--- 索引 {index.name} 删除失败: {e} ---")

    print("--- 性能优化索引删除完成 ---")


def analyze_query_performance():
    """分析查询性能建议"""
    performance_tips = {
        "knowledge_entries": {
            "frequent_queries": [
                "按query_text精确查询",
                "按entry_type筛选",
                "按timestamp排序",
                "复合查询(query_text + entry_type)",
            ],
            "indexes": [
                "idx_knowledge_entries_query_text",
                "idx_knowledge_entries_entry_type",
                "idx_knowledge_entries_timestamp",
                "idx_knowledge_entries_query_type",
            ],
        },
        "entry_aliases": {
            "frequent_queries": [
                "按alias_text模糊查询",
                "按entry_id关联查询",
                "复合查询(alias_text + entry_id)",
            ],
            "indexes": [
                "idx_entry_aliases_alias_text",
                "idx_entry_aliases_entry_id",
                "idx_entry_aliases_alias_entry",
            ],
        },
        "follow_ups": {
            "frequent_queries": [
                "按entry_id查询追问",
                "按timestamp排序",
                "复合查询(entry_id + timestamp)",
            ],
            "indexes": [
                "idx_follow_ups_entry_id",
                "idx_follow_ups_timestamp",
                "idx_follow_ups_entry_time",
            ],
        },
    }

    return performance_tips


# 数据库查询优化建议
QUERY_OPTIMIZATION_TIPS = """
数据库查询性能优化建议：

1. 批量查询优化：
   - 使用 IN 操作符替代多次单独查询
   - 使用 JOIN 替代多次查询
   - 避免在循环中执行数据库查询

2. 索引使用：
   - 为频繁查询的字段创建索引
   - 为复合查询创建复合索引
   - 定期分析索引使用情况

3. 查询优化：
   - 只查询必要的字段
   - 使用 LIMIT 限制结果集大小
   - 避免使用 SELECT *
   - 使用适当的排序和分页

4. 缓存策略：
   - 缓存频繁访问的数据
   - 使用适当的缓存过期时间
   - 在数据更新时清除相关缓存

5. 连接池优化：
   - 配置合适的连接池大小
   - 监控连接使用情况
   - 及时释放数据库连接
"""
