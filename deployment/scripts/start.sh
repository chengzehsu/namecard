#!/bin/bash

echo "🚀 啟動 Telegram Bot 名片管理系統..."
echo "📍 當前目錄: $(pwd)"
echo "📂 可用文件:"
ls -la *.py

echo "🔧 環境變數檢查:"
echo "PORT: ${PORT:-5003}"
echo "TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}..."

echo "🎯 啟動 Telegram Bot 應用..."
exec python telegram_app.py