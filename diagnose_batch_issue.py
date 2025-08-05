#!/usr/bin/env python3
"""
批次處理組件診斷工具
檢查批次處理系統的狀態和問題
"""

import asyncio
import logging
import sys
import time
from typing import List, Dict, Any

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def diagnose_batch_image_collector():
    """診斷批次圖片收集器"""
    print("=" * 60)
    print("🔍 診斷 BatchImageCollector")
    print("=" * 60)
    
    try:
        from src.namecard.core.services.batch_image_collector import (
            BatchImageCollector, 
            get_batch_collector,
            PendingImage
        )
        
        print("✅ BatchImageCollector 模組導入成功")
        
        # 測試創建收集器
        collector = BatchImageCollector()
        print(f"✅ BatchImageCollector 初始化成功")
        print(f"  - batch_timeout: {collector.batch_timeout}秒")
        print(f"  - max_batch_size: {collector.max_batch_size}")
        print(f"  - cleanup_interval: {collector.cleanup_interval}秒")
        
        # 測試全域收集器
        global_collector = get_batch_collector()
        print(f"✅ 全域收集器獲取成功: {id(global_collector)}")
        
        return True, collector
        
    except Exception as e:
        print(f"❌ BatchImageCollector 診斷失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False, None


def diagnose_ultra_fast_processor():
    """診斷超高速處理器"""
    print("\n" + "=" * 60)
    print("🚀 診斷 UltraFastProcessor")
    print("=" * 60)
    
    try:
        from src.namecard.infrastructure.ai.ultra_fast_processor import (
            UltraFastProcessor,
            get_ultra_fast_processor,
            UltraFastResult
        )
        
        print("✅ UltraFastProcessor 模組導入成功")
        
        # 測試創建處理器
        processor = UltraFastProcessor()
        print("✅ UltraFastProcessor 初始化成功")
        print(f"  - AI處理器: {processor.ai_processor is not None}")
        print(f"  - 圖片下載器: {processor.image_downloader is not None}")
        print(f"  - 處理歷史數量: {len(processor.processing_history)}")
        
        # 測試性能儀表板
        dashboard = processor.get_performance_dashboard()
        print(f"✅ 性能儀表板: {dashboard.get('message', '有數據')}")
        
        return True, processor
        
    except Exception as e:
        print(f"❌ UltraFastProcessor 診斷失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False, None


def diagnose_safe_batch_processor():
    """診斷安全批次處理器"""
    print("\n" + "=" * 60)
    print("🛡️ 診斷 SafeBatchProcessor")
    print("=" * 60)
    
    try:
        from src.namecard.core.services.safe_batch_processor import (
            SafeBatchProcessor,
            SafeProcessingConfig,
            get_safe_batch_processor,
            initialize_safe_batch_processor
        )
        
        print("✅ SafeBatchProcessor 模組導入成功")
        
        # 測試配置
        config = SafeProcessingConfig()
        print(f"✅ SafeProcessingConfig 創建成功")
        print(f"  - max_concurrent_processing: {config.max_concurrent_processing}")
        print(f"  - processing_timeout: {config.processing_timeout}秒")
        print(f"  - enable_ultra_fast: {config.enable_ultra_fast}")
        print(f"  - fallback_to_traditional: {config.fallback_to_traditional}")
        
        # 測試處理器創建
        processor = SafeBatchProcessor(config=config)
        print("✅ SafeBatchProcessor 初始化成功")
        
        # 測試統計
        stats = processor.get_stats()
        print(f"✅ 統計信息: {stats['total_batches_processed']} 批次已處理")
        
        return True, processor
        
    except Exception as e:
        print(f"❌ SafeBatchProcessor 診斷失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False, None


async def test_batch_processing_flow():
    """測試批次處理流程"""
    print("\n" + "=" * 60)
    print("🔄 測試批次處理流程")
    print("=" * 60)
    
    try:
        # 導入必要組件
        from src.namecard.core.services.batch_image_collector import (
            BatchImageCollector,
            PendingImage
        )
        from src.namecard.core.services.safe_batch_processor import (
            SafeBatchProcessor,
            SafeProcessingConfig
        )
        
        # 創建測試收集器
        collector = BatchImageCollector(batch_timeout=2.0)  # 短超時用於測試
        
        # 創建測試處理器
        config = SafeProcessingConfig(
            max_concurrent_processing=2,
            processing_timeout=10.0,
            enable_ultra_fast=False,  # 測試時關閉，避免依賴問題
            fallback_to_traditional=False  # 測試時關閉
        )
        processor = SafeBatchProcessor(config=config)
        
        print("✅ 測試組件創建成功")
        
        # 模擬添加圖片到收集器
        test_images = []
        for i in range(3):
            # 創建模擬的待處理圖片
            pending_image = PendingImage(
                image_data=f"mock_image_data_{i}",
                file_id=f"test_file_{i}",
                chat_id=123456789,
                user_id="test_user_123",
                metadata={"test": True, "index": i}
            )
            test_images.append(pending_image)
        
        print(f"✅ 創建了 {len(test_images)} 個測試圖片對象")
        
        # 測試處理流程（不實際執行，只檢查邏輯）
        print("🔄 測試批次處理邏輯...")
        
        # 模擬批次處理（不實際調用 AI）
        user_id = "test_user_123"
        print(f"✅ 模擬用戶 {user_id} 的 {len(test_images)} 張圖片批次處理")
        
        # 檢查處理器統計
        stats_before = processor.get_stats()
        print(f"📊 處理前統計: {stats_before}")
        
        return True
        
    except Exception as e:
        print(f"❌ 批次處理流程測試失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False


def diagnose_telegram_integration():
    """診斷 Telegram Bot 整合"""
    print("\n" + "=" * 60)
    print("📱 診斷 Telegram Bot 整合")
    print("=" * 60)
    
    try:
        # 檢查主要模組是否可用
        from src.namecard.api.telegram_bot.main import (
            batch_image_collector,
            ultra_fast_processor,
            enhanced_telegram_handler,
            batch_processor_callback,
            batch_progress_notifier
        )
        
        print("✅ Telegram Bot 主模組導入成功")
        
        # 檢查各組件狀態
        print(f"📦 batch_image_collector: {batch_image_collector is not None}")
        print(f"🚀 ultra_fast_processor: {ultra_fast_processor is not None}")
        print(f"⚡ enhanced_telegram_handler: {enhanced_telegram_handler is not None}")
        print(f"🔄 batch_processor_callback: {callable(batch_processor_callback)}")
        print(f"📢 batch_progress_notifier: {callable(batch_progress_notifier)}")
        
        # 檢查批次收集器的回調設置
        if batch_image_collector:
            has_processor = batch_image_collector.batch_processor is not None
            has_notifier = batch_image_collector.progress_notifier is not None
            print(f"🔧 收集器回調設置: 處理器={has_processor}, 通知器={has_notifier}")
            
            # 檢查收集器狀態
            stats = batch_image_collector.get_stats()
            print(f"📊 收集器統計: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram Bot 整合診斷失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False


def diagnose_media_group_handling():
    """診斷媒體群組處理邏輯"""
    print("\n" + "=" * 60)
    print("📸 診斷媒體群組處理邏輯")
    print("=" * 60)
    
    try:
        from src.namecard.api.telegram_bot.main import (
            media_group_collector,
            handle_media_group_message,
            process_media_group_photos
        )
        
        print("✅ 媒體群組處理模組導入成功")
        print(f"📦 media_group_collector: {type(media_group_collector)} - {len(media_group_collector)} 個活躍群組")
        print(f"🔄 handle_media_group_message: {callable(handle_media_group_message)}")
        print(f"⚡ process_media_group_photos: {callable(process_media_group_photos)}")
        
        # 檢查是否有遺留的媒體群組
        if media_group_collector:
            print(f"📋 當前媒體群組狀態:")
            for group_id, group_data in media_group_collector.items():
                photos_count = len(group_data.get('photos', []))
                created_at = group_data.get('created_at', 0)
                age = time.time() - created_at if created_at else 0
                print(f"  - 群組 {group_id}: {photos_count} 張圖片, 存在 {age:.1f} 秒")
                
                # 檢查計時器狀態
                timer_task = group_data.get('timer_task')
                if timer_task:
                    print(f"    計時器: {'運行中' if not timer_task.done() else '已完成'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 媒體群組處理診斷失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False


async def simulate_batch_collection_timeout():
    """模擬批次收集超時測試"""
    print("\n" + "=" * 60)
    print("⏰ 模擬批次收集超時測試")
    print("=" * 60)
    
    try:
        from src.namecard.core.services.batch_image_collector import BatchImageCollector
        
        # 創建測試收集器（短超時）
        collector = BatchImageCollector(batch_timeout=1.0)
        
        # 模擬處理器回調
        processed_batches = []
        
        async def mock_batch_processor(user_id: str, images: List):
            processed_batches.append({
                'user_id': user_id,
                'image_count': len(images),
                'timestamp': time.time()
            })
            print(f"🔄 模擬處理: 用戶 {user_id}, {len(images)} 張圖片")
        
        # 設置回調
        collector.set_batch_processor(mock_batch_processor)
        await collector.start()
        
        print("✅ 模擬收集器啟動成功")
        
        # 添加測試圖片
        user_id = "test_timeout_user"
        chat_id = 987654321
        
        print("📥 添加第一張圖片...")
        result1 = await collector.add_image(
            user_id=user_id,
            chat_id=chat_id,
            image_data="mock_data_1",
            file_id="test_file_1"
        )
        print(f"  結果: {result1}")
        
        # 等待 0.5 秒，添加第二張圖片
        await asyncio.sleep(0.5)
        print("📥 添加第二張圖片...")
        result2 = await collector.add_image(
            user_id=user_id,
            chat_id=chat_id,
            image_data="mock_data_2",
            file_id="test_file_2"
        )
        print(f"  結果: {result2}")
        
        # 等待超時觸發
        print("⏰ 等待批次超時觸發...")
        await asyncio.sleep(1.5)
        
        # 檢查結果
        if processed_batches:
            batch = processed_batches[0]
            print(f"✅ 批次處理成功觸發:")
            print(f"  - 用戶: {batch['user_id']}")
            print(f"  - 圖片數: {batch['image_count']}")
            print(f"  - 時間戳: {batch['timestamp']}")
        else:
            print("❌ 批次處理未觸發")
        
        # 停止收集器
        await collector.stop()
        print("✅ 收集器已停止")
        
        return len(processed_batches) > 0
        
    except Exception as e:
        print(f"❌ 批次收集超時測試失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False


def check_telegram_file_compatibility():
    """檢查 Telegram File 對象兼容性"""
    print("\n" + "=" * 60)
    print("📄 檢查 Telegram File 對象兼容性")
    print("=" * 60)
    
    try:
        from telegram import File
        from src.namecard.infrastructure.ai.ultra_fast_processor import UltraFastProcessor
        
        print("✅ Telegram File 和 UltraFastProcessor 導入成功")
        
        # 檢查 UltraFastProcessor 是否能處理 Telegram File
        processor = UltraFastProcessor()
        
        # 檢查方法是否存在
        has_batch_method = hasattr(processor, 'process_telegram_photos_batch_ultra_fast')
        has_single_method = hasattr(processor, 'process_telegram_photo_ultra_fast')
        
        print(f"🔄 批次處理方法: {has_batch_method}")
        print(f"🔄 單張處理方法: {has_single_method}")
        
        if has_batch_method:
            import inspect
            sig = inspect.signature(processor.process_telegram_photos_batch_ultra_fast)
            print(f"📋 批次方法簽名: {sig}")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram File 兼容性檢查失敗: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        return False


def main():
    """主診斷流程"""
    print("🔍 批次處理系統診斷工具")
    print("="*80)
    
    results = {}
    
    # 1. 診斷批次圖片收集器
    success, collector = diagnose_batch_image_collector()
    results['batch_image_collector'] = success
    
    # 2. 診斷超高速處理器
    success, processor = diagnose_ultra_fast_processor()
    results['ultra_fast_processor'] = success
    
    # 3. 診斷安全批次處理器
    success, safe_processor = diagnose_safe_batch_processor()
    results['safe_batch_processor'] = success
    
    # 4. 診斷 Telegram Bot 整合
    success = diagnose_telegram_integration()
    results['telegram_integration'] = success
    
    # 5. 診斷媒體群組處理
    success = diagnose_media_group_handling()
    results['media_group_handling'] = success
    
    # 6. 檢查 Telegram File 兼容性
    success = check_telegram_file_compatibility()
    results['telegram_file_compatibility'] = success
    
    # 7. 異步測試
    print("\n" + "=" * 60)
    print("🧪 開始異步測試...")
    print("=" * 60)
    
    # 運行異步測試
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 測試批次處理流程
        flow_success = loop.run_until_complete(test_batch_processing_flow())
        results['batch_flow_test'] = flow_success
        
        # 測試批次收集超時
        timeout_success = loop.run_until_complete(simulate_batch_collection_timeout())
        results['timeout_test'] = timeout_success
        
    except Exception as e:
        print(f"❌ 異步測試失敗: {e}")
        results['async_tests'] = False
    finally:
        loop.close()
    
    # 8. 總結報告
    print("\n" + "=" * 80)
    print("📊 診斷結果總結")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    print(f"總測試項目: {total_tests}")
    print(f"通過測試: {passed_tests}")
    print(f"通過率: {passed_tests/total_tests:.1%}")
    print()
    
    for test_name, success in results.items():
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"{test_name:<30}: {status}")
    
    print("\n" + "=" * 80)
    
    if passed_tests == total_tests:
        print("🎉 所有診斷測試通過！批次處理系統狀態良好。")
    elif passed_tests >= total_tests * 0.7:
        print("⚠️ 大部分組件正常，但有部分問題需要修復。")
    else:
        print("🚨 發現嚴重問題，需要立即修復批次處理系統。")
    
    print("\n📋 建議的修復步驟:")
    if not results.get('batch_image_collector'):
        print("1. 檢查 BatchImageCollector 的依賴和初始化")
    if not results.get('ultra_fast_processor'):
        print("2. 檢查 UltraFastProcessor 的 AI 組件設置")
    if not results.get('telegram_integration'):
        print("3. 檢查 Telegram Bot 主程序的組件整合")
    if not results.get('timeout_test'):
        print("4. 檢查批次收集器的計時器邏輯")
    
    print("\n💡 如果問題持續，請檢查:")
    print("  - 環境變數設置 (API Keys)")
    print("  - Python 依賴版本")
    print("  - 異步事件循環管理")
    print("  - 連接池配置")


if __name__ == "__main__":
    main()