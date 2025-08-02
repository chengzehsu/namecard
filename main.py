# Telegram Bot 主入口文件 - 確保運行正確的應用
import os
import sys

# 設置路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 導入並啟動 Telegram Bot
from telegram_app import flask_app, setup_telegram_handlers, log_message

if __name__ == "__main__":
    # 設置 Telegram Bot 處理器
    setup_telegram_handlers()
    
    # 使用統一日誌輸出
    log_message("🚀 啟動 Telegram Bot 名片管理系統 via main.py...")
    log_message("📋 使用 Notion 作為資料庫")
    log_message("🤖 使用 Google Gemini AI 識別名片 + 多名片檢測")
    log_message("🎯 支援品質評估和用戶交互選擇")
    
    # 獲取端口配置
    port = int(os.environ.get("PORT", 5003))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    log_message(f"⚡ Telegram Bot 服務啟動中... 端口: {port}, Debug: {debug_mode}")
    
    # 生產環境配置
    flask_app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=False,
    )