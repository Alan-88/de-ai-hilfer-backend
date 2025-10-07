# 部署指南

## 概述

本文档详细介绍了De-AI-Hilfer-Backend项目的部署流程，包括开发环境、测试环境和生产环境的部署方案。

## 环境要求

### 系统要求
- **操作系统**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+
- **Python**: 3.11+
- **数据库**: PostgreSQL 12+ (生产), SQLite 3.31+ (开发)
- **内存**: 最低 2GB RAM
- **存储**: 最低 10GB 可用空间
- **网络**: 稳定的互联网连接

### 依赖服务
- **AI服务**: Gemini API, OpenAI API, 或 Ollama (本地)
- **数据库**: PostgreSQL (推荐) 或 SQLite
- **反向代理**: Nginx (推荐) 或 Apache

## 开发环境部署

### 1. 环境准备

#### 克隆项目
```bash
git clone https://github.com/Alan-88/de-ai-hilfer-backend.git
cd de-ai-hilfer-backend
```

#### 创建虚拟环境
```bash
# Python 3.11+
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

#### 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置设置

#### 环境变量配置
创建 `.env` 文件：
```bash
# 数据库配置
DATABASE_URL=sqlite:///./de_ai_hilfer.db
DB_ECHO=false

# AI服务配置
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# 应用配置
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

#### AI服务配置
创建 `config.yaml` 文件：
```yaml
llm:
  default_service: "gemini"
  services:
    gemini:
      api_key: "${GEMINI_API_KEY}"
      model: "gemini-pro"
      max_tokens: 2048
      temperature: 0.7
    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"
      max_tokens: 2048
      temperature: 0.7
    ollama:
      base_url: "http://localhost:11434"
      model: "llama2"
      max_tokens: 2048
      temperature: 0.7
```

### 3. 数据库初始化

#### 创建数据库表
```bash
# 使用Alembic创建数据库表
alembic upgrade head
```

#### 验证数据库连接
```bash
# 测试数据库连接
python -c "
from app.db.session import engine
from app.db.models import Base
Base.metadata.create_all(bind=engine)
print('数据库连接成功！')
"
```

### 4. 启动开发服务器

#### 使用uvicorn启动
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 验证服务启动
```bash
# 检查服务状态
curl http://localhost:8000/api/v1/status

# 查看API文档
open http://localhost:8000/docs
```

## 测试环境部署

### 1. 使用Docker部署

#### 构建Docker镜像
```bash
# 构建应用镜像
docker build -t de-ai-hilfer-backend:latest .

# 查看镜像
docker images | grep de-ai-hilfer-backend
```

#### 运行Docker容器
```bash
# 运行容器
docker run -d \
  --name de-ai-hilfer-backend \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/de_ai_hilfer.db \
  -e GEMINI_API_KEY=your-api-key \
  -v $(pwd)/data:/app/data \
  de-ai-hilfer-backend:latest

# 查看容器日志
docker logs -f de-ai-hilfer-backend
```

#### Docker Compose部署
创建 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/de_ai_hilfer
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - db
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=de_ai_hilfer
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

启动服务：
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止服务
docker-compose down
```

## 生产环境部署

### 1. 服务器准备

#### 系统配置
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nginx

# 创建应用用户
sudo useradd -m -s /bin/bash de-ai-hilfer
sudo usermod -aG sudo de-ai-hilfer
```

#### 防火墙配置
```bash
# 配置UFW防火墙
sudo ufw allow ssh
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw enable
```

### 2. 数据库配置

#### PostgreSQL安装配置
```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动PostgreSQL服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE de_ai_hilfer;
CREATE USER de_ai_hilfer WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE de_ai_hilfer TO de_ai_hilfer;
\q
EOF
```

### 3. 应用部署

#### 部署应用代码
```bash
# 切换到应用用户
sudo su - de-ai-hilfer

# 克隆代码
cd /opt
git clone https://github.com/Alan-88/de-ai-hilfer-backend.git
cd de-ai-hilfer-backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn
```

#### 配置生产环境
```bash
# 创建生产环境配置
cat > .env << EOF
DATABASE_URL=postgresql://de_ai_hilfer:your_secure_password@localhost/de_ai_hilfer
DB_ECHO=false

GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS=https://yourdomain.com
EOF
```

#### 数据库迁移
```bash
# 运行数据库迁移
alembic upgrade head
```

### 4. Gunicorn配置

#### 创建Gunicorn配置文件
创建 `gunicorn.conf.py`：
```python
# Gunicorn配置文件
import multiprocessing

# 服务器套接字
bind = "127.0.0.1:8000"

# 工作进程配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# 超时配置
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志配置
accesslog = "/var/log/de-ai-hilfer/access.log"
errorlog = "/var/log/de-ai-hilfer/error.log"
loglevel = "info"

# 进程命名
proc_name = "de-ai-hilfer"
```

