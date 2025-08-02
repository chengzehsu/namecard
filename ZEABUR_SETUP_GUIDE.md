# 🚀 Zeabur Telegram Bot 部署設置指南

## 📋 設置檢查清單

### ✅ 已完成
- [x] GitHub CLI 已授權
- [x] 代碼和配置文件就緒
- [x] 環境變數配置完整

### 🔄 需要完成
- [ ] 1. 綁定 GitHub 帳號到 Zeabur
- [ ] 2. 安裝 Zeabur GitHub App  
- [ ] 3. 在 Zeabur 上創建 Project 和 Service
- [ ] 4. 設置環境變數
- [ ] 5. 測試自動部署

---

## 🎯 方案一：GitHub App 部署（推薦）

### 步驟 1: 綁定 GitHub 帳號
👉 **立即操作**: [點擊綁定 GitHub 帳號](https://github.com/login/oauth/authorize?client_id=Iv1.eb8b8a6402b888d3&redirect_uri=https://zeabur.com/auth/github/callback&state=e30=)

### 步驟 2: 安裝 Zeabur GitHub App
👉 **立即操作**: [點擊安裝 GitHub App](https://github.com/apps/zeabur/installations/new)

**重要設置**:
- ✅ 選擇 `chengzehsu/namecard` repository
- ✅ 授予必要權限（讀取代碼、部署狀態）

### 步驟 3: 在 Zeabur 創建專案

1. **前往 Zeabur Dashboard**: https://dash.zeabur.com/
2. **創建新專案**:
   - 專案名稱: `namecard-telegram-bot`
   - 區域: `Hong Kong` (hkg)
3. **添加服務**:
   - 選擇 `GitHub Repository`
   - 選擇 `chengzehsu/namecard`
   - 服務名稱: `telegram-bot`
   - 分支: `main`

### 步驟 4: 配置服務設置

在 Zeabur 服務設置中：

```json
{
  "name": "telegram-bot",
  "source": {
    "type": "git",
    "repository": "chengzehsu/namecard",
    "branch": "main"
  },
  "build": {
    "commands": ["pip install -r requirements-telegram.txt"]
  },
  "start": {
    "command": "python main.py"
  },
  "port": 5003,
  "healthcheck": {
    "path": "/health"
  }
}
```

### 步驟 5: 設置環境變數

在 Zeabur Service > Environment 中添加：

```bash
# Bot Configuration
TELEGRAM_BOT_TOKEN=8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4
SERVICE_TYPE=telegram-bot

# AI Configuration  
GOOGLE_API_KEY=AIzaSyDv8zdH2jWnQWvCWtzQQHdUDHbxdZd17Ik
GOOGLE_API_KEY_FALLBACK=your_fallback_key_here
GEMINI_MODEL=gemini-2.5-pro

# Database Configuration
NOTION_API_KEY=secret_sBJHDjfBjzfRPHJbhZlKbTXe0L5S0U8rUCBKVHZfJQn
NOTION_DATABASE_ID=15aca5dfa95d80219cd3cfcfcceffe9a

# Runtime Configuration
PORT=5003
FLASK_ENV=production
PYTHONUNBUFFERED=1
PYTHON_VERSION=3.9
```

### 步驟 6: 部署測試

1. **完成設置後**，Push 任何代碼變更到 `main` 分支
2. **自動觸發部署**，在 Zeabur Dashboard 查看部署進度
3. **獲取部署 URL**，通常格式為 `https://telegram-bot-xxx.zeabur.app`

---

## 🎯 方案二：API Token 部署（進階）

如果您偏好使用 GitHub Actions + API Token：

### 1. 獲取 Zeabur API Token
- 前往: https://dash.zeabur.com/account/developer
- 生成新的 API Token
- 複製 Token 值

### 2. 設置 GitHub Secrets
```bash
# 在 GitHub Repository > Settings > Secrets and variables > Actions
ZEABUR_TOKEN=your_api_token_here
```

### 3. 修改 GitHub Actions 工作流
```yaml
name: Deploy Telegram Bot to Zeabur

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Zeabur
        env:
          ZEABUR_TOKEN: ${{ secrets.ZEABUR_TOKEN }}
        run: |
          curl -X POST "https://zeabur.com/api/projects/YOUR_PROJECT_ID/services/YOUR_SERVICE_ID/deploy" \
            -H "Authorization: Bearer $ZEABUR_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{
              "environment": "production",
              "branch": "main"
            }'
```

---

## 🔧 當前配置文件狀態

### ✅ 已準備就緒的文件:
- `main.py` - 入口文件 ✅
- `telegram_main.py` - 主邏輯 ✅  
- `telegram_app.py` - Flask 應用 ✅
- `requirements-telegram.txt` - 依賴文件 ✅
- `zeabur.json` - 部署配置 ✅

### 📝 建議的檔案結構：
```
namecard/
├── main.py                    # Zeabur 入口文件
├── telegram_main.py           # 主邏輯
├── telegram_app.py            # Flask 應用
├── requirements-telegram.txt  # 依賴清單
├── zeabur.json               # Zeabur 配置
└── .env.telegram.example     # 環境變數範例
```

---

## 🎯 推薦操作順序

1. **⭐ 首選**: 使用 GitHub App 方式
   - 點擊上面的連結完成 GitHub 授權和 App 安裝
   - 在 Zeabur 創建專案和服務
   - 設置環境變數
   - Push 代碼自動部署

2. **🔧 備選**: 如果需要更多控制，使用 API Token 方式

---

## 🆘 常見問題

### Q: GitHub App 與 API Token 方式有什麼區別？
**A**: 
- **GitHub App**: 官方推薦，自動化程度高，Push 即部署
- **API Token**: 更多控制權，可自定義部署流程

### Q: 如何查看部署狀態？
**A**: 前往 Zeabur Dashboard > 你的專案 > 服務詳情

### Q: 部署失敗怎麼辦？
**A**: 檢查：
1. GitHub App 權限是否正確
2. 環境變數是否完整
3. `main.py` 是否能正常啟動
4. 依賴是否正確安裝

---

## 🚀 立即開始

**建議您現在就點擊上面的連結開始設置！完成後，只需要 Push 代碼就能自動部署了。**

需要任何協助，請告知！