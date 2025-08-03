#!/usr/bin/env python3
"""
Telegram Bot 名片管理系統主入口 - 使用獨立版本
確保完全避免 LINE Bot 依賴
"""

import os
import sys

# 確保使用當前目錄的模組
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 導入並執行獨立的 Telegram Bot 主程序
if __name__ == "__main__":
    try:
        # 使用完全獨立的入口文件
        import telegram_main

        telegram_main.main()
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        print("嘗試使用備用方法...")

        # 備用啟動方法
        try:
            from telegram_app import flask_app, log_message, setup_telegram_handlers

            # 設置 Telegram Bot 處理器
            setup_telegram_handlers()

            # 使用統一日誌輸出
            log_message("🚀 啟動 Telegram Bot 名片管理系統 (備用方法)")
            log_message("📋 使用 Notion 作為資料庫")
            log_message("🤖 使用 Google Gemini AI 識別名片")

            # 獲取端口配置
            port = int(os.environ.get("PORT", 5003))
            debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

            log_message(f"⚡ Telegram Bot 服務啟動中... 端口: {port}")

            # 生產環境配置
            flask_app.run(
                host="0.0.0.0",
                port=port,
                debug=debug_mode,
                use_reloader=False,
            )
        except Exception as backup_error:
            print(f"❌ 備用方法也失敗: {backup_error}")
            sys.exit(1)
