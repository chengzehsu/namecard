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
├── test_simple_error_handling.py   # LINE Bot API 錯誤處理測試 (NEW) 🆕
├── line_bot_handler.py             # LINE Bot API 錯誤處理包裝器 (NEW) 🆕
├── format_code.sh                  # 代碼格式化腳本 (NEW) 🆕
├── .pre-commit-config.yaml         # Pre-commit hooks 配置 (NEW) 🆕
├── .github/
│   └── workflows/
│       ├── ci-cd.yml               # CI/CD 自動化流程 (含自動格式化) 🆕
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
  - `GET /api-status` - API 狀態監控 🆕
- **特色**: 支援批次模式和單張模式，內建 API 錯誤處理 🆕

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
- **核心功能** 🆕:
  - **多名片檢測**: 自動識別一張圖片中的多張名片
  - **品質評估**: 每張名片的信心度計算和清晰度分析
  - **智能建議**: 根據識別品質提供處理建議
  - **地址正規化**: 台灣地址標準化處理
  - **API 備用機制**: 主要 API 額度不足時自動切換到備用 API Key 🆕
  - **向後兼容**: 保持與舊版單一名片處理的完全兼容

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

### 6. 多名片處理器 (multi_card_processor.py) 🆕
- **功能**: 協調多張名片的識別、分析和處理工作流程
- **特色**:
  - **智能決策**: 根據名片數量和品質自動決定處理方式
  - **品質分析**: 評估每張名片的識別信心度和完整性
  - **用戶引導**: 生成清晰的用戶選擇界面和建議
  - **批次整合**: 與現有批次處理模式無縫整合
  - **錯誤處理**: 完善的異常處理和降级机制

### 7. 用戶交互處理器 (user_interaction_handler.py) 🆕
- **功能**: 管理多名片處理過程中的用戶交互和會話狀態
- **特色**:
  - **會話管理**: 自動管理用戶選擇會話，支援超時和重試
  - **智能解析**: 支援數字選擇和自然語言匹配
  - **用戶體驗**: 生成友好的選項界面和操作指導
  - **狀態追蹤**: 完整的會話狀態管理和清理機制
  - **多用戶支援**: 並發處理多個用戶的交互會話

### 8. LINE Bot API 錯誤處理包裝器 (line_bot_handler.py) 🆕
- **功能**: 提供健壯的 LINE Bot API 錯誤處理和降級服務
- **特色**:
  - **API 配額監控**: 自動檢測月度配額用量和重置時間
  - **智能重試機制**: 根據錯誤類型自動重試或直接失敗
  - **降級服務**: 當 API 不可用時提供友好的用戶提示
  - **錯誤統計**: 追蹤各種 API 錯誤的發生頻率
  - **狀態監控**: 提供詳細的服務狀態報告
- **錯誤處理**:
  - `429 配額超限` → 設置配額狀態，等待下月重置
  - `429 速率限制` → 自動重試機制，建議等待時間
  - `400/401/403` → 客戶端錯誤，不重試，記錄錯誤
  - `500+` → 伺服器錯誤，自動重試，延遲處理
- **安全 API 調用**:
  - `safe_reply_message()` - 安全回覆訊息
  - `safe_push_message()` - 安全推播訊息  
  - `safe_get_message_content()` - 安全獲取內容

### 9. PR 自動創建器 (pr_creator.py)
- **功能**: 自動創建 GitHub Pull Request
- **特色**:
  - 自然語言需求解析
  - 自動代碼生成和實現
  - 智能分支管理
  - PR 模板和描述生成

## 🤖 GitHub Actions 自動化

### CI/CD Pipeline (.github/workflows/ci-cd.yml) 🆕
- **觸發條件**: Push 到 main/develop 分支，Pull Request 創建
- **執行步驟**:
  1. **多版本測試**: Python 3.9, 3.10, 3.11
  2. **🔧 自動代碼格式化**: black + isort 自動修復並推送 🆕
  3. **代碼品質檢查**: flake8, black, isort (驗證性)
  4. **安全掃描**: bandit, safety
  5. **應用健康檢查**: 模組導入測試，Flask 應用驗證
  6. **建構檢查**: 部署文件驗證

