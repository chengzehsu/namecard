"""異常處理系統

定義了應用程式的異常體系和統一錯誤處理機制。
"""

import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type


class ErrorCode(Enum):
    """錯誤代碼枚舉"""

    # 通用錯誤 (1000-1999)
    UNKNOWN_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    CONFIGURATION_ERROR = "E1002"
    TIMEOUT_ERROR = "E1003"
    RATE_LIMIT_ERROR = "E1004"

    # AI 處理錯誤 (2000-2999)
    AI_PROCESSING_FAILED = "E2000"
    AI_API_QUOTA_EXCEEDED = "E2001"
    AI_INVALID_RESPONSE = "E2002"
    AI_IMAGE_PROCESSING_FAILED = "E2003"
    AI_MODEL_UNAVAILABLE = "E2004"

    # 儲存服務錯誤 (3000-3999)
    STORAGE_ERROR = "E3000"
    NOTION_API_ERROR = "E3001"
    NOTION_DATABASE_NOT_FOUND = "E3002"
    NOTION_INVALID_PROPERTIES = "E3003"
    NOTION_PERMISSION_DENIED = "E3004"

    # LINE Bot 錯誤 (4000-4999)
    LINE_API_ERROR = "E4000"
    LINE_INVALID_SIGNATURE = "E4001"
    LINE_MESSAGE_SEND_FAILED = "E4002"
    LINE_WEBHOOK_ERROR = "E4003"

    # 業務邏輯錯誤 (5000-5999)
    BUSINESS_LOGIC_ERROR = "E5000"
    INVALID_CARD_DATA = "E5001"
    BATCH_SESSION_EXPIRED = "E5002"
    USER_SESSION_NOT_FOUND = "E5003"
    CARD_QUALITY_TOO_LOW = "E5004"

    # 系統錯誤 (6000-6999)
    SYSTEM_ERROR = "E6000"
    DATABASE_CONNECTION_ERROR = "E6001"
    EXTERNAL_SERVICE_UNAVAILABLE = "E6002"
    INSUFFICIENT_RESOURCES = "E6003"


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseException(Exception):
    """基礎異常類"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        recoverable: bool = True,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.severity = severity
        self.user_message = user_message or self._get_default_user_message()
        self.recoverable = recoverable
        self.timestamp = datetime.now()

        super().__init__(self.message)

    def _get_default_user_message(self) -> str:
        """獲取預設的用戶友好訊息"""
        user_messages = {
            ErrorCode.AI_PROCESSING_FAILED: "名片識別失敗，請重新拍攝清晰的名片照片",
            ErrorCode.AI_API_QUOTA_EXCEEDED: "系統暫時繁忙，請稍後再試",
            ErrorCode.NOTION_API_ERROR: "資料保存失敗，請稍後再試",
            ErrorCode.LINE_API_ERROR: "訊息發送失敗，請檢查網路連接",
            ErrorCode.BATCH_SESSION_EXPIRED: "批次會話已過期，請重新開始",
            ErrorCode.CARD_QUALITY_TOO_LOW: "名片品質太低，建議重新拍攝",
        }

        return user_messages.get(self.code, "系統發生錯誤，請稍後再試")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self):
        return f"[{self.code.value}] {self.message}"


class ValidationError(BaseException):
    """驗證錯誤"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[Type] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        if expected_type:
            details["expected_type"] = expected_type.__name__

        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )


