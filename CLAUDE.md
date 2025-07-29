# 名片管理 LINE Bot - Claude 開發記錄

## 📋 專案概述

這是一個基於 LINE Bot 的智能名片管理系統，使用 Google Gemini AI 識別名片內容，並自動存入 Notion 資料庫。支援單張處理和批次處理模式，並整合 GitHub Actions 實現 CI/CD 自動化和 Claude Code AI 驅動開發。

## 🏗️ 系統架構

```
LINE Bot Webhook (Flask)
    ↓
名片圖片處理 (Google Gemini AI)
    ↓
地址正規化處理 (Address Normalizer) 🆕
    ↓
資料存儲 (Notion API)
    ↓
批次狀態管理 (內存管理)
    ↓
GitHub Actions CI/CD Pipeline
    ↓
Claude Code AI 自動化 (功能開發、測試、部署)
```

## 📂 檔案結構

```
namecard/
├── app.py                          # Flask 主應用，LINE Bot webhook 處理
├── config.py                       # 配置文件管理
├── name_card_processor.py          # Gemini AI 名片識別處理器
├── notion_manager.py               # Notion 資料庫操作管理器
├── batch_manager.py                # 批次處理狀態管理器
├── address_normalizer.py           # 地址正規化處理器 (NEW)
├── pr_creator.py                   # PR 自動創建功能
├── test_new_webhook.py             # Webhook 測試工具
├── test_address_normalizer.py      # 地址正規化測試 (NEW)
├── .github/
│   └── workflows/
│       ├── ci-cd.yml               # CI/CD 自動化流程
│       └── claude-code.yml         # Claude Code AI 自動化
├── requirements.txt                # Python 依賴列表
├── Procfile                        # Heroku 部署配置
├── railway_app.py                  # Railway 部署入口
└── CLAUDE.md                       # 本文件 (開發指導原則)
```

## 🔧 核心組件

### 1. LINE Bot 處理器 (app.py)
- **功能**: 接收 LINE webhook，處理文字和圖片訊息
- **端點**: 
  - `POST /callback` - LINE webhook 回調
  - `GET /health` - 健康檢查
  - `GET /test` - 服務測試
- **特色**: 支援批次模式和單張模式

### 2. 名片識別處理器 (name_card_processor.py)
- **AI 模型**: Google Gemini AI
- **識別欄位**:
  - 姓名 (name)
  - 公司名稱 (company)
  - 部門 (department)
  - 職稱 (title)
  - 決策影響力 (decision_influence)
  - Email (email)
  - 電話 (phone)
  - 地址 (address) - **整合地址正規化** 🆕
  - 聯繫來源 (contact_source)
  - 備註 (notes)
- **新增功能** 🆕:
  - 自動地址正規化處理
  - 地址信心度評估
  - 地址格式警告提示

### 3. Notion 資料庫管理器 (notion_manager.py)
- **功能**: 建立 Notion 頁面記錄
- **特色**: 
  - 自動欄位類型驗證 (email/phone_number)
  - 容錯處理 (格式錯誤時建立備註欄位)
  - 圖片處理資訊記錄
  - 手動貼圖提示區塊
  - **地址驗證和處理資訊** 🆕
    - 台灣地址格式驗證
    - 地址正規化前後對比顯示
    - 地址信心度和處理狀態展示

### 4. 批次處理管理器 (batch_manager.py)
- **功能**: 管理用戶批次處理狀態
- **特色**:
  - 多用戶並發支援
  - 自動過期機制 (10分鐘)
  - 即時進度追蹤
  - 統計報告生成

### 5. 地址正規化處理器 (address_normalizer.py) 🆕
- **功能**: 台灣地址標準化和驗證
- **特色**:
  - 縣市名稱統一化 (台北 → 台北市)
  - 區域名稱標準化 (信義 → 信義區)
  - 道路段數中文化 (5段 → 五段)
  - 樓層格式統一 (1F → 1樓, B1 → 地下1樓)
  - 地址組件解析和重建
  - 信心度評估和警告提示
  - 台灣地址格式驗證

### 6. PR 自動創建器 (pr_creator.py)
- **功能**: 自動創建 GitHub Pull Request
- **特色**:
  - 自然語言需求解析
  - 自動代碼生成和實現
  - 智能分支管理
  - PR 模板和描述生成

## 🤖 GitHub Actions 自動化

### CI/CD Pipeline (.github/workflows/ci-cd.yml)
- **觸發條件**: Push 到 main/develop 分支，Pull Request 創建
- **執行步驟**:
  1. **多版本測試**: Python 3.9, 3.10, 3.11
  2. **代碼品質檢查**: flake8, black, isort
  3. **安全掃描**: bandit, safety
  4. **應用健康檢查**: 模組導入測試，Flask 應用驗證
  5. **建構檢查**: 部署文件驗證

