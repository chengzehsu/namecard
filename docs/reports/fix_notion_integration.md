# 🔧 Notion API 修復完整指南

## 📊 問題分析

根據診斷結果：
- ✅ **Telegram Webhook URL 設置正確** (`/telegram-webhook`)
- ✅ **基本 webhook 功能正常** (返回 200 OK)
- ❌ **Notion API 無效** (`API token is invalid`)
- ❌ **圖片處理返回 500 錯誤** (由於 Notion 連接失敗)

## 🎯 根本問題

當您上傳圖片到 Telegram Bot 時：
1. ✅ Telegram 發送 webhook 到正確端點
2. ✅ Bot 接收並開始處理
3. ❌ **Notion API 連接失敗，導致整個流程失敗**
4. ❌ **用戶沒有收到任何回應**

## 🛠️ 修復步驟

### Step 1: 重新創建 Notion Integration

1. **前往 Notion Integrations 頁面**
   ```
   https://www.notion.so/my-integrations
   ```

2. **創建新的 Integration**
   - 點擊 `+ New integration`
   - Name: `名片管理系統` 或 `Business Card Manager`
   - Associated workspace: 選擇您的工作區
   - 點擊 `Submit`

3. **複製 API Key**
   - 複製 `Internal Integration Token`
   - 格式應該是: `secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **確保複製完整，包括 `secret_` 前綴**

### Step 2: 連接資料庫

1. **開啟您的名片資料庫**
   - 前往您的 Notion 名片資料庫頁面

2. **添加 Integration 權限**
   - 點擊右上角 `...` (三個點)
   - 選擇 `Share` 或 `連結`
   - 點擊 `Invite`
   - 搜尋您剛創建的 Integration 名稱
   - 選擇 Integration 並給予權限
   - 點擊 `Invite`

3. **確認權限設置**
   - 確保 Integration 有 `Edit` 權限
   - 不只是 `View` 權限

### Step 3: 獲取正確的 Database ID

1. **複製資料庫 URL**
   - 在資料庫頁面複製瀏覽器地址欄的 URL
   - 格式類似: `https://www.notion.so/yourname/DATABASE_ID?v=VIEW_ID`

2. **提取 Database ID**
   - 找到 URL 中的 32 位字符串
   - **移除所有連字符 (`-`)**
   - 例如: `a1b2c3d4-e5f6-7890-abcd-ef1234567890` → `a1b2c3d4e5f67890abcdef1234567890`

### Step 4: 更新 Zeabur 環境變數

1. **前往 Zeabur Dashboard**
   ```
   https://dash.zeabur.com/
   ```

2. **找到您的專案和服務**
   - 點擊專案名稱
   - 點擊服務名稱 (通常是 `telegram-bot` 或類似名稱)

3. **更新環境變數**
   - 點擊 `Variables` 或 `Environment Variables` 標籤
   - 更新以下變數:
     ```
     NOTION_API_KEY=secret_your_new_integration_token_here
     NOTION_DATABASE_ID=your_32_character_database_id_here
     ```
   - **確保沒有多餘的空格或換行**

4. **保存並重新部署**
   - 點擊 `Save`
   - 點擊 `Redeploy` 或 `Deploy`
   - 等待部署完成 (通常 2-3 分鐘)

### Step 5: 驗證修復效果

1. **檢查服務狀態**
   ```bash
   curl https://namecard-app.zeabur.app/test
   ```

   預期結果:
   ```json
   {
     "notion": {"success": true, "message": "Notion 連接正常"},
     "telegram": {"success": true, "message": "Telegram Bot 連接正常"},
     "gemini": {"success": true, "message": "Gemini 連接正常"}
   }
   ```

2. **測試 Telegram Bot**
   - 在 Telegram 中發送一張名片圖片
   - 應該收到: `📸 收到名片圖片！正在使用 AI 識別中，請稍候...`
   - 然後收到處理結果或錯誤訊息

## 🔍 常見問題排查

### 問題 1: API Key 格式錯誤
**症狀**: `API token is invalid`
**解決**: 確保 API Key 以 `secret_` 開頭，完整複製所有字符

### 問題 2: Database ID 錯誤
**症狀**: `Database not found` 或 `Object not found`
**解決**: 重新獲取 Database ID，移除所有連字符

### 問題 3: 權限不足
**症狀**: `Insufficient permissions`
**解決**: 確保 Integration 有資料庫的 Edit 權限

### 問題 4: 環境變數更新後沒生效
**症狀**: 修改後仍顯示舊錯誤
**解決**: 確保點擊了 `Redeploy`，等待部署完成

## 📋 資料庫欄位檢查

確保您的 Notion 資料庫包含以下欄位：

| 欄位名稱 | 類型 | 是否必要 |
|---------|------|----------|
| Name | Title | ✅ 必要 |
| 公司名稱 | Text | ✅ 必要 |
| 部門 | Text | 建議 |
| 職稱 | Select | 建議 |
| 決策影響力 | Select | 建議 |
| Email | Email | 建議 |
| 電話 | Phone | 建議 |
| 地址 | Text | 建議 |
| 取得聯繫來源 | Text | 建議 |
| 聯繫注意事項 | Text | 建議 |

## 🎉 成功驗證

修復成功後，您應該能夠：

1. **上傳名片圖片到 Telegram Bot**
2. **收到處理中訊息**: `📸 收到名片圖片！正在使用 AI 識別中，請稍候...`
3. **收到 AI 識別結果**，包含：
   - 姓名、公司、職稱等信息
   - Notion 頁面連結
   - 識別信心度

## 📞 需要幫助？

如果按照步驟操作後仍有問題：

1. **檢查 Zeabur 服務日誌**
   - Dashboard → 專案 → 服務 → Logs 標籤

2. **確認所有環境變數**
   - `TELEGRAM_BOT_TOKEN`: 設置正確
   - `GOOGLE_API_KEY`: 設置正確
   - `NOTION_API_KEY`: 新的有效 Token
   - `NOTION_DATABASE_ID`: 正確的 32 位 ID

3. **重新測試**
   - 等待 5 分鐘讓部署完全生效
   - 重新上傳圖片測試