class AIProcessingError(BaseException):
    """AI 處理錯誤"""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        api_response: Optional[Dict] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if model:
            details["model"] = model
        if api_response:
            details["api_response"] = api_response

        super().__init__(
            code=ErrorCode.AI_PROCESSING_FAILED,
            message=message,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class StorageError(BaseException):
    """儲存錯誤"""

    def __init__(
        self,
        message: str,
        storage_type: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if storage_type:
            details["storage_type"] = storage_type
        if operation:
            details["operation"] = operation

        super().__init__(
            code=ErrorCode.STORAGE_ERROR,
            message=message,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class LineBotError(BaseException):
    """LINE Bot 錯誤"""

    def __init__(
        self,
        message: str,
        line_error_code: Optional[str] = None,
        line_error_message: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if line_error_code:
            details["line_error_code"] = line_error_code
        if line_error_message:
            details["line_error_message"] = line_error_message

        super().__init__(
            code=ErrorCode.LINE_API_ERROR,
            message=message,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class BusinessLogicError(BaseException):
    """業務邏輯錯誤"""

    def __init__(
        self, message: str, business_context: Optional[Dict[str, Any]] = None, **kwargs
    ):
        details = kwargs.get("details", {})
        if business_context:
            details.update(business_context)

        super().__init__(
            code=ErrorCode.BUSINESS_LOGIC_ERROR,
            message=message,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ExceptionHandler:
    """統一異常處理器"""

    def __init__(self, logger=None):
        self.logger = logger
        self.error_statistics = {}

    def handle_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        處理異常並返回標準化錯誤響應

        Args:
            exception: 異常實例
            context: 額外上下文資訊

        Returns:
            標準化錯誤響應
        """
        context = context or {}

        # 如果是我們自定義的異常
        if isinstance(exception, BaseException):
            error_response = exception.to_dict()
        else:
            # 處理未預期的異常
            error_response = self._handle_unexpected_exception(exception)

        # 添加上下文資訊
        if context:
            error_response["context"] = context

        # 記錄統計
        self._record_error_statistics(error_response["error_code"])

        # 記錄日誌
        if self.logger:
            self.logger.error(
                f"Exception handled: {error_response['error_code']}",
                exception=exception,
                error_response=error_response,
                **context,
            )

        return error_response

    def _handle_unexpected_exception(self, exception: Exception) -> Dict[str, Any]:
        """處理未預期的異常"""

        # 嘗試根據異常類型映射到已知錯誤
        error_mappings = {
            ValueError: ErrorCode.VALIDATION_ERROR,
            TypeError: ErrorCode.VALIDATION_ERROR,
            TimeoutError: ErrorCode.TIMEOUT_ERROR,
            ConnectionError: ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
            FileNotFoundError: ErrorCode.CONFIGURATION_ERROR,
        }

        error_code = error_mappings.get(type(exception), ErrorCode.UNKNOWN_ERROR)

        return {
            "error_code": error_code.value,
            "message": str(exception),
            "user_message": "系統發生未預期錯誤，請稍後再試",
            "details": {
                "exception_type": type(exception).__name__,
                "traceback": traceback.format_exc(),
            },
            "severity": ErrorSeverity.HIGH.value,
            "recoverable": True,
            "timestamp": datetime.now().isoformat(),
        }

    def _record_error_statistics(self, error_code: str):
        """記錄錯誤統計"""
        if error_code not in self.error_statistics:
            self.error_statistics[error_code] = {
                "count": 0,
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
            }

        self.error_statistics[error_code]["count"] += 1
        self.error_statistics[error_code]["last_seen"] = datetime.now()

    def get_error_statistics(self) -> Dict[str, Any]:
        """獲取錯誤統計資訊"""
        return {
            "total_errors": sum(
                stat["count"] for stat in self.error_statistics.values()
            ),
            "error_breakdown": self.error_statistics,
            "most_common_errors": sorted(
                self.error_statistics.items(), key=lambda x: x[1]["count"], reverse=True
            )[:10],
        }

    def create_user_friendly_response(self, error: BaseException) -> str:
        """創建用戶友好的錯誤響應"""

        # 根據錯誤類型生成不同的建議
        suggestions = {
            ErrorCode.AI_PROCESSING_FAILED: [
                "📸 請確保名片照片清晰",
                "💡 建議在光線充足的環境下拍攝",
                "🔄 可以嘗試重新拍攝",
            ],
            ErrorCode.CARD_QUALITY_TOO_LOW: [
                "📐 請確保名片完整出現在畫面中",
                "🔍 避免名片模糊或反光",
                "📱 可以調整拍攝角度",
            ],
            ErrorCode.BATCH_SESSION_EXPIRED: [
                "⏰ 批次會話已超時",
                "🔄 請重新開始批次模式",
                "💾 已處理的名片資料已保存",
            ],
        }

        message_parts = [f"❌ {error.user_message}"]

        if error.code in suggestions:
            message_parts.append("\n💡 建議：")
            message_parts.extend(suggestions[error.code])

        if error.recoverable:
            message_parts.append("\n🔄 您可以重試此操作")

        return "\n".join(message_parts)


# 全域異常處理器實例
_exception_handler: Optional[ExceptionHandler] = None


def get_exception_handler(logger=None) -> ExceptionHandler:
    """獲取全域異常處理器實例"""
    global _exception_handler

    if _exception_handler is None:
        _exception_handler = ExceptionHandler(logger)

    return _exception_handler


# 裝飾器：自動異常處理
def handle_exceptions(logger=None, context_provider=None):
    """
    異常處理裝飾器

    Args:
        logger: 日誌器實例
        context_provider: 上下文提供函數
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_exception_handler(logger)
                context = context_provider() if context_provider else {}
                error_response = handler.handle_exception(e, context)

                # 可以根據需要決定是否重新拋出異常
                # 或者返回錯誤響應
                raise BaseException(
                    code=ErrorCode(error_response["error_code"]),
                    message=error_response["message"],
                    details=error_response.get("details", {}),
                    severity=ErrorSeverity(error_response["severity"]),
                )

        return wrapper

    return decorator


# 快捷函數
def raise_validation_error(message: str, **kwargs):
    """拋出驗證錯誤"""
    raise ValidationError(message, **kwargs)


def raise_ai_error(message: str, **kwargs):
    """拋出 AI 處理錯誤"""
    raise AIProcessingError(message, **kwargs)


def raise_storage_error(message: str, **kwargs):
    """拋出儲存錯誤"""
    raise StorageError(message, **kwargs)


def raise_linebot_error(message: str, **kwargs):
    """拋出 LINE Bot 錯誤"""
    raise LineBotError(message, **kwargs)


def raise_business_error(message: str, **kwargs):
    """拋出業務邏輯錯誤"""
    raise BusinessLogicError(message, **kwargs)


# 使用範例
"""
# 基本使用
try:
    # 某些操作
    pass
except Exception as e:
    handler = get_exception_handler(logger)
    error_response = handler.handle_exception(e, {'user_id': 'user123'})
    return error_response

# 使用裝飾器
@handle_exceptions(logger=my_logger)
def some_function():
    # 函數邏輯
    pass

# 拋出自定義異常
if not card_data:
    raise_validation_error("名片資料不能為空", field="card_data")

# 處理業務邏輯錯誤
if confidence_score < 0.5:
    raise BusinessLogicError(
        "名片識別信心度過低", 
        business_context={'confidence': confidence_score, 'threshold': 0.5}
    )
"""