### Claude Code AI 自動化 (.github/workflows/claude-code.yml)
- **觸發條件**:
  - Issue 標記為 `claude-code`
  - Issue 評論包含 `@claude-code`
  - 手動觸發 (workflow_dispatch)
- **AI 功能**:
  - **自動 PR 創建**: 從自然語言描述生成完整功能
  - **Issue 轉代碼**: 將 GitHub Issue 自動轉換為工作代碼
  - **智能實現**: 根據專案模式和 CLAUDE.md 指導原則進行開發
  - **自動測試**: 語法檢查和基本功能驗證

## 🎯 主要功能

### 單張名片處理
1. 用戶發送名片圖片
2. Gemini AI 識別內容
3. 存入 Notion 並建立獨立頁面
4. 返回詳細處理結果

### 批次處理模式
1. 發送「批次」進入批次模式
2. 連續發送多張名片圖片
3. 每張獨立處理並建立頁面
4. 發送「結束批次」查看統計

## 📱 LINE Bot 指令

| 指令 | 功能 | 範例 |
|------|------|------|
| `批次` / `batch` | 啟動批次模式 | 批次 |
| `結束批次` / `完成批次` | 結束批次並顯示統計 | 結束批次 |
| `狀態` / `status` | 查看批次進度 | 狀態 |
| `help` / `幫助` | 顯示使用說明 | help |
| 圖片上傳 | 名片識別處理 | [發送圖片] |

## 🔧 環境配置

### 必要環境變數
```bash
# LINE Bot 配置
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Google Gemini AI 配置
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-1.5-flash

# Notion 配置
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
```

### GitHub Actions Secrets 配置
```bash
# GitHub Repository Settings > Secrets and variables > Actions

# 必要 Secrets (用於 CI/CD)
GITHUB_TOKEN                    # 自動提供，用於 GitHub API 訪問
LINE_CHANNEL_ACCESS_TOKEN      # LINE Bot API 權杖
LINE_CHANNEL_SECRET            # LINE Bot 驗證密鑰  
GOOGLE_API_KEY                 # Google Gemini AI API 金鑰
NOTION_API_KEY                 # Notion 整合 API 金鑰
NOTION_DATABASE_ID             # Notion 資料庫 ID

# Claude Code AI 自動化 (可選)
ANTHROPIC_API_KEY              # Claude AI API 金鑰 (推薦)
OPENAI_API_KEY                 # OpenAI API 金鑰 (備用)

# 部署相關 (依平台而定)
ZEABUR_TOKEN                   # Zeabur 部署權杖 (推薦)
RAILWAY_TOKEN                  # Railway 部署權杖 (備用)
HEROKU_API_KEY                 # Heroku 部署 API 金鑰 (傳統)
```

### GitHub Actions 使用指南

#### 1. 自動 CI/CD 流程
- **自動觸發**: 推送代碼到 main/develop 分支時自動執行
- **手動觸發**: 在 GitHub Repository > Actions 中手動運行
- **測試報告**: 在 Actions 頁面查看詳細測試結果

#### 2. Claude Code AI 自動化使用
```bash
# 方法 1: 透過 Issue 標籤
# 1. 創建 GitHub Issue 描述功能需求
# 2. 添加標籤 "claude-code"
# 3. 系統自動分析並創建 PR

# 方法 2: 透過 Issue 評論
# 1. 在 Issue 中評論 "@claude-code 請實現這個功能"
# 2. 系統自動處理並回應

# 方法 3: 手動觸發
# 1. 前往 GitHub Repository > Actions
# 2. 選擇 "Claude Code AI 自動化" workflow
# 3. 點擊 "Run workflow" 並輸入功能描述
```

#### 3. Zeabur 自動部署使用
```bash
# 自動部署 (推送到 main 分支)
git push origin main                # 自動觸發部署

# 手動部署
# 1. 前往 GitHub Repository > Actions
# 2. 選擇 "部署到 Zeabur" workflow
# 3. 點擊 "Run workflow"
# 4. 選擇環境 (production/staging)
# 5. 可選擇是否強制部署 (跳過測試)

# 獲取 Zeabur Token
# 1. 前往 https://dash.zeabur.com/account/developer
# 2. 生成新的 API Token
# 3. 在 GitHub Secrets 中設置 ZEABUR_TOKEN

# 部署後更新 LINE Webhook
# 1. 獲取部署 URL: https://your-app.zeabur.app
# 2. 前往 LINE Developers Console
# 3. 更新 Webhook URL: https://your-app.zeabur.app/callback
```

