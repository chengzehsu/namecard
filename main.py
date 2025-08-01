"""新的應用入口點

使用重構後的架構啟動應用程式。
"""

import os
import sys

from flask import Flask

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.container import get_container
from app.core.utils.logger import configure_logging, get_logger
from config.settings import ConfigurationError, get_config


def create_app(config_override=None) -> Flask:
    """
    創建 Flask 應用實例

    Args:
        config_override: 配置覆蓋（主要用於測試）

    Returns:
        Flask 應用實例
    """

    # 載入配置
    try:
        if config_override:
            config = config_override
        else:
            config = get_config()
    except ConfigurationError as e:
        print(f"❌ 配置錯誤: {e}")
        sys.exit(1)

    # 配置日誌
    configure_logging(
        level=config.monitoring.log_level,
        enable_structured=config.monitoring.enable_structured_logging,
        log_file=(
            config.monitoring.log_file_path if config.monitoring.log_to_file else None
        ),
    )

    logger = get_logger("main")
    logger.info(
        "🚀 Starting namecard LINE Bot application",
        environment=config.environment.value,
    )

    # 創建 Flask 應用
    app = Flask(__name__)
    app.config.update(
        {
            "DEBUG": config.debug,
            "SECRET_KEY": os.urandom(24),  # 為 session 生成隨機密鑰
            "MAX_CONTENT_LENGTH": config.security.max_request_size_mb * 1024 * 1024,
        }
    )

    # 初始化依賴注入容器
    container = get_container()

    # 註冊路由
    _register_routes(app, container, logger)

    # 註冊錯誤處理器
    _register_error_handlers(app, container, logger)

    # 註冊中間件
    _register_middleware(app, container, logger)

    logger.info(
        "✅ Application initialized successfully", port=config.port, debug=config.debug
    )

    return app


def _register_routes(app: Flask, container, logger):
    """註冊應用路由"""

    # Webhook 路由
    @app.route("/callback", methods=["POST"])
    def webhook():
        """LINE Bot webhook 端點"""
        webhook_controller = container.webhook_controller()
        return webhook_controller.handle_webhook()

    # 健康檢查路由
    @app.route("/health", methods=["GET"])
    def health_check():
        """健康檢查端點"""
        health_controller = container.health_controller()
        return health_controller.check_health()

    # 測試路由
    @app.route("/test", methods=["GET"])
    def test():
        """測試端點"""
        return {
            "status": "OK",
            "message": "名片管理 LINE Bot 運行中",
            "version": "2.0.0-refactored",
            "environment": container.config.environment.value(),
        }

    # 狀態路由（詳細信息）
    @app.route("/status", methods=["GET"])
    def status():
        """詳細狀態信息"""
        try:
            health_controller = container.health_controller()
            return health_controller.get_detailed_status()
        except Exception as e:
            logger.error("Status check failed", exception=e)
            return {"error": "Status check failed"}, 500

    # 指標路由（如果啟用監控）
    if container.config.monitoring.enable_metrics():

        @app.route("/metrics", methods=["GET"])
        def metrics():
            """Prometheus 風格的指標端點"""
            performance_monitor = container.performance_monitor()
            return performance_monitor.get_metrics()

    logger.info("📍 Routes registered successfully")


def _register_error_handlers(app: Flask, container, logger):
    """註冊錯誤處理器"""

    exception_handler = container.exception_handler()

    @app.errorhandler(404)
    def not_found(error):
        logger.warning("404 Not Found", path=error.description)
        return {"error": "Not Found", "message": "請求的端點不存在"}, 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning("405 Method Not Allowed", method=error.description)
        return {"error": "Method Not Allowed", "message": "請求方法不被允許"}, 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("500 Internal Server Error", exception=error)
        error_response = exception_handler.handle_exception(error)
        return error_response, 500

    logger.info("🛡️ Error handlers registered successfully")


def _register_middleware(app: Flask, container, logger):
    """註冊中間件"""

    request_middleware = container.request_middleware()

    @app.before_request
    def before_request():
        """請求前處理"""
        return request_middleware.before_request()

    @app.after_request
    def after_request(response):
        """請求後處理"""
        return request_middleware.after_request(response)

    logger.info("🔧 Middleware registered successfully")


def main():
    """主入口函數"""

    # 載入配置
    try:
        config = get_config()
    except ConfigurationError as e:
        print(f"❌ 配置錯誤: {e}")
        sys.exit(1)

    # 創建應用
    app = create_app(config)

    # 獲取日誌器
    logger = get_logger("main")

    # 根據環境決定運行方式
    if config.environment.value == "development":
        logger.info("🔧 Running in development mode with Flask dev server")
        app.run(
            host=config.host,
            port=config.port,
            debug=config.debug,
            threaded=True,  # 支援多線程
        )
    else:
        logger.info("🚀 Running in production mode")
        # 生產環境應該使用 WSGI 服務器（如 Gunicorn）
        # 這裡提供基本的 Flask 服務器作為後備
        app.run(host=config.host, port=config.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
