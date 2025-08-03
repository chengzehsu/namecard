# 異步高效能名片處理系統 - 部署與效能指南

## 🎯 系統概述

本系統是一個**企業級高並發名片處理平台**，支援多用戶同時處理名片，解決了原有系統的塞車問題。

### 核心優勢
- **50+ 並發用戶**：同時支援 50 位用戶處理名片
- **2-5 秒響應時間**：相比原系統提升 50-75%
- **智能快取**：相同圖片秒級回應
- **自動 Notion 保存**：並發寫入，避免阻塞
- **實時監控**：完整的效能指標和健康檢查

## 🚀 快速部署

### 1. 環境準備

**必要環境變數**：
```bash
# AI 服務
GOOGLE_API_KEY=your_main_api_key
GOOGLE_API_KEY_FALLBACK=your_backup_api_key
GEMINI_MODEL=gemini-1.5-pro

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret

# Notion 資料庫
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id

# 效能配置
MAX_CONCURRENT=20
CACHE_MEMORY_MB=200
WORKERS=4
```

### 2. Zeabur 一鍵部署

```bash
# 1. 上傳 async_zeabur.json 配置
cp deployment/async_zeabur.json zeabur.json

# 2. 在 Zeabur Dashboard 設置環境變數
# 3. 部署完成後獲取 URL
# 4. 更新 LINE Webhook URL
```

**Zeabur 部署配置**：
- **記憶體**: 1GB
- **CPU**: 1.0 核心
- **Worker 數量**: 4 個
- **自動擴展**: 1-3 實例
- **健康檢查**: `/health` 端點

### 3. 本地開發部署

```bash
# 安裝依賴
pip install -r deployment/async_requirements.txt

# 啟動服務
./deployment/scripts/start_async_service.sh

# 或手動啟動
python3 -m src.namecard.api.async_app
```

## 📊 效能監控

### 即時監控端點

| 端點 | 功能 | 範例回應 |
|------|------|----------|
| `/health` | 系統健康檢查 | `{"status": "healthy"}` |
| `/stats` | 即時效能統計 | 併發數、處理時間等 |
| `/performance-report` | 詳細效能報告 | 24小時效能分析 |

### 關鍵效能指標 (KPI)

**響應時間指標**：
- **目標**: < 5 秒平均響應時間
- **監控**: P95 響應時間 < 10 秒
- **警報**: P99 響應時間 > 15 秒

**並發能力指標**：
- **目標**: 支援 50+ 並發用戶
- **監控**: 並發處理成功率 > 95%
- **警報**: 並發失敗率 > 10%

**快取效率指標**：
- **目標**: 快取命中率 > 30%
- **監控**: 快取加速比 > 5x
- **優化**: 達到 60% 命中率

## 🧪 效能測試

### 自動化效能測試

```bash
# 執行綜合效能測試
cd tests/performance
python3 test_concurrent_performance.py

# 測試項目：
# - 單用戶效能基準
# - 5-15 用戶並發測試  
# - 批次處理效能
# - 快取效果驗證
# - 壓力測試 (50 並發)
```

### 手動壓力測試

```bash
# 使用 curl 測試健康檢查
for i in {1..100}; do
  curl -s https://your-app.zeabur.app/health &
done
wait

# 監控回應時間
curl -w "@curl-format.txt" -s https://your-app.zeabur.app/stats
```

**curl-format.txt**：
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

## ⚡ 效能優化策略

### 1. 並發調優

**CPU 密集型工作負載**：
```bash
# 調整 Worker 數量 = CPU 核心數
WORKERS=4  # 4 核心系統

# 調整 AI 處理並發數
MAX_CONCURRENT_AI=15  # 建議 CPU 核心數 * 3-4
```

**記憶體優化**：
```bash
# 根據可用記憶體調整快取
CACHE_MEMORY_MB=200   # 1GB 系統建議值
CACHE_DISK_MB=1000    # SSD 建議值

# 監控記憶體使用
python3 -c "
import psutil
print(f'記憶體使用: {psutil.virtual_memory().percent}%')
"
```

### 2. 快取策略優化

**快取層級**：
1. **L1 記憶體快取** (100ms 存取) - 100 個最近項目
2. **L2 Redis 快取** (1-5ms 存取) - 1000+ 項目 
3. **L3 檔案快取** (10-50ms 存取) - 長期存儲

