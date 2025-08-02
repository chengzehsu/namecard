# Telegram Bot 名片管理系統

## 📋 專案概述

這是基於原有 LINE Bot 名片管理系統開發的 Telegram Bot 版本，提供完全相同的功能：使用 Google Gemini AI 識別名片內容，並自動存入 Notion 資料庫。支援單張處理、批次處理模式、多名片檢測和品質評估。

## 🏗️ 系統架構

```
Telegram Bot Webhook (Flask)
    ↓
名片圖片處理 (Google Gemini AI)
    ↓
地址正規化處理 (Address Normalizer)
    ↓
資料存儲 (Notion API)
    ↓
批次狀態管理 (內存管理)
    ↓
用戶交互會話管理
```

## 📂 Telegram Bot 檔案結構

```
namecard/
├── telegram_app.py                 # Telegram Bot 主應用程序
├── telegram_bot_handler.py         # Telegram Bot API 錯誤處理包裝器
├── requirements-telegram.txt       # Telegram Bot 專用依賴包
├── test_telegram_webhook.py        # Telegram Bot 測試工具
├── .env.telegram.example          # Telegram Bot 環境變數範例
│
├── config.py                      # 配置文件管理 (已更新支援 Telegram)
├── name_card_processor.py         # Gemini AI 名片識別處理器 (共用)
├── notion_manager.py              # Notion 資料庫操作管理器 (共用)
├── batch_manager.py               # 批次處理狀態管理器 (共用)
├── address_normalizer.py          # 地址正規化處理器 (共用)
├── multi_card_processor.py        # 多名片處理協調器 (共用)
├── user_interaction_handler.py    # 用戶交互會話管理 (共用)
└── README-TELEGRAM.md             # Telegram Bot 說明文檔
```

## 🚀 快速開始

### 1. 環境設置

```bash
# 複製環境變數範例
cp .env.telegram.example .env.telegram

# 編輯環境變數文件
nano .env.telegram
```

### 2. 安裝依賴

```bash
# 安裝 Telegram Bot 專用依賴
pip install -r requirements-telegram.txt
```

### 3. 配置 Telegram Bot

