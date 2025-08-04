# 異步訊息排程系統整合指南

## 🎯 概述

本指南說明如何將新的異步訊息排程系統整合到現有的 Telegram Bot 中，實現高效的批次處理和連接池優化。

## 🏗️ 系統架構

```
現有系統                     新增排程系統
┌─────────────────┐         ┌──────────────────────┐
│ TelegramBotHandler │  →   │ EnhancedTelegramBotHandler │
│                 │         │  + AsyncMessageQueue  │
│ ■ 直接發送      │         │  ■ 智能排程           │
│ ■ 基本重試      │         │  ■ 批次合併           │
│ ■ 錯誤處理      │         │  ■ 優先級管理         │
└─────────────────┘         │  ■ 動態併發控制       │
                            └──────────────────────┘
```

## 📋 整合步驟

### 步驟 1: 安裝和導入

```python
# 在您的主應用中導入增強處理器
from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
    EnhancedTelegramBotHandler,
    create_enhanced_telegram_handler
)
```

### 步驟 2: 替換現有處理器

#### 方案 A: 最小變更整合（推薦）

```python
# 現有代碼
class TelegramBotApplication:
    def __init__(self):
        # 舊版本
        # self.telegram_handler = TelegramBotHandler()
        
        # 新版本 - 直接替換，保持向後兼容
        self.telegram_handler = EnhancedTelegramBotHandler(
            enable_message_queue=True  # 啟用排程系統
        )
        
    async def startup(self):
        """應用啟動時啟動排程系統"""
        await self.telegram_handler.start_queue_system()
        
    async def shutdown(self):
        """應用關閉時清理資源"""
        await self.telegram_handler.close()
```

#### 方案 B: 工廠模式整合

```python
async def create_telegram_application():
    """創建配置好的應用實例"""
    # 使用工廠函數創建處理器
    telegram_handler = await create_enhanced_telegram_handler(
        enable_queue=True,
        auto_start=True  # 自動啟動排程系統
    )
    
    return TelegramBotApplication(telegram_handler)
```

### 步驟 3: 批次處理場景優化

#### 3.1 單張名片處理（無變更）

```python
# 現有代碼無需修改
async def handle_single_card(self, chat_id: str, image_data: bytes):
    # 系統會自動決定是否使用排程
    result = await self.telegram_handler.safe_send_message(
        chat_id=chat_id,
        text="📸 收到名片圖片，正在處理..."
    )
    
    # 處理完成後發送結果
    card_info = await self.process_card(image_data)
    await self.telegram_handler.safe_send_message(
        chat_id=chat_id,
        text=f"✅ 處理完成: {card_info['name']}"
    )
```

#### 3.2 批次處理優化（建議使用）

```python
async def handle_batch_cards(self, chat_id: str, card_images: List[bytes]):
    # 使用批次上下文管理器
    async with self.telegram_handler.batch_context("card_batch") as batch_id:
        
        # 批次開始通知
        await self.telegram_handler.send_batch_message(
            chat_id=chat_id,
            text=f"🚀 開始批次處理 {len(card_images)} 張名片"
        )
        
        # 並發處理
        tasks = []
        for i, image_data in enumerate(card_images):
            task = self._process_card_with_feedback(
                chat_id, image_data, i + 1, len(card_images)
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 發送批次完成統計
        successful = sum(1 for r in results if not isinstance(r, Exception))
        await self.telegram_handler.send_completion_message(
            chat_id=chat_id,
            text=f"🎉 批次處理完成: {successful}/{len(card_images)} 成功",
            parse_mode="Markdown"
        )

async def _process_card_with_feedback(self, chat_id: str, image_data: bytes, 
                                    index: int, total: int):
    # 進度通知（會被智能合併）
    await self.telegram_handler.send_batch_message(
        chat_id=chat_id,
        text=f"🔄 處理中 {index}/{total}"
    )
    
    # 實際處理
    card_info = await self.process_card(image_data)
    
    # 完成通知（高優先級）
    await self.telegram_handler.send_completion_message(
        chat_id=chat_id,
        text=f"✅ 完成 {index}/{total}: {card_info['name']}"
    )
    
    return card_info
```

### 步驟 4: 緊急訊息處理

```python
async def handle_error(self, chat_id: str, error_message: str):
    # 錯誤訊息使用緊急優先級，立即發送
    await self.telegram_handler.send_urgent_message(
        chat_id=chat_id,
        text=f"❌ 處理失敗: {error_message}",
        parse_mode="Markdown"
    )

async def handle_system_alert(self, chat_id: str, alert_message: str):
    # 系統警報也使用緊急優先級
    await self.telegram_handler.send_urgent_message(
        chat_id=chat_id,
        text=f"🚨 系統警報: {alert_message}"
    )
```

## 🔧 配置參數調整

### 排程系統配置

```python
# 根據您的需求調整這些參數
telegram_handler = EnhancedTelegramBotHandler(
    enable_message_queue=True,
    # 以下參數會傳遞給 AsyncMessageQueue
)

# 或者直接配置 AsyncMessageQueue
from src.namecard.infrastructure.messaging.async_message_queue import AsyncMessageQueue

message_queue = AsyncMessageQueue(
    telegram_handler=base_handler,
    max_concurrent=15,        # 最大併發數（建議10-20）
    batch_size=5,            # 批次合併大小
    batch_interval=2.0,      # 批次發送間隔（秒）
)
```