### Notion 資料庫欄位設定
- **Name** (title) - 姓名
- **公司名稱** (rich_text) - 公司
- **部門** (rich_text) - 部門
- **職稱** (select) - 職位
- **決策影響力** (select) - 高/中/低
- **Email** (email) - 電子郵件
- **電話** (phone_number) - 電話號碼
- **地址** (rich_text) - 公司地址或聯絡地址
- **取得聯繫來源** (rich_text) - 來源
- **聯繫注意事項** (rich_text) - 備註
- **窗口的困擾或 KPI** (rich_text) - 待補充

## 🚀 部署資訊

### 本地開發
```bash
# 啟動應用
python app.py

# 啟動 ngrok 隧道 (開發用)
ngrok http 5002
```

### 🌐 Zeabur 雲端部署 (推薦)

#### 自動部署 (GitHub Actions)
- **觸發條件**: 推送到 main 分支自動部署
- **手動觸發**: GitHub Actions > "部署到 Zeabur" > Run workflow
- **部署 URL**: 自動生成，格式 `https://namecard-app-xxx.zeabur.app`

#### Zeabur 配置要求
```bash
# GitHub Secrets 中需要設置
ZEABUR_TOKEN=your_zeabur_token_here

# Zeabur Dashboard 獲取 Token
# https://dash.zeabur.com/account/developer
```

