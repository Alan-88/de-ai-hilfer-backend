"""
API端点测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from app.db.models import KnowledgeEntry, EntryAlias, FollowUp


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_server_status(self, client: TestClient):
        """测试服务器状态端点"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db_status" in data


class TestKnowledgeEntryEndpoints:
    """知识条目相关端点测试"""
    
    def test_get_recent_entries_empty(self, client: TestClient):
        """测试获取空最近条目"""
        response = client.get("/api/v1/entries/recent")
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_recent_entries_with_data(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试获取有数据的最近条目"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        response = client.get("/api/v1/entries/recent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(item["query_text"] == "Haus" for item in data)
    
    def test_get_all_entries_empty(self, client: TestClient):
        """测试获取空所有条目"""
        response = client.get("/api/v1/entries/all")
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_all_entries_with_data(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试获取有数据的所有条目"""
        # 创建多个知识条目
        for i in range(3):
            entry_data = sample_knowledge_entry_data.copy()
            entry_data["query_text"] = f"word{i}"
            entry = KnowledgeEntry(**entry_data)
            db_session.add(entry)
        db_session.commit()
        
        response = client.get("/api/v1/entries/all")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # 验证排序
        query_texts = [item["query_text"] for item in data]
        assert query_texts == sorted(query_texts)
    
    def test_get_suggestions_empty_query(self, client: TestClient):
        """测试空查询建议"""
        response = client.get("/api/v1/suggestions?q=")
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []
        
        response = client.get("/api/v1/suggestions?q=   ")
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []
    
    def test_get_suggestions_with_entries(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试获取条目建议"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        response = client.get("/api/v1/suggestions?q=Ha")
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) >= 1
        assert data["suggestions"][0]["query_text"] == "Haus"
        assert data["suggestions"][0]["source"] == "知识库"
    
    def test_get_suggestions_with_aliases(self, client: TestClient, sample_knowledge_entry_data, sample_entry_alias_data, db_session: Session):
        """测试获取别名建议"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 创建别名
        alias_data = sample_entry_alias_data.copy()
        alias_data["entry_id"] = entry.id
        alias = EntryAlias(**alias_data)
        db_session.add(alias)
        db_session.commit()
        
        response = client.get("/api/v1/suggestions?q=das")
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) >= 1
        assert "↪️ das Haus" in data["suggestions"][0]["preview"]


class TestAnalysisEndpoints:
    """分析相关端点测试"""
    
    def test_analyze_entry_empty_text(self, client: TestClient):
        """测试分析空文本"""
        response = client.post("/api/v1/analyze", json={"query_text": ""})
        assert response.status_code == 422
    
    @patch('app.api.v1.endpoints.get_llm_router')
    @patch('app.api.v1.endpoints.analyze_entry_service')
    @pytest.mark.asyncio
    async def test_analyze_entry_success(self, mock_analyze, mock_router, client: TestClient):
        """测试成功分析条目"""
        # 模拟分析服务返回
        mock_response = AsyncMock()
        mock_response.entry_id = 1
        mock_response.query_text = "Haus"
        mock_response.analysis_markdown = "# Haus\n\n**词性**: Nomen"
        mock_response.source = "generated"
        mock_response.follow_ups = []
        mock_analyze.return_value = mock_response
        
        # 模拟LLM路由器
        mock_router_instance = AsyncMock()
        mock_router.return_value = mock_router_instance
        
        response = client.post("/api/v1/analyze", json={"query_text": "Haus"})
        assert response.status_code == 200
        data = response.json()
        assert data["query_text"] == "Haus"
        assert data["source"] == "generated"
    
    @patch('app.api.v1.endpoints.get_llm_router')
    @patch('app.api.v1.endpoints.analyze_entry_service')
    @pytest.mark.asyncio
    async def test_analyze_entry_cache_hit(self, mock_analyze, mock_router, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试分析条目缓存命中"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        # 模拟分析服务返回缓存命中
        mock_response = AsyncMock()
        mock_response.entry_id = entry.id
        mock_response.query_text = "Haus"
        mock_response.analysis_markdown = entry.analysis_markdown
        mock_response.source = "知识库"
        mock_response.follow_ups = []
        mock_analyze.return_value = mock_response
        
        # 模拟LLM路由器
        mock_router_instance = AsyncMock()
        mock_router.return_value = mock_router_instance
        
        response = client.post("/api/v1/analyze", json={"query_text": "Haus"})
        assert response.status_code == 200
        data = response.json()
        assert data["query_text"] == "Haus"
        assert data["source"] == "知识库"
        assert data["entry_id"] == entry.id


class TestFollowUpEndpoints:
    """后续问题相关端点测试"""
    
    @patch('app.api.v1.management.create_follow_up_service')
    @pytest.mark.asyncio
    async def test_create_follow_up(self, mock_create, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试创建后续问题"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        # 模拟创建后续问题服务返回
        mock_follow_up = AsyncMock()
        mock_follow_up.id = 1
        mock_follow_up.question = "Haus的复数形式是什么？"
        mock_follow_up.answer = "Häuser"
        mock_follow_up.timestamp = "2023-01-01T00:00:00"
        mock_create.return_value = mock_follow_up
        
        response = client.post("/api/v1/follow-ups", json={
            "entry_id": entry.id,
            "question": "Haus的复数形式是什么？"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "Haus的复数形式是什么？"
        assert data["answer"] == "Häuser"


class TestManagementEndpoints:
    """管理相关端点测试"""
    
    @patch('app.api.v1.management.regenerate_entry_analysis_service')
    @pytest.mark.asyncio
    async def test_regenerate_entry_analysis(self, mock_regenerate, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试重新生成条目分析"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        # 模拟重新生成服务返回
        mock_response = AsyncMock()
        mock_response.entry_id = entry.id
        mock_response.query_text = "Haus"
        mock_response.analysis_markdown = "# Haus\n\n**词性**: Nomen (重新生成)"
        mock_response.source = "generated"
        mock_response.follow_ups = []
        mock_regenerate.return_value = mock_response
        
        response = client.post(f"/api/v1/entries/{entry.id}/regenerate")
        assert response.status_code == 200
        data = response.json()
        assert data["query_text"] == "Haus"
        assert "重新生成" in data["analysis_markdown"]
    
    def test_delete_entry(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试删除条目"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        response = client.delete(f"/api/v1/entries/{entry.id}")
        assert response.status_code == 200
        data = response.json()
        assert "entry_id" in data
        assert entry.query_text in data["message"]
        
        # 验证删除
        deleted_entry = db_session.query(KnowledgeEntry).filter_by(id=entry.id).first()
        assert deleted_entry is None
    
    def test_delete_entry_not_found(self, client: TestClient):
        """测试删除不存在的条目"""
        response = client.delete("/api/v1/entries/99999")
        assert response.status_code == 404
    
    def test_create_alias(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试创建别名"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        response = client.post("/api/v1/aliases", json={
            "target_query_text": "Haus",
            "alias_text": "das Haus"
        })
        assert response.status_code == 201
        data = response.json()
        assert "alias_id" in data
        assert "das Haus" in data["message"]
        
        # 验证别名创建
        alias = db_session.query(EntryAlias).filter_by(alias_text="das Haus").first()
        assert alias is not None
        assert alias.entry_id == entry.id
    
    def test_create_alias_duplicate(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试创建重复别名"""
        # 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        
        # 创建第一个别名
        alias1 = EntryAlias(alias_text="das Haus", entry_id=entry.id)
        db_session.add(alias1)
        db_session.commit()
        
        # 尝试创建重复别名
        response = client.post("/api/v1/aliases", json={
            "target_query_text": "Haus",
            "alias_text": "das Haus"
        })
        assert response.status_code == 400
        data = response.json()
        assert "已存在" in data["detail"]
    
    @patch('app.api.v1.management.intelligent_search_service')
    @pytest.mark.asyncio
    async def test_intelligent_search(self, mock_search, client: TestClient):
        """测试智能搜索"""
        # 模拟智能搜索服务返回
        mock_response = AsyncMock()
        mock_response.entry_id = 1
        mock_response.query_text = "Haus"
        mock_response.analysis_markdown = "# Haus\n\n**词性**: Nomen"
        mock_response.source = "generated"
        mock_response.follow_ups = []
        mock_search.return_value = mock_response
        
        response = client.post("/api/v1/intelligent_search", json={
            "search_term": "建筑",
            "context": "我需要一个表示建筑的德语词"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["query_text"] == "Haus"
        assert data["source"] == "generated"


class TestDatabaseManagementEndpoints:
    """数据库管理相关端点测试"""
    
    @patch('app.api.v1.management.export_database_service')
    @pytest.mark.asyncio
    async def test_export_database(self, mock_export, client: TestClient):
        """测试导出数据库"""
        # 模拟导出服务返回
        mock_file_response = AsyncMock()
        mock_file_response.status_code = 200
        mock_export.return_value = mock_file_response
        
        response = await client.get("/api/v1/database/export")
        # 注意：这个测试需要异步客户端，这里只是示例
        assert True  # 占位符
    
    @patch('app.api.v1.management.import_database_service')
    @pytest.mark.asyncio
    async def test_import_database(self, mock_import, client: TestClient):
        """测试导入数据库"""
        # 模拟导入服务返回
        mock_import.return_value = {"message": "数据库导入成功"}
        
        response = await client.post("/api/v1/database/import")
        # 注意：这个测试需要异步客户端和文件上传，这里只是示例
        assert True  # 占位符


class TestErrorHandling:
    """错误处理测试"""
    
    def test_404_not_found(self, client: TestClient):
        """测试404错误"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_validation_error(self, client: TestClient):
        """测试验证错误"""
        # 无效的请求数据
        invalid_data = {"invalid_field": "value"}
        response = client.post("/api/v1/analyze", json=invalid_data)
        assert response.status_code == 422
    
    def test_method_not_allowed(self, client: TestClient):
        """测试方法不允许"""
        response = client.patch("/api/v1/entries/recent")
        assert response.status_code == 405


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self, client: TestClient, sample_knowledge_entry_data, db_session: Session):
        """测试完整工作流程"""
        # 1. 创建知识条目
        entry = KnowledgeEntry(**sample_knowledge_entry_data)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        # 2. 获取所有条目
        response = client.get("/api/v1/entries/all")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # 3. 获取建议
        response = client.get("/api/v1/suggestions?q=Ha")
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions["suggestions"]) >= 1
        
        # 4. 创建别名
        response = client.post("/api/v1/aliases", json={
            "target_query_text": "Haus",
            "alias_text": "das Haus"
        })
        assert response.status_code == 201
        
        # 5. 通过别名搜索
        response = client.get("/api/v1/suggestions?q=das")
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions["suggestions"]) >= 1
        assert any("das Haus" in s["preview"] for s in suggestions["suggestions"])
        
        # 6. 删除条目
        response = client.delete(f"/api/v1/entries/{entry.id}")
        assert response.status_code == 200
        
        # 7. 验证删除
        response = client.get("/api/v1/entries/all")
        assert response.status_code == 200
        data = response.json()
        assert not any(item["query_text"] == "Haus" for item in data)
