# 使用官方的 Python 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /code

# 将依赖文件复制到工作目录
COPY requirements.txt .

# 安装项目依赖
# --no-cache-dir: 不缓存包，减小镜像体积
# --upgrade pip: 升级pip到最新版本
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# 将项目的所有文件复制到工作目录
COPY . .

# 暴露 FastAPI 应用运行的端口
EXPOSE 8000

# 容器启动时执行的命令
# 使用 uvicorn 启动 app.main 中的 app 实例
# --host 0.0.0.0: 让服务在容器外部可访问
# --port 8000: 指定服务运行的端口
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