#### 部署後設置
1. **更新 LINE Webhook URL**
   - 前往 [LINE Developers Console](https://developers.line.biz/console/)
   - 更新 Webhook URL 為: `https://your-app.zeabur.app/callback`
   - 啟用 "Use webhook"

2. **驗證部署**
   - 健康檢查: `https://your-app.zeabur.app/health`
   - 服務測試: `https://your-app.zeabur.app/test`

### 🔧 其他部署選項

#### Railway (備用選項)
```bash
# 如果有 Railway token
RAILWAY_TOKEN=your_railway_token_here
```

#### Heroku (傳統選項)
```bash
# 如果使用 Heroku
HEROKU_API_KEY=your_heroku_api_key_here
```

### Webhook URL 格式
- **Zeabur**: `https://your-app.zeabur.app/callback`
- **ngrok** (開發): `https://your-ngrok-url.ngrok-free.app/callback`
- **方法**: POST
- **Content-Type**: application/json

## 🧪 測試工具

### 本地測試工具

#### Webhook 測試 (test_new_webhook.py)
```bash
python test_new_webhook.py
```
- 健康檢查測試
- GET /callback 測試  
- POST /callback 模擬測試

#### 地址正規化測試 (test_address_normalizer.py) 🆕
```bash
python3 test_address_normalizer.py
```
- 台灣地址標準化測試
- 縣市區域名稱正規化測試
- 樓層格式統一測試
- 道路段數中文化測試
- 地址組件解析測試
- 信心度計算驗證
- 無效地址處理測試
- 非台灣地址識別測試

### GitHub Actions 測試

#### CI/CD Pipeline 測試
```bash
# 本地模擬 CI/CD 檢查
pip install flake8 black isort bandit safety

# 代碼品質檢查
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
black --check --diff .
isort --check-only --diff .

# 安全掃描
bandit -r . -f txt
safety check

# 模組導入測試
python -c "from app import app; print('✅ Flask 應用正常')"
```

#### 手動觸發 GitHub Actions
```bash
# 使用 GitHub CLI (需先安裝 gh)
gh workflow run "名片管理 LINE Bot CI/CD"
gh workflow run "Claude Code AI 自動化" -f feature_description="添加新功能"

# 查看 workflow 狀態
gh run list
gh run view [run-id]
```

### 常用開發指令
```bash
# 測試流程
python test_card.py                 # 名片處理測試
python test_new_webhook.py          # Webhook 測試

# 代碼格式化
black .                             # 自動格式化
isort .                             # 自動排序 imports

# 本地開發
python app.py                       # 啟動應用
ngrok http 5002                     # 建立隧道 (開發用)

# Git 流程
git add .
git commit -m "feat: 新功能"
git push origin main                # 觸發 CI/CD

# 部署
./deploy.sh                         # 執行部署腳本 (如果有)
```

## 🐛 已知問題與解決方案

### 1. Notion 欄位類型錯誤
**問題**: Email/電話欄位類型不匹配
**解決**: 使用正確的 `email` 和 `phone_number` 類型，並加入格式驗證

### 2. 批次模式記憶體管理
**問題**: 長時間運行可能累積過多會話
**解決**: 實作自動過期清理機制

### 3. ngrok 連接不穩定
**問題**: ngrok URL 會變動
**解決**: 每次重啟都需要更新 LINE Developers Console 的 Webhook URL

## 📊 效能指標

- **單張名片處理時間**: ~5-10 秒
- **Gemini AI 識別準確率**: ~90%
- **並發處理能力**: 支援多用戶同時批次處理
- **會話過期時間**: 10 分鐘

## 🔄 未來改進方向

1. **圖片存儲**: 整合外部圖片存儲服務 (Cloudinary/AWS S3)
2. **資料驗證**: 更嚴格的欄位格式驗證
3. **錯誤重試**: 自動重試失敗的處理
4. **使用分析**: 添加使用統計和分析
5. **多語言支援**: 支援更多語言的名片識別

## 📝 開發日誌

### 2025-07-29
- ✅ 設置 ZEABUR_TOKEN 並準備部署 🚀
- ✅ 實作友善的新用戶歡迎功能
- ✅ 添加 FollowEvent 處理器，歡迎關注 Bot 的用戶
- ✅ 增強 help 指令，提供詳細使用指南
- ✅ 優化批次處理模式的用戶體驗
- ✅ **整合 GitHub Actions CI/CD Pipeline**
- ✅ **實作 Claude Code AI 自動化 workflow**
- ✅ **創建自動 PR 生成和 Issue 轉代碼功能**
- ✅ **完善測試、代碼品質檢查、安全掃描流程**
- ✅ **更新專案文檔和配置指南**
- ✅ **🆕 實作地址正規化功能**
  - 創建 `address_normalizer.py` 地址標準化模組
  - 整合台灣地址正規化到名片處理流程
  - 縣市名稱統一化 (台北 → 台北市)
  - 區域名稱標準化 (信義 → 信義區)
  - 道路段數中文化 (5段 → 五段)
  - 樓層格式統一 (1F → 1樓, B1 → 地下1樓)
  - 地址信心度評估和警告系統
  - Notion 頁面地址處理詳情展示
  - 完整測試套件 (`test_address_normalizer.py`)

### 2025-07-28
- ✅ 實作基本名片識別功能
- ✅ 整合 Notion 資料庫存儲
- ✅ 添加部門欄位支援
- ✅ 實作批次處理模式
- ✅ 修復 Notion 欄位類型問題
- ✅ 完善圖片處理資訊記錄

## 🤝 協作資訊

- **開發者**: Claude (Anthropic AI Assistant)
- **協作方式**: 透過 Claude Code 進行互動式開發
- **版本控制**: Git + GitHub，整合 GitHub Actions 自動化
- **AI 輔助開發**: Claude Code GitHub Actions 智能 PR 創建
- **部署平台**: Railway/Heroku 等雲端平台
- **CI/CD**: GitHub Actions 自動化測試、建構、部署

### 🛠️ 開發工作流程
1. **功能開發**: 創建 GitHub Issue 描述需求
2. **AI 自動實現**: 標記 `claude-code` 或評論 `@claude-code`
3. **自動化處理**: Claude Code AI 自動創建 PR
4. **代碼審查**: 人工檢查 AI 生成的代碼
5. **CI/CD 流程**: 合併後自動測試和部署

### 🔧 快速開始指南
```bash
# 1. Clone 專案
git clone [repository-url]
cd namecard

# 2. 環境設置
cp .env.example .env
# 編輯 .env 填入 API keys

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 本地測試
python test_new_webhook.py
python app.py

# 5. 開發新功能 (使用 AI)
# 創建 GitHub Issue → 標記 claude-code → AI 自動實現
```

---

> 📌 **重要提醒**: 
> - **GitHub Secrets**: 確保在 Repository Settings 中設置所有必要的 API Keys
> - **ngrok 更新**: 每次重新啟動 ngrok 都需要更新 LINE Webhook URL
> - **API 配額**: 定期檢查各 API 的使用配額和限制
> - **安全性**: 避免在代碼中直接寫入密鑰，使用環境變數
> - **Claude Code**: 利用 AI 自動化功能可大幅提升開發效率
> - **CI/CD**: 推送代碼時會自動觸發測試，確保代碼品質

## 🚀 Claude Code AI 開發優勢

- **🤖 智能開發**: 用自然語言描述需求，AI 自動生成完整功能
- **⚡ 快速迭代**: 從 Issue 到 PR 只需幾分鐘
- **🧪 自動測試**: AI 生成的代碼包含基本測試驗證
- **📝 完整文檔**: 自動生成 PR 描述和技術文檔
- **🔄 持續整合**: 與現有 CI/CD 流程無縫整合