"""配置工廠和設定管理

提供配置創建和環境特定設定的統一入口。
"""

import os
from typing import Any, Dict, Optional

from .base import BaseConfig, Environment


class ConfigurationError(Exception):
    """配置錯誤異常"""

    pass


def get_config(environment: Optional[str] = None) -> BaseConfig:
    """
    獲取配置實例

    Args:
        environment: 環境名稱，如果未提供則從環境變數讀取

    Returns:
        配置實例

    Raises:
        ConfigurationError: 配置錯誤時拋出
    """

    # 確定環境
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()

    try:
        env_enum = Environment(environment)
    except ValueError:
        raise ConfigurationError(f"Invalid environment: {environment}")

    # 創建基礎配置
    try:
        config = BaseConfig.from_env()
        config.environment = env_enum
    except ValueError as e:
        raise ConfigurationError(f"Configuration validation failed: {str(e)}")

    # 應用環境特定配置
    if env_enum == Environment.DEVELOPMENT:
        config = _apply_development_config(config)
    elif env_enum == Environment.STAGING:
        config = _apply_staging_config(config)
    elif env_enum == Environment.PRODUCTION:
        config = _apply_production_config(config)
    elif env_enum == Environment.TESTING:
        config = _apply_testing_config(config)

    # 最終驗證
    validation_errors = config.validate()
    if validation_errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        raise ConfigurationError(error_msg)

    return config


def _apply_development_config(config: BaseConfig) -> BaseConfig:
    """應用開發環境配置"""

    # 開發環境特定設定
    config.debug = True
    config.monitoring.log_level = config.monitoring.log_level.__class__.DEBUG
    config.monitoring.enable_structured_logging = True

    # 安全設定較寬鬆
    config.security.enable_signature_validation = False
    config.security.enable_rate_limiting = False

    # 性能設定
    config.performance.enable_async_processing = True
    config.performance.max_worker_threads = 2  # 開發環境資源有限

    # 會話設定
    config.session.timeout_minutes = 30  # 開發時更長超時
    config.session.cleanup_interval_minutes = 10

    # 額外開發配置
    config.extra_config.update(
        {
            "enable_debug_endpoints": True,
            "mock_external_apis": False,
            "enable_hot_reload": True,
        }
    )

    return config


def _apply_staging_config(config: BaseConfig) -> BaseConfig:
    """應用預發環境配置"""

    # 預發環境接近生產但保留調試能力
    config.debug = False
    config.monitoring.log_level = config.monitoring.log_level.__class__.INFO
    config.monitoring.enable_structured_logging = True

    # 安全設定適中
    config.security.enable_signature_validation = True
    config.security.enable_rate_limiting = True
    config.security.rate_limit_requests_per_minute = 200

    # 性能設定
    config.performance.enable_async_processing = True
    config.performance.max_worker_threads = 3
    config.performance.connection_pool_size = 15

    # 監控增強
    config.monitoring.enable_metrics = True
    config.monitoring.enable_health_checks = True

    # 額外預發配置
    config.extra_config.update(
        {
            "enable_debug_endpoints": True,
            "mock_external_apis": False,
            "enable_performance_profiling": True,
        }
    )

    return config


def _apply_production_config(config: BaseConfig) -> BaseConfig:
    """應用生產環境配置"""

    # 生產環境最嚴格配置
    config.debug = False
    config.monitoring.log_level = config.monitoring.log_level.__class__.INFO
    config.monitoring.enable_structured_logging = True
    config.monitoring.log_to_file = True

    # 安全設定最嚴格
    config.security.enable_signature_validation = True
    config.security.enable_rate_limiting = True
    config.security.rate_limit_requests_per_minute = 100
    config.security.mask_sensitive_data_in_logs = True
    config.security.enable_audit_logging = True

    # 性能設定優化
    config.performance.enable_async_processing = True
    config.performance.max_worker_threads = 4
    config.performance.connection_pool_size = 20
    config.performance.enable_caching = True

    # 會話管理嚴格
    config.session.timeout_minutes = 10
    config.session.cleanup_interval_minutes = 5
    config.session.max_concurrent_sessions = 200

    # 監控完整
    config.monitoring.enable_metrics = True
    config.monitoring.enable_health_checks = True
    config.monitoring.health_check_interval_seconds = 30

    # 額外生產配置
    config.extra_config.update(
        {
            "enable_debug_endpoints": False,
            "mock_external_apis": False,
            "enable_performance_monitoring": True,
            "enable_error_tracking": True,
        }
    )

    return config


