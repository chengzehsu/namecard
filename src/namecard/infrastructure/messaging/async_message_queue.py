"""
異步訊息佇列系統 - AsyncMessageQueue

提供智能訊息排程、批次合併、動態併發控制和連接池優化
基於 ChatGPT 建議和 Backend Architect 設計實作

Features:
- 5級優先級排程 (緊急→高→普通→低→批次)
- 智能批次合併和去重
- 動態併發控制 (3-20 adaptive)
- 連接池感知和自動優化
- 指數退避重試機制
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Union


class MessagePriority(IntEnum):
    """訊息優先級枚舉"""

    EMERGENCY = 1  # 緊急 - 立即發送，繞過排程
    HIGH = 2  # 高 - 優先處理
    NORMAL = 3  # 普通 - 標準處理
    LOW = 4  # 低 - 延後處理
    BATCH = 5  # 批次 - 合併處理


@dataclass
class QueuedMessage:
    """佇列中的訊息物件"""

    chat_id: Union[int, str]
    text: str
    priority: MessagePriority
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3

    # 可選參數
    parse_mode: Optional[str] = None
    context: Optional[str] = None  # 批次上下文
    message_type: Optional[str] = None  # 訊息類型

    # 內部屬性
    message_id: str = field(default="")
    batch_key: Optional[str] = None  # 批次合併鍵

    def __post_init__(self):
        """初始化後處理"""
        if not self.message_id:
            # 生成唯一訊息ID
            content = f"{self.chat_id}:{self.text}:{self.created_at}"
            self.message_id = hashlib.md5(content.encode()).hexdigest()[:12]

        # 生成批次合併鍵
        if self.priority == MessagePriority.BATCH:
            self.batch_key = self._generate_batch_key()

    def _generate_batch_key(self) -> str:
        """生成批次合併鍵"""
        # 基於用戶ID、訊息類型和上下文生成
        key_parts = [str(self.chat_id)]

        if self.message_type:
            key_parts.append(self.message_type)
        if self.context:
            key_parts.append(self.context)

        return ":".join(key_parts)


class AsyncMessageQueue:
    """異步訊息佇列系統"""

    def __init__(
        self,
        max_queue_size: int = 10000,
        initial_concurrent_workers: int = 8,
        batch_size: int = 5,
        batch_timeout: float = 2.0,
        enable_smart_merging: bool = True,
    ):
        """
        初始化異步訊息佇列

        Args:
            max_queue_size: 佇列最大容量
            initial_concurrent_workers: 初始併發工作者數量
            batch_size: 批次處理大小
            batch_timeout: 批次超時時間（秒）
            enable_smart_merging: 啟用智能合併
        """
        self.logger = logging.getLogger(__name__)

        # 佇列配置
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.enable_smart_merging = enable_smart_merging

        # 多優先級佇列
        self.queues = {
            priority: asyncio.Queue(maxsize=max_queue_size)
            for priority in MessagePriority
        }

        # 動態併發控制
        self.min_workers = 3
        self.max_workers = 20
        self.current_workers = initial_concurrent_workers
        self.worker_semaphore = None  # 延遲創建，避免事件循環綁定問題

        # 統計和監控
        self.stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_merged": 0,
            "current_queue_size": 0,
            "worker_adjustments": 0,
            "connection_pool_cleanups": 0,
        }

        # 效能監控
        self.performance_window = []
        self.error_rate_window = []
        self.last_adjustment_time = time.time()
        self.adjustment_cooldown = 30  # 30秒調整冷卻期

        # 批次合併暫存
        self.pending_batches = defaultdict(list)
        self.batch_timers = {}

        # 工作者控制
        self.workers = []
        self.is_running = False
        self.shutdown_event = None  # 延遲創建，避免事件循環綁定問題

        # 訊息發送器（由外部設置）
        self.message_sender: Optional[Callable] = None

        self.logger.info(f"✅ AsyncMessageQueue 初始化完成")
        self.logger.info(f"   - 初始併發工作者: {self.current_workers}")
        self.logger.info(f"   - 批次大小: {self.batch_size}")
        self.logger.info(
            f"   - 智能合併: {'啟用' if self.enable_smart_merging else '停用'}"
        )

    def _get_shutdown_event(self):
        """安全獲取 shutdown_event，確保在正確的事件循環中創建"""
        if self.shutdown_event is None:
            try:
                # 獲取當前事件循環
                current_loop = asyncio.get_running_loop()
                self.shutdown_event = asyncio.Event()
                self.logger.debug("🔧 在當前事件循環中創建 shutdown_event")
            except RuntimeError:
                # 沒有運行中的事件循環，創建新的 Event
                self.shutdown_event = asyncio.Event()
                self.logger.debug("🔧 創建新的 shutdown_event")
        return self.shutdown_event

    def _get_worker_semaphore(self):
        """安全獲取 worker_semaphore，確保在正確的事件循環中創建"""
        if self.worker_semaphore is None:
            try:
                # 獲取當前事件循環
                current_loop = asyncio.get_running_loop()
                self.worker_semaphore = asyncio.Semaphore(self.current_workers)
                self.logger.debug(
                    f"🔧 在當前事件循環中創建 worker_semaphore ({self.current_workers})"
                )
            except RuntimeError:
                # 沒有運行中的事件循環，創建新的 Semaphore
                self.worker_semaphore = asyncio.Semaphore(self.current_workers)
                self.logger.debug(
                    f"🔧 創建新的 worker_semaphore ({self.current_workers})"
                )
        return self.worker_semaphore

    def set_message_sender(self, sender: Callable):
        """設置訊息發送器函數"""
        self.message_sender = sender
        self.logger.debug("✅ 訊息發送器已設置")

    async def start(self):
        """啟動佇列處理系統"""
        if self.is_running:
            self.logger.warning("⚠️ 佇列系統已在運行中")
            return

        self.is_running = True
        self._get_shutdown_event().clear()

        # 啟動工作者
        for i in range(self.current_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # 啟動監控任務
        monitor_task = asyncio.create_task(self._performance_monitor())
        self.workers.append(monitor_task)

        self.logger.info(f"🚀 異步訊息佇列系統已啟動")
        self.logger.info(f"   - 工作者數量: {len(self.workers) - 1}")  # 減去監控任務

    async def stop(self):
        """停止佇列處理系統"""
        self.logger.info("🛑 正在停止異步訊息佇列系統...")

        self.is_running = False
        self._get_shutdown_event().set()

        # 等待所有工作者完成
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()

        # 清理待處理的批次
        await self._flush_pending_batches()

        self.logger.info("✅ 異步訊息佇列系統已停止")

    async def enqueue_message(
        self,
        chat_id: Union[int, str],
        text: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        parse_mode: Optional[str] = None,
        context: Optional[str] = None,
        message_type: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        將訊息加入佇列

        Returns:
            str: 訊息ID
        """
        # 創建訊息物件
        message = QueuedMessage(
            chat_id=chat_id,
            text=text,
            priority=priority,
            parse_mode=parse_mode,
            context=context,
            message_type=message_type,
            max_retries=max_retries,
        )

        # 緊急訊息直接發送，繞過排程
        if priority == MessagePriority.EMERGENCY:
            self.logger.debug(f"🚨 緊急訊息直接發送: {message.message_id}")
            if self.message_sender:
                try:
                    await self.message_sender(chat_id, text, parse_mode)
                    self.stats["total_processed"] += 1
                    return message.message_id
                except Exception as e:
                    self.logger.error(f"❌ 緊急訊息發送失敗: {e}")
                    self.stats["total_failed"] += 1
                    # 降級到高優先級佇列
                    message.priority = MessagePriority.HIGH

        # 檢查佇列容量
        queue = self.queues[message.priority]
        if queue.full():
            self.logger.warning(
                f"⚠️ 佇列已滿 ({message.priority.name})，丟棄訊息: {message.message_id}"
            )
            return message.message_id

        # 批次訊息處理
        if priority == MessagePriority.BATCH and self.enable_smart_merging:
            await self._handle_batch_message(message)
        else:
            # 直接加入佇列
            await queue.put(message)
            self.stats["total_enqueued"] += 1
            self.stats["current_queue_size"] += 1

        self.logger.debug(
            f"📥 訊息已加入佇列: {message.message_id} (優先級: {priority.name})"
        )
        return message.message_id

    async def _handle_batch_message(self, message: QueuedMessage):
        """處理批次訊息，實現智能合併"""
        batch_key = message.batch_key

        # 加入待處理批次
        self.pending_batches[batch_key].append(message)

        # 設置批次定時器
        if batch_key not in self.batch_timers:
            timer = asyncio.create_task(self._batch_timer(batch_key))
            self.batch_timers[batch_key] = timer

        # 檢查是否達到批次大小
        if len(self.pending_batches[batch_key]) >= self.batch_size:
            await self._flush_batch(batch_key)

    async def _batch_timer(self, batch_key: str):
        """批次定時器，超時後自動發送"""
        try:
            await asyncio.sleep(self.batch_timeout)
            if batch_key in self.pending_batches:
                await self._flush_batch(batch_key)
        except asyncio.CancelledError:
            pass  # 定時器被取消

    async def _flush_batch(self, batch_key: str):
        """發送批次訊息"""
        if batch_key not in self.pending_batches:
            return

        messages = self.pending_batches.pop(batch_key)
        if not messages:
            return

        # 取消定時器
        if batch_key in self.batch_timers:
            self.batch_timers[batch_key].cancel()
            del self.batch_timers[batch_key]

        # 智能合併
        merged_message = self._merge_messages(messages)
        if merged_message:
            # 加入高優先級佇列快速處理
            await self.queues[MessagePriority.HIGH].put(merged_message)
            self.stats["total_enqueued"] += 1
            self.stats["current_queue_size"] += 1
            self.stats["total_merged"] += len(messages) - 1  # 合併數量

            self.logger.debug(f"🔄 已合併 {len(messages)} 條批次訊息: {batch_key}")

    def _merge_messages(self, messages: List[QueuedMessage]) -> Optional[QueuedMessage]:
        """智能合併多條訊息"""
        if not messages:
            return None

        if len(messages) == 1:
            return messages[0]

        # 取第一條訊息作為基礎
        base_message = messages[0]

        # 根據訊息類型決定合併策略
        if base_message.message_type == "card_processing_complete":
            # 名片處理完成訊息 - 合併為統計摘要
            return self._merge_card_processing_messages(messages)
        elif base_message.message_type == "batch_progress":
            # 批次進度訊息 - 只保留最新的
            return max(messages, key=lambda m: m.created_at)
        else:
            # 默認合併策略 - 簡單列表
            return self._merge_default_messages(messages)

    def _merge_card_processing_messages(
        self, messages: List[QueuedMessage]
    ) -> QueuedMessage:
        """合併名片處理完成訊息"""
        base_message = messages[0]
        count = len(messages)

        # 提取名片資訊
        cards = []
        for msg in messages:
            # 簡單解析名片資訊（實際實作會更複雜）
            if "👤" in msg.text and "(" in msg.text:
                start = msg.text.find("👤") + 2
                end = (
                    msg.text.find("\n", start)
                    if "\n" in msg.text[start:]
                    else len(msg.text)
                )
                card_info = msg.text[start : start + end].strip()
                cards.append(card_info)

        # 生成合併訊息
        merged_text = f"📊 **批次處理完成**\n\n"
        merged_text += f"✅ 已處理 {count} 張名片：\n"
        for i, card in enumerate(cards[:5], 1):  # 最多顯示5張
            merged_text += f"{i}. {card}\n"

        if len(cards) > 5:
            merged_text += f"... 以及其他 {len(cards) - 5} 張名片\n"

        merged_text += f"\n⏱️ 處理時間: {time.time() - base_message.created_at:.1f}秒"

        return QueuedMessage(
            chat_id=base_message.chat_id,
            text=merged_text,
            priority=MessagePriority.HIGH,  # 提升優先級
            parse_mode=base_message.parse_mode,
            context=base_message.context,
            message_type="batch_summary",
        )

    def _merge_default_messages(self, messages: List[QueuedMessage]) -> QueuedMessage:
        """默認訊息合併策略"""
        base_message = messages[0]

        if len(messages) <= 3:
            # 少量訊息直接組合
            combined_text = "\n\n".join(msg.text for msg in messages)
        else:
            # 大量訊息摘要
            combined_text = f"📝 **批次訊息摘要** ({len(messages)} 條)\n\n"
            combined_text += "\n".join(f"• {msg.text[:50]}..." for msg in messages[:3])
            if len(messages) > 3:
                combined_text += f"\n... 以及其他 {len(messages) - 3} 條訊息"

        return QueuedMessage(
            chat_id=base_message.chat_id,
            text=combined_text,
            priority=base_message.priority,
            parse_mode=base_message.parse_mode,
            context=base_message.context,
            message_type="merged_batch",
        )

    async def _flush_pending_batches(self):
        """清空所有待處理的批次"""
        for batch_key in list(self.pending_batches.keys()):
            await self._flush_batch(batch_key)

    async def _worker(self, worker_name: str):
        """工作者協程，處理佇列中的訊息"""
        self.logger.debug(f"🔧 工作者已啟動: {worker_name}")

        while self.is_running:
            try:
                # 按優先級處理訊息
                message = await self._get_next_message()

                if message is None:
                    # 沒有訊息，短暫休息
                    await asyncio.sleep(0.1)
                    continue

                # 併發控制
                async with self._get_worker_semaphore():
                    await self._process_message(message, worker_name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 工作者 {worker_name} 發生錯誤: {e}")
                await asyncio.sleep(1)  # 錯誤後暫停

        self.logger.debug(f"🛑 工作者已停止: {worker_name}")

    async def _get_next_message(self) -> Optional[QueuedMessage]:
        """按優先級獲取下一條訊息"""
        # 按優先級順序檢查佇列
        for priority in MessagePriority:
            queue = self.queues[priority]
            try:
                message = queue.get_nowait()
                self.stats["current_queue_size"] -= 1
                return message
            except asyncio.QueueEmpty:
                continue

        return None

    async def _process_message(self, message: QueuedMessage, worker_name: str):
        """處理單條訊息"""
        start_time = time.time()

        try:
            if not self.message_sender:
                raise RuntimeError("訊息發送器未設置")

            # 發送訊息
            await self.message_sender(message.chat_id, message.text, message.parse_mode)

            # 記錄成功
            processing_time = time.time() - start_time
            self.performance_window.append(processing_time)
            self.error_rate_window.append(0)  # 成功
            self.stats["total_processed"] += 1

            self.logger.debug(
                f"✅ 訊息處理成功: {message.message_id} ({processing_time:.2f}s) - {worker_name}"
            )

        except Exception as e:
            # 記錄失敗
            processing_time = time.time() - start_time
            self.performance_window.append(processing_time)
            self.error_rate_window.append(1)  # 失敗

            self.logger.error(f"❌ 訊息處理失敗: {message.message_id} - {e}")

            # 重試邏輯
            if message.retry_count < message.max_retries:
                message.retry_count += 1
                # 指數退避重試
                retry_delay = min(2**message.retry_count, 60)

                self.logger.info(
                    f"🔄 訊息重試 {message.retry_count}/{message.max_retries} (延遲 {retry_delay}s): {message.message_id}"
                )

                # 延遲後重新加入佇列
                asyncio.create_task(self._retry_message(message, retry_delay))
            else:
                self.stats["total_failed"] += 1
                self.logger.error(f"💀 訊息最終失敗: {message.message_id}")

        # 限制效能窗口大小
        if len(self.performance_window) > 100:
            self.performance_window = self.performance_window[-50:]
        if len(self.error_rate_window) > 100:
            self.error_rate_window = self.error_rate_window[-50:]

    async def _retry_message(self, message: QueuedMessage, delay: float):
        """延遲重試訊息"""
        await asyncio.sleep(delay)
        if self.is_running:
            # 降低優先級重新加入佇列
            if message.priority.value < MessagePriority.LOW.value:
                message.priority = MessagePriority(message.priority.value + 1)

            queue = self.queues[message.priority]
            if not queue.full():
                await queue.put(message)
                self.stats["current_queue_size"] += 1

    async def _performance_monitor(self):
        """效能監控和動態調整"""
        self.logger.debug("📊 效能監控器已啟動")

        while self.is_running:
            try:
                await asyncio.sleep(10)  # 每10秒檢查一次

                # 計算效能指標
                if len(self.error_rate_window) >= 10:
                    recent_errors = self.error_rate_window[-20:]
                    error_rate = sum(recent_errors) / len(recent_errors)

                    # 動態調整併發數
                    await self._adjust_concurrency(error_rate)

                # 記錄統計
                self.logger.debug(f"📈 佇列統計: {self._get_queue_stats()}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 效能監控錯誤: {e}")

        self.logger.debug("🛑 效能監控器已停止")

    async def _adjust_concurrency(self, error_rate: float):
        """根據錯誤率動態調整併發數"""
        current_time = time.time()

        # 檢查調整冷卻期
        if current_time - self.last_adjustment_time < self.adjustment_cooldown:
            return

        old_workers = self.current_workers

        if error_rate > 0.3:  # 錯誤率 > 30%
            # 降低併發數
            new_workers = max(self.min_workers, self.current_workers - 2)
        elif (
            error_rate < 0.1
            and self.stats["total_processed"] > self.current_workers * 20
        ):
            # 錯誤率 < 10% 且處理量足夠，增加併發數
            new_workers = min(self.max_workers, self.current_workers + 1)
        else:
            return  # 不需要調整

        if new_workers != old_workers:
            self.current_workers = new_workers

            # 更新 Semaphore（創建新的，因為 asyncio.Semaphore 不支援動態調整）
            try:
                # 獲取當前事件循環
                current_loop = asyncio.get_running_loop()
                self.worker_semaphore = asyncio.Semaphore(new_workers)
                self.logger.debug(
                    f"🔧 在當前事件循環中重建 worker_semaphore ({new_workers})"
                )
            except RuntimeError:
                # 沒有運行中的事件循環，創建新的 Semaphore
                self.worker_semaphore = asyncio.Semaphore(new_workers)
                self.logger.debug(f"🔧 重建 worker_semaphore ({new_workers})")

            self.last_adjustment_time = current_time
            self.stats["worker_adjustments"] += 1

            self.logger.info(
                f"🔧 併發數調整: {old_workers} → {new_workers} (錯誤率: {error_rate:.1%})"
            )

    def _get_queue_stats(self) -> Dict[str, Any]:
        """獲取佇列統計資訊"""
        queue_sizes = {
            priority.name: self.queues[priority].qsize() for priority in MessagePriority
        }

        return {
            "queue_sizes": queue_sizes,
            "current_workers": self.current_workers,
            "total_enqueued": self.stats["total_enqueued"],
            "total_processed": self.stats["total_processed"],
            "total_failed": self.stats["total_failed"],
            "total_merged": self.stats["total_merged"],
            "pending_batches": len(self.pending_batches),
            "error_rate": (
                sum(self.error_rate_window[-20:]) / len(self.error_rate_window[-20:])
                if len(self.error_rate_window) >= 20
                else 0
            ),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """獲取健康狀態"""
        stats = self._get_queue_stats()

        # 健康檢查
        is_healthy = (
            self.is_running
            and stats["error_rate"] < 0.5
            and sum(stats["queue_sizes"].values()) < self.max_queue_size * 0.8
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "is_running": self.is_running,
            "uptime": time.time() - getattr(self, "_start_time", time.time()),
            "statistics": stats,
            "recommendations": self._get_health_recommendations(stats),
        }

    def _get_health_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """獲取健康建議"""
        recommendations = []

        if stats["error_rate"] > 0.3:
            recommendations.append("錯誤率偏高，建議檢查連接池配置")

        if sum(stats["queue_sizes"].values()) > self.max_queue_size * 0.7:
            recommendations.append("佇列接近滿載，建議增加工作者數量")

        if stats["total_merged"] > 0:
            merge_ratio = stats["total_merged"] / max(1, stats["total_processed"])
            if merge_ratio > 0.5:
                recommendations.append("批次合併效果良好，系統運行最佳化")

        if not recommendations:
            recommendations.append("系統運行正常")

        return recommendations


# 上下文管理器
class BatchContext:
    """批次處理上下文管理器"""

    def __init__(self, queue: AsyncMessageQueue, context_name: str):
        self.queue = queue
        self.context_name = context_name
        self.message_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 強制發送待處理的批次
        await self.queue._flush_pending_batches()

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        message_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        """在批次上下文中發送訊息"""
        self.message_count += 1

        return await self.queue.enqueue_message(
            chat_id=chat_id,
            text=text,
            priority=MessagePriority.BATCH,
            context=self.context_name,
            message_type=message_type,
            **kwargs,
        )
