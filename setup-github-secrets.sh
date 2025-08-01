#!/bin/bash

# GitHub Secrets 設定腳本
# 用於快速設定 namecard LINE Bot 所需的 GitHub Secrets

echo "🔐 GitHub Secrets 設定工具"
echo "=========================="
echo ""

# 檢查是否安裝了 gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) 未安裝"
    echo "請先安裝 GitHub CLI: https://cli.github.com/"
    exit 1
fi

# 檢查是否已登入 GitHub
if ! gh auth status &> /dev/null; then
    echo "❌ 未登入 GitHub CLI"
    echo "請先執行: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI 已就緒"
echo ""

# 顯示目前已設定的 secrets
echo "📋 目前已設定的 Secrets:"
gh secret list
echo ""

# 設定 secrets 的函數
set_secret() {
    local secret_name=$1
    local description=$2
    local current_value=$3
    
    echo "🔑 設定 $secret_name"
    echo "   說明: $description"
    
    if [ -n "$current_value" ]; then
        echo "   目前狀態: ✅ 已設定"
        read -p "   是否要更新? (y/N): " update_choice
        if [[ ! "$update_choice" =~ ^[Yy]$ ]]; then
            echo "   ⏭️  跳過 $secret_name"
            echo ""
            return
        fi
    else
        echo "   目前狀態: ❌ 未設定"
    fi
    
    read -s -p "   請輸入 $secret_name 的值: " secret_value
    echo ""
    
    if [ -z "$secret_value" ]; then
        echo "   ⚠️  值為空，跳過設定"
        echo ""
        return
    fi
    
    if gh secret set "$secret_name" --body "$secret_value"; then
        echo "   ✅ $secret_name 設定成功"
    else
        echo "   ❌ $secret_name 設定失敗"
    fi
    echo ""
}

# 檢查目前的 secrets
echo "🔍 檢查目前的 Secrets 狀態..."
current_secrets=$(gh secret list --json name --jq '.[].name')

check_secret_exists() {
    echo "$current_secrets" | grep -q "^$1$"
}

# 設定各個 secrets
echo ""
echo "開始設定 Secrets..."
echo "==================="

# LINE Bot 設定
set_secret "LINE_CHANNEL_ACCESS_TOKEN" "LINE Bot Channel Access Token" $(check_secret_exists "LINE_CHANNEL_ACCESS_TOKEN" && echo "已設定" || echo "")
set_secret "LINE_CHANNEL_SECRET" "LINE Bot Channel Secret" $(check_secret_exists "LINE_CHANNEL_SECRET" && echo "已設定" || echo "")

# Google API 設定
set_secret "GOOGLE_API_KEY" "Google Gemini AI API Key (主要)" $(check_secret_exists "GOOGLE_API_KEY" && echo "已設定" || echo "")

# Notion 設定  
set_secret "NOTION_API_KEY" "Notion Integration API Key" $(check_secret_exists "NOTION_API_KEY" && echo "已設定" || echo "")
set_secret "NOTION_DATABASE_ID" "Notion Database ID" $(check_secret_exists "NOTION_DATABASE_ID" && echo "已設定" || echo "")

echo "🎉 Secrets 設定完成！"
echo ""

# 顯示最終的 secrets 列表
echo "📋 最終 Secrets 列表:"
gh secret list
echo ""

# 提示下一步
echo "🚀 下一步操作:"
echo "1. 驗證所有必要的 Secrets 都已設定"
echo "2. 執行部署: gh workflow run '部署到 Zeabur'"
echo "3. 檢查部署狀態: gh run list --limit 5"
echo ""

# 詢問是否立即部署
read -p "是否要立即觸發部署到 Zeabur? (y/N): " deploy_choice
if [[ "$deploy_choice" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 觸發部署..."
    gh workflow run "部署到 Zeabur"
    echo "✅ 部署已觸發"
    echo ""
    echo "📊 查看部署狀態:"
    echo "   gh run list --limit 3"
    echo "   gh run watch \$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')"
fi

echo ""
echo "🔗 相關連結:"
echo "- GitHub Actions: https://github.com/$(gh repo view --json owner,name --jq '.owner.login + \"/\" + .name')/actions"
echo "- Zeabur Dashboard: https://dash.zeabur.com/"
echo "- LINE Developers Console: https://developers.line.biz/console/"