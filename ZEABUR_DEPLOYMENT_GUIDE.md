# Zeabur 部署指南

## 🌟 為什麼選擇 Zeabur？

Zeabur 是現代化的雲端應用部署平台，特別適合這個 LINE Bot 專案：

- ⚡ **快速部署**: 從推送代碼到上線只需幾分鐘
- 🔄 **自動 CI/CD**: 與 GitHub 完美整合
- 🌏 **全球節點**: 亞洲地區（香港、新加坡）低延遲
- 💰 **免費額度**: 小型專案免費使用
- 🎛️ **簡單管理**: 直觀的 Dashboard 介面

## 🚀 快速部署步驟

### 方法 1: 使用 GitHub Actions 自動部署 (推薦)

#### 1. 設置 Zeabur Token

1. 前往 [Zeabur Dashboard](https://dash.zeabur.com/)
2. 註冊/登入帳戶
3. 前往 **Account** → **Developer** → **API Tokens**
4. 點擊 **Generate New Token**
5. 複製生成的 Token

#### 2. 設置 GitHub Secrets

1. 前往您的 GitHub Repository
2. 點擊 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**
4. 添加以下 Secret:
   ```
   Name: ZEABUR_TOKEN
   Value: [您的 Zeabur Token]
   ```

#### 3. 觸發部署

**自動部署 (推薦)**:
```bash
# 推送代碼到 main 分支即可自動部署
git add .
git commit -m "deploy: 部署到 Zeabur"
git push origin main
```

**手動部署**:
1. 前往 GitHub Repository → **Actions**
2. 選擇 "部署到 Zeabur" workflow
3. 點擊 **Run workflow**
4. 選擇部署環境 (production/staging)
5. 點擊 **Run workflow**

#### 4. 監控部署過程

1. 在 GitHub Actions 中查看部署日誌
2. 部署成功後會顯示應用 URL
3. 前往 [Zeabur Dashboard](https://dash.zeabur.com/) 查看應用狀態

### 方法 2: 手動部署

#### 1. 安裝 Zeabur CLI

```bash
# macOS/Linux
curl -fsSL https://zeabur.com/install.sh | bash

# Windows (PowerShell)
iwr -useb https://zeabur.com/install.ps1 | iex
```

#### 2. 登入 Zeabur

```bash
zeabur auth login
# 會開啟瀏覽器進行登入
```

#### 3. 部署專案

```bash
# 在專案根目錄執行
zeabur deploy

# 或指定專案名稱
zeabur deploy --name namecard-line-bot
```

## 🔧 部署後配置

### 1. 設置環境變數

在 Zeabur Dashboard 中設置以下環境變數：

```bash
# LINE Bot 配置
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Google Gemini AI 配置
GOOGLE_API_KEY=your_google_api_key

# Notion 配置
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id

# 應用配置
PORT=5002
FLASK_ENV=production
```

### 2. 獲取應用 URL

部署成功後，Zeabur 會提供一個 URL，格式如下：
```
https://namecard-app-xxxx.zeabur.app
```

### 3. 更新 LINE Bot Webhook

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 選擇您的 Channel
3. 前往 **Messaging API** 標籤
4. 在 **Webhook settings** 中:
   - 更新 **Webhook URL**: `https://your-app.zeabur.app/callback`
   - 啟用 **Use webhook**
   - 點擊 **Verify** 測試連接

### 4. 驗證部署

測試以下端點確認部署成功：

```bash
# 健康檢查
curl https://your-app.zeabur.app/health

# 服務測試
curl https://your-app.zeabur.app/test

# Callback 端點
curl https://your-app.zeabur.app/callback
```

## 📊 監控和管理

### Zeabur Dashboard 功能

1. **應用概覽**: 查看應用狀態、CPU、記憶體使用
2. **日誌**: 即時查看應用日誌
3. **環境變數**: 管理配置變數
4. **域名**: 設置自定義域名
5. **擴展**: 調整實例數量和規格

### 日誌查看

```bash
# CLI 查看日誌
zeabur logs --project namecard-line-bot --service namecard-app

# 實時日誌
zeabur logs --project namecard-line-bot --service namecard-app --follow
```

### 重新部署

```bash
# GitHub Actions 重新部署
# 推送任何變更到 main 分支即可

# CLI 重新部署
zeabur redeploy --project namecard-line-bot --service namecard-app
```

## 🔧 配置文件說明

### zeabur.json
專案根目錄的 `zeabur.json` 包含部署配置：

```json
{
  "name": "namecard-line-bot",
  "type": "python",
  "framework": "flask",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "python app.py",
  "environment": {
    "PYTHON_VERSION": "3.9",
    "PORT": "5002"
  },
  "scaling": {
    "minInstances": 1,
    "maxInstances": 3
  },
  "healthCheck": {
    "path": "/health",
    "port": 5002
  }
}
```

### runtime.txt
指定 Python 版本：
```
python-3.9.19
```

## 🐛 常見問題

### 1. 部署失敗

**問題**: GitHub Actions 部署失敗
**解決**:
- 檢查 `ZEABUR_TOKEN` 是否正確設置
- 確認 Zeabur CLI 權限
- 查看 Actions 日誌找出具體錯誤

### 2. 應用無法啟動

**問題**: 部署成功但應用無回應
**解決**:
- 檢查環境變數是否完整設置
- 查看 Zeabur Dashboard 中的應用日誌
- 確認 `PORT` 環境變數設為 `5002`

### 3. LINE Bot 無回應

**問題**: LINE Bot 收不到訊息
**解決**:
- 確認 Webhook URL 已更新為 Zeabur 的 URL
- 測試 `/callback` 端點是否可訪問
- 檢查 LINE Channel 設置

### 4. API 調用失敗

**問題**: Notion 或 Gemini API 調用失敗
**解決**:
- 檢查 API Keys 是否正確設置
- 確認 API 配額是否足夠
- 檢查網路連接和防火牆設置

## 💰 費用說明

### Zeabur 免費額度
- **免費用量**: 每月 $5 USD 信用額度
- **適用範圍**: 小型應用、個人專案
- **限制**: CPU 和記憶體使用量限制

### 收費標準
- **按使用量計費**: 根據實際 CPU、記憶體、網路使用量
- **無閒置費用**: 應用不運行時不計費
- **透明計價**: 在 Dashboard 中即時查看用量

## 🚀 進階配置

### 自定義域名

1. 在 Zeabur Dashboard 中前往 **Domains**
2. 點擊 **Add Custom Domain**
3. 輸入您的域名
4. 在 DNS 提供商中設置 CNAME 記錄

### 擴展配置

```json
{
  "scaling": {
    "minInstances": 1,
    "maxInstances": 5,
    "targetCPU": 70,
    "targetMemory": 80
  }
}
```

### SSL 憑證

Zeabur 自動提供 Let's Encrypt SSL 憑證，無需額外配置。

## 📞 技術支援

- **官方文檔**: [zeabur.com/docs](https://zeabur.com/docs)
- **Discord 社群**: [discord.gg/zeabur](https://discord.gg/zeabur)
- **GitHub 議題**: 在本專案中開啟 Issue

## 🎯 最佳實踐

1. **監控應用**: 定期查看 Dashboard 中的性能指標
2. **環境分離**: 使用不同專案進行開發和生產環境
3. **備份策略**: 定期備份重要資料和配置
4. **安全管理**: 定期更換 API Keys 和 Tokens
5. **版本控制**: 使用 Git Tags 標記發布版本

---

🎉 恭喜！您已成功將名片管理 LINE Bot 部署到 Zeabur。享受現代化的雲端部署體驗吧！