#!/bin/bash

# 直接部署腳本 - 更新現有 Zeabur 服務為 Telegram Bot
# 這個腳本會更新現有的 namecard-app 服務來運行 Telegram Bot

set -e

echo "🚀 開始直接部署 Telegram Bot 到現有 Zeabur 服務..."

# 確保我們有最新的代碼
echo "📦 確保代碼是最新的..."
git add .
git commit -m "deploy: 觸發 Telegram Bot 直接部署 - $(date)" || echo "沒有新變更需要提交"
git push origin main

echo "✅ 代碼已推送，正在觸發部署..."

# 顯示部署信息
echo ""
echo "📋 **部署信息:**"
echo "- 目標服務: namecard-app.zeabur.app"
echo "- 入口點: python main.py"
echo "- 端口: 5003"
echo "- 應用類型: Telegram Bot"
echo ""

# 觸發 GitHub Actions 部署
echo "🎯 觸發 GitHub Actions 部署..."
gh workflow run "部署到 Zeabur" --ref main -f environment=production -f force_deploy=true

echo ""
echo "🔄 **監控部署進度:**"
echo "1. GitHub Actions: https://github.com/$(gh repo view --json owner,name -q '.owner.login + \"/\" + .name')/actions"
echo "2. Zeabur Dashboard: https://dash.zeabur.com/"
echo ""

echo "⏳ 等待部署完成..."
sleep 5

# 監控最新的部署
latest_run=$(gh run list --workflow="部署到 Zeabur" --limit=1 --json databaseId --jq '.[0].databaseId')
echo "📊 監控部署 Run ID: $latest_run"

# 等待部署完成並檢查結果
echo "🔍 監控部署狀態..."
gh run watch $latest_run

echo ""
echo "🎉 部署流程完成！"
echo ""
echo "📝 **後續步驟:**"
echo "1. 等待 1-2 分鐘讓服務完全重啟"
echo "2. 測試健康檢查: curl https://namecard-app.zeabur.app/health"
echo "3. 測試 Telegram webhook: curl https://namecard-app.zeabur.app/telegram-webhook"
echo "4. 設置 Telegram Bot Webhook 到新的 URL"
echo ""