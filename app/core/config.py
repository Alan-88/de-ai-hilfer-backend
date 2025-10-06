"""
应用配置管理模块

集中管理应用的所有配置项，包括数据库配置、API配置等。
"""

import json
from typing import Optional, List

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """数据库配置类"""

    url: str = Field("sqlite:///./de_ai_hilfer.db", env="DATABASE_URL", description="数据库连接URL")
    echo: bool = Field(False, env="DB_ECHO", description="是否打印SQL语句")
    pool_size: int = Field(5, env="DB_POOL_SIZE", description="连接池大小")
    max_overflow: int = Field(10, env="DB_MAX_OVERFLOW", description="连接池最大溢出")

    class Config:
        env_prefix = "DB_"


class APIConfig(BaseSettings):
    """API配置类"""

    title: str = Field("De-AI-Hilfer API", description="API标题")
    description: str = Field("为个人德语学习生态系统提供核心后端服务。", description="API描述")
    version: str = Field("1.1.1", description="API版本")
    debug: bool = Field(False, env="DEBUG", description="调试模式")

    # CORS配置
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:5173",  # SvelteKit 开发服务器
            "http://localhost",
            "https://vercel.app",  # Vercel 域名
            "https://*.vercel.app",  # Vercel 子域名
            "https://de-ai-hilfer-webapp.vercel.app",  # 具体的Vercel应用域名
        ],
        env="CORS_ORIGINS",
        description="允许的CORS源",
    )

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """解析CORS_ORIGINS环境变量，支持JSON数组格式和逗号分隔格式"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # 尝试解析为JSON数组
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # 如果不是JSON，则按逗号分隔
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # 缓存配置
    recent_searches_limit: int = Field(10, description="最近搜索记录限制")
    cache_ttl: int = Field(3600, description="缓存TTL（秒）")

    class Config:
        env_prefix = "API_"


class BackupConfig(BaseSettings):
    """备份配置类"""

    backup_dir: str = Field("/tmp", description="备份文件目录")
    backup_retention_days: int = Field(7, description="备份文件保留天数")
    max_backup_size_mb: int = Field(100, description="最大备份文件大小（MB）")

    # 数据库工具路径
    pg_dump_path: str = Field("pg_dump", description="pg_dump命令路径")
    psql_path: str = Field("psql", description="psql命令路径")

    class Config:
        env_prefix = "BACKUP_"


class LoggingConfig(BaseSettings):
    """日志配置类"""

    level: str = Field("INFO", env="LOG_LEVEL", description="日志级别")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式"
    )
    file_path: Optional[str] = Field(None, env="LOG_FILE", description="日志文件路径")
    max_file_size_mb: int = Field(10, description="日志文件最大大小（MB）")
    backup_count: int = Field(5, description="日志文件备份数量")

    class Config:
        env_prefix = "LOG_"


class AppConfig(BaseSettings):
    """应用总配置类"""

    # 环境配置
    environment: str = Field("development", env="ENVIRONMENT", description="运行环境")

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # AI配置文件路径
    ai_config_path: str = Field("config.yaml", description="AI配置文件路径")

    # 应用特定配置
    max_analysis_length: int = Field(10000, description="最大分析文本长度")
    max_follow_up_length: int = Field(1000, description="最大追问文本长度")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


# 全局配置实例
settings = AppConfig()


def get_database_url() -> str:
    """获取数据库连接URL"""
    return settings.database.url


def get_ai_config_path() -> str:
    """获取AI配置文件路径"""
    return settings.ai_config_path


def is_debug_mode() -> bool:
    """是否为调试模式"""
    return settings.api.debug


def is_production() -> bool:
    """是否为生产环境"""
    return settings.environment.lower() == "production"


def is_development() -> bool:
    """是否为开发环境"""
    return settings.environment.lower() == "development"