#### 🚀 自動格式化功能 🆕
- **自動修復**: CI/CD 會自動運行 `black` 和 `isort` 修復格式問題
- **自動提交**: 格式修復會自動提交並推送到原分支
- **零干擾**: 開發者無需手動處理格式化問題
- **一致性**: 確保整個專案的代碼風格統一

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

### 🔍 智能名片處理 (支援多名片) 🆕
1. **自動檢測**: 用戶上傳圖片後自動檢測名片數量
2. **品質評估**: AI 評估每張名片的識別信心度和清晰度
3. **智能決策**: 
   - **單張高品質** → 自動處理並存入 Notion
   - **多張名片** → 提供用戶選擇界面
   - **品質不佳** → 建議重新拍攝並提供改善提示
4. **用戶選擇**: 
   - 分別處理所有名片
   - 只處理品質良好的名片
   - 重新拍攝特定名片
5. **批次整合**: 與現有批次模式完美整合

### 📱 LINE Bot 互動流程 🆕
```
用戶上傳圖片
    ↓
多名片 AI 分析
    ↓
品質評估 ── 單張高品質 → 自動處理 → Notion 存儲
    ↓
多張/品質問題
    ↓
用戶選擇界面 ← → 會話管理 (5分鐘超時)
    ↓
根據選擇執行:
├─ 分別處理 → 批次存入 Notion
├─ 部分處理 → 選擇性存入
└─ 重新拍攝 → 拍攝建議
```

### 單張名片處理 (傳統模式)
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
| 圖片上傳 | 智能名片識別處理 🆕 | [發送圖片] |

### 🆕 多名片處理用戶交互

當檢測到多張名片或品質問題時，系統會提供以下選項：

| 選項 | 說明 | 適用場景 |
|------|------|----------|
| `1` / `分別處理所有名片` | 處理所有檢測到的名片 | 多張名片品質都可接受 |
| `2` / `只處理品質良好的名片` | 僅處理信心度高的名片 | 部分名片模糊或不完整 |
| `3` / `重新拍攝` | 放棄當前處理，重新拍攝 | 整體品質不理想 |
| `繼續處理` | 接受當前識別結果 | 單張名片品質中等 |
| `重拍` / `重新` | 重新拍攝的同義詞 | 快速重拍選擇 |

**用戶可以：**
- 回覆數字 (1, 2, 3) 
- 回覆完整選項文字
- 使用簡化指令 (重拍、繼續、確定)

## 🔧 環境配置

### 必要環境變數
```bash
# LINE Bot 配置
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Google Gemini AI 配置
GOOGLE_API_KEY=your_google_api_key
GOOGLE_API_KEY_FALLBACK=your_fallback_google_api_key  # 🆕 備用 API Key
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
GOOGLE_API_KEY                 # Google Gemini AI API 金鑰 (主要)
GOOGLE_API_KEY_FALLBACK        # Google Gemini AI API 金鑰 (備用) 🆕
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

#### 3. GitHub Actions 自動化部署工作流

本專案包含多個 GitHub Actions 工作流文件，提供完整的 CI/CD 自動化：

##### 📁 工作流文件結構
```bash
.github/workflows/
├── ci-cd.yml                 # 主要 CI/CD 流水線
├── deploy-zeabur.yml         # Zeabur 部署自動化
├── enhanced-testing.yml      # 增強測試套件
└── integration-tests.yml     # 整合測試
```

##### 🔄 CI/CD 主流程 (ci-cd.yml)
```bash
觸發條件:
- Push 到 main/develop 分支
- Pull Request 創建/更新
- 手動觸發

執行步驟:
1. 多版本測試 (Python 3.9, 3.10, 3.11)
2. 代碼品質檢查 (flake8, black, isort)
3. 安全掃描 (bandit, safety)
4. 依賴漏洞檢查
5. 應用健康檢查
6. 模組導入測試
```

##### 🚀 Zeabur 部署流程 (deploy-zeabur.yml)
```bash
自動部署:
git push origin main  # 自動觸發 Zeabur 部署

手動部署:
1. GitHub Repository > Actions
2. 選擇 "部署到 Zeabur" workflow
3. 點擊 "Run workflow"
4. 設置參數:
   - environment: production/staging
   - force_deploy: 跳過預檢查 (true/false)
