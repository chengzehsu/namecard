"""依賴注入容器

定義了應用程式的依賴注入容器，管理所有服務的實例化和生命週期。
"""

from typing import Optional

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

# 導入配置
from config.settings import BaseConfig, get_current_config

# 導入接口
from .interfaces.ai_processor import AddressNormalizerInterface, AIProcessorInterface
from .interfaces.message_handler import (
    BatchManagerInterface,
    LineBotClientInterface,
    MessageHandlerInterface,
    UserInteractionInterface,
)
from .interfaces.storage_service import (
    CacheInterface,
    NotionStorageInterface,
    StorageServiceInterface,
)
from .utils.exceptions import ExceptionHandler

# 導入工具類
from .utils.logger import StructuredLogger


class Container(containers.DeclarativeContainer):
    """主要依賴注入容器"""

    # 核心配置
    config = providers.Configuration()

    # === 基礎設施層 ===

    # 日誌系統
    logger = providers.Singleton(StructuredLogger, name="namecard_app")

    # 異常處理器
    exception_handler = providers.Singleton(ExceptionHandler, logger=logger)

    # 快取服務
    cache_service = providers.Singleton(
        "app.infrastructure.persistence.memory_cache.MemoryCache",
        ttl_seconds=config.performance.cache_ttl_seconds,
        max_size_mb=config.performance.max_cache_size_mb,
    )

    # === 外部 API 客戶端 ===

    # LINE Bot 客戶端
    line_bot_client = providers.Singleton(
        "app.infrastructure.external_apis.line_bot_client.LineBotClient",
        channel_access_token=config.line_bot.channel_access_token,
        channel_secret=config.line_bot.channel_secret,
        timeout_seconds=config.line_bot.webhook_timeout_seconds,
        logger=logger,
    )

    # Google Gemini 客戶端
    gemini_client = providers.Singleton(
        "app.infrastructure.external_apis.gemini_client.GeminiClient",
        api_key=config.google_ai.api_key,
        fallback_api_key=config.google_ai.fallback_api_key,
        model=config.google_ai.model,
        timeout_seconds=config.google_ai.timeout_seconds,
        max_retries=config.google_ai.max_retries,
        temperature=config.google_ai.temperature,
        logger=logger,
    )

    # Notion 客戶端
    notion_client = providers.Singleton(
        "app.infrastructure.external_apis.notion_client.NotionClient",
        api_key=config.notion.api_key,
        database_id=config.notion.database_id,
        api_version=config.notion.api_version,
        timeout_seconds=config.notion.timeout_seconds,
        max_retries=config.notion.max_retries,
        logger=logger,
    )

    # === 核心服務層 ===

    # 地址正規化服務
    address_normalizer = providers.Singleton(
        "app.core.services.ai_services.address_normalizer_service.AddressNormalizerService",
        logger=logger,
    )

    # AI 處理服務
    ai_processor = providers.Singleton(
        "app.core.services.ai_services.gemini_processor_service.GeminiProcessorService",
        gemini_client=gemini_client,
        address_normalizer=address_normalizer,
        cache_service=cache_service,
        logger=logger,
    )

    # 儲存服務
    storage_service = providers.Singleton(
        "app.core.services.storage_services.notion_storage_service.NotionStorageService",
        notion_client=notion_client,
        field_mappings=config.notion.field_mappings,
        logger=logger,
    )

    # 名片處理服務
    single_card_service = providers.Factory(
        "app.core.services.card_processing.single_card_service.SingleCardService",
        ai_processor=ai_processor,
        storage_service=storage_service,
        logger=logger,
    )

    multi_card_service = providers.Factory(
        "app.core.services.card_processing.multi_card_service.MultiCardService",
        ai_processor=ai_processor,
        storage_service=storage_service,
        logger=logger,
    )

    # 批次處理服務
    batch_manager = providers.Singleton(
        "app.core.services.batch_service.BatchService",
        timeout_minutes=config.session.timeout_minutes,
        cleanup_interval_minutes=config.session.cleanup_interval_minutes,
        max_concurrent_sessions=config.session.max_concurrent_sessions,
        logger=logger,
    )

    # 用戶互動服務
    user_interaction_service = providers.Singleton(
        "app.core.services.user_interaction_service.UserInteractionService",
        timeout_minutes=config.session.timeout_minutes,
        cache_service=cache_service,
        logger=logger,
    )

    # === API 層服務 ===

    # 訊息處理器
    message_handler = providers.Factory(
        "app.api.controllers.message_handler.MessageHandler",
        single_card_service=single_card_service,
        multi_card_service=multi_card_service,
        batch_manager=batch_manager,
        user_interaction_service=user_interaction_service,
        line_bot_client=line_bot_client,
        logger=logger,
    )

    # Webhook 控制器
    webhook_controller = providers.Factory(
        "app.api.controllers.webhook_controller.WebhookController",
        message_handler=message_handler,
        line_bot_client=line_bot_client,
        exception_handler=exception_handler,
        logger=logger,
    )

    # 健康檢查控制器
    health_controller = providers.Factory(
        "app.api.controllers.health_controller.HealthController",
        ai_processor=ai_processor,
        storage_service=storage_service,
        cache_service=cache_service,
        logger=logger,
    )

    # === 監控和中間件 ===

    # 性能監控
    performance_monitor = providers.Singleton(
        "app.infrastructure.monitoring.performance_monitor.PerformanceMonitor",
        enable_metrics=config.monitoring.enable_metrics,
        logger=logger,
    )

    # 請求中間件
    request_middleware = providers.Factory(
        "app.api.middleware.request_middleware.RequestMiddleware",
        enable_rate_limiting=config.security.enable_rate_limiting,
        rate_limit_rpm=config.security.rate_limit_requests_per_minute,
        enable_signature_validation=config.security.enable_signature_validation,
        channel_secret=config.line_bot.channel_secret,
        performance_monitor=performance_monitor,
        logger=logger,
    )


