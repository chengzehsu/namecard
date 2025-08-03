#!/bin/bash
# 異步名片處理服務啟動腳本

set -e

echo "🚀 啟動異步名片處理服務..."

# 檢查 Python 版本
python_version=$(python3 --version 2>&1 | cut -d" " -f2 | cut -d"." -f1,2)
echo "📍 Python 版本: $python_version"

# 檢查必要的環境變數
required_vars=(
    "GOOGLE_API_KEY"
    "NOTION_API_KEY" 
    "NOTION_DATABASE_ID"
    "LINE_CHANNEL_ACCESS_TOKEN"
    "LINE_CHANNEL_SECRET"
)

echo "🔍 檢查環境變數..."
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 缺少必要環境變數: $var"
        exit 1
    else
        echo "✅ $var: [已設置]"
    fi
done

# 設置預設值
export PORT=${PORT:-5002}
export MAX_CONCURRENT=${MAX_CONCURRENT:-20}
export CACHE_MEMORY_MB=${CACHE_MEMORY_MB:-200}
export WORKERS=${WORKERS:-4}

echo "⚙️ 服務配置:"
echo "  - 端口: $PORT"
echo "  - 最大並發: $MAX_CONCURRENT"
echo "  - 快取大小: ${CACHE_MEMORY_MB}MB"
echo "  - Worker 數量: $WORKERS"

# 檢查並安裝依賴
if [ -f "deployment/async_requirements.txt" ]; then
    echo "📦 安裝異步服務依賴..."
    pip install -r deployment/async_requirements.txt
else
    echo "⚠️ 找不到 async_requirements.txt，使用標準依賴"
    pip install -r requirements.txt quart hypercorn
fi

# 檢查服務健康狀態
echo "🏥 檢查服務組件..."

# 檢查 Redis（如果需要）
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis 連接正常"
    else
        echo "⚠️ Redis 未運行，將使用記憶體快取"
    fi
else
    echo "📝 Redis 未安裝，將使用記憶體快取"
fi

# 創建日誌目錄
mkdir -p logs

# 啟動服務
echo "🎯 啟動異步名片處理服務..."

if [ "$ENVIRONMENT" = "production" ]; then
    echo "🏭 生產模式啟動"
    exec hypercorn src.namecard.api.async_app:app \
        --bind 0.0.0.0:$PORT \
        --workers $WORKERS \
        --worker-class asyncio \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info
else
    echo "🔧 開發模式啟動"
    exec python3 -m src.namecard.api.async_app
fi