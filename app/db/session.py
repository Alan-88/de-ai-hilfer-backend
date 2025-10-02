import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中获取 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("未找到 DATABASE_URL 环境变量，请在 .env 文件中设置它。")

# 【修改】移除只针对 SQLite 的 connect_args
# create_engine 函数会自动为 PostgreSQL 选择正确的配置
engine = create_engine(DATABASE_URL)

# 创建一个配置好的 "Session" 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 一个简单的函数，用于创建一个新的数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
