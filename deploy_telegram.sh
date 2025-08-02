#!/bin/bash
# 部署 Telegram Bot 到 Zeabur

set -e  # 出錯時退出

echo "🚀 開始部署 Telegram Bot 到 Zeabur..."

# 檢查必要環境變數
if [[ -z "$ZEABUR_TOKEN" ]]; then
    echo "❌ 錯誤: ZEABUR_TOKEN 環境變數未設置"
    echo "請先設置 ZEABUR_TOKEN: export ZEABUR_TOKEN=your_token_here"
    exit 1
fi

if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
    echo "❌ 錯誤: TELEGRAM_BOT_TOKEN 環境變數未設置"
    echo "請先設置 TELEGRAM_BOT_TOKEN: export TELEGRAM_BOT_TOKEN=your_bot_token_here"
    exit 1
fi

# 檢查必要文件
echo "🔍 檢查必要文件..."
required_files=("telegram_app.py" "requirements-telegram.txt" "config.py" "zeabur.json")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ 錯誤: 缺少必要文件 $file"
        exit 1
    fi
    echo "✅ $file 存在"
done

# 檢查 Zeabur CLI
if ! command -v zeabur &> /dev/null; then
    echo "📦 安裝 Zeabur CLI..."
    
    # 創建目錄
    mkdir -p ~/.zeabur/bin
    
    # 下載並安裝 Zeabur CLI
    ZEABUR_VERSION="0.5.4"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="linux_amd64"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="darwin_amd64"
    else
        echo "❌ 不支援的操作系統: $OSTYPE"
        exit 1
    fi
    
    curl -sSL "https://github.com/zeabur/cli/releases/download/v${ZEABUR_VERSION}/zeabur_${ZEABUR_VERSION}_${PLATFORM}" -o ~/.zeabur/bin/zeabur
    chmod +x ~/.zeabur/bin/zeabur
    
    # 添加到 PATH
    export PATH="$HOME/.zeabur/bin:$PATH"
    echo "✅ Zeabur CLI 安裝完成"
else
    echo "✅ Zeabur CLI 已安裝"
fi

# 登入 Zeabur
echo "🔐 登入 Zeabur..."
echo "$ZEABUR_TOKEN" | zeabur auth login --token

# 專案和服務配置
PROJECT_NAME="namecard-telegram-bot"
SERVICE_NAME="namecard-app"

# 檢查專案是否存在
echo "📁 檢查專案 $PROJECT_NAME..."
if ! zeabur project list | grep -q "$PROJECT_NAME"; then
    echo "📁 創建新專案: $PROJECT_NAME"
    zeabur project create "$PROJECT_NAME"
else
    echo "✅ 專案已存在: $PROJECT_NAME"
fi

# 部署服務
echo "🚀 部署服務..."
DEPLOY_OUTPUT=$(zeabur service deploy \
    --project="$PROJECT_NAME" \
    --service="$SERVICE_NAME" \
    --source=. \
    --type=python 2>&1)

echo "$DEPLOY_OUTPUT"

# 設置環境變數
echo "🔧 設置環境變數..."
env_vars=(
    "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
    "GOOGLE_API_KEY=$GOOGLE_API_KEY"
    "GOOGLE_API_KEY_FALLBACK=$GOOGLE_API_KEY_FALLBACK"
    "NOTION_API_KEY=$NOTION_API_KEY"
    "NOTION_DATABASE_ID=$NOTION_DATABASE_ID"
    "PORT=5003"
    "FLASK_ENV=production"
    "PYTHONUNBUFFERED=1"
)

for env_var in "${env_vars[@]}"; do
    key=$(echo "$env_var" | cut -d'=' -f1)
    value=$(echo "$env_var" | cut -d'=' -f2-)
    
    if [[ -n "$value" && "$value" != "" ]]; then
        echo "🔑 設置環境變數: $key"
        zeabur env set \
            --project="$PROJECT_NAME" \
            --service="$SERVICE_NAME" \
            "$key" "$value" || echo "⚠️ 設置 $key 失敗"
    else
        echo "⚠️ 跳過空值環境變數: $key"
    fi
done

# 提取部署 URL
APP_URL=$(echo "$DEPLOY_OUTPUT" | grep -oP 'https://[^\s]+' | head -1)

if [[ -n "$APP_URL" ]]; then
    echo ""
    echo "🎉 部署成功!"
    echo "🔗 應用 URL: $APP_URL"
    echo "📞 Webhook URL: $APP_URL/telegram-webhook"
    echo ""
    echo "📋 後續步驟:"
    echo "1. 設置 Telegram Bot Webhook URL:"
    echo "   curl -X POST \"https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook\" \\"
    echo "        -H \"Content-Type: application/json\" \\"
    echo "        -d '{\"url\": \"$APP_URL/telegram-webhook\"}'"
    echo ""
    echo "2. 驗證 webhook 設置:"
    echo "   curl \"https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo\""
    echo ""
    echo "3. 測試 Bot 功能:"
    echo "   在 Telegram 中搜尋您的 Bot 並發送 /start"
else
    echo "⚠️ 部署完成，但無法提取 URL"
    echo "請前往 Zeabur Dashboard 查看: https://dash.zeabur.com/"
fi

echo ""
echo "✅ 部署腳本執行完成!"