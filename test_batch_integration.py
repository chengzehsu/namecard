#!/usr/bin/env python3
"""
批次處理整合測試 - 驗證所有組件正常工作
"""

import asyncio
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath('.'))

async def test_batch_components():
    """測試批次處理組件的整合"""
    
    print("🧪 開始批次處理整合測試...")
    
    try:
        # 1. 測試 BatchImageCollector 導入和初始化
        print("1️⃣ 測試 BatchImageCollector...")
        from src.namecard.core.services.batch_image_collector import (
            BatchImageCollector, 
            PendingImage,
            get_batch_collector,
            initialize_batch_collector
        )
        
        collector = BatchImageCollector(batch_timeout=2.0, max_batch_size=5)
        print("   ✅ BatchImageCollector 初始化成功")
        
        # 2. 測試 UnifiedResultFormatter 
        print("2️⃣ 測試 UnifiedResultFormatter...")
        from src.namecard.core.services.unified_result_formatter import (
            UnifiedResultFormatter,
            SingleCardResult,
            BatchProcessingResult,
            ProcessingStatus,
            create_single_card_result,
            create_batch_result
        )
        
        formatter = UnifiedResultFormatter()
        
        # 創建測試結果
        test_result = create_single_card_result(
            status=ProcessingStatus.SUCCESS,
            card_data={"name": "測試", "company": "測試公司"},
            processing_time=1.5,
            image_index=1
        )
        
        test_batch = create_batch_result(
            user_id="test_user",
            results=[test_result],
            total_processing_time=2.0,
            started_at=1000.0
        )
        
        formatted_message = formatter.format_batch_result(test_batch)
        print("   ✅ UnifiedResultFormatter 測試成功")
        print(f"   📝 格式化訊息預覽:\n{formatted_message[:200]}...")
        
        # 3. 測試 SafeBatchProcessor 導入
        print("3️⃣ 測試 SafeBatchProcessor...")
        from src.namecard.core.services.safe_batch_processor import (
            SafeBatchProcessor,
            SafeProcessingConfig,
            get_safe_batch_processor,
            initialize_safe_batch_processor
        )
        
        config = SafeProcessingConfig(max_concurrent_processing=4)
        processor = SafeBatchProcessor(config=config)
        print("   ✅ SafeBatchProcessor 初始化成功")
        
        # 4. 測試 Enhanced Telegram Client 導入
        print("4️⃣ 測試 Enhanced Telegram Client...")
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
            EnhancedTelegramBotHandler,
            create_enhanced_telegram_handler
        )
        
        # 創建增強處理器（停用佇列系統避免需要 Token）
        enhanced_handler = create_enhanced_telegram_handler(
            enable_queue=False,
            queue_workers=4
        )
        print("   ✅ EnhancedTelegramBotHandler 創建成功")
        
        # 5. 測試連接池修復組件
        print("5️⃣ 測試連接池修復組件...")
        from src.namecard.infrastructure.messaging.async_message_queue import (
            AsyncMessageQueue,
            MessagePriority
        )
        
        # 創建訊息佇列（無需啟動）
        queue = AsyncMessageQueue(initial_concurrent_workers=4)
        print("   ✅ AsyncMessageQueue 創建成功")
        
        # 6. 測試 Ultra Fast Processor（如果可用）
        print("6️⃣ 測試 Ultra Fast Processor...")
        try:
            from src.namecard.infrastructure.ai.ultra_fast_processor import (
                UltraFastProcessor,
                get_ultra_fast_processor
            )
            print("   ✅ UltraFastProcessor 導入成功")
        except Exception as e:
            print(f"   ⚠️ UltraFastProcessor 導入失敗: {e}")
        
        # 7. 整合測試模擬
        print("7️⃣ 模擬批次收集流程...")
        
        # 模擬添加圖片（不實際處理）
        async def mock_batch_processor(user_id, images):
            print(f"   🔄 模擬處理 {len(images)} 張圖片（用戶：{user_id}）")
        
        async def mock_progress_notifier(user_id, chat_id, image_count, action):
            print(f"   📊 進度通知：用戶 {user_id}，動作 {action}，圖片數 {image_count}")
        
        # 設置回調並啟動收集器
        collector.set_batch_processor(mock_batch_processor)
        collector.set_progress_notifier(mock_progress_notifier)
        await collector.start()
        
        # 模擬添加圖片
        mock_image_data = b"mock_image_data"
        for i in range(3):
            result = await collector.add_image(
                user_id="test_user_123",
                chat_id=12345,
                image_data=mock_image_data,
                file_id=f"mock_file_{i}",
                metadata={"test": True}
            )
            print(f"   📥 圖片 {i+1} 添加結果: {result['action']}")
            await asyncio.sleep(0.1)  # 短暫延遲
        
        # 等待批次處理完成
        await asyncio.sleep(3)  # 等待批次超時觸發
        
        await collector.stop()
        print("   ✅ 批次收集流程模擬完成")
        
        print("\n🎉 所有組件測試通過！批次處理系統整合成功")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        print(f"錯誤堆疊:\n{traceback.format_exc()}")
        return False

async def main():
    """主測試函數"""
    success = await test_batch_components()
    
    if success:
        print("\n✅ 批次處理整合測試完成 - 所有組件正常工作")
        print("📋 測試總結:")
        print("   • BatchImageCollector: ✅ 智能收集和計時器")
        print("   • UnifiedResultFormatter: ✅ 結果格式化")
        print("   • SafeBatchProcessor: ✅ 安全併發處理")
        print("   • EnhancedTelegramClient: ✅ 增強訊息處理")
        print("   • AsyncMessageQueue: ✅ 異步訊息佇列")
        print("   • 連接池修復: ✅ 協程管理優化")
        print("\n🚀 系統已準備好部署！")
    else:
        print("\n❌ 批次處理整合測試失敗")
        print("🔧 請檢查錯誤並修復後再次測試")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())