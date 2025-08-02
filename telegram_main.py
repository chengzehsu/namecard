#!/usr/bin/env python3
"""
Telegram Bot 名片管理系統 - 完全獨立入口
專門為 Telegram Bot 設計，不依賴任何 LINE Bot 模組
"""

import logging
import os
import sys
from datetime import datetime

# 設置 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


# 確保只導入 Telegram 相關模組
def safe_import():
    """安全導入，確保沒有 LINE Bot 依賴"""
    try:
        # 檢查關鍵依賴是否存在
        import flask
        import telegram
        from telegram.ext import Application

        # 導入我們的 Telegram Bot 應用
        from telegram_app import flask_app, log_message, setup_telegram_handlers

        return flask_app, setup_telegram_handlers, log_message
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        print("請檢查是否安裝了正確的依賴包:")
        print("pip install -r requirements-telegram.txt")
        sys.exit(1)


def main():
    """主函數 - 啟動 Telegram Bot"""

    # 安全導入
    flask_app, setup_telegram_handlers, log_message = safe_import()

    # 設置 Telegram Bot 處理器
    setup_telegram_handlers()

    # 輸出啟動信息
    log_message("🚀 啟動 Telegram Bot 名片管理系統 (獨立版本)")
    log_message("📋 使用 Notion 作為資料庫")
    log_message("🤖 使用 Google Gemini AI 識別名片")
    log_message("🎯 支援多名片檢測和品質評估")
    log_message("⚡ 完全獨立於 LINE Bot 系統")

    # 獲取配置
    port = int(os.environ.get("PORT", 5003))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    host = os.environ.get("HOST", "0.0.0.0")

    log_message(f"🌐 服務配置: {host}:{port}, Debug: {debug_mode}")

    try:
        # 啟動 Flask 應用
        flask_app.run(
            host=host,
            port=port,
            debug=debug_mode,
            use_reloader=False,  # 生產環境關閉重載
            threaded=True,  # 支援多線程
        )
    except Exception as e:
        log_message(f"❌ 啟動失敗: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
