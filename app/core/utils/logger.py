"""結構化日誌系統

提供統一的日誌管理和結構化日誌功能。
"""

import json
import logging
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union


class LogLevel(Enum):
    """日誌等級枚舉"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """結構化日誌記錄器"""

    def __init__(
        self,
        name: str,
        level: Union[str, LogLevel] = LogLevel.INFO,
        enable_structured: bool = True,
        mask_sensitive: bool = True,
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.enable_structured = enable_structured
        self.mask_sensitive = mask_sensitive

        # 設置日誌等級
        if isinstance(level, str):
            level = LogLevel(level.upper())
        self.logger.setLevel(getattr(logging, level.value))

        # 設置處理器
        self._setup_handlers()

        # 敏感資料關鍵字
        self.sensitive_keywords = {
            "password",
            "token",
            "key",
            "secret",
            "api_key",
            "access_token",
            "channel_secret",
            "channel_access_token",
            "notion_api_key",
            "google_api_key",
        }

    def _setup_handlers(self):
        """設置日誌處理器"""
        # 避免重複添加處理器
        if self.logger.handlers:
            return

        # 創建控制台處理器
        console_handler = logging.StreamHandler(sys.stdout)

        if self.enable_structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 確保不向父處理器傳播（避免重複）
        self.logger.propagate = False

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """遮罩敏感資料"""
        if not self.mask_sensitive:
            return data

        masked_data = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_keywords):
                if isinstance(value, str) and len(value) > 6:
                    masked_data[key] = f"{value[:3]}***{value[-3:]}"
                else:
                    masked_data[key] = "***"
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    self._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data

    def _create_log_entry(
        self,
        level: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """創建日誌條目"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "logger": self.name,
            "level": level,
            "message": message,
        }

        if extra_data:
            entry["data"] = self._mask_sensitive_data(extra_data)

        if exception:
            entry["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            }

        return entry

    def debug(self, message: str, **kwargs):
        """記錄調試訊息"""
        if self.enable_structured:
            entry = self._create_log_entry("DEBUG", message, kwargs)
            self.logger.debug(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """記錄資訊訊息"""
        if self.enable_structured:
            entry = self._create_log_entry("INFO", message, kwargs)
            self.logger.info(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """記錄警告訊息"""
        if self.enable_structured:
            entry = self._create_log_entry("WARNING", message, kwargs)
            self.logger.warning(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """記錄錯誤訊息"""
        if self.enable_structured:
            entry = self._create_log_entry("ERROR", message, kwargs, exception)
            self.logger.error(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            self.logger.error(message, exc_info=exception, extra=kwargs)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """記錄嚴重錯誤訊息"""
        if self.enable_structured:
            entry = self._create_log_entry("CRITICAL", message, kwargs, exception)
            self.logger.critical(json.dumps(entry, ensure_ascii=False, indent=2))
        else:
            self.logger.critical(message, exc_info=exception, extra=kwargs)

    @contextmanager
    def operation(self, operation_name: str, **context):
        """操作上下文管理器"""
        operation_id = context.get("operation_id", f"op_{datetime.now().timestamp()}")
        start_time = datetime.now()

        self.info(
            f"🚀 Starting operation: {operation_name}",
            operation_id=operation_id,
            operation_name=operation_name,
            **context,
        )

        try:
            yield operation_id
            duration = (datetime.now() - start_time).total_seconds()
            self.info(
                f"✅ Completed operation: {operation_name}",
                operation_id=operation_id,
                operation_name=operation_name,
                duration_seconds=duration,
                **context,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.error(
                f"❌ Failed operation: {operation_name}",
                exception=e,
                operation_id=operation_id,
                operation_name=operation_name,
                duration_seconds=duration,
                **context,
            )
            raise

    @contextmanager
    def user_context(self, user_id: str, **context):
        """用戶上下文管理器"""
        context["user_id"] = user_id

        # 可以在這裡添加用戶相關的上下文邏輯
        # 例如：用戶行為追蹤、個人化日誌等

        yield context

    def api_call(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """記錄 API 呼叫"""
        self.info(
            f"API call: {method} {url}",
            api_method=method,
            api_url=url,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )

    def business_event(
        self, event_name: str, entity_type: str, entity_id: str, **kwargs
    ):
        """記錄業務事件"""
        self.info(
            f"Business event: {event_name}",
            event_name=event_name,
            entity_type=entity_type,
            entity_id=entity_id,
            **kwargs,
        )

    def performance_metric(
        self, metric_name: str, value: Union[int, float], unit: str = "", **kwargs
    ):
        """記錄性能指標"""
        self.info(
            f"Performance metric: {metric_name} = {value}{unit}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs,
        )

    def security_event(self, event_type: str, severity: str = "INFO", **kwargs):
        """記錄安全事件"""
        log_method = getattr(self, severity.lower(), self.info)
        log_method(
            f"Security event: {event_type}",
            security_event=event_type,
            severity=severity,
            **kwargs,
        )


class StructuredFormatter(logging.Formatter):
    """結構化日誌格式化器"""

    def format(self, record):
        """格式化日誌記錄"""
        # 如果訊息已經是 JSON 格式，直接返回
        if record.getMessage().startswith("{"):
            return record.getMessage()

        # 否則創建結構化格式
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加額外資料
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                }:
                    log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


# 全域日誌器實例快取
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(
    name: str,
    level: Union[str, LogLevel] = LogLevel.INFO,
    enable_structured: bool = True,
    mask_sensitive: bool = True,
) -> StructuredLogger:
    """獲取日誌器實例（單例模式）"""

    if name not in _loggers:
        _loggers[name] = StructuredLogger(
            name=name,
            level=level,
            enable_structured=enable_structured,
            mask_sensitive=mask_sensitive,
        )

    return _loggers[name]


def configure_logging(
    level: Union[str, LogLevel] = LogLevel.INFO,
    enable_structured: bool = True,
    log_file: Optional[str] = None,
):
    """配置全域日誌設定"""

    # 設置根日誌器等級
    if isinstance(level, str):
        level = LogLevel(level.upper())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.value))

    # 清除現有處理器
    root_logger.handlers.clear()

    # 添加控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    if enable_structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(console_handler)

    # 添加文件處理器（如果指定）
    if log_file:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            log_file, maxBytes=100 * 1024 * 1024, backupCount=5  # 100MB
        )
        if enable_structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        root_logger.addHandler(file_handler)


# 便利的日誌器實例
default_logger = get_logger("namecard")


# 使用範例
"""
# 基本使用
logger = get_logger("my_service")
logger.info("Service started", port=5000)

# 操作追蹤
with logger.operation("processing_card", user_id="user123") as op_id:
    # 執行操作
    logger.info("Card processed successfully", operation_id=op_id)

# 用戶上下文
with logger.user_context("user123", session_id="sess456") as ctx:
    logger.info("User action", action="upload_card", **ctx)

# API 呼叫記錄
logger.api_call("POST", "/api/cards", status_code=200, duration_ms=1500)

# 業務事件
logger.business_event("card_processed", "business_card", "card123", confidence=0.95)

# 性能指標
logger.performance_metric("processing_time", 2.5, "seconds")

# 錯誤處理
try:
    # 某些操作
    pass
except Exception as e:
    logger.error("Operation failed", exception=e, context="additional_info")
"""