#### 创建systemd服务文件
创建 `/etc/systemd/system/de-ai-hilfer-backend.service`：
```ini
[Unit]
Description=De-AI-Hilfer Backend Service
After=network.target postgresql.service

[Service]
Type=exec
User=de-ai-hilfer
Group=de-ai-hilfer
WorkingDirectory=/opt/de-ai-hilfer-backend
Environment=PATH=/opt/de-ai-hilfer-backend/venv/bin
ExecStart=/opt/de-ai-hilfer-backend/venv/bin/gunicorn -c gunicorn.conf.py app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5. Nginx反向代理配置

#### 安装Nginx
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 配置Nginx
创建 `/etc/nginx/sites-available/de-ai-hilfer`：
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 启用站点配置
```bash
# 删除默认站点
sudo rm /etc/nginx/sites-enabled/default

# 启用新站点
sudo ln -s /etc/nginx/sites-available/de-ai-hilfer /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 6. SSL证书配置

#### 使用Let's Encrypt
```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 7. 启动服务

#### 启动应用服务
```bash
# 启动应用服务
sudo systemctl start de-ai-hilfer-backend
sudo systemctl enable de-ai-hilfer-backend

# 查看服务状态
sudo systemctl status de-ai-hilfer-backend
```

#### 验证部署
```bash
# 检查服务状态
curl https://yourdomain.com/api/v1/status

# 测试API功能
curl -X POST https://yourdomain.com/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Haus", "entry_type": "WORD"}'
```

## 监控和维护

### 1. 日志管理

#### 应用日志
```bash
# 查看应用日志
sudo journalctl -u de-ai-hilfer-backend -f

# 查看错误日志
sudo journalctl -u de-ai-hilfer-backend -e

# 查看最近的日志
sudo journalctl -u de-ai-hilfer-backend --since "1 hour ago"
```

#### Nginx日志
```bash
# 查看Nginx访问日志
sudo tail -f /var/log/nginx/access.log

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log
```

### 2. 性能监控

#### 系统资源监控
```bash
# 安装监控工具
sudo apt install -y htop iotop nethogs

# 查看系统资源
htop
```

#### 应用性能监控
```bash
# 查看进程状态
ps aux | grep gunicorn

# 查看网络连接
netstat -tulpn | grep :8000

# 查看磁盘使用
df -h
```

### 3. 备份策略

#### 数据库备份
```bash
# 创建备份脚本
cat > /opt/de-ai-hilfer-backend/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/de-ai-hilfer"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/de_ai_hilfer_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -h localhost -U de_ai_hilfer -d de_ai_hilfer > $BACKUP_FILE

# 压缩备份
gzip $BACKUP_FILE

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_FILE.gz"
EOF

chmod +x /opt/de-ai-hilfer-backend/scripts/backup.sh

# 设置定时备份
sudo crontab -e
# 每天凌晨2点备份
0 2 * * * /opt/de-ai-hilfer-backend/scripts/backup.sh
EOF
```

## 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查服务状态
sudo systemctl status de-ai-hilfer-backend

# 查看详细错误
sudo journalctl -u de-ai-hilfer-backend -n 50

# 检查配置文件
cat /opt/de-ai-hilfer-backend/.env

# 检查端口占用
sudo netstat -tulpn | grep :8000
```

#### 2. 数据库连接失败
```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 测试数据库连接
psql -h localhost -U de_ai_hilfer -d de_ai_hilfer

# 检查数据库日志
sudo tail -f /var/log/postgresql/postgresql.log
```

#### 3. AI服务连接失败
```bash
# 测试API密钥
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent

# 检查网络连接
ping generativelanguage.googleapis.com

# 查看应用日志
sudo journalctl -u de-ai-hilfer-backend -f
```

## 安全最佳实践

### 1. 应用安全
- 使用HTTPS加密所有通信
- 定期更新依赖包
- 实施输入验证和输出编码
- 使用强密码和密钥管理

### 2. 数据库安全
- 使用强密码认证
- 限制数据库访问权限
- 定期备份数据
- 启用数据库日志审计

### 3. 系统安全
- 定期更新系统补丁
- 配置防火墙规则
- 禁用不必要的服务
- 使用非root用户运行应用

### 4. 网络安全
- 配置反向代理
- 启用DDoS保护
- 实施速率限制
- 监控异常流量

## 扩展部署

### 1. 负载均衡
```bash
# 配置多个应用实例
# 使用不同的端口启动多个实例
uvicorn app.main:app --port 8001
uvicorn app.main:app --port 8002
uvicorn app.main:app --port 8003

# 配置Nginx负载均衡
upstream backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}
```

### 2. 容器编排
使用Kubernetes或Docker Swarm进行大规模部署。

### 3. 云服务部署
支持AWS、Google Cloud、Azure等云平台部署。

---

*最后更新: 2025-10-02*