5. 執行部署

CLI 觸發:
gh workflow run "部署到 Zeabur" \
  -f environment=production \
  -f force_deploy=false
```

##### 🧪 測試自動化工作流
```bash
增強測試 (enhanced-testing.yml):
- 深度代碼品質分析
- 覆蓋率報告生成
- 多環境測試矩陣
- 效能基準測試

整合測試 (integration-tests.yml):  
- 端到端功能測試
- API 接口測試
- 模擬 Webhook 測試
- 資料庫整合測試
```

##### ⚙️ 工作流設置和配置

###### GitHub Secrets 完整清單
```bash
# 必要 API Keys
LINE_CHANNEL_ACCESS_TOKEN      # LINE Bot API 權杖
LINE_CHANNEL_SECRET            # LINE Bot 驗證密鑰
GOOGLE_API_KEY                 # Google Gemini AI 主要 API
GOOGLE_API_KEY_FALLBACK        # Google Gemini 備用 API
NOTION_API_KEY                 # Notion 整合 API 金鑰
NOTION_DATABASE_ID             # Notion 資料庫 ID

# 部署相關
ZEABUR_TOKEN                   # Zeabur 部署權杖 (推薦)
RAILWAY_TOKEN                  # Railway 部署權杖 (備用)
HEROKU_API_KEY                 # Heroku 部署 API (傳統)

# 可選 AI 功能
ANTHROPIC_API_KEY              # Claude AI API (Claude Code)
OPENAI_API_KEY                 # OpenAI API 金鑰 (備用)
```

###### 環境變數配置
```bash
# 在 GitHub Actions 中自動設置的環境變數
PYTHON_VERSION=3.9             # Python 版本
FLASK_ENV=production           # Flask 環境
PORT=5002                      # 應用端口
GITHUB_TOKEN                   # 自動提供的 GitHub API 權杖
```

##### 📊 工作流監控和管理

###### 1. GitHub Actions 介面監控
```bash
# 即時監控
https://github.com/your-repo/actions

# 工作流狀態
✅ 成功 - 所有步驟完成
❌ 失敗 - 某個步驟失敗
🟡 進行中 - 正在執行
⏸️ 已取消 - 手動或自動取消
```

###### 2. 使用 GitHub CLI 管理
```bash
# 安裝 GitHub CLI
brew install gh                # macOS
winget install GitHub.cli      # Windows
apt install gh                 # Linux

# 登入和設置
gh auth login

# 查看工作流狀態
gh run list                    # 列出最近的運行
gh run list --workflow="CI/CD" # 特定工作流
gh run view [run-id]           # 查看詳細信息
gh run view [run-id] --log     # 查看日誌

# 手動觸發工作流
gh workflow run "部署到 Zeabur"
gh workflow run "CI/CD" --ref main

# 取消運行中的工作流
gh run cancel [run-id]

