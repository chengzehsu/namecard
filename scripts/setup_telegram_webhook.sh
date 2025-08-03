#!/bin/bash

# Telegram Bot Webhook 設置腳本
# 使用方法: ./setup_telegram_webhook.sh <BOT_TOKEN>

set -e

# 檢查參數
if [ -z "$1" ]; then
    echo "❌ 錯誤: 請提供 Telegram Bot Token"
    echo "使用方法: $0 <BOT_TOKEN>"
    echo ""
    echo "範例:"
    echo "  $0 123456789:ABCDEFGHijklmnopqrstuvwxyz"
    exit 1
fi

BOT_TOKEN="$1"
WEBHOOK_URL="https://namecard-app.zeabur.app/telegram-webhook"

echo "🔧 設置 Telegram Bot Webhook..."
echo "📱 Bot Token: ${BOT_TOKEN:0:10}..."
echo "🌐 Webhook URL: $WEBHOOK_URL"
echo ""

# 設置 Webhook
echo "📡 正在設置 webhook..."
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=$WEBHOOK_URL" \
  -d "drop_pending_updates=true")

echo "📥 設置回應: $RESPONSE"

# 驗證 Webhook 設置
echo ""
echo "🔍 驗證 webhook 設置..."
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")

echo "📊 Webhook 資訊: $WEBHOOK_INFO"

# 檢查設置是否成功
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo ""
    echo "✅ Telegram Bot Webhook 設置成功！"
    echo ""
    echo "📋 下一步："
    echo "1. 在 Telegram 中找到你的 Bot"
    echo "2. 發送 /start 測試基本響應"
    echo "3. 發送 /help 查看功能說明"
    echo "4. 發送名片圖片測試 AI 識別功能"
    echo ""
    echo "🔍 測試 webhook:"
    echo "  curl -X POST '$WEBHOOK_URL' -H 'Content-Type: application/json' -d '{}'"
else
    echo ""
    echo "❌ Webhook 設置失敗"
    echo "請檢查 Bot Token 是否正確"
fi