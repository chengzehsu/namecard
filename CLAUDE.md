# LINE Bot 名片管理系統 - Claude 開發記錄

## 📋 專案概述
智能 LINE Bot 名片管理系統，使用 Google Gemini AI 識別名片內容，並自動存入 Notion 資料庫。

**核心特色**:
- ✅ LINE Bot 掃描名片
- ✅ Google Gemini AI 識別
- ✅ Notion 資料庫自動存儲
- ✅ 批次處理 + 多名片檢測
- ✅ 地址正規化
- ✅ API 備用機制

## 🏗️ 系統架構
```
LINE Bot 名片識別流程 🚀
LINE用戶上傳名片圖片
    ↓
LINE Webhook 接收 (/callback)
    ↓
Gemini AI 智能識別
├── 多名片檢測
├── 品質評估
└── 地址正規化
    ↓
自動存入 Notion 資料庫
    ↓
回傳處理結果給用戶
```

## 📂 核心文件結構
```
namecard/
├── app.py                           # LINE Bot 主啟動入口 🆕
├── simple_config.py                 # 統一配置管理
├── requirements.txt                 # LINE Bot 依賴包
├── zeabur.json                      # 部署配置
├── src/namecard/
│   ├── api/line_bot/main.py         # LINE Bot 核心邏輯
│   ├── infrastructure/ai/
│   │   └── card_processor.py        # Gemini AI 名片處理器
│   ├── infrastructure/storage/
│   │   └── notion_client.py         # Notion 資料庫管理
│   └── core/services/               # 核心業務服務
└── .github/workflows/               # CI/CD 自動化
```

## 🔧 環境配置

### 必要環境變數
```bash
# LINE Bot 配置
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret

# AI 配置
GOOGLE_API_KEY=your_google_api_key
GOOGLE_API_KEY_FALLBACK=your_fallback_key  # 備用 API

# 資料庫配置
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
```

### GitHub Actions Secrets
在 Repository Settings → Secrets 中設置所有上述環境變數用於自動部署。

## 🚀 快速開始

### 本地開發
```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設置環境變數 (.env 文件)
cp .env.example .env
# 編輯 .env 填入 API keys

# 3. 啟動 LINE Bot
python app.py
# 📱 LINE Bot 將在 http://localhost:5002 啟動

# 4. 測試健康檢查
curl http://localhost:5002/health
```

### 部署到 Zeabur
```bash
# 1. 推送代碼自動觸發部署
git add .
git commit -m "feat: LINE Bot 名片識別系統"
git push origin main

# 2. 在 Zeabur Dashboard 設置環境變數
# 3. 設置 LINE Webhook URL: https://your-app.zeabur.app/callback
```

## 🎯 LINE Bot 功能

### 指令列表
| 指令 | 功能 | 範例 |
|------|------|------|
| `批次` | 啟動批次模式 | 批次 |
| `結束批次` | 結束批次並顯示統計 | 結束批次 |
| `狀態` | 查看批次進度 | 狀態 |
| `help` | 顯示使用說明 | help |
| 圖片上傳 | 智能名片識別 | [發送名片圖片] |

### 使用流程
1. **添加 LINE Bot**: 掃描 QR Code 或搜尋 Bot 名稱
2. **發送 help**: 查看使用說明
3. **上傳名片**: 直接發送名片照片
4. **批次處理**: 發送「批次」→ 連續上傳多張 → 發送「結束批次」
5. **查看結果**: 系統自動回傳 Notion 連結

### 智能功能
- **多名片檢測**: 自動識別單張圖片中的多張名片
- **品質評估**: AI 評估識別信心度，建議重拍模糊圖片
- **地址正規化**: 台灣地址自動標準化（台北 → 台北市）
- **API 容錯**: 主要 API 額度不足時自動切換備用 Key

## 🧪 測試和驗證

### 基本測試
```bash
# 健康檢查
curl http://localhost:5002/health

# 服務測試
curl http://localhost:5002/test

# Webhook 測試 (需要 LINE 簽名)
curl -X POST http://localhost:5002/callback
```

### 功能測試
1. **基本識別**: 發送單張清晰名片
2. **多名片**: 發送包含多張名片的照片
3. **批次處理**: 連續發送多張名片
4. **錯誤處理**: 發送非名片圖片測試錯誤處理

## 📊 性能指標
- **識別準確率**: ~90% (Gemini AI)
- **處理速度**: 5-10 秒/張
- **支援格式**: JPG, PNG, WebP
- **多名片**: 最多檢測 5 張/圖
- **批次處理**: 支援多用戶並發

## 🔄 開發工作流程
```bash
# 1. 本地開發測試
python app.py

# 2. 代碼提交
git add .
git commit -m "feat: 新功能"

# 3. 推送觸發 CI/CD
git push origin main

# 4. 自動部署到 Zeabur
# GitHub Actions 自動處理

# 5. 更新 LINE Webhook URL
# https://your-app.zeabur.app/callback
```

## 🐛 常見問題

### 部署相關
- **502 錯誤**: 檢查 Zeabur 環境變數是否設置完整
- **Webhook 失效**: 確認 LINE Developer Console 中的 URL 正確
- **依賴錯誤**: 檢查 requirements.txt 是否包含所有必要套件

### 功能相關
- **識別失敗**: 確保名片圖片清晰，光線充足
- **Notion 錯誤**: 檢查 API Key 和 Database ID 是否正確
- **API 額度**: 設置 GOOGLE_API_KEY_FALLBACK 備用 Key

## 📞 技術支援
- **GitHub Issues**: 回報問題和建議
- **CI/CD 自動化**: GitHub Actions 自動處理測試和部署
- **AI 協作**: 使用 Claude Code 進行功能開發

---

> **使用提醒**:
> - 確保 LINE 和 Notion API Keys 正確設置
> - 定期檢查 Gemini API 配額使用情況
> - 建議設置備用 API Key 避免服務中斷