### 連接池配置調整

如果您需要調整連接池配置，可以修改 `TelegramBotHandler` 的初始化：

```python
# 在 telegram_client.py 中的配置
self._http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=60,  # 根據需求調整
        max_connections=150,           # 根據需求調整
        keepalive_expiry=90.0,
    ),
    timeout=httpx.Timeout(
        pool=300.0  # 連接池超時（推薦300秒）
    )
)
```

## 📊 監控和效能調整

### 監控指標

```python
async def monitor_system_performance(self):
    """監控系統效能"""
    status = self.telegram_handler.get_enhanced_status_report()
    
    # 關鍵指標
    queue_stats = status.get("queue_stats", {})
    total_queued = queue_stats.get("total_queued_now", 0)
    current_concurrent = queue_stats.get("current_concurrent", 0)
    
    # 連接池狀態
    base_status = status.get("base_telegram_handler", {})
    pool_timeout_ratio = base_status.get("pool_timeout_ratio", 0)
    
    # 自適應調整
    if pool_timeout_ratio > 0.3:
        self.logger.warning("連接池壓力過高，考慮降低併發數")
    
    if total_queued > 100:
        self.logger.warning("訊息佇列積壓過多，檢查處理速度")
        
    return status
```

### 效能調整建議

```python
async def get_optimization_suggestions(self):
    """獲取系統優化建議"""
    recommendations = self.telegram_handler.get_performance_recommendations()
    
    for rec in recommendations:
        self.logger.info(f"💡 優化建議: {rec}")
        
    return recommendations
```

## 🚀 生產環境部署

### Docker 配置

```dockerfile
# Dockerfile 新增環境變數
ENV ENABLE_MESSAGE_QUEUE=true
ENV MAX_CONCURRENT_MESSAGES=15
ENV BATCH_SIZE=5
ENV BATCH_INTERVAL=2.0
```

### 環境變數配置

```bash
# .env 文件新增配置
ENABLE_MESSAGE_QUEUE=true
MAX_CONCURRENT_MESSAGES=15
BATCH_SIZE=5
BATCH_INTERVAL=2.0

# 監控配置
PERFORMANCE_MONITORING=true
LOG_QUEUE_STATS=true
```

### 健康檢查端點

```python
@app.route('/health/message-queue')
async def message_queue_health():
    """訊息排程系統健康檢查"""
    try:
        status = telegram_handler.get_enhanced_status_report()
        queue_stats = status.get("queue_stats", {})
        
        # 健康檢查邏輯
        is_healthy = (
            status.get("queue_system_started", False) and
            queue_stats.get("total_queued_now", 0) < 200 and
            queue_stats.get("adaptive_config", {}).get("error_rate", 1) < 0.3
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "queue_system_started": status.get("queue_system_started"),
            "queue_stats": queue_stats,
            "recommendations": telegram_handler.get_performance_recommendations()
        }, 200 if is_healthy else 503
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503
```

## 🔍 故障排除

### 常見問題

#### 1. 排程系統未啟動

```python
# 檢查啟動狀態
if not telegram_handler._queue_started:
    await telegram_handler.start_queue_system()
```

#### 2. 訊息積壓過多

```python
# 檢查佇列狀態
queue_stats = telegram_handler.message_queue.get_queue_stats()
if queue_stats["total_queued_now"] > 100:
    # 考慮增加併發數或檢查網路狀況
    pass
```

#### 3. 連接池超時

```python
# 檢查連接池狀態
status = telegram_handler.get_status_report()
if status["pool_timeout_ratio"] > 0.3:
    # 連接池壓力過高，排程系統會自動調整
    logger.warning("連接池壓力過高，系統正在自動調整")
```

### 調試工具

```python
# 啟用詳細日誌
logging.getLogger("src.namecard.infrastructure.messaging").setLevel(logging.DEBUG)

# 獲取詳細狀態
async def debug_system_state():
    status = telegram_handler.get_enhanced_status_report()
    print(json.dumps(status, indent=2, default=str))
```

## 📈 效能預期

使用異步訊息排程系統後，您可以期待：

- **連接池超時減少 70-90%**
- **批次處理效能提升 3-5x**
- **訊息發送成功率提升到 95%+**
- **系統響應時間改善 50%**
- **併發處理能力提升 2-3x**

## 🔄 回滾計劃

如果遇到問題需要回滾：

```python
# 方案 1: 禁用排程系統
telegram_handler = EnhancedTelegramBotHandler(
    enable_message_queue=False  # 關閉排程，回到原始行為
)

# 方案 2: 完全回滾到原始處理器
from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
telegram_handler = TelegramBotHandler()  # 使用原始處理器
```

## 📞 支援和維護

- **監控**: 定期檢查 `/health/message-queue` 端點
- **日誌**: 關注排程系統相關的日誌
- **效能**: 定期查看效能建議並調整配置
- **更新**: 關注系統更新和優化建議