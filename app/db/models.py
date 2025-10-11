import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

# 导入序列化工具
from .serializers import (
    serialize_entry_alias,
    serialize_follow_up,
    serialize_knowledge_entry,
)

Base = declarative_base()


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String, index=True, nullable=False, unique=True)
    entry_type = Column(String(50), nullable=False, default="WORD")
    analysis_markdown = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    follow_ups = relationship("FollowUp", back_populates="entry", cascade="all, delete-orphan")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。

        注意：此方法已弃用，请使用 serialize_knowledge_entry(self) 替代。
        为了向后兼容性而保留，将在未来版本中移除。
        """
        return serialize_knowledge_entry(self)

    def serialize(self, include_fields=None, exclude_fields=None):
        """使用新的序列化系统进行序列化。"""
        from .serializers import serialize_model

        return serialize_model(
            self,
            include_fields=include_fields,
            exclude_fields=exclude_fields,
            nested_relations={
                "follow_ups": {
                    "many": True,
                    "include_fields": {"id", "question", "answer", "timestamp"},
                }
            },
        )

    def __repr__(self):
        return f"<KnowledgeEntry(query='{self.query_text}', type='{self.entry_type}')>"


class EntryAlias(Base):
    __tablename__ = "entry_aliases"

    id = Column(Integer, primary_key=True, index=True)
    alias_text = Column(String, index=True, nullable=False, unique=True)
    entry_id = Column(Integer, ForeignKey("knowledge_entries.id"), nullable=False)

    entry = relationship("KnowledgeEntry")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。

        注意：此方法已弃用，请使用 serialize_entry_alias(self) 替代。
        为了向后兼容性而保留，将在未来版本中移除。
        """
        return serialize_entry_alias(self)

    def serialize(self, include_fields=None, exclude_fields=None):
        """使用新的序列化系统进行序列化。"""
        from .serializers import serialize_model

        return serialize_model(self, include_fields=include_fields, exclude_fields=exclude_fields)

    def __repr__(self):
        return f"<EntryAlias(alias='{self.alias_text}', entry='{self.entry.query_text}')>"


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("knowledge_entries.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    entry = relationship("KnowledgeEntry", back_populates="follow_ups")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。

        注意：此方法已弃用，请使用 serialize_follow_up(self) 替代。
        为了向后兼容性而保留，将在未来版本中移除。
        """
        return serialize_follow_up(self)

    def serialize(self, include_fields=None, exclude_fields=None):
        """使用新的序列化系统进行序列化。"""
        from .serializers import serialize_model

        return serialize_model(self, include_fields=include_fields, exclude_fields=exclude_fields)

    def __repr__(self):
        return f"<FollowUp(question='{self.question[:20]}...', entry='{self.entry.query_text}')>"


class LearningProgress(Base):
    __tablename__ = 'learning_progress'
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey('knowledge_entries.id'), nullable=False, index=True)
    
    # 间隔重复算法核心字段
    mastery_level = Column(Integer, default=0, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    next_review_at = Column(Date, nullable=False, default=datetime.date.today, index=True)
    last_reviewed_at = Column(Date, nullable=True)
    ease_factor = Column(Float, default=2.5, nullable=False)
    interval = Column(Integer, default=0, nullable=False) # 单位：天

    entry = relationship("KnowledgeEntry")

    def __repr__(self):
        return f"<LearningProgress(entry_id={self.entry_id}, next_review='{self.next_review_at.date()}')>"