#### 3.1 創建 Telegram Bot
1. 在 Telegram 中找到 [@BotFather](https://t.me/botfather)
2. 發送 `/newbot` 創建新的 Bot
3. 設置 Bot 名稱和用戶名
4. 獲取 Bot Token，填入 `.env.telegram` 中的 `TELEGRAM_BOT_TOKEN`

#### 3.2 設置 Bot 指令 (可選)
向 @BotFather 發送 `/setcommands` 並選擇你的 Bot，然後輸入：
```
start - 開始使用名片管理 Bot
help - 顯示使用說明
batch - 開啟批次處理模式
endbatch - 結束批次處理
status - 查看批次處理狀態
```

### 4. 啟動應用

```bash
# 本地開發
python telegram_app.py

# 或使用指定端口
PORT=5003 python telegram_app.py
```

### 5. 設置 Webhook (生產環境)

```bash
# 設置 webhook URL (替換為你的實際域名)
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/telegram-webhook"}'

# 檢查 webhook 狀態
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 🔧 環境變數配置

### 必要環境變數

```bash
# Telegram Bot 配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Google Gemini AI 配置
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_API_KEY_FALLBACK=your_fallback_google_api_key_here

# Notion 配置
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here

# Flask 配置
PORT=5003
FLASK_DEBUG=false
```

## 📱 Telegram Bot 功能

### 🎯 主要指令

| 指令 | 功能 | 範例 |
|------|------|------|
| `/start` | 開始使用，顯示歡迎訊息 | `/start` |
| `/help` | 顯示詳細使用說明 | `/help` |
| `/batch` | 啟動批次處理模式 | `/batch` |
| `/endbatch` | 結束批次並顯示統計 | `/endbatch` |
| `/status` | 查看批次處理進度 | `/status` |
| 圖片上傳 | 智能名片識別處理 | [發送圖片] |

### 🔍 智能名片處理流程

```
用戶上傳圖片
    ↓
多名片 AI 分析
    ↓
品質評估 ── 單張高品質 → 自動處理 → Notion 存储
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

### 🆕 多名片處理用戶交互

當檢測到多張名片或品質問題時，系統會提供選項：

| 選項 | 說明 | 適用場景 |
|------|------|----------|
| `1` / `分別處理所有名片` | 處理所有檢測到的名片 | 多張名片品質都可接受 |
| `2` / `只處理品質良好的名片` | 僅處理信心度高的名片 | 部分名片模糊或不完整 |
| `3` / `重新拍攝` | 放棄當前處理，重新拍攝 | 整體品質不理想 |

## 🧪 測試工具

### 本地測試

```bash
# 執行 Telegram Bot 測試套件
python test_telegram_webhook.py

# 測試內容包括:
# - 健康檢查端點
# - 服務狀態檢查
# - Webhook 端點測試
# - 模擬 Telegram 更新處理
```

### 手動測試流程

1. **基本功能測試**
   ```bash
   # 在 Telegram 中找到你的 Bot
   # 發送 /start 測試基本響應
   # 發送 /help 查看功能說明
   ```

2. **名片識別測試**
   ```bash
   # 發送名片圖片測試 AI 識別
   # 檢查 Notion 資料庫是否正確存儲
   # 驗證地址正規化功能
   ```

3. **批次處理測試**
   ```bash
   # 發送 /batch 開啟批次模式
   # 連續發送多張名片圖片
   # 發送 /endbatch 查看統計結果
   ```

4. **多名片功能測試**
   ```bash
   # 發送包含多張名片的圖片
   # 測試用戶選擇界面
   # 驗證品質評估功能
   ```

## 🌐 部署指南

### 本地開發部署

```bash
# 1. 啟動應用
python telegram_app.py

# 2. 使用 ngrok 建立公網隧道 (開發用)
ngrok http 5003

# 3. 設置 webhook
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -d "url=https://your-ngrok-url.ngrok-free.app/telegram-webhook"
```

### 生產環境部署

#### 使用 Zeabur (推薦)

1. **準備部署檔案**
   ```bash
   # 確保 requirements-telegram.txt 包含所有依賴
   # 設置啟動指令: python telegram_app.py
   ```

2. **配置環境變數**
   - 在 Zeabur 控制台設置所有必要的環境變數
   - 特別注意 `TELEGRAM_BOT_TOKEN` 的設置

3. **設置 Webhook**
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
        -d "url=https://your-app.zeabur.app/telegram-webhook"
   ```

#### 使用 Railway

```bash
# 1. 安裝 Railway CLI
npm install -g @railway/cli

# 2. 登入 Railway
railway login

# 3. 初始化專案
railway init

# 4. 設置環境變數
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
railway variables set GOOGLE_API_KEY=your_api_key_here
# ... 設置其他變數

# 5. 部署
railway up
```

#### 使用 Heroku

```bash
# 1. 創建 Procfile
echo "web: python telegram_app.py" > Procfile.telegram

# 2. 創建 Heroku 應用
heroku create your-telegram-bot-app

# 3. 設置環境變數
heroku config:set TELEGRAM_BOT_TOKEN=your_token_here
heroku config:set GOOGLE_API_KEY=your_api_key_here
# ... 設置其他變數

# 4. 部署
git add .
git commit -m "Deploy Telegram Bot"
git push heroku main
```

## 📊 API 端點

| 端點 | 方法 | 功能 | 說明 |
|------|------|------|------|
| `/` | GET | 首頁信息 | 顯示 Bot 基本信息 |
| `/health` | GET | 健康檢查 | 檢查服務狀態 |
| `/test` | GET | 服務測試 | 測試各組件連接 |
| `/telegram-webhook` | POST | Telegram Webhook | 接收 Telegram 更新 |

## 🔧 故障排除

### 常見問題

1. **Bot Token 無效**
   ```bash
   # 檢查 Token 格式: 通常是 "數字:字母數字_字符"
   # 確認從 @BotFather 獲取的 Token 正確
   ```

2. **Webhook 設置失敗**
   ```bash
   # 檢查 URL 是否可公開訪問
   # 確認使用 HTTPS (本地開發可用 ngrok)
   # 驗證端點路徑: /telegram-webhook
   ```

3. **名片識別失敗**
   ```bash
   # 檢查 Google API Key 是否有效
   # 確認 Notion API 配置正確
   # 查看應用日誌了解具體錯誤
   ```

4. **批次模式異常**
   ```bash
   # 檢查會話管理是否正常
   # 確認內存管理器運行狀態
   # 測試會話超時機制
   ```

### 日誌和監控

```bash
# 查看應用日誌
tail -f telegram_app.log

# 檢查錯誤統計
curl http://localhost:5003/test

# 監控 Webhook 狀態
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## 🆚 LINE Bot vs Telegram Bot 差異

| 功能 | LINE Bot | Telegram Bot | 說明 |
|------|----------|--------------|------|
| 基本名片識別 | ✅ | ✅ | 完全相同 |
| 批次處理 | ✅ | ✅ | 完全相同 |
| 多名片檢測 | ✅ | ✅ | 完全相同 |
| 地址正規化 | ✅ | ✅ | 完全相同 |
| API 錯誤處理 | ✅ | ✅ | 適配不同 API |
| Webhook 格式 | LINE 格式 | Telegram 格式 | 協議差異 |
| 指令語法 | 自然語言 | `/` 開頭指令 | Bot 平台差異 |
| 訊息格式 | LINE 專用 | Markdown/HTML | 支援格式不同 |

## 🔄 功能對照表

| LINE Bot 功能 | Telegram Bot 對應 | 說明 |
|---------------|-------------------|------|
| `批次` | `/batch` | 啟動批次模式 |
| `結束批次` | `/endbatch` | 結束批次處理 |
| `狀態` | `/status` | 查看處理進度 |
| `help` | `/help` | 顯示幫助信息 |
| 圖片上傳 | 圖片上傳 | 名片識別功能 |
| Follow 事件 | `/start` 指令 | 歡迎新用戶 |

## 🔮 升級和維護

### 版本更新

```bash
# 更新依賴包
pip install -r requirements-telegram.txt --upgrade

# 檢查 Telegram Bot API 更新
# https://core.telegram.org/bots/api

# 更新 Google Gemini API
pip install google-generativeai --upgrade
```

### 性能監控

```bash
# 監控 Bot 響應時間
# 檢查 API 調用頻率
# 追蹤錯誤率統計
# 監控內存使用情況
```

---

## 📞 技術支援

- **文檔**: 查看本 README 和原有的 `CLAUDE.md`
- **測試**: 使用 `test_telegram_webhook.py` 進行診斷
- **日誌**: 檢查應用輸出和錯誤日誌
- **API 狀態**: 訪問 `/test` 端點查看服務狀態

## 🎉 部署成功檢查

✅ Bot 在 Telegram 中響應 `/start` 指令  
✅ 上傳名片圖片能正確識別並存入 Notion  
✅ 批次處理模式正常工作  
✅ 多名片檢測和用戶交互功能正常  
✅ Webhook 端點正常接收和處理更新  
✅ 錯誤處理和重試機制有效運作  

**🚀 恭喜！您的 Telegram Bot 名片管理系統已經成功運行！**