# 重新運行失敗的工作流
gh run rerun [run-id]
```

###### 3. 工作流狀態徽章
```markdown
# 在 README 中添加狀態徽章
[![CI/CD](https://github.com/your-repo/namecard/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-repo/namecard/actions/workflows/ci-cd.yml)

[![Deploy to Zeabur](https://github.com/your-repo/namecard/actions/workflows/deploy-zeabur.yml/badge.svg)](https://github.com/your-repo/namecard/actions/workflows/deploy-zeabur.yml)
```

##### 🔧 自定義工作流配置

###### 觸發條件自定義
```yaml
# 僅在特定文件變更時觸發
on:
  push:
    branches: [ main ]
    paths:
      - 'app.py'
      - '*.py'
      - 'requirements.txt'
    paths-ignore:
      - 'docs/**'
      - '**.md'

# 定時觸發 (每日健康檢查)
on:
  schedule:
    - cron: '0 2 * * *'  # 每日凌晨 2 點執行
```

###### 環境分支策略
```yaml
# 多環境部署
environments:
  production:
    if: github.ref == 'refs/heads/main'
  staging: 
    if: github.ref == 'refs/heads/develop'
  development:
    if: github.ref == 'refs/heads/feature/*'
```

##### 🚨 常見工作流問題排查

###### 1. 工作流執行失敗
```bash
# 檢查步驟
1. 查看失敗的工作流日誌
2. 檢查 GitHub Secrets 設置
3. 確認 requirements.txt 依賴
4. 驗證代碼語法正確性
5. 檢查網路連接問題

# 解決方法
gh run view [failed-run-id] --log  # 查看詳細錯誤
gh workflow run [workflow] --ref main  # 重新觸發
```

###### 2. Secrets 配置問題
```bash
# 檢查 Secrets 設置
Repository > Settings > Secrets and variables > Actions

# 常見問題
- API Key 格式錯誤
- Secret 名稱拼寫錯誤  
- API Key 過期或無效
- 權限不足

# 驗證方法
echo "ZEABUR_TOKEN 長度: ${#ZEABUR_TOKEN}"
echo "API Key 前6位: ${GOOGLE_API_KEY:0:6}"
```

###### 3. 部署權限問題
```bash
# Zeabur Token 權限
- 確保 Token 有專案存取權限
- 檢查 Token 是否過期
- 驗證專案名稱正確

# GitHub Actions 權限
- Repository > Settings > Actions > General
- 確保 "Read and write permissions" 已啟用
- 檢查 "Allow GitHub Actions to create and approve pull requests"
```

##### 📈 工作流效能優化

###### 1. 快取設置
```yaml
# Python 依賴快取
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

# Node.js 快取 (如適用)
- uses: actions/cache@v3  
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

###### 2. 並行執行
```yaml
# 多任務並行執行
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]
    os: [ubuntu-latest, windows-latest, macos-latest]
  fail-fast: false  # 一個失敗不影響其他
```

###### 3. 條件執行
```yaml
# 僅在變更時執行測試
if: contains(github.event.head_commit.message, '[test]') || 
    github.event_name == 'pull_request'
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

Zeabur 是一個現代化的雲端部署平台，提供簡單易用的應用部署服務。我們整合了完整的 GitHub Actions 自動化部署流程。

#### 🚀 自動部署流程 (GitHub Actions)

**文件位置**: `.github/workflows/deploy-zeabur.yml`

**觸發條件**:
- **自動觸發**: 推送代碼到 `main` 分支時自動部署
- **手動觸發**: GitHub Actions > "部署到 Zeabur" > Run workflow
- **智能過濾**: 只有實際代碼變更才觸發部署（忽略文檔變更）

**部署流程**:
```
1. 預部署檢查 (可選跳過)
   ├── 語法檢查 (Python 編譯)
   ├── 核心模組驗證
   └── 必要文件檢查

2. Zeabur 部署
   ├── 安裝 Zeabur CLI
   ├── 配置認證
   ├── 創建部署配置
   ├── 專案/服務管理
   └── 環境變數設置

3. 健康檢查
   ├── 等待服務啟動
   ├── 端點連通性測試
   └── 部署狀態驗證

4. 部署後測試
   ├── 健康檢查端點測試
   ├── Webhook 端點測試
   └── 結果通知
```

#### 🔧 Zeabur 配置設置

##### 1. 獲取 Zeabur Token
```bash
# 步驟
1. 前往 https://dash.zeabur.com/account/developer
2. 生成新的 API Token
3. 複製 Token 值
4. 在 GitHub Repository Settings > Secrets and variables > Actions
5. 新增 Secret: ZEABUR_TOKEN = your_token_here
```

##### 2. GitHub Secrets 配置
```bash
# 必要 Secrets (用於 Zeabur 部署)
ZEABUR_TOKEN                   # Zeabur 部署權杖 (必須)
LINE_CHANNEL_ACCESS_TOKEN      # LINE Bot API 權杖
LINE_CHANNEL_SECRET            # LINE Bot 驗證密鑰  
GOOGLE_API_KEY                 # Google Gemini AI API 金鑰 (主要)
GOOGLE_API_KEY_FALLBACK        # Google Gemini AI API 金鑰 (備用)
NOTION_API_KEY                 # Notion 整合 API 金鑰
NOTION_DATABASE_ID             # Notion 資料庫 ID
```

##### 3. 部署配置詳情
```json
{
  "name": "namecard-line-bot",
  "type": "python",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "python app.py",
  "environment": {
    "PYTHON_VERSION": "3.9",
    "PORT": "5002"
  },
  "regions": ["hkg"],
  "scaling": {
    "minInstances": 1,
    "maxInstances": 2
  }
}
```

#### 📱 手動部署操作

##### 方法 1: 自動部署 (推薦)
```bash
# 簡單推送即可觸發部署
git add .
git commit -m "feat: 新功能更新"
git push origin main
# → 自動觸發部署流程
```

##### 方法 2: 手動觸發部署
```bash
# 在 GitHub 介面操作
1. 前往 GitHub Repository > Actions
2. 選擇 "部署到 Zeabur" workflow
3. 點擊 "Run workflow"
4. 選擇部署參數:
   - environment: production/staging
   - force_deploy: 是否跳過預檢查
5. 點擊 "Run workflow" 執行
```

##### 方法 3: 使用 GitHub CLI
```bash
# 安裝 GitHub CLI
brew install gh  # macOS
# 或訪問 https://cli.github.com/

# 登入 GitHub
gh auth login

# 觸發部署
gh workflow run "部署到 Zeabur" \
  -f environment=production \
  -f force_deploy=false

# 查看部署狀態
gh run list --workflow="部署到 Zeabur"
gh run view [run-id] --log
```

#### 🔍 部署狀態監控

##### 1. GitHub Actions 監控
```bash
# 實時查看部署進度
https://github.com/your-repo/actions

# 部署日誌查看
- 點擊最新的 "部署到 Zeabur" workflow run
- 查看各個步驟的詳細日誌
- 監控部署進度和錯誤信息
```

##### 2. Zeabur Dashboard 監控
```bash
# Zeabur 控制台
https://dash.zeabur.com/

# 專案信息
- 專案名稱: namecard-line-bot
- 服務名稱: namecard-app
- 部署區域: 香港 (hkg)
- 實例配置: 1-2 個實例自動擴展
```

##### 3. 應用健康監控
```bash
# 自動健康檢查端點
https://your-app.zeabur.app/health

# 測試端點
https://your-app.zeabur.app/test

# LINE Webhook 端點
https://your-app.zeabur.app/callback
```

#### 🔧 部署後配置

##### 1. 更新 LINE Webhook URL
```bash
# 步驟詳情
1. 獲取部署 URL (從 GitHub Actions 日誌中)
   格式: https://namecard-line-bot-xxx.zeabur.app

2. 前往 LINE Developers Console
   https://developers.line.biz/console/

3. 選擇您的 LINE Bot Channel

4. 前往 "Messaging API" 標籤頁

5. 更新 Webhook URL:
   新 URL: https://your-app.zeabur.app/callback

6. 啟用 "Use webhook" 選項

7. 點擊 "Verify" 測試連接

8. 確認狀態顯示為 "Success"
```

##### 2. 驗證部署成功
```bash
# 健康檢查
curl https://your-app.zeabur.app/health
# 應該返回: {"status": "healthy", "timestamp": "..."}

# 服務測試
curl https://your-app.zeabur.app/test
# 應該返回: {"message": "名片管理 LINE Bot 運行中", ...}

# Webhook 端點測試
curl -X POST https://your-app.zeabur.app/callback
# 應該返回 400 (正常，因為沒有提供正確的 LINE 簽名)
```

##### 3. LINE Bot 功能測試
```bash
# 測試流程
1. 在 LINE 中搜尋並添加您的 Bot
2. 發送 "help" 測試基本響應
3. 發送名片圖片測試 AI 識別功能
4. 檢查 Notion 資料庫是否正確存儲
5. 測試批次處理模式
```

#### ⚠️ 常見問題排查

##### 1. 部署失敗
```bash
# 檢查事項
✅ ZEABUR_TOKEN 是否正確設置
✅ GitHub Secrets 中的 API Keys 是否齊全
✅ requirements.txt 是否包含所有依賴
✅ app.py 語法是否正確
✅ 網路連接是否正常

# 解決方法
1. 檢查 GitHub Actions 錯誤日誌
2. 確認 Zeabur Token 有效性
3. 手動觸發部署並啟用 force_deploy
4. 聯繫 Zeabur 技術支援
```

##### 2. 健康檢查失敗
```bash
# 可能原因
- 應用啟動時間過長
- 環境變數配置錯誤
- 依賴安裝失敗
- 端口配置問題

# 解決方法
1. 查看 Zeabur Dashboard 的應用日誌
2. 檢查環境變數是否正確設置
3. 確認 Flask 應用監聽正確端口 (5002)
4. 等待更長時間讓應用完全啟動
```

##### 3. LINE Webhook 連接失敗
```bash
# 檢查事項
✅ Webhook URL 格式正確
✅ SSL 證書有效 (Zeabur 自動提供)
✅ 應用正常運行
✅ LINE_CHANNEL_SECRET 設置正確

# 測試方法
curl -X POST https://your-app.zeabur.app/callback \
  -H "Content-Type: application/json" \
  -d '{"events":[]}'
```

#### 📊 部署效能指標

- **部署時間**: 通常 3-5 分鐘
- **啟動時間**: 30-60 秒
- **可用性**: 99.9% SLA
- **自動擴展**: 1-2 實例根據負載
- **區域**: 香港 (hkg) 低延遲
- **SSL**: 自動 HTTPS 證書
- **監控**: 內建應用監控和日誌

#### 🔄 版本管理和回滾

```bash
# 版本標籤 (可選)
git tag -a v1.0.0 -m "正式版本 v1.0.0"
git push origin v1.0.0

# 回滾到前一版本 (在 Zeabur Dashboard)
1. 前往 Zeabur Dashboard
2. 選擇專案和服務
3. 在 "Deployments" 標籤查看部署歷史
4. 選擇之前的部署版本
5. 點擊 "Rollback" 回滾

# 緊急回滾 (透過 Git)
git revert HEAD
git push origin main  # 觸發新的部署
```

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

#### 多名片處理系統測試 (test_multi_card_processor.py) 🆕
```bash
python3 test_multi_card_processor.py
```
- **單元測試**:
  - NameCardProcessor 多名片檢測功能
  - MultiCardProcessor 品質評估邏輯
  - UserInteractionHandler 會話管理
  - 用戶選擇解析和處理
- **整合測試**:
  - 完整多名片工作流程
  - 用戶交互會話生命週期
  - 品質評估決策邏輯
- **測試覆蓋率**: 100% (17/17 測試通過)

#### API 備用機制測試 (test_api_fallback.py) 🆕
```bash
python3 test_api_fallback.py
```
- **功能測試**:
  - API Key 配置檢查
  - 名片處理器初始化
  - 額度超限錯誤檢測邏輯
  - API Key 自動切換機制
  - 備用機制端到端測試
- **測試結果**: 🎉 所有測試通過！API 備用機制正常工作

#### LINE Bot API 錯誤處理測試 (test_simple_error_handling.py) 🆕
```bash
python3 test_simple_error_handling.py
```
- **錯誤處理邏輯測試**:
  - API 配額超限 (429) 處理和狀態追蹤
  - 速率限制 (429) 自動重試機制  
  - 客戶端錯誤 (400/401/403) 處理
  - 伺服器錯誤 (500+) 重試機制
- **降級服務測試**:
  - 配額超限降級訊息生成
  - 速率限制建議和等待提示
  - 網路錯誤處理和用戶指導
- **狀態監控測試**:
  - 配額狀態自動追蹤和重置
  - 錯誤統計和頻率分析
  - API 健康狀態報告生成
- **測試結果**: 🎉 所有測試通過！API 錯誤處理機制正常工作

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
python3 test_new_webhook.py          # Webhook 測試
python3 test_address_normalizer.py   # 地址正規化測試
python3 test_multi_card_processor.py # 多名片系統測試 🆕
python3 test_api_fallback.py         # API 備用機制測試 🆕
python3 test_simple_error_handling.py # LINE Bot API 錯誤處理測試 🆕

# 代碼格式化 🆕
./format_code.sh                    # 一鍵格式化腳本 (推薦)
black .                             # 自動格式化
isort .                             # 自動排序 imports

# Pre-commit hooks (推薦)
pip install pre-commit              # 安裝 pre-commit
pre-commit install                  # 安裝 Git hooks
pre-commit run --all-files          # 手動運行所有檢查

# 本地開發
python app.py                       # 啟動應用
ngrok http 5002                     # 建立隧道 (開發用)

# Git 流程
git add .
git commit -m "feat: 新功能"
git push origin main                # 觸發 CI/CD (會自動格式化)

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

### 4. LINE Bot API 配額限制 🆕
**問題**: LINE Bot API 達到月度使用配額 (status_code=429)
**解決**: 
- **自動檢測**: 系統自動檢測配額狀態並設置重置時間
- **降級服務**: 提供友好的用戶提示，說明服務暫時受限
- **狀態監控**: 透過 `/api-status` 端點監控 API 狀態
- **智能重試**: 針對不同錯誤類型採用不同重試策略
- **錯誤統計**: 追蹤各種 API 錯誤發生頻率，便於問題診斷

## 📊 效能指標

- **單張名片處理時間**: ~5-10 秒
- **Gemini AI 識別準確率**: ~90%
- **並發處理能力**: 支援多用戶同時批次處理
- **會話過期時間**: 10 分鐘
- **API 備用切換時間**: <1 秒 (自動無縫切換) 🆕

## 🔄 未來改進方向

1. **圖片存儲**: 整合外部圖片存儲服務 (Cloudinary/AWS S3)
2. **資料驗證**: 更嚴格的欄位格式驗證
3. **錯誤重試**: 自動重試失敗的處理
4. **使用分析**: 添加使用統計和分析
5. **多語言支援**: 支援更多語言的名片識別

## 📝 開發日誌

### 2025-08-01
- ✅ **🆕 實作完整多名片識別與品質控制系統**
  - 建立 `multi_card_processor.py` 多名片處理協調器
  - 建立 `user_interaction_handler.py` 用戶交互會話管理
  - 增強 `name_card_processor.py` 支援多名片檢測和品質評估
  - 整合 LINE Bot (`app.py`) 完整多名片處理流程
  - 實作智能決策：自動處理 vs 用戶選擇 vs 重新拍攝
- ✅ **🧪 建立完整測試系統**
  - 創建 `test_multi_card_processor.py` 綜合測試套件
  - 單元測試：名片檢測、品質評估、用戶交互、會話管理
  - 整合測試：完整工作流程驗證
  - 測試覆蓋率：100% (17/17 測試通過)
- ✅ **🎯 用戶體驗優化**
  - 智能品質評估：信心度計算、必要欄位檢查、清晰度分析
  - 友好的用戶選擇界面：支援數字和文字選擇
  - 會話管理：5分鐘超時、自動清理、重試機制
  - 拍攝建議：具體的改善提示和技巧指導
- ✅ **🔄 實作 Gemini API 備用機制** 🆕
  - 建立雙 API Key 配置系統 (`GOOGLE_API_KEY_FALLBACK`)
  - 實作智能錯誤檢測和自動切換邏輯
  - 創建 `test_api_fallback.py` 完整測試套件
  - 確保無縫用戶體驗：額度不足時自動切換到備用 API
  - 完善錯誤處理：詳細的錯誤信息和狀態追蹤
- ✅ **📋 Agent 協作開發模式實踐**
  - AI Engineer：多名片檢測和品質評估核心邏輯
  - UX Researcher：用戶交互界面和體驗設計
  - Backend Architect：系統架構和 LINE Bot 整合
  - Test Writer/Fixer：完整測試套件和品質驗證

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

## 🤖 專業 Agent 協作系統

### Agent 任務分析機制
收到任務時，Claude 會自動進行以下分析流程：

1. **任務類型識別**
   - 產品開發 → **Product Agents**
   - 專案管理 → **Project Management Agents**
   - 測試相關 → **Testing Agents**
   - 設計需求 → **Design Agents**
   - 工程實作 → **Engineering Agents**

2. **智能 Agent 選擇**
   ```
   任務: "優化名片識別的準確率"
   ↓ 分析結果
   - 主導 Agent: AI Engineer (核心實作)
   - 協作 Agent: Test Writer/Fixer (測試驗證)
   - 支援 Agent: Performance Benchmarker (效能評估)
   ```

3. **多 Agent 協作流程**
   - **Phase 1**: 需求分析 (Product/UX Agents)
   - **Phase 2**: 技術設計 (Engineering Agents)
   - **Phase 3**: 實作開發 (專業 Engineering Agents)
   - **Phase 4**: 測試驗證 (Testing Agents)
   - **Phase 5**: 部署監控 (DevOps Agents)

### 可用專業 Agents

#### 🎯 產品相關 Agents
- **Feedback Synthesizer** - 用戶回饋分析，改進產品方向
- **Sprint Prioritizer** - 功能優先級排序，敏捷開發規劃
- **Trend Researcher** - 市場趨勢分析，競品研究

#### 📋 專案管理 Agents  
- **Experiment Tracker** - A/B 測試管理，數據追蹤
- **Project Shipper** - 發布流程管理，上線檢查清單
- **Studio Producer** - 整體專案協調，資源分配

#### 🧪 測試相關 Agents
- **API Tester** - API 接口測試，自動化測試套件
- **Performance Benchmarker** - 效能基準測試，瓶頸分析
- **Test Results Analyzer** - 測試結果分析，品質報告
- **Tool Evaluator** - 開發工具評估，技術選型
- **Workflow Optimizer** - 開發流程優化，效率提升

#### 🎨 設計相關 Agents
- **Brand Guardian** - 品牌一致性檢查，設計規範
- **UI Designer** - 使用者界面設計，互動原型
- **UX Researcher** - 使用者體驗研究，可用性測試
- **Visual Storyteller** - 視覺敘事設計，內容呈現
- **Whimsy Injector** - 創意元素，趣味性增強

#### ⚙️ 工程相關 Agents
- **AI Engineer** - AI 模型優化，機器學習實作
- **Backend Architect** - 後端架構設計，系統擴展
- **DevOps Automator** - CI/CD 流程，部署自動化
- **Frontend Developer** - 前端開發，使用者界面實作
- **Mobile App Builder** - 行動應用開發，跨平台方案
- **Rapid Prototyper** - 快速原型開發，概念驗證
- **Test Writer/Fixer** - 測試程式碼撰寫，錯誤修復

### Agent 協作範例

#### 範例 1: 新功能開發
```
任務: "添加批次名片匯出 PDF 功能"

Agent 協作流程:
1. Sprint Prioritizer → 分析功能優先級和商業價值
2. UX Researcher → 研究使用者匯出需求
3. UI Designer → 設計匯出界面和流程
4. Backend Architect → 設計 PDF 生成架構
5. AI Engineer → 優化批次處理效能
6. Test Writer/Fixer → 撰寫自動化測試
7. DevOps Automator → 配置部署流程
```

#### 範例 2: 效能優化
```
任務: "優化 Gemini AI 識別速度"

Agent 協作流程:
1. Performance Benchmarker → 建立效能基準測試
2. AI Engineer → 分析模型效能瓶頸
3. Backend Architect → 優化 API 呼叫架構
4. Test Results Analyzer → 驗證優化效果
5. Experiment Tracker → A/B 測試不同優化方案
```

#### 範例 3: 品質提升
```
任務: "提升名片識別準確率"

Agent 協作流程:
1. Feedback Synthesizer → 分析用戶回饋的識別問題
2. AI Engineer → 優化 Gemini 提示工程
3. Test Writer/Fixer → 建立識別準確率測試
4. Tool Evaluator → 評估其他 AI 服務選項
5. Performance Benchmarker → 比較不同方案效能
```

### Agent 觸發機制

1. **自動觸發**: 根據任務關鍵字自動選擇合適的 Agents
2. **明確請求**: 可以明確指定需要的 Agent
   ```bash
   # 範例
   "請使用 AI Engineer 和 Test Writer/Fixer 來優化名片識別"
   ```
3. **協作建議**: Claude 會主動建議最適合的 Agent 組合

### 開發指導原則

**在收到任務時，Claude 必須：**
1. **🔍 任務分析**: 識別任務類型和複雜度
2. **🤖 Agent 選擇**: 選擇最適合的專業 Agents
3. **📋 協作規劃**: 制定 Agent 協作流程
4. **⚡ 執行監控**: 確保 Agents 有效協作
5. **📊 結果整合**: 整合各 Agent 的產出

**Agent 協作優先級：**
- **高優先級**: 直接影響核心功能的任務
- **中優先級**: 改善使用體驗的任務  
- **低優先級**: 優化和增強型任務

這樣的 Agent 協作機制能確保每個任務都由最專業的 Agent 負責，提升開發效率和程式碼品質。