# 🚀 LINE Bot 雲端部署指南

無需 ngrok，讓更多人都能使用你的名片管理 LINE Bot！

## 📋 **推薦的部署平台**

### 1. 🚂 **Railway** (最推薦)
- ✅ **免費額度**: 每月 $5 免費額度
- ✅ **自動部署**: 連接 GitHub 自動部署
- ✅ **固定 URL**: 不會像 ngrok 一樣變動
- ✅ **簡單設定**: 幾分鐘完成部署

### 2. 🌊 **Render** (次推薦)
- ✅ **免費方案**: 有免費的靜態和 Web 服務
- ✅ **自動 SSL**: 自動提供 HTTPS
- ✅ **GitHub 整合**: 自動從 GitHub 部署

### 3. ☁️ **Heroku** (傳統選擇)
- ⚠️ **付費**: 已取消免費方案
- ✅ **成熟平台**: 功能完整
- ✅ **文檔齊全**: 教學資源豐富

---

## 🛠️ **Railway 部署步驟**

### Step 1: 準備 GitHub 倉庫
你的代碼已經在 GitHub 上了：`https://github.com/chengzehsu/namecard.git`

### Step 2: 註冊 Railway
1. 前往 [Railway.app](https://railway.app/)
2. 使用 GitHub 帳號登入
3. 授權 Railway 存取你的 GitHub

### Step 3: 創建新專案
1. 點擊 **"New Project"**
2. 選擇 **"Deploy from GitHub repo"**
3. 選擇你的 `namecard` 倉庫
4. 點擊 **"Deploy Now"**

### Step 4: 設定環境變數
在 Railway 專案設定中添加以下環境變數：

```bash
# LINE Bot 設定
LINE_CHANNEL_SECRET=a2b8d02fc60e86bf814ba8b74e87ea4a
LINE_CHANNEL_ACCESS_TOKEN=qrq7RXBDXqh/7bn1wfjqj32/QzbtR96bsuKBmSxDc66WHpJoTmPlz3Kk+jur/YsEbyHsp0y51+SV+d3GBpE+pOaWs5/vVAoW7RvySjBEn2uq0rM2oFf1F20x+ZZAIcpPv0sce9AdrsBygU1RVFPijQdB04t89/1O/w1cDnyilFU=

# Google Gemini API 設定
GOOGLE_API_KEY=AIzaSyCjDLiquCFpnghpMEzId5UfP3wq1OogRRs

# Notion API 設定
NOTION_API_KEY=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
NOTION_DATABASE_ID=2377cb1a9ac98006bfc1c92f522b8bd4

# 部署設定
PORT=8080
```

### Step 5: 設定部署檔案
Railway 會自動偵測你的 `railway_app.py` 和 `requirements_deploy.txt`

如果需要，創建 `Procfile`:
```
web: python railway_app.py
```

### Step 6: 部署完成
- Railway 會自動部署並提供一個固定 URL
- 例如：`https://namecard-production.up.railway.app`

### Step 7: 更新 LINE Webhook URL
1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Bot 頻道
3. 在 **Messaging API** 設定中
4. 將 **Webhook URL** 更新為：`https://your-railway-url.railway.app/callback`
5. 點擊 **Verify** 驗證連接
6. 啟用 **Use webhook**

---

## 🎯 **其他部署選項**

### Option 2: Render 部署

1. **註冊 Render**: 前往 [render.com](https://render.com)
2. **連接 GitHub**: 授權 Render 存取倉庫
3. **創建 Web Service**:
   - Repository: `chengzehsu/namecard`
   - Build Command: `pip install -r requirements_deploy.txt`
   - Start Command: `python railway_app.py`
4. **設定環境變數**: 添加相同的環境變數
5. **部署**: Render 會提供固定 URL

### Option 3: Google Cloud Run

1. **安裝 Google Cloud CLI**
2. **創建 Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_deploy.txt .
RUN pip install -r requirements_deploy.txt

COPY . .

EXPOSE 8080
CMD ["python", "railway_app.py"]
```

3. **部署指令**:
```bash
gcloud run deploy namecard-bot \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

---

## 🔧 **部署後設定**

### 測試部署
```bash
# 健康檢查
curl https://your-app-url.com/health

# 應該返回
{"status": "healthy", "message": "LINE Bot is running on Railway"}
```

### 監控和日誌
- **Railway**: 在控制台查看部署日誌
- **Render**: 在 Dashboard 查看運行狀態
- **Google Cloud**: 使用 Cloud Logging

### 自動部署
所有平台都支援 **Git 推送自動部署**：
```bash
# 本地修改後
git add .
git commit -m "更新功能"
git push origin main

# 平台會自動重新部署
```

---

## 💰 **成本比較**

| 平台 | 免費額度 | 付費起價 | 推薦度 |
|------|----------|----------|--------|
| **Railway** | $5/月 | $0.01/小時 | ⭐⭐⭐⭐⭐ |
| **Render** | 750小時/月 | $7/月 | ⭐⭐⭐⭐ |
| **Google Cloud Run** | 200萬請求/月 | 按使用量 | ⭐⭐⭐ |
| **Heroku** | 無免費 | $7/月 | ⭐⭐ |

## 🎉 **部署完成後的優勢**

### ✅ **不再需要 ngrok**
- 固定的 HTTPS URL
- 24/7 穩定運行
- 不會斷線或重新連接

### ✅ **更多人可以使用**
- 任何人都可以加 LINE Bot 好友
- 不限制同時使用人數
- 全球都能存取

### ✅ **自動化管理**
- 自動重啟服務
- 自動擴展資源
- 自動備份和恢復

### ✅ **專業形象**
- 自定義域名（可選）
- 穩定的服務品質
- 企業級的可靠性

---

## 🔍 **故障排除**

### 常見問題

**1. 部署失敗**
```bash
# 檢查依賴項
pip install -r requirements_deploy.txt

# 檢查 Python 版本
python --version  # 應該是 3.9+
```

**2. 環境變數問題**
- 確認所有必要環境變數都已設定
- 檢查 API 金鑰是否正確
- 確認 PORT 環境變數設為 8080

**3. LINE Webhook 驗證失敗**
- 確認 URL 格式：`https://your-app.com/callback`
- 檢查應用是否正常運行
- 確認防火牆設定

**4. Notion 連接問題**
- 檢查 Notion API 金鑰權限
- 確認資料庫 ID 正確
- 檢查資料庫共享設定

### 監控工具
```bash
# 檢查應用狀態
curl https://your-app-url.com/health

# 檢查 LINE webhook
curl -X GET https://your-app-url.com/callback
```

---

## 📈 **進階功能**

### 自動縮放
大部分平台都支援自動根據流量調整資源

### 自定義域名
```bash
# 設定自定義域名
your-company.com -> your-app.railway.app
```

### SSL 憑證
所有推薦平台都自動提供 SSL 憑證

### 監控警報
設定當服務異常時發送通知

---

**準備好擺脫 ngrok，讓你的 LINE Bot 正式上線了嗎？** 🚀

選擇 Railway 開始部署，只需要 10 分鐘就能讓全世界的人使用你的名片管理系統！