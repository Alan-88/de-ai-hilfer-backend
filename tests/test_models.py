"""
数据库模型测试
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import KnowledgeEntry, EntryAlias, FollowUp


class TestKnowledgeEntry:
    """知识条目模型测试"""
    
    def test_create_knowledge_entry(self, db_session: Session):
        """测试创建知识条目"""
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen\n**词义**: 房子\n**词性**: das\n\n## 核心释义 (Bedeutung)\n\n* **n.** **房子** - 建筑物"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        assert entry.id is not None
        assert entry.query_text == "Haus"
        assert entry.entry_type == "WORD"
        assert entry.analysis_markdown is not None
        assert entry.timestamp is not None
    
    def test_knowledge_entry_to_dict(self, db_session: Session):
        """测试知识条目转字典"""
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen\n**词义**: 房子"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        entry_dict = entry.to_dict()
        assert entry_dict["query_text"] == "Haus"
        assert entry_dict["entry_type"] == "WORD"
        assert "id" in entry_dict
        assert "timestamp" in entry_dict
    
    def test_knowledge_entry_repr(self, db_session: Session):
        """测试知识条目字符串表示"""
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        repr_str = repr(entry)
        assert "KnowledgeEntry" in repr_str
        assert "Haus" in repr_str
        assert "WORD" in repr_str
    
    def test_knowledge_entry_serialize(self, db_session: Session):
        """测试知识条目序列化"""
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 测试新的序列化方法
        serialized = entry.serialize()
        assert serialized["query_text"] == "Haus"
        assert serialized["entry_type"] == "WORD"
        assert "id" in serialized
        
        # 测试包含字段
        serialized_include = entry.serialize(include_fields={"query_text", "entry_type"})
        assert "query_text" in serialized_include
        assert "entry_type" in serialized_include
        assert "analysis_markdown" not in serialized_include
        
        # 测试排除字段
        serialized_exclude = entry.serialize(exclude_fields={"analysis_markdown"})
        assert "analysis_markdown" not in serialized_exclude
        assert "query_text" in serialized_exclude


class TestEntryAlias:
    """条目别名模型测试"""
    
    def test_create_entry_alias(self, db_session: Session):
        """测试创建条目别名"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(
            alias_text="das Haus",
            entry_id=entry.id
        )
        db_session.add(alias)
        db_session.commit()
        db_session.refresh(alias)
        
        assert alias.id is not None
        assert alias.alias_text == "das Haus"
        assert alias.entry_id == entry.id
        assert alias.entry == entry
    
    def test_entry_alias_to_dict(self, db_session: Session):
        """测试条目别名转字典"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(
            alias_text="das Haus",
            entry_id=entry.id
        )
        db_session.add(alias)
        db_session.commit()
        db_session.refresh(alias)
        
        alias_dict = alias.to_dict()
        assert alias_dict["alias_text"] == "das Haus"
        assert alias_dict["entry_id"] == entry.id
        assert "id" in alias_dict
    
    def test_entry_alias_repr(self, db_session: Session):
        """测试条目别名字符串表示"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(
            alias_text="das Haus",
            entry_id=entry.id
        )
        db_session.add(alias)
        db_session.commit()
        db_session.refresh(alias)
        
        repr_str = repr(alias)
        assert "EntryAlias" in repr_str
        assert "das Haus" in repr_str
        assert "Haus" in repr_str
    
    def test_entry_alias_serialize(self, db_session: Session):
        """测试条目别名序列化"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias = EntryAlias(
            alias_text="das Haus",
            entry_id=entry.id
        )
        db_session.add(alias)
        db_session.commit()
        db_session.refresh(alias)
        
        # 测试序列化
        serialized = alias.serialize()
        assert serialized["alias_text"] == "das Haus"
        assert serialized["entry_id"] == entry.id
        assert "id" in serialized


class TestFollowUp:
    """后续问题模型测试"""
    
    def test_create_follow_up(self, db_session: Session):
        """测试创建后续问题"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建后续问题
        follow_up = FollowUp(
            entry_id=entry.id,
            question="Haus的复数形式是什么？",
            answer="Häuser"
        )
        db_session.add(follow_up)
        db_session.commit()
        db_session.refresh(follow_up)
        
        assert follow_up.id is not None
        assert follow_up.entry_id == entry.id
        assert follow_up.question == "Haus的复数形式是什么？"
        assert follow_up.answer == "Häuser"
        assert follow_up.timestamp is not None
        assert follow_up.entry == entry
    
    def test_follow_up_to_dict(self, db_session: Session):
        """测试后续问题转字典"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建后续问题
        follow_up = FollowUp(
            entry_id=entry.id,
            question="Haus的复数形式是什么？",
            answer="Häuser"
        )
        db_session.add(follow_up)
        db_session.commit()
        db_session.refresh(follow_up)
        
        follow_up_dict = follow_up.to_dict()
        assert follow_up_dict["question"] == "Haus的复数形式是什么？"
        assert follow_up_dict["answer"] == "Häuser"
        assert follow_up_dict["entry_id"] == entry.id
        assert "id" in follow_up_dict
        assert "timestamp" in follow_up_dict
    
    def test_follow_up_repr(self, db_session: Session):
        """测试后续问题字符串表示"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建后续问题
        follow_up = FollowUp(
            entry_id=entry.id,
            question="Haus的复数形式是什么？",
            answer="Häuser"
        )
        db_session.add(follow_up)
        db_session.commit()
        db_session.refresh(follow_up)
        
        repr_str = repr(follow_up)
        assert "FollowUp" in repr_str
        assert "Haus的复数形式是什么？" in repr_str
        assert "Haus" in repr_str
    
    def test_follow_up_serialize(self, db_session: Session):
        """测试后续问题序列化"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建后续问题
        follow_up = FollowUp(
            entry_id=entry.id,
            question="Haus的复数形式是什么？",
            answer="Häuser"
        )
        db_session.add(follow_up)
        db_session.commit()
        db_session.refresh(follow_up)
        
        # 测试序列化
        serialized = follow_up.serialize()
        assert serialized["question"] == "Haus的复数形式是什么？"
        assert serialized["answer"] == "Häuser"
        assert serialized["entry_id"] == entry.id
        assert "id" in serialized


class TestModelRelationships:
    """模型关系测试"""
    
    def test_knowledge_entry_follow_ups_relationship(self, db_session: Session):
        """测试知识条目与后续问题的关系"""
        # 创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建多个后续问题
        follow_up1 = FollowUp(
            entry_id=entry.id,
            question="Haus的复数形式是什么？",
            answer="Häuser"
        )
        follow_up2 = FollowUp(
            entry_id=entry.id,
            question="Haus的词性是什么？",
            answer="Nomen"
        )
        db_session.add_all([follow_up1, follow_up2])
        db_session.commit()
        
        # 测试关系
        assert len(entry.follow_ups) == 2
        assert follow_up1.entry == entry
        assert follow_up2.entry == entry
        
        # 验证后续问题内容
        questions = [fu.question for fu in entry.follow_ups]
        assert "Haus的复数形式是什么？" in questions
        assert "Haus的词性是什么？" in questions
    
    def test_entry_alias_relationship(self, db_session: Session):
        """测试条目别名与知识条目的关系"""
        # 创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建多个别名
        alias1 = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        alias2 = EntryAlias(alias_text="Häuser", entry_id=entry.id)
        db_session.add_all([alias1, alias2])
        db_session.commit()
        
        # 测试关系
        assert alias1.entry == entry
        assert alias2.entry == entry
        assert alias1.entry_id == entry.id
        assert alias2.entry_id == entry.id


class TestModelConstraints:
    """模型约束测试"""
    
    def test_knowledge_entry_unique_constraint(self, db_session: Session):
        """测试知识条目唯一约束"""
        # 创建第一个条目
        entry1 = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry1)
        db_session.commit()
        
        # 尝试创建重复的条目
        entry2 = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry2)
        
        with pytest.raises(Exception):  # 应该抛出唯一约束异常
            db_session.commit()
    
    def test_entry_alias_unique_constraint(self, db_session: Session):
        """测试条目别名唯一约束"""
        # 先创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建第一个别名
        alias1 = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        db_session.add(alias1)
        db_session.commit()
        
        # 尝试创建重复的别名
        alias2 = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        db_session.add(alias2)
        
        with pytest.raises(Exception):  # 应该抛出唯一约束异常
            db_session.commit()
    
    def test_foreign_key_constraint(self, db_session: Session):
        """测试外键约束"""
        # 尝试创建指向不存在条目的别名
        alias = EntryAlias(alias_text="invalid", entry_id=99999)
        db_session.add(alias)
        
        with pytest.raises(Exception):  # 应该抛出外键约束异常
            db_session.commit()
        
        # 尝试创建指向不存在条目的后续问题
        follow_up = FollowUp(entry_id=99999, question="?", answer="?")
        db_session.add(follow_up)
        
        with pytest.raises(Exception):  # 应该抛出外键约束异常
            db_session.commit()


class TestCascadeDelete:
    """级联删除测试"""
    
    def test_delete_knowledge_entry_cascade(self, db_session: Session):
        """测试删除知识条目时的级联删除"""
        # 创建知识条目
        entry = KnowledgeEntry(
            query_text="Haus",
            entry_type="WORD",
            analysis_markdown="# Haus\n\n**词性**: Nomen"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名和后续问题
        alias = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        follow_up = FollowUp(entry_id=entry.id, question="?", answer="?")
        db_session.add_all([alias, follow_up])
        db_session.commit()
        
        # 验证数据存在
        assert db_session.query(EntryAlias).filter_by(entry_id=entry.id).count() == 1
        assert db_session.query(FollowUp).filter_by(entry_id=entry.id).count() == 1
        
        # 删除知识条目
        db_session.delete(entry)
        db_session.commit()
        
        # 验证级联删除
        assert db_session.query(EntryAlias).filter_by(entry_id=entry.id).count() == 0
        assert db_session.query(FollowUp).filter_by(entry_id=entry.id).count() == 0
        assert db_session.query(KnowledgeEntry).filter_by(id=entry.id).count() == 0
