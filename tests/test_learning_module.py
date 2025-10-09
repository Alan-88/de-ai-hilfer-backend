"""
学习模块API测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.db.models import KnowledgeEntry, LearningProgress

client = TestClient(app)


class TestLearningModule:
    """学习模块API测试类"""
    
    def test_get_learning_stats_empty(self, db_session: Session):
        """测试获取空的学习统计"""
        response = client.get("/api/v1/learning/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_words"] == 0
        assert data["due_today"] == 0
        assert data["average_ease_factor"] == 0.0
        assert data["mastery_distribution"] == []
    
    def test_get_learning_session_empty(self, db_session: Session):
        """测试获取空的学习会话"""
        response = client.get("/api/v1/learning/session")
        assert response.status_code == 200
        
        data = response.json()
        assert data["review_words"] == []
        assert data["new_words"] == []
    
    def test_add_word_to_learning(self, db_session: Session):
        """测试添加单词到学习计划"""
        # 首先创建一个测试单词
        test_entry = KnowledgeEntry(
            query_text="helfen",
            entry_type="WORD",
            analysis_markdown="### **helfen**\n\n#### 核心释义 (Bedeutung)\n* **v.** **帮助**"
        )
        db_session.add(test_entry)
        db_session.commit()
        db_session.refresh(test_entry)
        
        # 添加到学习计划
        response = client.post(f"/api/v1/learning/add/{test_entry.id}")
        assert response.status_code == 201
        
        data = response.json()
        assert data["entry_id"] == test_entry.id
        assert data["query_text"] == "helfen"
        assert data["mastery_level"] == 0
        assert data["review_count"] == 0
        assert data["ease_factor"] == 2.5
        assert data["interval"] == 0
        
        # 清理
        db_session.delete(test_entry)
        db_session.commit()
    
    def test_add_nonexistent_word_to_learning(self):
        """测试添加不存在的单词到学习计划"""
        response = client.post("/api/v1/learning/add/99999")
        assert response.status_code == 404
        assert "单词不存在" in response.json()["detail"]
    
    def test_get_word_insight(self, db_session: Session):
        """测试获取单词深度解析"""
        # 创建一个包含深度解析的测试单词
        test_entry = KnowledgeEntry(
            query_text="helfen",
            entry_type="WORD",
            analysis_markdown="""### **helfen**

#### 核心释义 (Bedeutung)
* **v.** **帮助**

#### 🧐 深度解析 (Einblicke)
* **多维解释**
    helfen是一个强变化动词，表示帮助或协助某人。它与helfen的用法相似，但在语法上有所不同。
* **词源 (Etymologie)**
    源自古高地德语"helfan"，意为"帮助"。
"""
        )
        db_session.add(test_entry)
        db_session.commit()
        db_session.refresh(test_entry)
        
        # 获取深度解析
        response = client.get(f"/api/v1/learning/insight/{test_entry.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["entry_id"] == test_entry.id
        assert "多维解释" in data["insight"]
        assert "词源" in data["insight"]
        
        # 清理
        db_session.delete(test_entry)
        db_session.commit()
    
    def test_get_insight_nonexistent_word(self):
        """测试获取不存在单词的深度解析"""
        response = client.get("/api/v1/learning/insight/99999")
        assert response.status_code == 404
    
    def test_submit_review_nonexistent_progress(self):
        """测试提交不存在学习进度的复习"""
        response = client.post("/api/v1/learning/review/99999?quality=5")
        assert response.status_code == 404
        assert "学习进度不存在" in response.json()["detail"]
    
    def test_submit_review_invalid_quality(self):
        """测试提交无效质量评分的复习"""
        response = client.post("/api/v1/learning/review/1?quality=10")
        assert response.status_code == 400
        assert "质量评分必须在0-5之间" in response.json()["detail"]
    
    def test_generate_example_nonexistent_word(self):
        """测试为不存在的单词生成例句"""
        response = client.post("/api/v1/learning/generate-example/99999")
        assert response.status_code == 400
        assert "单词不存在" in response.json()["detail"]
    
    def test_generate_quiz_nonexistent_word(self):
        """测试为不存在的单词生成题目"""
        response = client.post("/api/v1/learning/generate-quiz/99999")
        assert response.status_code == 400
        assert "单词不存在" in response.json()["detail"]


def test_learning_progress_algorithm(db_session: Session):
    """测试间隔重复算法"""
    from app.api.v1.learning_service import update_learning_progress_service
    
    # 创建测试数据
    test_entry = KnowledgeEntry(
        query_text="helfen",
        entry_type="WORD",
        analysis_markdown="### **helfen**\n\n#### 核心释义 (Bedeutung)\n* **v.** **帮助**"
    )
    db_session.add(test_entry)
    db_session.commit()
    db_session.refresh(test_entry)
    
    progress = LearningProgress(
        entry_id=test_entry.id,
        mastery_level=0,
        review_count=0,
        ease_factor=2.5,
        interval=0
    )
    db_session.add(progress)
    db_session.commit()
    db_session.refresh(progress)
    
    # 测试完全忘记 (quality=0)
    updated_progress = update_learning_progress_service(progress, 0, db_session)
    assert updated_progress.mastery_level == 0
    assert updated_progress.interval == 1
    assert updated_progress.ease_factor == 2.3  # 2.5 - 0.2
    
    # 测试完全掌握 (quality=5)
    updated_progress = update_learning_progress_service(updated_progress, 5, db_session)
    assert updated_progress.mastery_level == 1
    assert updated_progress.interval == 1
    
    # 再次完全掌握 (quality=5)
    updated_progress = update_learning_progress_service(updated_progress, 5, db_session)
    assert updated_progress.mastery_level == 2
    assert updated_progress.interval == 6
    
    # 第三次完全掌握 (quality=5)
    updated_progress = update_learning_progress_service(updated_progress, 5, db_session)
    assert updated_progress.mastery_level == 3
    assert updated_progress.interval == 15  # 6 * 2.5 (ease_factor)
    
    # 清理
    db_session.delete(progress)
    db_session.delete(test_entry)
    db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__])
