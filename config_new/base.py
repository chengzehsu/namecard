"""基礎配置定義

定義了應用程式的基礎配置結構和環境無關的設定。
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Environment(Enum):
    """環境類型枚舉"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """日誌等級枚舉"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LineBotConfig:
    """LINE Bot 配置"""

    channel_secret: str
    channel_access_token: str
    webhook_verify_ssl: bool = True
    webhook_timeout_seconds: int = 30

    def __post_init__(self):
        """配置後驗證"""
        if not self.channel_secret:
            raise ValueError("LINE_CHANNEL_SECRET is required")
        if not self.channel_access_token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required")


@dataclass
class GoogleAIConfig:
    """Google AI 配置"""

    api_key: str
    fallback_api_key: Optional[str] = None
    model: str = "gemini-2.5-pro"
    max_retries: int = 3
    timeout_seconds: int = 60
    rate_limit_requests_per_minute: int = 60

    # AI 處理參數
    temperature: float = 0.1
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 2048

    def __post_init__(self):
        """配置後驗證"""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required")

        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")


@dataclass
class NotionConfig:
    """Notion 配置"""

    api_key: str
    database_id: str
    api_version: str = "2022-06-28"
    timeout_seconds: int = 30
    max_retries: int = 3

    # 資料庫欄位映射
    field_mappings: Dict[str, str] = field(
        default_factory=lambda: {
            "name": "Name",
            "company": "公司名稱",
            "department": "部門",
            "title": "職稱",
            "email": "Email",
            "phone": "電話",
            "address": "地址",
            "decision_influence": "決策影響力",
            "contact_source": "取得聯繫來源",
            "notes": "聯繫注意事項",
            "kpi_concerns": "窗口的困擾或 KPI",
        }
    )

    def __post_init__(self):
        """配置後驗證"""
        if not self.api_key:
            raise ValueError("NOTION_API_KEY is required")
        if not self.database_id:
            raise ValueError("NOTION_DATABASE_ID is required")


@dataclass
class SessionConfig:
    """會話管理配置"""

    timeout_minutes: int = 10
    cleanup_interval_minutes: int = 5
    max_concurrent_sessions: int = 100
    enable_persistence: bool = False
    persistence_backend: str = "memory"  # memory, redis, database

    # 批次處理配置
    batch_max_cards: int = 50
    batch_timeout_minutes: int = 30
    batch_auto_save_interval: int = 5


@dataclass
class SecurityConfig:
    """安全配置"""

    enable_signature_validation: bool = True
    allowed_origins: List[str] = field(default_factory=list)
    max_request_size_mb: int = 10
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 100

    # 敏感資料處理
    mask_sensitive_data_in_logs: bool = True
    enable_audit_logging: bool = True


@dataclass
class PerformanceConfig:
    """性能配置"""

    enable_async_processing: bool = True
    max_worker_threads: int = 4
    connection_pool_size: int = 10
    request_timeout_seconds: int = 30

    # 快取配置
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    max_cache_size_mb: int = 100


@dataclass
class MonitoringConfig:
    """監控配置"""

    enable_metrics: bool = True
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 30

    # 日誌配置
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured_logging: bool = True
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    max_log_file_size_mb: int = 100
    log_rotation_count: int = 5


