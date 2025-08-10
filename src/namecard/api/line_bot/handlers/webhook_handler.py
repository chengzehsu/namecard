"""Webhook 處理器"""

import logging
import sys
from datetime import datetime

from flask import abort, request
from linebot.exceptions import InvalidSignatureError


class WebhookHandler:
    """處理 LINE Bot webhook 請求"""

    def __init__(self, handler, line_bot_api, config):
        self.handler = handler  # LINE SDK WebhookHandler
        self.line_bot_api = line_bot_api  # LINE Bot API
        self.config = config
        self.logger = logging.getLogger(__name__)

    def log_message(self, message, level="INFO"):
        """統一日誌輸出函數"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {level}: {message}"
        print(log_line, flush=True)
        sys.stdout.flush()
        return log_line

    def handle_callback(self):
        """處理 LINE Bot webhook 回調函數 - 容錯模式"""

        # 記錄請求資訊（使用統一日誌函數）
        self.log_message(f"📥 收到 POST 請求到 /callback")
        self.log_message(f"📋 Request headers: {dict(request.headers)}")

        # 檢查 LINE Bot 是否已初始化
        if not self.handler or not self.line_bot_api:
            self.log_message("⚠️ LINE Bot 未初始化，無法處理 webhook", "WARNING")
            return "LINE Bot not configured", 503

        # 1. 檢查 Content-Type（LINE 要求 application/json）
        content_type = request.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            self.log_message(f"❌ 錯誤的 Content-Type: {content_type}", "ERROR")
            return "Content-Type must be application/json", 400

        # 2. 獲取 X-Line-Signature header（必須）
        signature = request.headers.get("X-Line-Signature")
        if not signature:
            self.log_message("❌ 缺少必要的 X-Line-Signature header", "ERROR")
            return "Missing X-Line-Signature header", 400

        # 3. 獲取請求體
        body = request.get_data(as_text=True)
        if not body:
            self.log_message("❌ 空的請求體", "ERROR")
            return "Empty request body", 400

        self.log_message(f"📄 Request body length: {len(body)}")

        # 4. 驗證簽名並處理 webhook
        try:
            self.handler.handle(body, signature)
            self.log_message("✅ Webhook 處理成功")

            # LINE API 要求返回 200 狀態碼
            return "OK", 200

        except InvalidSignatureError as e:
            self.log_message(f"❌ 簽名驗證失敗: {e}", "ERROR")
            self.log_message(
                f"🔑 使用的 Channel Secret: {self.config.LINE_CHANNEL_SECRET[:10]}...",
                "ERROR",
            )
            abort(400)

        except Exception as e:
            self.log_message(f"❌ Webhook 處理過程中發生錯誤: {e}", "ERROR")
            import traceback

            traceback.print_exc()
            abort(500)

    def handle_callback_info(self):
        """顯示 callback 端點資訊 (GET 請求)"""
        return {
            "message": "LINE Bot webhook endpoint",
            "method": "POST only",
            "status": "ready",
        }
