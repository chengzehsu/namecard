"""
增強型 Telegram Bot 處理器 - EnhancedTelegramBotHandler

整合異步訊息佇列系統，提供智能排程和批次優化
完全向後兼容現有的 TelegramBotHandler API

Features:
- 無縫整合 AsyncMessageQueue
- 智能路由 (直接發送 vs 排程發送)
- 批次上下文管理器
- 高階 API (緊急、完成、批次訊息)
- 完全向後兼容
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager

# 導入基礎處理器和佇列系統
from .telegram_client import TelegramBotHandler
from .async_message_queue import AsyncMessageQueue, MessagePriority, BatchContext


class EnhancedTelegramBotHandler(TelegramBotHandler):
    """增強型 Telegram Bot 處理器
    
    在原有 TelegramBotHandler 基礎上整合異步訊息佇列系統
    提供智能排程、批次優化和完全向後兼容的 API
    """
    
    def __init__(
        self, 
        enable_message_queue: bool = True,
        queue_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化增強型處理器
        
        Args:
            enable_message_queue: 是否啟用訊息佇列系統
            queue_config: 佇列系統配置參數
        """
        # 初始化基礎處理器
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.enable_message_queue = enable_message_queue
        
        # 佇列系統配置
        default_queue_config = {
            "max_queue_size": 10000,
            "initial_concurrent_workers": 8,
            "batch_size": 5,
            "batch_timeout": 2.0,
            "enable_smart_merging": True
        }
        
        if queue_config:
            default_queue_config.update(queue_config)
        
        # 初始化佇列系統（如果啟用）
        self.message_queue: Optional[AsyncMessageQueue] = None
        if self.enable_message_queue:
            self.message_queue = AsyncMessageQueue(**default_queue_config)
            # 設置訊息發送器
            self.message_queue.set_message_sender(self._internal_send_message)
        
        # 批次上下文追蹤
        self._active_batch_contexts = {}
        self._batch_context_counter = 0
        
        # 統計追蹤
        self.enhanced_stats = {
            "total_direct_sends": 0,
            "total_queued_sends": 0,
            "total_emergency_sends": 0,
            "total_batch_contexts": 0,
            "queue_bypasses": 0
        }
        
        self.logger.info(f"✅ EnhancedTelegramBotHandler 初始化完成")
        self.logger.info(f"   - 佇列系統: {'啟用' if self.enable_message_queue else '停用'}")
        if self.message_queue:
            self.logger.info(f"   - 佇列配置: {default_queue_config}")
    
    async def start_queue_system(self):
        """啟動佇列系統"""
        if self.message_queue and not self.message_queue.is_running:
            await self.message_queue.start()
            self.logger.info("🚀 異步訊息佇列系統已啟動")
    
    async def stop_queue_system(self):
        """停止佇列系統"""
        if self.message_queue and self.message_queue.is_running:
            await self.message_queue.stop()
            self.logger.info("🛑 異步訊息佇列系統已停止")
    
    async def _internal_send_message(
        self, 
        chat_id: Union[int, str], 
        text: str, 
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """內部訊息發送器（供佇列系統使用）"""
        return await super().safe_send_message(chat_id, text, parse_mode)
    
    async def safe_send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        max_retries: int = 3,
        priority: MessagePriority = MessagePriority.NORMAL,
        context: Optional[str] = None,
        message_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增強版安全發送訊息
        
        智能路由：根據佇列狀態和訊息特性決定直接發送或排程發送
        完全向後兼容原有 API
        """
        # 決定發送策略
        should_use_queue = self._should_use_queue(priority, text, context)
        
        if should_use_queue and self.message_queue:
            # 使用佇列排程發送
            try:
                message_id = await self.message_queue.enqueue_message(
                    chat_id=chat_id,
                    text=text,
                    priority=priority,
                    parse_mode=parse_mode,
                    context=context,
                    message_type=message_type,
                    max_retries=max_retries
                )
                
                self.enhanced_stats["total_queued_sends"] += 1
                
                return {
                    "success": True,
                    "message": "訊息已加入佇列",
                    "message_id": message_id,
                    "queued": True
                }
                
            except Exception as e:
                self.logger.warning(f"⚠️ 佇列發送失敗，降級到直接發送: {e}")
                self.enhanced_stats["queue_bypasses"] += 1
                # 降級到直接發送
        
        # 直接發送（原有邏輯）
        self.enhanced_stats["total_direct_sends"] += 1
        result = await super().safe_send_message(chat_id, text, parse_mode, max_retries)
        result["queued"] = False
        return result
    
    def _should_use_queue(
        self, 
        priority: MessagePriority, 
        text: str, 
        context: Optional[str]
    ) -> bool:
        """智能決策：是否使用佇列系統"""
        if not self.enable_message_queue or not self.message_queue:
            return False
        
        # 緊急訊息直接發送
        if priority == MessagePriority.EMERGENCY:
            return False
        
        # 佇列系統未運行
        if not self.message_queue.is_running:
            return False
        
        # 錯誤訊息直接發送（保證即時性）
        if any(keyword in text.lower() for keyword in ["錯誤", "失敗", "error", "failed", "❌"]):
            return False
        
        # 批次上下文中的訊息使用佇列
        if context and context in self._active_batch_contexts:
            return True
        
        # 批次優先級訊息使用佇列
        if priority == MessagePriority.BATCH:
            return True
        
        # 長訊息使用佇列（避免阻塞）
        if len(text) > 500:
            return True
        
        # 普通和低優先級訊息在高負載時使用佇列
        if priority in [MessagePriority.NORMAL, MessagePriority.LOW]:
            queue_stats = self.message_queue._get_queue_stats()
            # 如果當前佇列負載不高，直接發送更快
            total_queued = sum(queue_stats["queue_sizes"].values())
            if total_queued < 10:
                return False
            else:
                return True
        
        # 預設不使用佇列
        return False
    
    # === 高階 API 方法 ===
    
    async def send_emergency_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """發送緊急訊息（立即發送，繞過佇列）"""
        self.enhanced_stats["total_emergency_sends"] += 1
        
        return await self.safe_send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            priority=MessagePriority.EMERGENCY
        )
    
    async def send_completion_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """發送完成訊息（高優先級，快速處理）"""
        return await self.safe_send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            priority=MessagePriority.HIGH,
            context=context,
            message_type="completion"
        )
    
    async def send_batch_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        context: Optional[str] = None,
        message_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """發送批次訊息（智能合併）"""
        return await self.safe_send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            priority=MessagePriority.BATCH,
            context=context,
            message_type=message_type
        )
    
    async def send_card_processing_complete(
        self,
        chat_id: Union[int, str],
        card_info: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """發送名片處理完成訊息（專用格式）"""
        # 格式化名片完成訊息
        text = f"✅ 名片處理完成\n👤 {card_info.get('name', 'N/A')} ({card_info.get('company', 'N/A')})"
        
        return await self.send_batch_message(
            chat_id=chat_id,
            text=text,
            context=context,
            message_type="card_processing_complete"
        )
    
    async def send_progress_update(
        self,
        chat_id: Union[int, str],
        current: int,
        total: int,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """發送進度更新訊息（會被智能合併）"""
        text = f"📊 進度: {current}/{total} 完成"
        
        return await self.send_batch_message(
            chat_id=chat_id,
            text=text,
            context=context,
            message_type="batch_progress"
        )
    
    # === 批次上下文管理 ===
    
    @asynccontextmanager
    async def batch_context(self, context_name: str):
        """批次處理上下文管理器
        
        使用方式:
        async with handler.batch_context("card_processing") as batch:
            await batch.send_message(chat_id, "處理完成 1")
            await batch.send_message(chat_id, "處理完成 2")
        # 自動合併並發送
        """
        if not self.message_queue:
            # 如果沒有佇列系統，提供簡化的上下文
            yield SimpleBatchContext(self, context_name)
            return
        
        self._batch_context_counter += 1
        context_id = f"{context_name}_{self._batch_context_counter}"
        
        # 創建批次上下文
        batch_context = BatchContext(self.message_queue, context_id)
        self._active_batch_contexts[context_id] = batch_context
        self.enhanced_stats["total_batch_contexts"] += 1
        
        try:
            async with batch_context as ctx:
                yield EnhancedBatchContext(ctx, self, context_id)
        finally:
            # 清理上下文
            if context_id in self._active_batch_contexts:
                del self._active_batch_contexts[context_id]
    
    # === 監控和統計 ===
    
    def get_enhanced_status_report(self) -> Dict[str, Any]:
        """獲取增強版狀態報告"""
        base_report = super().get_status_report()
        
        enhanced_report = {
            "base_handler": base_report,
            "queue_enabled": self.enable_message_queue,
            "enhanced_statistics": self.enhanced_stats.copy(),
            "active_batch_contexts": len(self._active_batch_contexts)
        }
        
        # 添加佇列統計
        if self.message_queue:
            enhanced_report["message_queue"] = self.message_queue.get_health_status()
        
        # 計算總體統計
        total_sends = (
            self.enhanced_stats["total_direct_sends"] + 
            self.enhanced_stats["total_queued_sends"]
        )
        
        if total_sends > 0:
            enhanced_report["queue_usage_ratio"] = (
                self.enhanced_stats["total_queued_sends"] / total_sends
            )
            enhanced_report["emergency_ratio"] = (
                self.enhanced_stats["total_emergency_sends"] / total_sends
            )
        
        return enhanced_report
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """獲取效能指標"""
        metrics = {
            "handler_type": "enhanced",
            "queue_enabled": self.enable_message_queue,
            "total_processed": (
                self.enhanced_stats["total_direct_sends"] + 
                self.enhanced_stats["total_queued_sends"]
            )
        }
        
        if self.message_queue:
            queue_stats = self.message_queue._get_queue_stats()
            metrics.update({
                "queue_efficiency": {
                    "total_merged": queue_stats["total_merged"],
                    "current_workers": queue_stats["current_workers"],
                    "error_rate": queue_stats["error_rate"],
                    "queue_sizes": queue_stats["queue_sizes"]
                }
            })
        
        return metrics
    
    # === 資源管理 ===
    
    async def close(self):
        """清理資源"""
        try:
            # 停止佇列系統
            if self.message_queue:
                await self.stop_queue_system()
            
            # 清理批次上下文
            self._active_batch_contexts.clear()
            
            # 調用基礎類別的清理
            await super().close()
            
            self.logger.info("✅ EnhancedTelegramBotHandler 資源已清理")
            
        except Exception as e:
            self.logger.warning(f"⚠️ 清理增強處理器時發生錯誤: {e}")
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self.start_queue_system()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.close()


class EnhancedBatchContext:
    """增強批次上下文包裝器"""
    
    def __init__(
        self, 
        batch_context: BatchContext, 
        handler: EnhancedTelegramBotHandler,
        context_id: str
    ):
        self.batch_context = batch_context
        self.handler = handler
        self.context_id = context_id
        self.message_count = 0
    
    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        message_type: Optional[str] = None,
        parse_mode: Optional[str] = None
    ) -> str:
        """在批次上下文中發送訊息"""
        self.message_count += 1
        
        if self.batch_context:
            # 使用佇列系統的批次上下文
            return await self.batch_context.send_message(
                chat_id=chat_id,
                text=text,
                message_type=message_type,
                parse_mode=parse_mode
            )
        else:
            # 直接發送（降級模式）
            result = await self.handler.send_batch_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                context=self.context_id,
                message_type=message_type
            )
            return result.get("message_id", "")
    
    async def send_card_complete(
        self,
        chat_id: Union[int, str],
        card_info: Dict[str, Any]
    ) -> str:
        """發送名片完成訊息"""
        return await self.send_message(
            chat_id=chat_id,
            text=f"✅ 名片處理完成\n👤 {card_info.get('name', 'N/A')} ({card_info.get('company', 'N/A')})",
            message_type="card_processing_complete"
        )
    
    async def send_progress(
        self,
        chat_id: Union[int, str],
        current: int,
        total: int
    ) -> str:
        """發送進度更新"""
        return await self.send_message(
            chat_id=chat_id,
            text=f"📊 進度: {current}/{total} 完成",
            message_type="batch_progress"
        )


class SimpleBatchContext:
    """簡化批次上下文（當佇列系統停用時使用）"""
    
    def __init__(self, handler: EnhancedTelegramBotHandler, context_name: str):
        self.handler = handler
        self.context_name = context_name
        self.message_count = 0
    
    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        message_type: Optional[str] = None,
        parse_mode: Optional[str] = None
    ) -> str:
        """簡化批次發送（直接發送）"""
        self.message_count += 1
        result = await self.handler.safe_send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            context=self.context_name
        )
        return result.get("message_id", "")
    
    async def send_card_complete(
        self,
        chat_id: Union[int, str],
        card_info: Dict[str, Any]
    ) -> str:
        """發送名片完成訊息"""
        text = f"✅ 名片處理完成\n👤 {card_info.get('name', 'N/A')} ({card_info.get('company', 'N/A')})"
        return await self.send_message(chat_id, text)
    
    async def send_progress(
        self,
        chat_id: Union[int, str],
        current: int,
        total: int
    ) -> str:
        """發送進度更新"""
        text = f"📊 進度: {current}/{total} 完成"
        return await self.send_message(chat_id, text)


# === 便利工廠函數 ===

def create_enhanced_telegram_handler(
    enable_queue: bool = True,
    queue_workers: int = 8,
    batch_size: int = 5,
    **kwargs
) -> EnhancedTelegramBotHandler:
    """創建增強型 Telegram Bot 處理器的便利函數"""
    queue_config = {
        "initial_concurrent_workers": queue_workers,
        "batch_size": batch_size,
        **kwargs
    }
    
    return EnhancedTelegramBotHandler(
        enable_message_queue=enable_queue,
        queue_config=queue_config
    )


# === 健康檢查端點 ===

async def get_message_queue_health() -> Dict[str, Any]:
    """獲取訊息佇列健康狀態（用於 Flask 端點）"""
    # 這個函數可以在 Flask 應用中使用
    # 實際使用時需要傳入 handler 實例
    return {
        "status": "healthy",
        "message": "請通過 handler.get_enhanced_status_report() 獲取詳細狀態",
        "timestamp": time.time()
    }