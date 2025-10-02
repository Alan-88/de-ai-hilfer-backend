"""
统一异常处理模块

定义应用的自定义异常类和异常处理机制。
"""

import logging
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import HTTPStatusCodes, create_error_response

# 配置日志
logger = logging.getLogger(__name__)


class BaseAppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatusCodes.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class DatabaseException(BaseAppException):
    """数据库相关异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            details=details,
        )


class ValidationException(BaseAppException):
    """数据验证异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=HTTPStatusCodes.BAD_REQUEST, details=details)


class NotFoundException(BaseAppException):
    """资源未找到异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=HTTPStatusCodes.NOT_FOUND, details=details)


class ConflictException(BaseAppException):
    """资源冲突异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=HTTPStatusCodes.CONFLICT, details=details)


class AIServiceException(BaseAppException):
    """AI服务异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            details=details,
        )


class FileOperationException(BaseAppException):
    """文件操作异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            details=details,
        )


class ConfigurationException(BaseAppException):
    """配置异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            details=details,
        )


def create_app_exception(
    exception_class: type, message: str, details: Optional[Dict[str, Any]] = None
) -> BaseAppException:
    """
    创建应用异常的工厂函数

    Args:
        exception_class: 异常类
        message: 错误消息
        details: 错误详情

    Returns:
        应用异常实例
    """
    return exception_class(message=message, details=details)


def handle_database_error(error: Exception, operation: str = "数据库操作") -> DatabaseException:
    """
    处理数据库错误的统一函数

    Args:
        error: 原始异常
        operation: 操作描述

    Returns:
        DatabaseException实例
    """
    logger.error(f"{operation}失败: {str(error)}", exc_info=True)
    return DatabaseException(
        message=f"{operation}失败: {str(error)}",
        details={"operation": operation, "original_error": str(error)},
    )


def handle_validation_error(error: Exception, field: str = None) -> ValidationException:
    """
    处理验证错误的统一函数

    Args:
        error: 原始异常
        field: 验证失败的字段

    Returns:
        ValidationException实例
    """
    message = f"数据验证失败: {str(error)}"
    if field:
        message = f"字段 '{field}' 验证失败: {str(error)}"

    logger.warning(message)
    return ValidationException(
        message=message, details={"field": field, "original_error": str(error)}
    )


def handle_ai_service_error(error: Exception, operation: str = "AI服务调用") -> AIServiceException:
    """
    处理AI服务错误的统一函数

    Args:
        error: 原始异常
        operation: 操作描述

    Returns:
        AIServiceException实例
    """
    logger.error(f"{operation}失败: {str(error)}", exc_info=True)
    return AIServiceException(
        message=f"{operation}失败: {str(error)}",
        details={"operation": operation, "original_error": str(error)},
    )


def handle_file_operation_error(
    error: Exception, operation: str, file_path: str = None
) -> FileOperationException:
    """
    处理文件操作错误的统一函数

    Args:
        error: 原始异常
        operation: 操作描述
        file_path: 文件路径

    Returns:
        FileOperationException实例
    """
    message = f"{operation}失败: {str(error)}"
    if file_path:
        message = f"{operation}失败 ({file_path}): {str(error)}"

    logger.error(message, exc_info=True)
    return FileOperationException(
        message=message,
        details={
            "operation": operation,
            "file_path": file_path,
            "original_error": str(error),
        },
    )


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """
    应用异常处理器

    Args:
        request: FastAPI请求对象
        exc: 应用异常

    Returns:
        JSON响应
    """
    logger.error(f"应用异常: {exc.message}", exc_info=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code, detail=exc.message, **exc.details
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    请求验证异常处理器

    Args:
        request: FastAPI请求对象
        exc: 验证异常

    Returns:
        JSON响应
    """
    logger.warning(f"请求验证失败: {exc.errors()}")

    return JSONResponse(
        status_code=HTTPStatusCodes.BAD_REQUEST,
        content=create_error_response(
            status_code=HTTPStatusCodes.BAD_REQUEST,
            detail="请求参数验证失败",
            validation_errors=exc.errors(),
        ),
    )


async def http_exception_handler(
    request: Request, exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """
    HTTP异常处理器

    Args:
        request: FastAPI请求对象
        exc: HTTP异常

    Returns:
        JSON响应
    """
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(status_code=exc.status_code, detail=exc.detail),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器

    Args:
        request: FastAPI请求对象
        exc: 通用异常

    Returns:
        JSON响应
    """
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
        content=create_error_response(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            detail="服务器内部错误",
            original_error=str(exc),
        ),
    )


def setup_exception_handlers(app):
    """
    设置异常处理器

    Args:
        app: FastAPI应用实例
    """
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
