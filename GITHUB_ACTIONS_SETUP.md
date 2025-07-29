# GitHub Actions 設置指南

## 📋 概述

本指南將帶您完成 Claude Code + GitHub Actions 整合的完整設置流程，包括 CI/CD 自動化和 AI 驅動的功能開發。

## 🔧 第一步：GitHub Repository Secrets 設置

### 1. 進入 GitHub Repository Settings

1. 前往您的 GitHub repository
2. 點擊 **Settings** 標籤
3. 在左側菜單中選擇 **Secrets and variables** → **Actions**

### 2. 設置必要的 Secrets

點擊 **New repository secret** 並逐一添加以下 secrets：

#### 🤖 LINE Bot 配置 (必要)
```
Secret Name: LINE_CHANNEL_ACCESS_TOKEN
Description: LINE Bot Channel Access Token
Value: [您的 LINE Bot Channel Access Token]

Secret Name: LINE_CHANNEL_SECRET  
Description: LINE Bot Channel Secret
Value: [您的 LINE Bot Channel Secret]
```

#### 🧠 AI 服務配置 (必要)
```
Secret Name: GOOGLE_API_KEY
Description: Google Gemini AI API Key
Value: [您的 Google Gemini API Key]
```

#### 📄 Notion 配置 (必要)
```
Secret Name: NOTION_API_KEY
Description: Notion Integration API Key  
Value: [您的 Notion API Key]

Secret Name: NOTION_DATABASE_ID
Description: Notion Database ID
Value: [您的 Notion Database ID]
```

#### 🤖 Claude Code AI 配置 (推薦)
```
Secret Name: ANTHROPIC_API_KEY
Description: Anthropic Claude API Key for AI automation
Value: [您的 Anthropic API Key - 可選]

Secret Name: OPENAI_API_KEY  
Description: OpenAI API Key (backup for AI features)
Value: [您的 OpenAI API Key - 可選]
```

#### 🚀 部署配置 (依需求)
```
Secret Name: RAILWAY_TOKEN
Description: Railway deployment token
Value: [您的 Railway Token - 如果使用 Railway]

Secret Name: HEROKU_API_KEY
Description: Heroku API Key for deployment  
Value: [您的 Heroku API Key - 如果使用 Heroku]
```

### 3. 驗證 Secrets 設置

設置完成後，您的 Secrets 列表應包含：
- ✅ `LINE_CHANNEL_ACCESS_TOKEN`
- ✅ `LINE_CHANNEL_SECRET`
- ✅ `GOOGLE_API_KEY`
- ✅ `NOTION_API_KEY`
- ✅ `NOTION_DATABASE_ID`
- ⚡ `ANTHROPIC_API_KEY` (推薦)
- ⚡ `OPENAI_API_KEY` (可選)
- 🚀 部署相關 tokens (依需求)

## 🎯 第二步：啟用 GitHub Actions

### 1. 檢查 Actions 是否啟用

1. 前往 repository 的 **Actions** 標籤
2. 如果看到 "Actions aren't enabled for this repository"，點擊 **Enable Actions**
3. 選擇 **Allow all actions and reusable workflows**

### 2. 驗證 Workflow 文件

確認以下文件存在於您的 repository：
```
.github/
└── workflows/
    ├── ci-cd.yml              # CI/CD 自動化
    └── claude-code.yml        # Claude Code AI 自動化
```

## 🧪 第三步：測試 CI/CD Pipeline

### 1. 觸發 CI/CD 測試

推送任何變更到 `main` 或 `develop` 分支：
```bash
git add .
git commit -m "test: 觸發 CI/CD pipeline"
git push origin main
```

### 2. 監控 Actions 執行

1. 前往 **Actions** 標籤
2. 查看 "名片管理 LINE Bot CI/CD" workflow
3. 確認所有步驟都通過：

   ✅ **test (Python 3.9, 3.10, 3.11)**
   - 代碼品質檢查 (flake8, black, isort)
   - 模組導入測試
   - 基本功能驗證
   
   ✅ **security-scan**
   - 安全漏洞掃描 (bandit)
   - 依賴安全檢查 (safety)
   
   ✅ **build-check**
   - 部署文件驗證