def _apply_testing_config(config: BaseConfig) -> BaseConfig:
    """應用測試環境配置"""

    # 測試環境快速配置
    config.debug = True
    config.monitoring.log_level = (
        config.monitoring.log_level.__class__.WARNING
    )  # 減少測試噪音
    config.monitoring.enable_structured_logging = False

    # 安全設定寬鬆以利測試
    config.security.enable_signature_validation = False
    config.security.enable_rate_limiting = False

    # 性能設定簡化
    config.performance.enable_async_processing = False  # 同步測試更容易
    config.performance.max_worker_threads = 1
    config.performance.connection_pool_size = 5
    config.performance.enable_caching = False  # 避免測試間干擾

    # 會話設定快速超時
    config.session.timeout_minutes = 1
    config.session.cleanup_interval_minutes = 1
    config.session.max_concurrent_sessions = 10

    # 監控簡化
    config.monitoring.enable_metrics = False
    config.monitoring.enable_health_checks = False

    # 額外測試配置
    config.extra_config.update(
        {
            "enable_debug_endpoints": True,
            "mock_external_apis": True,
            "fast_test_mode": True,
            "disable_background_tasks": True,
        }
    )

    return config


def create_test_config(**overrides) -> BaseConfig:
    """
    創建測試專用配置

    Args:
        **overrides: 覆蓋的配置值

    Returns:
        測試配置實例
    """

    # 設置測試環境變數
    os.environ.update(
        {
            "ENVIRONMENT": "testing",
            "LINE_CHANNEL_SECRET": overrides.get("line_channel_secret", "test_secret"),
            "LINE_CHANNEL_ACCESS_TOKEN": overrides.get(
                "line_channel_access_token", "test_token"
            ),
            "GOOGLE_API_KEY": overrides.get("google_api_key", "test_google_key"),
            "NOTION_API_KEY": overrides.get("notion_api_key", "test_notion_key"),
            "NOTION_DATABASE_ID": overrides.get(
                "notion_database_id", "test_database_id"
            ),
        }
    )

    config = get_config("testing")

    # 應用覆蓋配置
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            config.extra_config[key] = value

    return config


def get_config_summary(config: BaseConfig) -> Dict[str, Any]:
    """
    獲取配置摘要（遮罩敏感資訊）

    Args:
        config: 配置實例

    Returns:
        配置摘要字典
    """

    summary = {
        "environment": config.environment.value,
        "debug": config.debug,
        "port": config.port,
        "host": config.host,
        "services": {
            "line_bot": {
                "configured": config.line_bot is not None,
                "webhook_timeout": (
                    config.line_bot.webhook_timeout_seconds if config.line_bot else None
                ),
            },
            "google_ai": {
                "configured": config.google_ai is not None,
                "model": config.google_ai.model if config.google_ai else None,
                "has_fallback": (
                    config.google_ai.fallback_api_key is not None
                    if config.google_ai
                    else False
                ),
            },
            "notion": {
                "configured": config.notion is not None,
                "api_version": config.notion.api_version if config.notion else None,
            },
        },
        "features": {
            "async_processing": config.performance.enable_async_processing,
            "caching": config.performance.enable_caching,
            "rate_limiting": config.security.enable_rate_limiting,
            "signature_validation": config.security.enable_signature_validation,
            "metrics": config.monitoring.enable_metrics,
            "health_checks": config.monitoring.enable_health_checks,
        },
        "limits": {
            "session_timeout_minutes": config.session.timeout_minutes,
            "max_concurrent_sessions": config.session.max_concurrent_sessions,
            "max_worker_threads": config.performance.max_worker_threads,
            "rate_limit_rpm": config.security.rate_limit_requests_per_minute,
        },
    }

    return summary


# 全域配置實例（延遲初始化）
_config_instance: Optional[BaseConfig] = None


def get_current_config() -> BaseConfig:
    """獲取當前配置實例（單例模式）"""
    global _config_instance

    if _config_instance is None:
        _config_instance = get_config()

    return _config_instance


def reset_config():
    """重置配置實例（主要用於測試）"""
    global _config_instance
    _config_instance = None
