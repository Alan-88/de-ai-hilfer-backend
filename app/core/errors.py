"""
错误消息定义模块

统一管理所有API错误消息，提供标准化的错误响应格式。
"""


class ErrorMessages:
    """API错误消息常量类"""

    # 通用错误
    NOT_FOUND = "资源未找到"
    INTERNAL_SERVER_ERROR = "服务器内部错误"
    BAD_REQUEST = "请求参数错误"
    UNAUTHORIZED = "未授权访问"
    FORBIDDEN = "禁止访问"

    # 数据库相关错误
    DATABASE_CONNECTION_ERROR = "数据库连接失败"
    DATABASE_URL_NOT_SET = "DATABASE_URL 环境变量未设置"
    DATABASE_BACKUP_FAILED = "数据库备份失败"
    DATABASE_RESTORE_FAILED = "数据库恢复失败"

    # 知识条目相关错误
    ENTRY_NOT_FOUND = "知识条目未找到"
    ENTRY_NOT_FOUND_WITH_ID = "ID为 {entry_id} 的知识条目未找到"
    ENTRY_ALREADY_EXISTS = "知识条目已存在"
    ENTRY_QUERY_NOT_FOUND = "知识条目 '{query_text}' 不存在"

    # 别名相关错误
    ALIAS_ALREADY_EXISTS = "'{alias_text}' 已作为别名存在"
    ALIAS_ENTRY_EXISTS = "'{alias_text}' 已作为核心知识条目存在"
    ALIAS_CREATE_SUCCESS = "成功将别名 '{alias_text}' 关联到 '{entry_query_text}'"

    # AI服务相关错误
    AI_SERVICE_ERROR = "LLM service failed to generate a valid response"
    AI_RESPONSE_INVALID = "AI 返回了无法解析的格式: {response_text}"
    AI_INFERENCE_FAILED = "AI 未能推断出有效的目标单词"

    # 文件相关错误
    FILE_NOT_FOUND = "文件未找到: {file_path}"
    INVALID_FILE_TYPE = "请上传一个有效的 .sql 数据库备份文件"
    INVALID_FILE_EXTENSION = "提供的路径不是一个 .sql 文件"
    FILE_REQUIRED = "必须通过文件上传或文件路径提供一个 .sql 备份文件"

    # 系统工具错误
    PG_DUMP_NOT_FOUND = (
        "服务器错误: 'pg_dump' 命令未找到。请确保 PostgreSQL 客户端工具已安装在后端环境中。"
    )
    PSQL_NOT_FOUND = (
        "服务器错误: 'psql' 命令未找到。请确保 PostgreSQL 客户端工具已安装在后端环境中。"
    )

    # 词汇分析相关错误
    SPELL_CHECK_WARNING = "[警告] 拼写检查器返回格式不规范，将 '{query}' 视为一个拼写正确的词。"
    PROTOTYPE_JSON_ERROR = "警告: AI返回的原型JSON格式错误: '{prototype_response_text}'。"
    PREVIEW_EXTRACTION_ERROR = "预览提取时发生轻微错误: {error}"

    # 备份恢复相关错误
    BACKUP_EXECUTION_FAILED = "[错误] pg_dump 执行失败: {error}"
    RESTORE_EXECUTION_FAILED = "[错误] psql 执行失败: {error}"
    BACKUP_FILE_CLEANUP = "[后台任务] 清理临时备份文件: {backup_path}"
    RESTORE_START = "[数据库导入] 开始从 {source_description} 恢复..."
    RESTORE_SUCCESS = "数据库从 {source_description} 恢复成功！新数据已生效。"


class HTTPStatusCodes:
    """HTTP状态码常量类"""

    # 成功响应
    OK = 200
    CREATED = 201
    NO_CONTENT = 204

    # 客户端错误
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409

    # 服务器错误
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


def create_error_response(status_code: int, detail: str, **kwargs) -> dict:
    """
    创建标准化的错误响应格式

    Args:
        status_code: HTTP状态码
        detail: 错误详情
        **kwargs: 额外的错误信息

    Returns:
        标准化的错误响应字典
    """
    error_response = {
        "error": True,
        "status_code": status_code,
        "detail": detail,
        "message": detail,  # 保持向后兼容
    }

    # 添加额外信息
    if kwargs:
        error_response.update(kwargs)

    return error_response