### 3. 查看測試結果

如果測試失敗：
1. 點擊失敗的 workflow run
2. 展開失敗的步驟查看詳細日誌
3. 根據錯誤信息修復問題
4. 重新推送代碼

## 🤖 第四步：測試 Claude Code AI 自動化

### 方法 1: 透過 GitHub Issue

1. **創建 Issue**
   - 前往 **Issues** 標籤
   - 點擊 **New issue**
   - 標題：`實現使用統計功能`
   - 描述：詳細說明您想要的功能

2. **添加標籤**
   - 在右側 **Labels** 中添加 `claude-code` 標籤
   - 如果沒有此標籤，需要先創建：
     - 前往 **Issues** → **Labels**
     - 點擊 **New label**
     - Name: `claude-code`
     - Color: `#0075ca` (藍色)
     - Description: `Trigger Claude Code AI automation`

3. **等待 AI 處理**
   - Claude Code workflow 會自動觸發
   - 前往 **Actions** 查看 "Claude Code AI 自動化" 運行狀態
   - AI 會分析需求並創建對應的 PR

### 方法 2: 透過 Issue 評論

1. 在任何 Issue 中評論：`@claude-code 請幫我實現登入功能`
2. 系統會自動觸發 Claude Code workflow

### 方法 3: 手動觸發

1. 前往 **Actions** 標籤
2. 選擇 "Claude Code AI 自動化" workflow
3. 點擊 **Run workflow**
4. 輸入功能描述：例如 `添加用戶認證系統`
5. 點擊 **Run workflow**

## 🔍 第五步：驗證完整流程

### 1. 端到端測試

完整的自動化流程應該是：
```
創建 Issue (標記 claude-code)
    ↓
Claude Code AI 分析需求
    ↓
自動創建功能分支
    ↓
生成代碼並創建 PR
    ↓
CI/CD Pipeline 自動運行
    ↓
代碼審查和合併
    ↓
自動部署 (如果配置)
```

### 2. 檢查清單

- [ ] 所有必要的 Secrets 已設置
- [ ] CI/CD Pipeline 成功運行
- [ ] Claude Code AI 能夠創建 PR
- [ ] 代碼品質檢查通過
- [ ] 安全掃描無問題
- [ ] 部署流程正常 (如適用)

## 🛠️ 故障排除

### 常見問題

#### 1. Secrets 無法訪問
**症狀**: workflow 中顯示環境變數為空
**解決**: 檢查 Secret 名稱是否正確，確保沒有拼寫錯誤

#### 2. API 配額超限
**症狀**: Google/Notion/Anthropic API 調用失敗
**解決**: 檢查各 API 的使用配額，升級計劃或等待配額重置

#### 3. Claude Code 無回應
**症狀**: 標記 `claude-code` 後沒有自動觸發
**解決**: 
- 檢查 `ANTHROPIC_API_KEY` 是否設置
- 確認 workflow 權限設置正確
- 查看 Actions 日誌排查問題

#### 4. CI/CD 測試失敗
**症狀**: 代碼品質檢查或測試失敗
**解決**:
```bash
# 本地運行相同檢查
pip install flake8 black isort
flake8 .
black --check .
isort --check-only .
```

### 獲取幫助

如果遇到問題：
1. 查看 GitHub Actions 的詳細日誌
2. 檢查 [Claude Code 文檔](https://docs.anthropic.com/claude-code)
3. 在專案 Issue 中報告問題
4. 參考 `CLAUDE.md` 中的故障排除部分

## 🎉 設置完成

設置完成後，您將擁有：

- 🔄 **自動化 CI/CD**: 每次推送代碼自動測試
- 🤖 **AI 驅動開發**: 用自然語言創建功能
- 🧪 **代碼品質保證**: 自動格式化和安全檢查
- 🚀 **快速迭代**: 從想法到代碼只需幾分鐘
- 📝 **完整文檔**: AI 自動生成技術文檔

開始使用 Claude Code 來加速您的開發吧！🚀