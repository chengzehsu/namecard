#!/bin/bash

# Telegram Bot 部署觸發腳本
echo "🚀 觸發 Telegram Bot 部署..."

# 添加一個小的變更來觸發重新部署
echo "# Deploy timestamp: $(date)" >> .deploy_trigger

# 提交變更
git add .deploy_trigger
git commit -m "trigger: 觸發 Telegram Bot 重新部署 - $(date)"
git push origin main

echo "✅ 部署觸發完成"
echo "⏳ 請等待 2-3 分鐘後檢查部署狀態"
echo "📱 或手動在 Zeabur Dashboard 重新部署: https://dash.zeabur.com"