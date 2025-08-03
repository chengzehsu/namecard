#!/bin/bash

# Telegram Bot 手動部署腳本
# 用於診斷和修復 Zeabur 部署問題

set -e

echo "🚀 開始手動部署 Telegram Bot 到 Zeabur"
echo "📅 部署時間: $(date)"

# 檢查必要的環境變數
echo ""
echo "🔍 檢查環境變數..."
if [ -z "$ZEABUR_TOKEN" ]; then
    echo "❌ ZEABUR_TOKEN 未設置"
    echo "請設置: export ZEABUR_TOKEN=your_token_here"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN 未設置"
    echo "請先設置環境變數或創建 .env.telegram 文件"
    exit 1
fi

echo "✅ 環境變數檢查通過"

# 檢查必要文件
echo ""
echo "📁 檢查必要文件..."
required_files=(
    "main.py"
    "telegram_main.py" 
    "telegram_app.py"
    "requirements-telegram.txt"
    "zeabur.json"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file 存在"
    else
        echo "❌ $file 缺失"
        exit 1
    fi
done

# 檢查依賴是否正確安裝
echo ""
echo "🔍 檢查 Python 依賴..."
if python3 -c "import flask, telegram, google.generativeai" 2>/dev/null; then
    echo "✅ 關鍵依賴已安裝"
else
    echo "⚠️ 部分依賴缺失，嘗試安裝..."
    pip3 install -r requirements-telegram.txt
fi

# 測試應用啟動
echo ""
echo "🧪 測試應用導入..."
if python3 -c "
import sys
sys.path.insert(0, '.')
from telegram_app import flask_app
from config import Config
print('✅ 應用可以正常導入')
print(f'Bot Token: {\"已設置\" if Config.TELEGRAM_BOT_TOKEN else \"未設置\"}')
"; then
    echo "✅ 應用測試通過"
else
    echo "❌ 應用測試失敗"
    exit 1
fi

# 開始部署
echo ""
echo "🚀 開始部署到 Zeabur..."

# 安裝 Zeabur CLI (如果需要)
if ! command -v zeabur &> /dev/null; then
    echo "📦 安裝 Zeabur CLI..."
    npm install -g @zeabur/cli
fi

echo "🔐 使用 ZEABUR_TOKEN 認證..."
export ZEABUR_TOKEN="$ZEABUR_TOKEN"

# 嘗試部署
echo "📤 執行部署..."
if zeabur deploy --environment production 2>&1; then
    echo "✅ 初始部署完成"
else
    echo "⚠️ 部署命令執行可能有問題，繼續設置環境變數..."
fi

# 設置環境變數
echo ""
echo "⚙️ 設置環境變數..."
env_vars=(
    "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
    "GOOGLE_API_KEY=$GOOGLE_API_KEY"
    "GOOGLE_API_KEY_FALLBACK=$GOOGLE_API_KEY_FALLBACK"
    "NOTION_API_KEY=$NOTION_API_KEY"
    "NOTION_DATABASE_ID=$NOTION_DATABASE_ID"
    "GEMINI_MODEL=gemini-2.5-pro"
    "PORT=5003"
    "FLASK_ENV=production"
    "PYTHONUNBUFFERED=1"
    "SERVICE_TYPE=telegram-bot"
)

for var in "${env_vars[@]}"; do
    key=$(echo "$var" | cut -d'=' -f1)
    value=$(echo "$var" | cut -d'=' -f2-)
    
    if [[ -n "$value" && "$value" != "" ]]; then
        echo "設置 $key..."
        if zeabur variable set "$key" "$value" 2>/dev/null; then
            echo "✅ $key 設置成功"
        else
            echo "⚠️ $key 設置可能失敗"
        fi
    else
        echo "⚠️ 跳過空值: $key"
    fi
done

# 重新部署以套用環境變數
echo ""
echo "🔄 重新部署以套用環境變數..."
if zeabur redeploy 2>&1; then
    echo "✅ 重新部署完成"
else
    echo "⚠️ 重新部署可能有問題"
fi

# 等待服務啟動
echo ""
echo "⏳ 等待服務啟動 (60秒)..."
sleep 60

# 檢查部署狀態
echo ""
echo "🔍 檢查部署狀態..."

# 嘗試獲取 URL
DEPLOY_URL=""
if command -v zeabur &> /dev/null; then
    DEPLOY_URL=$(zeabur domain list 2>/dev/null | grep -o 'https://[^[:space:]]*' | head -1 || echo "")
fi

if [[ -z "$DEPLOY_URL" ]]; then
    DEPLOY_URL="https://namecard-app.zeabur.app"
    echo "⚠️ 使用預設 URL: $DEPLOY_URL"
else
    echo "✅ 獲取到部署 URL: $DEPLOY_URL"
fi

# 健康檢查
echo ""
echo "🏥 執行健康檢查..."
for i in {1..5}; do
    echo "⏳ 健康檢查嘗試 $i/5..."
    
    if curl -f -s --max-time 30 "$DEPLOY_URL/health" > /dev/null; then
        echo "✅ Telegram Bot 健康檢查通過！"
        
        # 顯示健康檢查詳細資訊
        HEALTH_INFO=$(curl -s "$DEPLOY_URL/health" 2>/dev/null || echo "無法獲取詳細資訊")
        echo "📊 健康檢查詳情: $HEALTH_INFO"
        break
    else
        echo "❌ 健康檢查失敗，等待 15 秒後重試..."
        if [[ $i -lt 5 ]]; then
            sleep 15
        fi
    fi
    
    if [[ $i -eq 5 ]]; then
        echo "❌ 健康檢查最終失敗"
        echo "🔍 嘗試診斷問題..."
        
        # 嘗試獲取服務狀態
        echo "📋 檢查服務狀態..."
        zeabur service list 2>&1 || echo "無法獲取服務列表"
        
        # 測試其他端點
        echo "📡 測試其他端點..."
        curl -s -I "$DEPLOY_URL/test" || echo "測試端點無響應"
    fi
done

echo ""
echo "📊 部署結果總結:"
echo "🌐 部署 URL: $DEPLOY_URL"
echo "📅 部署時間: $(date)"
echo "🔗 設置 Telegram Webhook:"
echo "   curl -X POST \"https://api.telegram.org/bot\$TELEGRAM_BOT_TOKEN/setWebhook\" \\"
echo "        -d \"url=$DEPLOY_URL/telegram-webhook\""
echo ""
echo "🎉 部署腳本執行完成！"