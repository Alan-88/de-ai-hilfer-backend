"""
pytest配置文件
提供测试夹具和配置
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db
from app.db.models import Base


# 测试数据库URL（使用内存SQLite）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# 创建测试数据库引擎
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 创建测试会话工厂
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """创建测试数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=test_engine)
    
    # 创建会话
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 清理所有表
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture
def sample_knowledge_entry_data():
    """示例知识条目数据"""
    return {
        "query_text": "Haus",
        "entry_type": "WORD",
        "analysis_markdown": """# Haus

**词性**: Nomen  
**词义**: 房子  
**词性**: das

## 核心释义 (Bedeutung)

* **n.** **房子** - 建筑物，供人居住的场所

## 语法信息

- **性**: das (中性)
- **数**: 复数形式: Häuser
- **格**: 在句子中可作主语、宾语等

## 例句

1. Das Haus ist groß. (这所房子很大。)
2. Wir wohnen in einem alten Haus. (我们住在一所老房子里。)
"""
    }


@pytest.fixture
def sample_entry_alias_data():
    """示例条目别名数据"""
    return {
        "alias_text": "das Haus",
        "entry_id": 1
    }


@pytest.fixture
def sample_follow_up_data():
    """示例后续问题数据"""
    return {
        "question": "Haus的复数形式是什么？",
        "answer": "Häuser"
    }
