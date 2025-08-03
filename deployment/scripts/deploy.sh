#!/bin/bash

# 🚀 LINE Bot 快速部署腳本

echo "🚀 開始部署 LINE Bot 到雲端..."

# 檢查檔案
echo "📋 檢查必要檔案..."
if [[ ! -f "railway_app.py" ]]; then
    echo "❌ railway_app.py 不存在"
    exit 1
fi

if [[ ! -f "requirements_deploy.txt" ]]; then
    echo "❌ requirements_deploy.txt 不存在"
    exit 1
fi

if [[ ! -f "Procfile" ]]; then
    echo "❌ Procfile 不存在"
    exit 1
fi

echo "✅ 所有檔案檢查完成"

# 提交到 Git
echo "📤 推送代碼到 GitHub..."
git add .
git commit -m "🚀 準備部署到雲端平台

- 更新應用包含最新功能
- 新增地址欄位支援
- 完整的雲端部署配置
- 包含所有必要依賴

準備在以下平台部署：
- Zeabur (推薦)
- Render
- Google Cloud Run"

git push origin main

echo "✅ 代碼已推送到 GitHub"

echo "
🎉 部署準備完成！

下一步：
1. 前往 Zeabur.com 註冊帳號
2. 連接你的 GitHub 倉庫
3. 設定環境變數
4. 一鍵部署！

📋 需要設定的環境變數：
- LINE_CHANNEL_SECRET
- LINE_CHANNEL_ACCESS_TOKEN  
- GOOGLE_API_KEY
- NOTION_API_KEY
- NOTION_DATABASE_ID
- PORT=8080

📖 詳細步驟請參考 DEPLOYMENT_GUIDE.md
"