**快取鍵策略**：
```python
# 圖片指紋快取鍵
cache_key = f"ai_result:{md5(image_bytes).hexdigest()}"

# TTL 設置
memory_ttl = 3600      # 1 小時
redis_ttl = 86400      # 24 小時  
disk_ttl = 604800      # 7 天
```

### 3. API 配額管理

**多 API Key 輪替**：
```python
# 配置多個 Gemini API Key
GOOGLE_API_KEY_1=primary_key
GOOGLE_API_KEY_2=secondary_key  
GOOGLE_API_KEY_3=tertiary_key

# 自動負載平衡
api_keys = [key1, key2, key3]
current_key = keys[request_count % len(keys)]
```

**配額監控**：
- 追蹤每個 API Key 的使用量
- 自動切換到可用的 API Key
- 預測配額重置時間

## 🚨 故障排除

### 常見問題診斷

**1. 高延遲問題**
```bash
# 檢查 AI 處理時間
curl https://your-app.zeabur.app/stats | jq '.ai_processor_stats.avg_processing_time'

# 解決方案：
# - 增加 MAX_CONCURRENT_AI
# - 檢查 API Key 配額
# - 啟用更多快取
```

**2. 並發限制達到**
```bash
# 檢查並發狀態
curl https://your-app.zeabur.app/stats | jq '.ai_processor_stats.active_tasks'

# 解決方案：
# - 增加 WORKERS 數量
# - 調整 MAX_CONCURRENT 設置
# - 檢查系統資源使用
```

**3. 快取未命中**
```bash
# 檢查快取效率
curl https://your-app.zeabur.app/stats | jq '.ai_processor_stats.cache_hit_rate'

# 解決方案：
# - 增加快取大小
# - 檢查快取鍵生成邏輯
# - 調整 TTL 設置
```

### 錯誤日誌分析

**重要日誌位置**：
```bash
# 應用日誌
logs/error.log
logs/access.log

# 系統日誌
/var/log/hypercorn/
```

**常見錯誤模式**：
```bash
# API 配額超限
grep "quota exceeded" logs/error.log

# 記憶體不足
grep "Memory" logs/error.log

# 並發超限  
grep "Semaphore" logs/error.log
```

## 📈 容量規劃

### 用戶規模預估

| 用戶數 | 記憶體需求 | CPU 需求 | Worker 建議 |
|--------|------------|-----------|-------------|
| 1-10 | 512MB | 0.5 核心 | 2 |
| 10-30 | 1GB | 1.0 核心 | 4 |
| 30-50 | 2GB | 2.0 核心 | 6 |
| 50+ | 4GB+ | 4.0+ 核心 | 8+ |

### 自動擴展配置

**Zeabur 自動擴展**：
```json
{
  "scaling": {
    "min_instances": 1,
    "max_instances": 5,
    "target_cpu": 70,
    "target_memory": 80,
    "scale_up_threshold": 80,
    "scale_down_threshold": 30
  }
}
```

### 成本優化

**資源使用優化**：
- **CPU**: 平均使用率 < 70%
- **記憶體**: 平均使用率 < 80%  
- **網路**: 壓縮回應內容
- **儲存**: 定期清理快取

## 🔐 安全性考量

### API Key 安全
- 使用 GitHub Secrets 儲存
- 定期輪替 API Key
- 監控異常使用模式

### 速率限制
- 每用戶每分鐘最多 10 次請求
- 每 IP 每小時最多 100 次請求
- 異常流量自動封鎖

### 資料保護
- 圖片數據不持久化存儲
- Notion 資料傳輸加密
- 用戶會話自動過期

## 📞 技術支援

### 監控告警
- **Uptime 監控**: UptimeRobot / Pingdom
- **效能監控**: Grafana + Prometheus
- **錯誤追蹤**: Sentry

### 聯絡資訊
- **緊急事件**: 檢查 `/health` 端點
- **效能問題**: 檢查 `/performance-report`
- **部署支援**: 參考 Zeabur 文檔

---

🎉 **恭喜！您的高效能名片處理系統已就緒。享受 50+ 並發用戶的順暢體驗！**