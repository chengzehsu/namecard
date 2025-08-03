"""
異步批次處理服務 - 支援高並發多用戶批次處理
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import weakref

from src.namecard.infrastructure.ai.async_card_processor import AsyncCardProcessor, ProcessingPriority


class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """批次處理項目"""
    item_id: str
    image_bytes: bytes
    user_id: str
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: BatchStatus = BatchStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    processing_duration: float = 0.0


@dataclass
class BatchSession:
    """批次處理會話"""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    items: List[BatchItem] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    auto_process: bool = False
    max_concurrent: int = 3
    timeout_minutes: int = 10


class AsyncBatchService:
    """異步批次處理服務，支援多用戶並發批次處理"""
    
    def __init__(self, card_processor: AsyncCardProcessor, max_global_concurrent: int = 50):
        """
        初始化異步批次服務
        
        Args:
            card_processor: 異步名片處理器
            max_global_concurrent: 全局最大並發數
        """
        self.card_processor = card_processor
        self.max_global_concurrent = max_global_concurrent
        
        # 會話管理
        self.active_sessions: Dict[str, BatchSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        
        # 並發控制
        self.global_semaphore = asyncio.Semaphore(max_global_concurrent)
        self.processing_tasks: weakref.WeakSet = weakref.WeakSet()
        
        # 統計資訊
        self.stats = {
            "total_sessions": 0,
            "total_items_processed": 0,
            "total_processing_time": 0.0,
            "active_sessions_count": 0,
            "peak_concurrent_sessions": 0
        }
        
        # 清理任務
        self.cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """啟動清理任務"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """定期清理過期會話"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分鐘清理一次
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"清理任務錯誤: {e}")
    
    async def _cleanup_expired_sessions(self):
        """清理過期會話"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if (now - session.last_activity).total_seconds() > session.timeout_minutes * 60:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._remove_session(session_id)
            print(f"清理過期會話: {session_id}")
    
    async def create_batch_session(
        self, 
        user_id: str,
        auto_process: bool = False,
        max_concurrent: int = 3,
        timeout_minutes: int = 10
    ) -> str:
        """
        創建批次處理會話
        
        Args:
            user_id: 用戶ID
            auto_process: 是否自動處理
            max_concurrent: 會話內最大並發數
            timeout_minutes: 會話超時時間（分鐘）
            
        Returns:
            會話ID
        """
        session_id = f"batch_{user_id}_{int(time.time() * 1000)}"
        
        session = BatchSession(
            session_id=session_id,
            user_id=user_id,
            auto_process=auto_process,
            max_concurrent=max_concurrent,
            timeout_minutes=timeout_minutes
        )
        
        self.active_sessions[session_id] = session
        
        # 更新用戶會話映射
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        # 更新統計
        self.stats["total_sessions"] += 1
        self.stats["active_sessions_count"] = len(self.active_sessions)
        if self.stats["active_sessions_count"] > self.stats["peak_concurrent_sessions"]:
            self.stats["peak_concurrent_sessions"] = self.stats["active_sessions_count"]
        
        print(f"創建批次會話: {session_id} (用戶: {user_id})")
        return session_id
    
    async def add_item_to_batch(
        self,
        session_id: str,
        item_id: str,
        image_bytes: bytes,
        priority: ProcessingPriority = ProcessingPriority.NORMAL
    ) -> bool:
        """
        添加項目到批次
        
        Args:
            session_id: 會話ID
            item_id: 項目ID
            image_bytes: 圖片數據
            priority: 處理優先級
            
        Returns:
            是否添加成功
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        # 更新最後活動時間
        session.last_activity = datetime.now()
        
        # 創建批次項目
        item = BatchItem(
            item_id=item_id,
            image_bytes=image_bytes,
            user_id=session.user_id,
            priority=priority
        )
        
        session.items.append(item)
        
        # 如果啟用自動處理，立即開始處理
        if session.auto_process:
            asyncio.create_task(self._process_batch_item(session_id, item))
        
        print(f"添加項目到批次 {session_id}: {item_id}")
        return True
    
    async def process_batch(
        self,
        session_id: str,
        process_all: bool = True,
        max_concurrent: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        處理批次
        
        Args:
            session_id: 會話ID
            process_all: 是否處理所有項目
            max_concurrent: 並發數限制
            
        Returns:
            處理結果摘要
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "會話不存在"}
        
        # 更新最後活動時間
        session.last_activity = datetime.now()
        session.status = BatchStatus.PROCESSING
        
        # 確定並發數
        concurrent_limit = max_concurrent or session.max_concurrent
        
        # 獲取待處理項目
        pending_items = [
            item for item in session.items 
            if item.status == BatchStatus.PENDING
        ]
        
        if not pending_items:
            return {"message": "沒有待處理的項目", "processed": 0}
        
        print(f"開始處理批次 {session_id}: {len(pending_items)} 個項目")
        
        # 創建處理任務
        semaphore = asyncio.Semaphore(concurrent_limit)
        tasks = [
            self._process_batch_item_with_semaphore(session_id, item, semaphore)
            for item in pending_items
        ]
        
        # 並發執行所有任務
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processing_time = time.time() - start_time
        
        # 統計結果
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        # 更新會話狀態
        session.status = BatchStatus.COMPLETED if failed == 0 else BatchStatus.FAILED
        
        # 更新統計
        self.stats["total_items_processed"] += successful
        self.stats["total_processing_time"] += processing_time
        
        result_summary = {
            "session_id": session_id,
            "total_items": len(pending_items),
            "successful": successful,
            "failed": failed,
            "processing_time": processing_time,
            "items_per_second": len(pending_items) / processing_time if processing_time > 0 else 0
        }
        
        print(f"批次處理完成 {session_id}: {successful}/{len(pending_items)} 成功")
        return result_summary
    
    async def _process_batch_item_with_semaphore(
        self,
        session_id: str,
        item: BatchItem,
        semaphore: asyncio.Semaphore
    ):
        """帶信號量的批次項目處理"""
        async with semaphore:
            return await self._process_batch_item(session_id, item)
    
    async def _process_batch_item(self, session_id: str, item: BatchItem):
        """處理單個批次項目"""
        async with self.global_semaphore:
            try:
                item.status = BatchStatus.PROCESSING
                item.started_at = datetime.now()
                
                # 處理圖片
                result, metadata = await self.card_processor.process_image_async(
                    image_bytes=item.image_bytes,
                    priority=item.priority,
                    user_id=item.user_id,
                    timeout=30.0
                )
                
                # 記錄結果
                item.result = result
                item.status = BatchStatus.COMPLETED
                item.completed_at = datetime.now()
                item.processing_duration = metadata.processing_duration
                
                if "error" in result:
                    item.error = result["error"]
                    item.status = BatchStatus.FAILED
                
            except Exception as e:
                item.error = str(e)
                item.status = BatchStatus.FAILED
                item.completed_at = datetime.now()
                item.retry_count += 1
                
                print(f"批次項目處理失敗 {item.item_id}: {e}")
    
    async def get_batch_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取批次狀態"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        # 統計項目狀態
        status_counts = {}
        for status in BatchStatus:
            status_counts[status.value] = sum(
                1 for item in session.items if item.status == status
            )
        
        # 計算處理進度
        total_items = len(session.items)
        completed_items = status_counts.get("completed", 0) + status_counts.get("failed", 0)
        progress = (completed_items / total_items) if total_items > 0 else 0.0
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "status": session.status.value,
            "total_items": total_items,
            "progress": progress,
            "status_breakdown": status_counts,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
    
    async def get_batch_results(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """獲取批次處理結果"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        results = []
        for item in session.items:
            result_item = {
                "item_id": item.item_id,
                "status": item.status.value,
                "processing_duration": item.processing_duration,
                "retry_count": item.retry_count
            }
            
            if item.result:
                result_item["result"] = item.result
            if item.error:
                result_item["error"] = item.error
            if item.completed_at:
                result_item["completed_at"] = item.completed_at.isoformat()
            
            results.append(result_item)
        
        return results
    
    async def cancel_batch(self, session_id: str) -> bool:
        """取消批次處理"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        session.status = BatchStatus.CANCELLED
        
        # 取消所有待處理項目
        for item in session.items:
            if item.status == BatchStatus.PENDING:
                item.status = BatchStatus.CANCELLED
        
        print(f"取消批次處理: {session_id}")
        return True
    
    async def remove_batch_session(self, session_id: str) -> bool:
        """移除批次會話"""
        return await self._remove_session(session_id)
    
    async def _remove_session(self, session_id: str) -> bool:
        """內部移除會話方法"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        # 從用戶會話映射中移除
        user_id = session.user_id
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        # 移除會話
        del self.active_sessions[session_id]
        
        # 更新統計
        self.stats["active_sessions_count"] = len(self.active_sessions)
        
        return True
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """獲取用戶的所有會話"""
        return list(self.user_sessions.get(user_id, set()))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """獲取服務統計"""
        # 計算平均處理時間
        avg_processing_time = (
            self.stats["total_processing_time"] / self.stats["total_items_processed"]
            if self.stats["total_items_processed"] > 0 else 0.0
        )
        
        return {
            **self.stats,
            "avg_processing_time_per_item": avg_processing_time,
            "current_active_tasks": len(self.processing_tasks),
            "global_semaphore_available": self.global_semaphore._value
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            # 檢查處理器健康狀態
            processor_health = await self.card_processor.health_check()
            
            # 檢查服務負載
            active_sessions = len(self.active_sessions)
            load_percentage = (active_sessions / 100) * 100  # 假設最大 100 個會話
            
            status = "healthy"
            if processor_health["status"] != "healthy":
                status = processor_health["status"]
            elif load_percentage > 80:
                status = "warning"
            
            return {
                "status": status,
                "active_sessions": active_sessions,
                "load_percentage": load_percentage,
                "processor_health": processor_health,
                "cleanup_task_running": not (self.cleanup_task and self.cleanup_task.done())
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def shutdown(self):
        """優雅關閉服務"""
        # 取消清理任務
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
        
        # 等待所有處理任務完成
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        print("異步批次服務已關閉")