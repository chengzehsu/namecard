# 🚀 LINE Bot 名片管理系統 - 雲端部署指南

## 你的系統已經 100% 準備就緒！

✅ **已完成的功能**：
- Gemini AI 名片識別：完美運作
- Notion 資料庫整合：成功儲存
- 智能欄位推斷：自動分析決策影響力
- 電話格式化：國際化處理
- 完整的 LINE Bot 功能

## 🌐 選項 1：Zeabur 部署（推薦）

### 步驟：
1. **上傳到 GitHub**：
   ```bash
   git init
   git add .
   git commit -m "LINE Bot namecard system"
   git branch -M main
   git remote add origin <your-github-repo>
   git push -u origin main
   ```

2. **Zeabur 部署**：
   - 前往 https://zeabur.com
   - 登入並連接 GitHub
   - 選擇你的 repository
   - Zeabur 會自動偵測並部署

3. **設定環境變數**：
   ```
   LINE_CHANNEL_SECRET=a2b8d02fc60e86bf814ba8b74e87ea4a
   LINE_CHANNEL_ACCESS_TOKEN=qrq7RXBDXqh/7bn1wfjqj32/QzbtR96bsuKBmSxDc66WHpJoTmPlz3Kk+jur/YsEbyHsp0y51+SV+d3GBpE+pOaWs5/vVAoW7RvySjBEn2uq0rM2oFf1F20x+ZZAIcpPv0sce9AdrsBygU1RVFPijQdB04t89/1O/w1cDnyilFU=
   GOOGLE_API_KEY=AIzaSyCjDLiquCFpnghpMEzId5UfP3wq1OogRRs
   NOTION_API_KEY=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
   NOTION_DATABASE_ID=2377cb1a9ac98006bfc1c92f522b8bd4
   ```

4. **獲得 URL**：Zeabur 會給你一個穩定的 URL，如：
   `https://your-app-name.zeabur.app`

## 🌐 選項 2：Heroku 部署

### 步驟：
1. **安裝 Heroku CLI**
2. **創建 Heroku app**：
   ```bash
   heroku create your-linebot-app
   ```
3. **設定環境變數**：
   ```bash
   heroku config:set LINE_CHANNEL_SECRET=a2b8d02fc60e86bf814ba8b74e87ea4a
   heroku config:set LINE_CHANNEL_ACCESS_TOKEN=qrq7RXBDXqh/7bn1wfjqj32/QzbtR96bsuKBmSxDc66WHpJoTmPlz3Kk+jur/YsEbyHsp0y51+SV+d3GBpE+pOaWs5/vVAoW7RvySjBEn2uq0rM2oFf1F20x+ZZAIcpPv0sce9AdrsBygU1RVFPijQdB04t89/1O/w1cDnyilFU=
   heroku config:set GOOGLE_API_KEY=AIzaSyCjDLiquCFpnghpMEzId5UfP3wq1OogRRs
   heroku config:set NOTION_API_KEY=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
   heroku config:set NOTION_DATABASE_ID=2377cb1a9ac98006bfc1c92f522b8bd4
   ```
4. **部署**：
   ```bash
   git push heroku main
   ```

## 🌐 選項 3：Render 部署

1. 前往 https://render.com
2. 連接 GitHub repository
3. 選擇 "Web Service"
4. 設定環境變數
5. 自動部署

## 📱 設定 LINE Webhook

部署成功後：
1. 前往 LINE Developers Console
2. 設定 Webhook URL：`https://your-app-url.com/callback`
3. 開啟 "Use webhook"
4. 點擊 "Verify"（應該成功 ✅）
5. 關閉 "Auto-reply messages"

## 🎊 完成！

你的 LINE Bot 名片管理系統就完全運作了！

### 使用方式：
1. 加你的 LINE Bot 為好友
2. 傳送 "help" 查看說明
3. 上傳名片照片
4. 系統會自動識別並存入 Notion

### 功能特色：
- 🤖 Gemini AI 精準識別中英文名片
- 📊 自動推斷決策影響力（董事長→高，經理→中，專員→低）
- 📞 電話號碼自動格式化為國際格式 (+886...)
- 💾 直接存入你的 Notion 利害關係人資料庫
- 🔗 回傳 Notion 頁面連結方便查看

你已經有一個完整的企業級名片管理系統了！🎉