class TestContainer(Container):
    """測試專用依賴注入容器"""

    def __init__(self):
        super().__init__()
        self._setup_test_overrides()

    def _setup_test_overrides(self):
        """設置測試專用的依賴覆蓋"""

        # 使用 Mock 客戶端
        self.line_bot_client.override(
            providers.Singleton("tests.mocks.mock_line_bot_client.MockLineBotClient")
        )

        self.gemini_client.override(
            providers.Singleton("tests.mocks.mock_gemini_client.MockGeminiClient")
        )

        self.notion_client.override(
            providers.Singleton("tests.mocks.mock_notion_client.MockNotionClient")
        )

        # 使用快速內存快取
        self.cache_service.override(
            providers.Singleton(
                "app.infrastructure.persistence.memory_cache.MemoryCache",
                ttl_seconds=60,
                max_size_mb=10,
            )
        )


# 全域容器實例
container: Optional[Container] = None
test_container: Optional[TestContainer] = None


def get_container() -> Container:
    """獲取全域容器實例"""
    global container

    if container is None:
        container = Container()
        # 載入配置
        config = get_current_config()
        container.config.from_pydantic(config)

        # 初始化 wiring
        container.wire(
            modules=[
                "app.api.controllers.webhook_controller",
                "app.api.controllers.health_controller",
                "app.core.services.card_processing.single_card_service",
                "app.core.services.card_processing.multi_card_service",
                "app.core.services.batch_service",
                "app.main",
            ]
        )

    return container


def get_test_container() -> TestContainer:
    """獲取測試容器實例"""
    global test_container

    if test_container is None:
        test_container = TestContainer()

        # 載入測試配置
        from config.settings import create_test_config

        test_config = create_test_config()
        test_container.config.from_pydantic(test_config)

        # 初始化測試 wiring
        test_container.wire(
            modules=["tests.unit.core.services", "tests.integration", "tests.e2e"]
        )

    return test_container


def reset_container():
    """重置容器（主要用於測試）"""
    global container, test_container
    container = None
    test_container = None


# 依賴注入裝飾器快捷方式
def inject_dependencies(func):
    """依賴注入裝飾器"""
    return inject(func)


# 常用依賴提供者
def provide_logger() -> StructuredLogger:
    """提供日誌器"""
    return Provide[Container.logger]


def provide_ai_processor() -> AIProcessorInterface:
    """提供 AI 處理器"""
    return Provide[Container.ai_processor]


def provide_storage_service() -> StorageServiceInterface:
    """提供儲存服務"""
    return Provide[Container.storage_service]


def provide_batch_manager() -> BatchManagerInterface:
    """提供批次管理器"""
    return Provide[Container.batch_manager]


def provide_line_bot_client() -> LineBotClientInterface:
    """提供 LINE Bot 客戶端"""
    return Provide[Container.line_bot_client]


# 容器上下文管理器
class ContainerContext:
    """容器上下文管理器"""

    def __init__(self, use_test_container: bool = False):
        self.use_test_container = use_test_container
        self.container = None

    def __enter__(self):
        if self.use_test_container:
            self.container = get_test_container()
        else:
            self.container = get_container()
        return self.container

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 異常處理日誌
            logger = self.container.logger()
            logger.error(f"Container context error: {exc_val}")


# 使用範例
"""
# 在服務中使用依賴注入
from app.core.container import inject_dependencies, provide_logger, provide_ai_processor

class SomeService:
    @inject_dependencies
    def __init__(
        self,
        logger: StructuredLogger = provide_logger(),
        ai_processor: AIProcessorInterface = provide_ai_processor()
    ):
        self.logger = logger
        self.ai_processor = ai_processor

# 在測試中使用
def test_something():
    with ContainerContext(use_test_container=True) as container:
        service = container.some_service()
        # 測試邏輯...
"""
