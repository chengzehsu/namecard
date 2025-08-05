#!/usr/bin/env python3
"""
智能批次圖片收集器 - BatchImageCollector

實現智能的多張圖片批次收集和處理，減少訊息數量並提升用戶體驗。
核心功能：
- 5秒延遲批次檢測
- 用戶隔離狀態管理  
- 計時器自動觸發處理
- 記憶體安全和資源清理
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta


@dataclass
class PendingImage:
    """待處理圖片數據結構"""
    image_data: Any  # 圖片文件對象或字節數據
    file_id: str
    chat_id: int
    user_id: str
    received_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchStatus:
    """批次狀態數據結構"""
    user_id: str
    images: List[PendingImage] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    is_processing: bool = False
    chat_id: Optional[int] = None


class BatchImageCollector:
    """智能批次圖片收集器"""
    
    def __init__(
        self,
        batch_timeout: float = 5.0,  # 5秒批次等待時間
        max_batch_size: int = 20,    # 最大批次大小
        cleanup_interval: float = 300.0,  # 5分鐘清理間隔
        max_batch_age: float = 600.0  # 10分鐘最大批次生命週期
    ):
        """
        初始化批次收集器
        
        Args:
            batch_timeout: 批次等待超時時間（秒）
            max_batch_size: 最大批次大小
            cleanup_interval: 清理過期批次的間隔時間
            max_batch_age: 批次最大生命週期
        """
        self.batch_timeout = batch_timeout
        self.max_batch_size = max_batch_size
        self.cleanup_interval = cleanup_interval
        self.max_batch_age = max_batch_age
        
        # 狀態管理
        self.pending_batches: Dict[str, BatchStatus] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 回調函數
        self.batch_processor: Optional[Callable] = None
        self.progress_notifier: Optional[Callable] = None
        
        # 統計和監控
        self.stats = {
            "total_images_collected": 0,
            "total_batches_processed": 0,
            "total_single_images": 0,
            "total_multi_images": 0,
            "average_batch_size": 0.0,
            "cleanup_runs": 0
        }
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ BatchImageCollector 初始化完成")
        self.logger.info(f"   - 批次超時: {batch_timeout}秒")
        self.logger.info(f"   - 最大批次大小: {max_batch_size}")
    
    def set_batch_processor(self, processor: Callable):
        """設置批次處理器回調函數"""
        self.batch_processor = processor
        self.logger.debug("✅ 批次處理器已設置")
    
    def set_progress_notifier(self, notifier: Callable):
        """設置進度通知回調函數"""
        self.progress_notifier = notifier
        self.logger.debug("✅ 進度通知器已設置")
    
    async def start(self):
        """啟動批次收集器和清理任務"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
            self.logger.info("🚀 批次收集器已啟動")
    
    async def stop(self):
        """停止批次收集器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        # 處理所有待處理的批次
        for user_id in list(self.pending_batches.keys()):
            await self._process_batch_immediately(user_id)
        
        self.logger.info("🛑 批次收集器已停止")
    
    async def add_image(
        self, 
        user_id: str, 
        chat_id: int,
        image_data: Any, 
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加圖片到批次收集器
        
        Args:
            user_id: 用戶ID
            chat_id: 聊天ID
            image_data: 圖片數據
            file_id: 文件ID
            metadata: 額外元數據
            
        Returns:
            Dict 包含批次狀態信息
        """
        current_time = time.time()
        metadata = metadata or {}
        
        # 創建待處理圖片對象
        pending_image = PendingImage(
            image_data=image_data,
            file_id=file_id,
            chat_id=chat_id,
            user_id=user_id,
            received_at=current_time,
            metadata=metadata
        )
        
        # 獲取或創建批次狀態
        if user_id not in self.pending_batches:
            # 新批次
            batch_status = BatchStatus(
                user_id=user_id,
                chat_id=chat_id,
                created_at=current_time,
                last_updated=current_time
            )
            self.pending_batches[user_id] = batch_status
            
            self.logger.info(f"📸 用戶 {user_id} 創建新批次")
        else:
            # 現有批次
            batch_status = self.pending_batches[user_id]
            batch_status.last_updated = current_time
            
            # 取消現有計時器
            if batch_status.timer_task and not batch_status.timer_task.done():
                batch_status.timer_task.cancel()
                self.logger.debug(f"⏰ 用戶 {user_id} 重置批次計時器")
        
        # 添加圖片到批次
        batch_status.images.append(pending_image)
        image_count = len(batch_status.images)
        
        self.logger.info(f"📥 用戶 {user_id} 添加第 {image_count} 張圖片")
        
        # 更新統計
        self.stats["total_images_collected"] += 1
        
        # 檢查是否達到最大批次大小
        if image_count >= self.max_batch_size:
            self.logger.warning(f"⚠️ 用戶 {user_id} 達到最大批次大小 ({self.max_batch_size})，立即處理")
            await self._process_batch_immediately(user_id)
            return {
                "action": "immediate_processing",
                "image_count": image_count,
                "reason": "max_batch_size_reached"
            }
        
        # 設置新的計時器
        batch_status.timer_task = asyncio.create_task(
            self._batch_timer(user_id, self.batch_timeout)
        )
        
        # 通知進度更新
        if self.progress_notifier:
            try:
                await self.progress_notifier(
                    user_id=user_id,
                    chat_id=chat_id,
                    image_count=image_count,
                    action="image_added"
                )
            except Exception as e:
                self.logger.error(f"❌ 進度通知失敗: {e}")
        
        return {
            "action": "added_to_batch",
            "image_count": image_count,
            "timeout_seconds": self.batch_timeout,
            "batch_created_at": batch_status.created_at
        }
    
    async def _batch_timer(self, user_id: str, timeout: float):
        """批次計時器，超時後觸發處理"""
        try:
            self.logger.debug(f"⏰ 用戶 {user_id} 批次計時器啟動 ({timeout}秒)")
            await asyncio.sleep(timeout)
            
            # 計時器到期，處理批次
            self.logger.info(f"⏱️ 用戶 {user_id} 批次計時器到期，開始處理")
            await self._process_batch_immediately(user_id)
            
        except asyncio.CancelledError:
            self.logger.debug(f"⏰ 用戶 {user_id} 批次計時器被取消")
            raise
        except Exception as e:
            self.logger.error(f"❌ 用戶 {user_id} 批次計時器錯誤: {e}")
    
    async def _process_batch_immediately(self, user_id: str):
        """立即處理指定用戶的批次"""
        if user_id not in self.pending_batches:
            self.logger.warning(f"⚠️ 用戶 {user_id} 無待處理批次")
            return
        
        batch_status = self.pending_batches[user_id]
        
        # 檢查是否已在處理中
        if batch_status.is_processing:
            self.logger.warning(f"⚠️ 用戶 {user_id} 批次已在處理中，跳過")
            return
        
        # 取消計時器
        if batch_status.timer_task and not batch_status.timer_task.done():
            batch_status.timer_task.cancel()
        
        # 標記為處理中
        batch_status.is_processing = True
        image_count = len(batch_status.images)
        
        self.logger.info(f"🚀 開始處理用戶 {user_id} 的批次 ({image_count} 張圖片)")
        
        try:
            # 調用批次處理器
            if self.batch_processor:
                await self.batch_processor(user_id, batch_status.images)
            else:
                self.logger.warning("⚠️ 未設置批次處理器，跳過處理")
            
            # 更新統計
            self.stats["total_batches_processed"] += 1
            if image_count == 1:
                self.stats["total_single_images"] += 1
            else:
                self.stats["total_multi_images"] += 1
            
            # 更新平均批次大小
            total_images = self.stats["total_single_images"] + self.stats["total_multi_images"]
            if total_images > 0:
                self.stats["average_batch_size"] = self.stats["total_images_collected"] / self.stats["total_batches_processed"]
            
            self.logger.info(f"✅ 用戶 {user_id} 批次處理完成")
            
        except Exception as e:
            self.logger.error(f"❌ 用戶 {user_id} 批次處理失敗: {e}")
            import traceback
            self.logger.error(f"批次處理錯誤堆疊: {traceback.format_exc()}")
        
        finally:
            # 清理批次狀態
            if user_id in self.pending_batches:
                del self.pending_batches[user_id]
                self.logger.debug(f"🗑️ 用戶 {user_id} 批次狀態已清理")
    
    async def force_process_user_batch(self, user_id: str) -> bool:
        """強制處理指定用戶的批次"""
        if user_id not in self.pending_batches:
            return False
        
        self.logger.info(f"🔧 強制處理用戶 {user_id} 的批次")
        await self._process_batch_immediately(user_id)
        return True
    
    def get_batch_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """獲取指定用戶的批次狀態"""
        if user_id not in self.pending_batches:
            return None
        
        batch_status = self.pending_batches[user_id]
        current_time = time.time()
        
        return {
            "user_id": user_id,
            "image_count": len(batch_status.images),
            "is_processing": batch_status.is_processing,
            "created_at": batch_status.created_at,
            "last_updated": batch_status.last_updated,
            "age_seconds": current_time - batch_status.created_at,
            "time_since_last_update": current_time - batch_status.last_updated,
            "has_timer": batch_status.timer_task is not None and not batch_status.timer_task.done()
        }
    
    def get_all_batch_statuses(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有用戶的批次狀態"""
        return {
            user_id: self.get_batch_status(user_id)
            for user_id in self.pending_batches.keys()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取收集器統計信息"""
        current_time = time.time()
        return {
            **self.stats,
            "active_batches": len(self.pending_batches),
            "uptime_seconds": current_time,
            "pending_users": list(self.pending_batches.keys()),
            "memory_usage": {
                "pending_batches_count": len(self.pending_batches),
                "total_pending_images": sum(len(batch.images) for batch in self.pending_batches.values())
            }
        }
    
    async def _cleanup_worker(self):
        """定期清理過期批次的後台任務"""
        self.logger.info(f"🧹 批次清理工作者啟動，間隔: {self.cleanup_interval}秒")
        
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                expired_users = []
                
                # 檢查過期批次
                for user_id, batch_status in self.pending_batches.items():
                    age = current_time - batch_status.created_at
                    if age > self.max_batch_age:
                        expired_users.append(user_id)
                        self.logger.warning(f"⏰ 用戶 {user_id} 批次過期 ({age:.1f}秒)")
                
                # 處理過期批次
                for user_id in expired_users:
                    self.logger.info(f"🧹 清理用戶 {user_id} 的過期批次")
                    await self._process_batch_immediately(user_id)
                
                if expired_users:
                    self.stats["cleanup_runs"] += 1
                    self.logger.info(f"🧹 批次清理完成，處理了 {len(expired_users)} 個過期批次")
                
            except asyncio.CancelledError:
                self.logger.info("🛑 批次清理工作者停止")
                break
            except Exception as e:
                self.logger.error(f"❌ 批次清理工作者錯誤: {e}")
                # 繼續運行，不要因為清理錯誤而停止
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.stop()


# 全局批次收集器實例（單例模式）
_global_batch_collector: Optional[BatchImageCollector] = None


def get_batch_collector() -> BatchImageCollector:
    """獲取全局批次收集器實例"""
    global _global_batch_collector
    if _global_batch_collector is None:
        _global_batch_collector = BatchImageCollector()
    return _global_batch_collector


async def initialize_batch_collector(
    batch_processor: Optional[Callable] = None,
    progress_notifier: Optional[Callable] = None
) -> BatchImageCollector:
    """初始化並啟動全局批次收集器"""
    collector = get_batch_collector()
    
    if batch_processor:
        collector.set_batch_processor(batch_processor)
    
    if progress_notifier:
        collector.set_progress_notifier(progress_notifier)
    
    await collector.start()
    return collector