from collections import deque
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as api_router_v1
from app.core.llm_service import llm_router_instance
from app.db.models import Base
from app.db.session import engine

# 使用 lifespan 管理器来处理应用启动和关闭时的逻辑
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 在应用启动时执行的代码 ---
    print("--- 正在加载 De-AI-Hilfer 服务... ---")
    
    # 加载 .env 文件中的环境变量
    load_dotenv()
    
    # 初始化 LLMRouter 单例
    llm_router_instance.initialize()
    
    print("--- 正在初始化数据库... ---")
    try:
        Base.metadata.create_all(bind=engine)
        print("--- 数据库表创建成功 (如果不存在)。 ---")
    except Exception as e:
        print(f"!!! 数据库初始化失败: {e}")

    print("--- De-AI-Hilfer 服务加载完成 ---")
    
    yield # 应用在这里开始运行
    
    # --- 在应用关闭时执行的代码 ---
    print("--- De-AI-Hilfer 正在关闭... ---")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="De-AI-Hilfer API",
    description="为个人德语学习生态系统提供核心后端服务。",
    version="1.1.1", # 版本号+1
    lifespan=lifespan,
)

# 定义允许访问的源列表
origins = [
    "http://localhost:5173",  # SvelteKit 开发服务器
    "http://localhost",
    # 在未来，你还可以把你的Web应用的正式域名加进来
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # 允许所有HTTP方法
    allow_headers=["*"], # 允许所有HTTP请求头
)


# 包含 v1 版本的 API 路由
app.include_router(api_router_v1, prefix="/api/v1")

# 定义一个根路径，用于健康检查
@app.get("/", tags=["Health Check"])
def read_root():
    """
    一个简单的根端点，用于检查服务是否正在运行。
    """
    return {"status": "De-AI-Hilfer API is online."}