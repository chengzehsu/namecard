"""重構後的 LINE Bot 主入口 - 模塊化版本"""

import logging
import os
import sys
from datetime import datetime

from flask import Flask, request
from linebot import LineBotApi, WebhookHandler

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
sys.path.insert(0, root_dir)

from linebot.models import MessageEvent

from simple_config import Config
from src.namecard.api.line_bot.handlers.image_handler import ImageMessageHandler
from src.namecard.api.line_bot.handlers.message_handler import MessageHandler

# 修復導入路徑
from src.namecard.api.line_bot.handlers.text_handler import TextMessageHandler
from src.namecard.api.line_bot.handlers.webhook_handler import (
    WebhookHandler as CustomWebhookHandler,
)
from src.namecard.api.line_bot.routes.api_status import create_api_status_blueprint
from src.namecard.api.line_bot.routes.health import create_health_blueprint
from src.namecard.api.line_bot.utils import initialize_all_services


class LineBot:
    """LINE Bot 主應用類"""

    def __init__(self):
        self.app = Flask(__name__)
        self.config = Config
        self.services = {}
        self.line_bot_api = None
        self.handler = None
        self.webhook_handler = None
        self.message_handler = None

        self._setup_logging()
        self._validate_config()
        self._initialize_services()
        self._setup_line_bot()
        self._setup_handlers()
        self._register_routes()

    def _setup_logging(self):
        """設置日誌配置"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.StreamHandler(sys.stderr),
            ],
        )

        self.app.logger.setLevel(logging.INFO)
        self.app.logger.addHandler(logging.StreamHandler(sys.stdout))

    def _log_message(self, message, level="INFO"):
        """統一日誌輸出函數"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {level}: {message}"
        print(log_line, flush=True)
        sys.stdout.flush()
        return log_line

    def _validate_config(self):
        """驗證配置"""
        try:
            if not self.config.validate():
                self._log_message("❌ 配置驗證失敗", "ERROR")
                self._log_message("💡 請檢查環境變數設置", "INFO")
                exit(1)
            self._log_message("✅ 配置驗證成功")
        except Exception as e:
            self._log_message(f"❌ 配置錯誤: {e}", "ERROR")
            exit(1)

    def _initialize_services(self):
        """初始化所有服務"""
        try:
            self.services = initialize_all_services()
            self._log_message("✅ 服務初始化成功")
        except Exception as e:
            self._log_message(f"❌ 服務初始化失敗: {e}", "ERROR")
            exit(1)

    def _setup_line_bot(self):
        """設置 LINE Bot"""
        if self.config.LINE_CHANNEL_ACCESS_TOKEN and self.config.LINE_CHANNEL_SECRET:
            try:
                self.line_bot_api = LineBotApi(self.config.LINE_CHANNEL_ACCESS_TOKEN)
                self.handler = WebhookHandler(self.config.LINE_CHANNEL_SECRET)
                self._log_message("✅ LINE Bot 初始化成功")
            except Exception as e:
                self._log_message(f"⚠️ LINE Bot 初始化失敗: {e}", "WARNING")
        else:
            self._log_message("⚠️ LINE Bot 配置不完整，以基礎模式啟動", "WARNING")

    def _setup_handlers(self):
        """設置訊息處理器"""
        if self.line_bot_api and self.handler:
            # 創建各種處理器
            text_handler = TextMessageHandler(
                self.services["batch_manager"],
                self.services["safe_line_bot"],
                self.services["user_interaction_handler"],
                self.services["pr_creator"],
            )

            image_handler = ImageMessageHandler(
                self.services["batch_manager"],
                self.services["safe_line_bot"],
                self.services["multi_card_processor"],
                self.services["user_interaction_handler"],
            )

            # 主要訊息處理器
            self.message_handler = MessageHandler(text_handler, image_handler)

            # Webhook 處理器
            self.webhook_handler = CustomWebhookHandler(
                self.handler, self.line_bot_api, self.config
            )

            # 註冊 LINE SDK 事件處理器
            @self.handler.add(MessageEvent)
            def handle_message_event(event):
                self.message_handler.handle_message(event)

    def _register_routes(self):
        """註冊路由"""

        # 註冊 Webhook 路由
        @self.app.route("/callback", methods=["POST"])
        def callback():
            if self.webhook_handler:
                return self.webhook_handler.handle_callback()
            return "LINE Bot not configured", 503

        @self.app.route("/callback", methods=["GET"])
        def callback_info():
            if self.webhook_handler:
                return self.webhook_handler.handle_callback_info()
            return {"message": "LINE Bot not configured"}, 503

        # 註冊健康檢查藍圖
        health_bp = create_health_blueprint(
            self.services["notion_manager"], self.services["card_processor"]
        )
        self.app.register_blueprint(health_bp)

        # 註冊 API 狀態藍圖
        api_status_bp = create_api_status_blueprint(self.services["safe_line_bot"])
        self.app.register_blueprint(api_status_bp)

        # 調試通用路由
        @self.app.route("/", defaults={"path": ""})
        @self.app.route("/<path:path>")
        def catch_all(path):
            """捕獲所有請求以便調試"""
            print(f"🔍 收到請求: method={request.method}, path=/{path}")
            print(f"📋 Headers: {dict(request.headers)}")

            if path == "callback" and request.method == "POST":
                return callback()

            return {
                "message": "Debug endpoint",
                "path": f"/{path}",
                "method": request.method,
                "available_endpoints": ["/health", "/test", "/callback", "/api-status"],
            }

    def run(self, host="0.0.0.0", port=None, debug=False):
        """啟動應用"""
        if port is None:
            port = int(os.environ.get("PORT", 5002))

        self._log_message("🚀 LINE Bot 啟動中...")
        self._log_message(f"   端口: {port}")
        self._log_message(f"   除錯模式: {debug}")
        self._log_message(f"   健康檢查: http://localhost:{port}/health")
        self._log_message(f"   Webhook: http://localhost:{port}/callback")
        self._log_message("⚡ 系統已就緒，等待 LINE 用戶訊息...")
        self._log_message("=" * 60)

        self.app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,
        )


# 創建全域應用實例
line_bot_app = LineBot()
app = line_bot_app.app  # Flask 應用實例，供外部使用


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    line_bot_app.run(debug=debug_mode)
