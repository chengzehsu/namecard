# 🛡️ 安全更改正式環境 LINE TOKEN 指南

## 📋 完整驗證流程

### Step 1: 本地驗證新 TOKEN
```bash
# 運行驗證腳本
python verify_new_token.py

# 預期輸出:
# ✅ Access Token 驗證通過
# ✅ Channel Secret 格式正確
# ✅ API 配額檢查通過
# 🎉 驗證成功！可以安全地更新到正式環境
```

### Step 2: 備份當前配置
1. **截圖保存** Zeabur Dashboard 當前環境變數
2. **記錄當前 Webhook URL** (LINE Developers Console)
3. **測試當前系統**:
   ```bash
   curl https://your-app.zeabur.app/health
   curl https://your-app.zeabur.app/test
   ```

### Step 3: 漸進式更新策略

#### 3.1 更新環境變數 (低風險)
1. 前往 Zeabur Dashboard
2. 進入服務 → Environment Variables
3. **一次只更改一個變數**:
   - 先更新 `LINE_CHANNEL_ACCESS_TOKEN`
   - 點擊 Save → 觀察 2-3 分鐘
   - 確認無錯誤後再更新 `LINE_CHANNEL_SECRET`

#### 3.2 即時監控部署
```bash
# 持續監控健康狀態
watch -n 10 'curl -s https://your-app.zeabur.app/health | jq'

# 或使用簡單版本
while true; do curl -s https://your-app.zeabur.app/health && sleep 10; done
```

#### 3.3 驗證新配置
```bash
# 檢查服務狀態
curl https://your-app.zeabur.app/test

# 預期回應應包含:
# "notion": {"success": true}
# "gemini": {"success": true}
```

### Step 4: Webhook 更新與測試

#### 4.1 更新 LINE Webhook (如果 URL 有變)
1. LINE Developers Console → Messaging API
2. Webhook URL: `https://your-app.zeabur.app/callback`
3. **重要**: 點擊 "Verify" 按鈕測試連接

#### 4.2 端到端功能測試
1. **基本測試**: 發送 "help" 指令
2. **圖片測試**: 上傳一張測試名片
3. **批次測試**: 測試批次模式

## 🚨 緊急回滾計劃

### 如果出現問題:
1. **立即回滾環境變數**:
   - 返回 Zeabur Dashboard
   - 恢復舊的 TOKEN 值
   - 點擊 Redeploy

2. **檢查錯誤日誌**:
   - Zeabur Dashboard → Logs
   - 查看具體錯誤信息

3. **聯繫支援**:
   - 準備錯誤截圖
   - 記錄具體時間點

## ✅ 成功確認清單

- [ ] 新 TOKEN 本地驗證通過
- [ ] 當前配置已備份
- [ ] 環境變數更新無錯誤
- [ ] 健康檢查通過 (/health)
- [ ] 服務測試通過 (/test)
- [ ] LINE Webhook 驗證成功
- [ ] 基本功能測試通過
- [ ] 圖片識別功能正常

## 📞 故障排除

### 常見問題:
1. **502 Bad Gateway**: 通常是環境變數錯誤
2. **Webhook 驗證失敗**: Channel Secret 不正確
3. **Bot 無回應**: Access Token 無效或過期

### 診斷指令:
```bash
# 檢查部署狀態
curl -I https://your-app.zeabur.app/health

# 檢查 LINE Webhook
curl -X POST https://your-app.zeabur.app/callback \
  -H "Content-Type: application/json" \
  -d '{"events":[]}'
```

---
**⚠️ 重要提醒**: 在上班時間進行更改，確保能及時處理任何問題！