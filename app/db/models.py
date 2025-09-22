import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class KnowledgeEntry(Base):
    __tablename__ = 'knowledge_entries'

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String, index=True, nullable=False, unique=True)
    entry_type = Column(String(50), nullable=False, default='WORD')
    analysis_markdown = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    aliases = relationship("EntryAlias", back_populates="entry", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="entry", cascade="all, delete-orphan")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。"""
        return {
            "id": self.id,
            "query_text": self.query_text,
            "entry_type": self.entry_type,
            "analysis_markdown": self.analysis_markdown,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "follow_ups": [fu.to_dict() for fu in self.follow_ups]
        }

    def __repr__(self):
        return f"<KnowledgeEntry(query='{self.query_text}', type='{self.entry_type}')>"


class EntryAlias(Base):
    __tablename__ = 'entry_aliases'

    id = Column(Integer, primary_key=True, index=True)
    alias_text = Column(String, index=True, nullable=False, unique=True)
    entry_id = Column(Integer, ForeignKey('knowledge_entries.id'), nullable=False)

    entry = relationship("KnowledgeEntry", back_populates="aliases")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。"""
        return {
            "id": self.id,
            "alias_text": self.alias_text,
            "entry_id": self.entry_id
        }

    def __repr__(self):
        return f"<EntryAlias(alias='{self.alias_text}', entry='{self.entry.query_text}')>"


class FollowUp(Base):
    __tablename__ = 'follow_ups'

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey('knowledge_entries.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    entry = relationship("KnowledgeEntry", back_populates="follow_ups")

    def to_dict(self):
        """将SQLAlchemy对象转换为可序列化的字典。"""
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f"<FollowUp(question='{self.question[:20]}...', entry='{self.entry.query_text}')>"