@dataclass
class BaseConfig:
    """基礎配置類"""

    # 環境配置
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    port: int = 5002
    host: str = "0.0.0.0"

    # 服務配置
    line_bot: LineBotConfig = None
    google_ai: GoogleAIConfig = None
    notion: NotionConfig = None

    # 系統配置
    session: SessionConfig = field(default_factory=SessionConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # 額外配置
    extra_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """配置後初始化和驗證"""
        # 根據環境調整配置
        if self.environment == Environment.PRODUCTION:
            self.debug = False
            self.monitoring.log_level = LogLevel.INFO
            self.security.enable_signature_validation = True
        elif self.environment == Environment.DEVELOPMENT:
            self.debug = True
            self.monitoring.log_level = LogLevel.DEBUG
            self.security.enable_signature_validation = False
        elif self.environment == Environment.TESTING:
            self.debug = True
            self.monitoring.log_level = LogLevel.WARNING
            self.session.timeout_minutes = 1  # 快速測試

    @classmethod
    def from_env(cls) -> "BaseConfig":
        """從環境變數創建配置"""

        # 載入環境變數
        from dotenv import load_dotenv

        load_dotenv()

        # 環境檢測
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_name)
        except ValueError:
            environment = Environment.DEVELOPMENT

        # 必要配置檢查
        required_env_vars = {
            "LINE_CHANNEL_SECRET": os.getenv("LINE_CHANNEL_SECRET"),
            "LINE_CHANNEL_ACCESS_TOKEN": os.getenv("LINE_CHANNEL_ACCESS_TOKEN"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
            "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        }

        missing_vars = [k for k, v in required_env_vars.items() if not v]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        # 創建子配置
        line_bot_config = LineBotConfig(
            channel_secret=required_env_vars["LINE_CHANNEL_SECRET"],
            channel_access_token=required_env_vars["LINE_CHANNEL_ACCESS_TOKEN"],
            webhook_timeout_seconds=int(os.getenv("LINE_WEBHOOK_TIMEOUT", "30")),
        )

        google_ai_config = GoogleAIConfig(
            api_key=required_env_vars["GOOGLE_API_KEY"],
            fallback_api_key=os.getenv("GOOGLE_API_KEY_FALLBACK"),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            timeout_seconds=int(os.getenv("GOOGLE_AI_TIMEOUT", "60")),
            temperature=float(os.getenv("GOOGLE_AI_TEMPERATURE", "0.1")),
        )

        notion_config = NotionConfig(
            api_key=required_env_vars["NOTION_API_KEY"],
            database_id=required_env_vars["NOTION_DATABASE_ID"],
            timeout_seconds=int(os.getenv("NOTION_TIMEOUT", "30")),
        )

        # 會話配置
        session_config = SessionConfig(
            timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "10")),
            batch_timeout_minutes=int(os.getenv("BATCH_TIMEOUT_MINUTES", "30")),
            max_concurrent_sessions=int(os.getenv("MAX_CONCURRENT_SESSIONS", "100")),
        )

        # 性能配置
        performance_config = PerformanceConfig(
            enable_async_processing=os.getenv("ENABLE_ASYNC", "true").lower() == "true",
            max_worker_threads=int(os.getenv("MAX_WORKER_THREADS", "4")),
            connection_pool_size=int(os.getenv("CONNECTION_POOL_SIZE", "10")),
        )

        # 監控配置
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO

        monitoring_config = MonitoringConfig(
            log_level=log_level,
            enable_structured_logging=os.getenv("STRUCTURED_LOGGING", "true").lower()
            == "true",
            log_to_file=os.getenv("LOG_TO_FILE", "false").lower() == "true",
            log_file_path=os.getenv("LOG_FILE_PATH"),
        )

        return cls(
            environment=environment,
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            port=int(os.getenv("PORT", "5002")),
            host=os.getenv("HOST", "0.0.0.0"),
            line_bot=line_bot_config,
            google_ai=google_ai_config,
            notion=notion_config,
            session=session_config,
            performance=performance_config,
            monitoring=monitoring_config,
        )

    def validate(self) -> List[str]:
        """驗證配置並返回錯誤列表"""
        errors = []

        # 驗證必要配置
        if not self.line_bot:
            errors.append("LINE Bot configuration is missing")
        if not self.google_ai:
            errors.append("Google AI configuration is missing")
        if not self.notion:
            errors.append("Notion configuration is missing")

        # 驗證端口範圍
        if not 1024 <= self.port <= 65535:
            errors.append(f"Port {self.port} is not in valid range (1024-65535)")

        # 驗證會話配置
        if self.session.timeout_minutes <= 0:
            errors.append("Session timeout must be positive")

        # 驗證性能配置
        if self.performance.max_worker_threads <= 0:
            errors.append("Max worker threads must be positive")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於序列化）"""
        from dataclasses import asdict

        return asdict(self)

    def get_sensitive_fields(self) -> List[str]:
        """獲取敏感欄位列表（用於日誌遮罩）"""
        return [
            "line_bot.channel_secret",
            "line_bot.channel_access_token",
            "google_ai.api_key",
            "google_ai.fallback_api_key",
            "notion.api_key",
        ]
