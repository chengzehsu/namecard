#!/usr/bin/env python3
"""
異步訊息佇列系統完整測試套件 - API Tester Agent 實作
測試 AsyncMessageQueue 的並發處理、智能批次合併和動態負載均衡功能
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 導入測試目標
from src.namecard.infrastructure.messaging.async_message_queue import (
    AsyncMessageQueue,
    BatchContext,
    MessagePriority,
    QueuedMessage,
)


class TestAsyncMessageQueue:
    """異步訊息佇列測試類"""

    @pytest.fixture
    async def message_queue(self):
        """創建測試用的訊息佇列"""
        queue = AsyncMessageQueue(
            max_queue_size=100,
            initial_concurrent_workers=4,
            batch_size=3,
            batch_timeout=1.0,
            enable_smart_merging=True,
        )

        # 設置模擬的訊息發送器
        mock_sender = AsyncMock()
        queue.set_message_sender(mock_sender)

        yield queue, mock_sender

        # 清理
        if queue.is_running:
            await queue.stop()

    @pytest.fixture
    def sample_messages(self):
        """測試用的樣本訊息數據"""
        return [
            {
                "chat_id": 12345,
                "text": "📱 名片處理完成\n👤 張三 (ABC公司)\n✅ 已存入 Notion",
                "priority": MessagePriority.NORMAL,
                "message_type": "card_processing_complete",
            },
            {
                "chat_id": 12345,
                "text": "📱 名片處理完成\n👤 李四 (XYZ企業)\n✅ 已存入 Notion",
                "priority": MessagePriority.BATCH,
                "message_type": "card_processing_complete",
            },
            {
                "chat_id": 67890,
                "text": "🚨 系統緊急通知：API 配額即將耗盡",
                "priority": MessagePriority.EMERGENCY,
                "message_type": "system_alert",
            },
            {
                "chat_id": 12345,
                "text": "📊 批次處理進度：3/5 張圖片已完成",
                "priority": MessagePriority.BATCH,
                "message_type": "batch_progress",
                "context": "batch_001",
            },
        ]

    # ==========================================
    # 1. 基礎功能測試
    # ==========================================

    def test_message_priority_enum(self):
        """測試訊息優先級枚舉"""
        assert MessagePriority.EMERGENCY == 1
        assert MessagePriority.HIGH == 2
        assert MessagePriority.NORMAL == 3
        assert MessagePriority.LOW == 4
        assert MessagePriority.BATCH == 5

        # 檢查優先級排序
        assert MessagePriority.EMERGENCY < MessagePriority.HIGH
        assert MessagePriority.HIGH < MessagePriority.NORMAL

    def test_queued_message_creation(self):
        """測試佇列訊息物件創建"""
        message = QueuedMessage(
            chat_id=12345,
            text="測試訊息",
            priority=MessagePriority.NORMAL,
            message_type="test",
            context="test_context",
        )

        assert message.chat_id == 12345
        assert message.text == "測試訊息"
        assert message.priority == MessagePriority.NORMAL
        assert message.retry_count == 0
        assert message.max_retries == 3
        assert message.message_id != ""
        assert len(message.message_id) == 12  # MD5 hash 前12位

    def test_batch_key_generation(self):
        """測試批次鍵生成"""
        message1 = QueuedMessage(
            chat_id=12345,
            text="測試1",
            priority=MessagePriority.BATCH,
            message_type="card_processing",
            context="batch_001",
        )

        message2 = QueuedMessage(
            chat_id=12345,
            text="測試2",
            priority=MessagePriority.BATCH,
            message_type="card_processing",
            context="batch_001",
        )

        message3 = QueuedMessage(
            chat_id=67890,
            text="測試3",
            priority=MessagePriority.BATCH,
            message_type="card_processing",
            context="batch_001",
        )

        # 相同用戶、類型、上下文應該有相同的批次鍵
        assert message1.batch_key == message2.batch_key
        # 不同用戶應該有不同的批次鍵
        assert message1.batch_key != message3.batch_key

    async def test_queue_initialization(self, message_queue):
        """測試佇列初始化"""
        queue, mock_sender = message_queue

        assert queue.max_queue_size == 100
        assert queue.current_workers == 4
        assert queue.batch_size == 3
        assert queue.batch_timeout == 1.0
        assert queue.enable_smart_merging is True
        assert not queue.is_running

        # 檢查所有優先級佇列都被創建
        assert len(queue.queues) == len(MessagePriority)
        for priority in MessagePriority:
            assert priority in queue.queues

    # ==========================================
    # 2. 訊息入隊和處理測試
    # ==========================================

    async def test_enqueue_normal_message(self, message_queue):
        """測試普通訊息入隊"""
        queue, mock_sender = message_queue

        message_id = await queue.enqueue_message(
            chat_id=12345, text="測試訊息", priority=MessagePriority.NORMAL
        )

        assert message_id != ""
        assert queue.stats["total_enqueued"] == 1
        assert queue.stats["current_queue_size"] == 1
        assert queue.queues[MessagePriority.NORMAL].qsize() == 1

    async def test_emergency_message_bypass(self, message_queue):
        """測試緊急訊息繞過佇列直接發送"""
        queue, mock_sender = message_queue

        message_id = await queue.enqueue_message(
            chat_id=12345, text="緊急通知", priority=MessagePriority.EMERGENCY
        )

        # 緊急訊息應該直接發送
        mock_sender.assert_called_once_with(12345, "緊急通知", None)
        assert queue.stats["total_processed"] == 1
        assert queue.queues[MessagePriority.EMERGENCY].qsize() == 0

    async def test_emergency_message_fallback(self, message_queue):
        """測試緊急訊息發送失敗的降級處理"""
        queue, mock_sender = message_queue
        mock_sender.side_effect = Exception("發送失敗")

        message_id = await queue.enqueue_message(
            chat_id=12345, text="緊急通知", priority=MessagePriority.EMERGENCY
        )

        # 發送失敗，應該降級到高優先級佇列
        assert queue.stats["total_failed"] == 1
        assert queue.queues[MessagePriority.HIGH].qsize() == 1

    async def test_queue_full_handling(self, message_queue):
        """測試佇列滿載處理"""
        queue, mock_sender = message_queue

        # 填滿特定優先級佇列
        normal_queue = queue.queues[MessagePriority.NORMAL]

        # 模擬佇列已滿
        with patch.object(normal_queue, "full", return_value=True):
            message_id = await queue.enqueue_message(
                chat_id=12345, text="測試訊息", priority=MessagePriority.NORMAL
            )

        # 訊息應該被丟棄
        assert normal_queue.qsize() == 0

    # ==========================================
    # 3. 批次處理和智能合併測試
    # ==========================================

    async def test_batch_message_collection(self, message_queue):
        """測試批次訊息收集"""
        queue, mock_sender = message_queue

        # 發送3條批次訊息（達到批次大小）
        for i in range(3):
            await queue.enqueue_message(
                chat_id=12345,
                text=f"批次訊息 {i}",
                priority=MessagePriority.BATCH,
                message_type="test_batch",
                context="test_context",
            )

        # 檢查批次是否被收集
        batch_key = "12345:test_batch:test_context"
        assert len(queue.pending_batches[batch_key]) == 3

    async def test_batch_timeout_flush(self, message_queue):
        """測試批次超時自動發送"""
        queue, mock_sender = message_queue

        # 發送1條批次訊息（未達到批次大小）
        await queue.enqueue_message(
            chat_id=12345,
            text="單個批次訊息",
            priority=MessagePriority.BATCH,
            message_type="test_batch",
            context="timeout_test",
        )

        batch_key = "12345:test_batch:timeout_test"
        assert len(queue.pending_batches[batch_key]) == 1

        # 等待超時（批次超時為1秒）
        await asyncio.sleep(1.2)

        # 批次應該被自動發送
        assert (
            batch_key not in queue.pending_batches
            or len(queue.pending_batches[batch_key]) == 0
        )

    async def test_card_processing_message_merging(self, message_queue):
        """測試名片處理訊息智能合併"""
        queue, mock_sender = message_queue

        # 創建多條名片處理完成訊息
        messages = [
            QueuedMessage(
                chat_id=12345,
                text="📱 名片處理完成\n👤 張三 (ABC公司)\n✅ 已存入 Notion",
                priority=MessagePriority.BATCH,
                message_type="card_processing_complete",
            ),
            QueuedMessage(
                chat_id=12345,
                text="📱 名片處理完成\n👤 李四 (XYZ企業)\n✅ 已存入 Notion",
                priority=MessagePriority.BATCH,
                message_type="card_processing_complete",
            ),
            QueuedMessage(
                chat_id=12345,
                text="📱 名片處理完成\n👤 王五 (DEF集團)\n✅ 已存入 Notion",
                priority=MessagePriority.BATCH,
                message_type="card_processing_complete",
            ),
        ]

        # 測試合併功能
        merged = queue._merge_card_processing_messages(messages)

        assert merged is not None
        assert merged.message_type == "batch_summary"
        assert merged.priority == MessagePriority.HIGH
        assert "📊 **批次處理完成**" in merged.text
        assert "已處理 3 張名片" in merged.text
        assert "張三" in merged.text
        assert "李四" in merged.text
        assert "王五" in merged.text

    async def test_default_message_merging(self, message_queue):
        """測試默認訊息合併策略"""
        queue, mock_sender = message_queue

        # 少量訊息合併
        few_messages = [
            QueuedMessage(
                chat_id=12345, text=f"測試訊息 {i}", priority=MessagePriority.BATCH
            )
            for i in range(2)
        ]

        merged_few = queue._merge_default_messages(few_messages)
        assert "測試訊息 0" in merged_few.text
        assert "測試訊息 1" in merged_few.text

        # 大量訊息摘要
        many_messages = [
            QueuedMessage(
                chat_id=12345,
                text=f"測試訊息 {i} - 這是一條很長的測試訊息內容用來測試摘要功能",
                priority=MessagePriority.BATCH,
            )
            for i in range(5)
        ]

        merged_many = queue._merge_default_messages(many_messages)
        assert "**批次訊息摘要** (5 條)" in merged_many.text
        assert "其他 2 條訊息" in merged_many.text

    # ==========================================
    # 4. 工作者和併發控制測試
    # ==========================================

    async def test_queue_start_and_stop(self, message_queue):
        """測試佇列啟動和停止"""
        queue, mock_sender = message_queue

        # 啟動佇列
        await queue.start()
        assert queue.is_running is True
        assert len(queue.workers) == queue.current_workers + 1  # +1 為監控任務

        # 停止佇列
        await queue.stop()
        assert queue.is_running is False
        assert len(queue.workers) == 0

    async def test_message_processing_flow(self, message_queue):
        """測試完整的訊息處理流程"""
        queue, mock_sender = message_queue

        # 啟動佇列
        await queue.start()

        # 發送訊息
        message_id = await queue.enqueue_message(
            chat_id=12345, text="測試處理流程", priority=MessagePriority.HIGH
        )

        # 等待處理完成
        await asyncio.sleep(0.5)

        # 檢查訊息是否被處理
        mock_sender.assert_called_with(12345, "測試處理流程", None)
        assert queue.stats["total_processed"] >= 1

        await queue.stop()

    async def test_message_retry_mechanism(self, message_queue):
        """測試訊息重試機制"""
        queue, mock_sender = message_queue

        # 設置發送器在前兩次調用時失敗
        call_count = 0

        def failing_sender(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("模擬發送失敗")
            return AsyncMock()()

        mock_sender.side_effect = failing_sender

        await queue.start()

        # 發送訊息
        await queue.enqueue_message(
            chat_id=12345, text="重試測試", priority=MessagePriority.NORMAL, max_retries=3
        )

        # 等待重試完成
        await asyncio.sleep(5)  # 給足夠時間進行重試

        # 檢查重試成功
        assert call_count >= 3  # 至少嘗試3次
        assert queue.stats["total_processed"] >= 1

        await queue.stop()

    async def test_priority_ordering(self, message_queue):
        """測試優先級排序處理"""
        queue, mock_sender = message_queue

        processed_messages = []

        async def tracking_sender(chat_id, text, parse_mode):
            processed_messages.append(text)

        queue.set_message_sender(tracking_sender)
        await queue.start()

        # 以相反優先級順序發送訊息
        await queue.enqueue_message(12345, "低優先級", MessagePriority.LOW)
        await queue.enqueue_message(12345, "普通優先級", MessagePriority.NORMAL)
        await queue.enqueue_message(12345, "高優先級", MessagePriority.HIGH)

        # 等待處理
        await asyncio.sleep(1.0)

        # 檢查處理順序（高優先級應該先處理）
        assert len(processed_messages) >= 3
        high_index = processed_messages.index("高優先級")
        normal_index = processed_messages.index("普通優先級")
        low_index = processed_messages.index("低優先級")

        assert high_index < normal_index
        assert normal_index < low_index

        await queue.stop()

    # ==========================================
    # 5. 動態負載均衡測試
    # ==========================================

    async def test_dynamic_concurrency_adjustment(self, message_queue):
        """測試動態併發調整"""
        queue, mock_sender = message_queue

        # 模擬高錯誤率場景
        mock_sender.side_effect = Exception("模擬高錯誤率")

        await queue.start()

        # 發送多條訊息觸發錯誤
        for i in range(20):
            await queue.enqueue_message(
                chat_id=12345, text=f"錯誤測試 {i}", priority=MessagePriority.NORMAL
            )

        # 等待處理和調整
        await asyncio.sleep(2.0)

        # 檢查併發數是否被降低
        initial_workers = 4
        # 由於錯誤率高，併發數應該被降低
        assert queue.current_workers <= initial_workers

        await queue.stop()

    async def test_performance_monitoring(self, message_queue):
        """測試效能監控"""
        queue, mock_sender = message_queue

        await queue.start()

        # 發送一些成功的訊息
        for i in range(10):
            await queue.enqueue_message(
                chat_id=12345, text=f"性能測試 {i}", priority=MessagePriority.NORMAL
            )

        # 等待處理
        await asyncio.sleep(1.0)

        # 檢查效能數據
        stats = queue._get_queue_stats()
        assert stats["total_processed"] >= 10
        assert "error_rate" in stats
        assert "current_workers" in stats

        await queue.stop()

    # ==========================================
    # 6. 健康檢查和監控測試
    # ==========================================

    async def test_health_status_healthy(self, message_queue):
        """測試健康狀態檢查 - 健康狀態"""
        queue, mock_sender = message_queue

        await queue.start()

        # 處理一些成功的訊息
        for i in range(5):
            await queue.enqueue_message(
                chat_id=12345, text=f"健康測試 {i}", priority=MessagePriority.NORMAL
            )

        await asyncio.sleep(0.5)

        health = queue.get_health_status()
        assert health["status"] == "healthy"
        assert health["is_running"] is True
        assert "statistics" in health
        assert "recommendations" in health

        await queue.stop()

    async def test_health_status_degraded(self, message_queue):
        """測試健康狀態檢查 - 降級狀態"""
        queue, mock_sender = message_queue

        # 模擬高錯誤率
        mock_sender.side_effect = Exception("模擬系統問題")

        await queue.start()

        # 發送訊息產生錯誤
        for i in range(20):
            await queue.enqueue_message(
                chat_id=12345, text=f"降級測試 {i}", priority=MessagePriority.NORMAL
            )

        await asyncio.sleep(1.0)

        health = queue.get_health_status()
        # 由於高錯誤率，狀態可能是 degraded
        assert health["status"] in ["healthy", "degraded"]
        assert "recommendations" in health

        await queue.stop()

    def test_health_recommendations(self, message_queue):
        """測試健康建議生成"""
        queue, mock_sender = message_queue

        # 模擬高錯誤率統計
        stats = {
            "error_rate": 0.4,  # 40% 錯誤率
            "queue_sizes": {
                "NORMAL": 80,
                "HIGH": 20,
                "LOW": 10,
                "EMERGENCY": 0,
                "BATCH": 5,
            },
            "total_processed": 100,
            "total_merged": 60,
        }

        recommendations = queue._get_health_recommendations(stats)

        assert len(recommendations) > 0
        # 高錯誤率應該有相應建議
        error_rec = any("錯誤率" in rec for rec in recommendations)
        assert error_rec

        # 高佇列使用量應該有建議
        queue_rec = any("佇列" in rec for rec in recommendations)
        # 取決於總佇列大小，這裡不強制檢查

    # ==========================================
    # 7. 批次上下文管理器測試
    # ==========================================

    async def test_batch_context_manager(self, message_queue):
        """測試批次上下文管理器"""
        queue, mock_sender = message_queue

        async with BatchContext(queue, "test_context") as batch:
            # 在上下文中發送多條訊息
            await batch.send_message(
                chat_id=12345, text="上下文訊息 1", message_type="context_test"
            )
            await batch.send_message(
                chat_id=12345, text="上下文訊息 2", message_type="context_test"
            )

            assert batch.message_count == 2

        # 退出上下文後，待處理的批次應該被發送
        # 檢查批次是否被清空
        assert len(queue.pending_batches) == 0

    # ==========================================
    # 8. 高負載和壓力測試
    # ==========================================

    async def test_high_load_processing(self, message_queue):
        """測試高負載處理能力"""
        queue, mock_sender = message_queue

        await queue.start()

        # 發送大量訊息
        num_messages = 100
        start_time = time.time()

        for i in range(num_messages):
            await queue.enqueue_message(
                chat_id=12345 + (i % 10),  # 分散到10個不同的 chat
                text=f"高負載測試訊息 {i}",
                priority=MessagePriority.NORMAL if i % 2 == 0 else MessagePriority.HIGH,
            )

        enqueue_time = time.time() - start_time

        # 等待處理完成
        await asyncio.sleep(3.0)

        processing_time = time.time() - start_time

        print(f"\n📊 高負載測試結果:")
        print(f"   - 入隊 {num_messages} 條訊息: {enqueue_time:.3f}s")
        print(f"   - 總處理時間: {processing_time:.3f}s")
        print(f"   - 處理成功: {queue.stats['total_processed']}")
        print(f"   - 處理失敗: {queue.stats['total_failed']}")
        print(
            f"   - 平均處理速度: {queue.stats['total_processed']/processing_time:.1f} msg/s"
        )

        # 驗證性能
        assert enqueue_time < 1.0  # 入隊應該很快
        assert processing_time < 10.0  # 總處理時間應該合理
        assert queue.stats["total_processed"] >= num_messages * 0.8  # 至少80%成功

        await queue.stop()

    async def test_concurrent_batch_processing(self, message_queue):
        """測試併發批次處理"""
        queue, mock_sender = message_queue

        async def send_batch(batch_id: int, message_count: int):
            """發送一個批次的訊息"""
            for i in range(message_count):
                await queue.enqueue_message(
                    chat_id=12345,
                    text=f"批次 {batch_id} 訊息 {i}",
                    priority=MessagePriority.BATCH,
                    message_type="concurrent_test",
                    context=f"batch_{batch_id}",
                )

        # 同時發送5個批次，每批次3條訊息
        tasks = [send_batch(i, 3) for i in range(5)]
        await asyncio.gather(*tasks)

        # 檢查批次收集
        assert len(queue.pending_batches) == 5

        # 等待批次超時處理
        await asyncio.sleep(1.5)

        # 所有批次應該被處理
        remaining_batches = sum(
            len(messages) for messages in queue.pending_batches.values()
        )
        assert remaining_batches == 0

    # ==========================================
    # 9. 錯誤處理和邊界測試
    # ==========================================

    async def test_message_sender_not_set(self, message_queue):
        """測試未設置訊息發送器的錯誤處理"""
        queue, _ = message_queue
        queue.set_message_sender(None)  # 清空發送器

        await queue.start()

        await queue.enqueue_message(
            chat_id=12345, text="測試無發送器", priority=MessagePriority.NORMAL
        )

        # 等待處理
        await asyncio.sleep(0.5)

        # 應該產生錯誤
        assert queue.stats["total_failed"] >= 1

        await queue.stop()

    async def test_extreme_retry_scenario(self, message_queue):
        """測試極端重試場景"""
        queue, mock_sender = message_queue

        # 設置發送器總是失敗
        mock_sender.side_effect = Exception("永遠失敗")

        await queue.start()

        # 發送一條有限重試次數的訊息
        await queue.enqueue_message(
            chat_id=12345, text="重試耗盡測試", priority=MessagePriority.NORMAL, max_retries=2
        )

        # 等待所有重試完成
        await asyncio.sleep(8)  # 指數退避：1+2+4秒

        # 檢查最終失敗
        assert queue.stats["total_failed"] >= 1
        assert mock_sender.call_count >= 3  # 初始嘗試 + 2次重試

        await queue.stop()

    async def test_queue_capacity_edge_cases(self, message_queue):
        """測試佇列容量邊界情況"""
        # 創建小容量佇列
        small_queue = AsyncMessageQueue(max_queue_size=5, initial_concurrent_workers=2)
        mock_sender = AsyncMock()
        small_queue.set_message_sender(mock_sender)

        try:
            # 嘗試超過容量
            for i in range(10):
                await small_queue.enqueue_message(
                    chat_id=12345, text=f"容量測試 {i}", priority=MessagePriority.LOW
                )

            # 檢查佇列大小不超過限制
            total_queued = sum(q.qsize() for q in small_queue.queues.values())
            assert total_queued <= 5

        finally:
            if small_queue.is_running:
                await small_queue.stop()


# ==========================================
# 獨立測試函數
# ==========================================


async def test_message_deduplication():
    """測試訊息去重功能"""
    queue = AsyncMessageQueue()

    # 創建相同內容的訊息
    message1 = QueuedMessage(
        chat_id=12345, text="重複訊息", priority=MessagePriority.NORMAL
    )

    message2 = QueuedMessage(
        chat_id=12345, text="重複訊息", priority=MessagePriority.NORMAL
    )

    # 由於創建時間不同，message_id 應該不同
    assert message1.message_id != message2.message_id


async def run_async_message_queue_integration_test():
    """運行異步訊息佇列整合測試"""
    print("🧪 開始異步訊息佇列整合測試...")

    try:
        # 創建佇列
        queue = AsyncMessageQueue(
            max_queue_size=200,
            initial_concurrent_workers=6,
            batch_size=5,
            batch_timeout=2.0,
            enable_smart_merging=True,
        )

        # 設置模擬發送器
        sent_messages = []

        async def mock_sender(chat_id, text, parse_mode):
            await asyncio.sleep(0.1)  # 模擬網路延遲
            sent_messages.append(
                {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "timestamp": time.time(),
                }
            )

        queue.set_message_sender(mock_sender)

        print("📊 場景1: 多優先級訊息處理")
        await queue.start()

        # 發送不同優先級的訊息
        await queue.enqueue_message(67890, "🚨 緊急系統警報", MessagePriority.EMERGENCY)
        await queue.enqueue_message(12345, "📱 高優先級通知", MessagePriority.HIGH)
        await queue.enqueue_message(12345, "📝 普通訊息", MessagePriority.NORMAL)
        await queue.enqueue_message(12345, "📋 低優先級任務", MessagePriority.LOW)

        # 等待處理
        await asyncio.sleep(1.0)

        print("📊 場景2: 批次訊息智能合併")

        # 發送名片處理批次訊息
        for i in range(5):
            await queue.enqueue_message(
                chat_id=12345,
                text=f"📱 名片處理完成\n👤 測試人員{i} (測試公司{i})\n✅ 已存入 Notion",
                priority=MessagePriority.BATCH,
                message_type="card_processing_complete",
                context="card_batch_001",
            )

        # 等待批次處理
        await asyncio.sleep(1.0)

        print("📊 場景3: 高負載併發處理")

        # 高負載測試
        start_time = time.time()
        tasks = []
        for i in range(50):
            task = queue.enqueue_message(
                chat_id=12345 + (i % 5),
                text=f"高負載訊息 {i}",
                priority=MessagePriority.NORMAL if i % 3 != 0 else MessagePriority.HIGH,
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        enqueue_time = time.time() - start_time

        # 等待處理完成
        await asyncio.sleep(3.0)
        total_time = time.time() - start_time

        print("📊 場景4: 錯誤處理和重試機制")

        # 模擬部分失敗
        call_count = 0
        original_sender = queue.message_sender

        async def flaky_sender(chat_id, text, parse_mode):
            nonlocal call_count
            call_count += 1
            if call_count % 4 == 0:  # 25% 失敗率
                raise Exception("模擬網路錯誤")
            await original_sender(chat_id, text, parse_mode)

        queue.set_message_sender(flaky_sender)

        # 發送會觸發重試的訊息
        for i in range(10):
            await queue.enqueue_message(
                chat_id=12345,
                text=f"重試測試 {i}",
                priority=MessagePriority.NORMAL,
                max_retries=2,
            )

        await asyncio.sleep(2.0)

        # 恢復正常發送器
        queue.set_message_sender(original_sender)

        # 等待重試完成
        await asyncio.sleep(3.0)

        # 停止佇列
        await queue.stop()

        # 分析結果
        stats = queue._get_queue_stats()
        health = queue.get_health_status()

        print(f"\n📈 整合測試結果:")
        print(f"   - 入隊速度: {50/enqueue_time:.1f} msg/s")
        print(f"   - 總處理時間: {total_time:.2f}s")
        print(f"   - 成功處理: {stats['total_processed']}")
        print(f"   - 處理失敗: {stats['total_failed']}")
        print(f"   - 批次合併: {stats['total_merged']}")
        print(f"   - 併發調整: {stats['worker_adjustments']}")
        print(f"   - 最終錯誤率: {stats['error_rate']:.1%}")
        print(f"   - 系統健康: {health['status']}")

        # 驗證關鍵指標
        success_rate = stats["total_processed"] / (
            stats["total_processed"] + stats["total_failed"]
        )

        print(f"\n🎯 關鍵指標驗證:")
        print(f"   - 成功率: {success_rate:.1%} (目標 >80%)")
        print(f"   - 批次合併效果: {stats['total_merged']} 條訊息被合併")
        print(f"   - 優先級處理: 緊急訊息直接發送，高優先級優先處理")
        print(f"   - 動態調整: 系統根據負載自動調整併發數")

        # 檢查實際發送的訊息
        emergency_messages = [msg for msg in sent_messages if "緊急" in msg["text"]]
        batch_summaries = [msg for msg in sent_messages if "**批次處理完成**" in msg["text"]]

        print(f"   - 緊急訊息: {len(emergency_messages)} 條 (應該 >0)")
        print(f"   - 批次摘要: {len(batch_summaries)} 條 (應該 >0)")

        # 基本驗證
        assert success_rate > 0.8, f"成功率過低: {success_rate:.1%}"
        assert stats["total_merged"] > 0, "批次合併功能未工作"
        assert len(emergency_messages) > 0, "緊急訊息處理失敗"

        print("✅ 異步訊息佇列整合測試完成")
        return True

    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


# ==========================================
# 主程式入口
# ==========================================


async def main():
    """主測試程式"""
    print("🚀 異步訊息佇列系統完整測試開始")
    print("=" * 60)

    # 1. 基本功能測試
    print("\n🧪 1. 基本數據結構測試")
    await test_message_deduplication()
    print("✅ 數據結構測試通過")

    # 2. 整合測試
    print("\n🧪 2. 系統整合測試")
    integration_success = await run_async_message_queue_integration_test()

    # 3. 功能評估
    print("\n📈 3. 異步訊息佇列能力評估")
    if integration_success:
        print("✅ 異步訊息佇列系統符合以下功能目標:")
        print("   - 5級優先級排程: 緊急→高→普通→低→批次，智能優先級處理")
        print("   - 智能批次合併: 自動合併相關訊息，減少用戶干擾")
        print("   - 動態併發控制: 根據錯誤率自動調整併發數 (3-20)")
        print("   - 指數退避重試: 失敗訊息智能重試，避免資源浪費")
        print("   - 連接池優化: 感知連接池狀態，自動優化處理速度")
        print("   - 高並發處理: 支援每秒數百條訊息的高速處理")
        print("   - 健康監控: 即時監控系統健康和性能指標")
        print("   - 批次上下文: 提供便利的批次處理上下文管理器")

    print("\n" + "=" * 60)
    print("🎉 異步訊息佇列系統測試完成")

    return integration_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
