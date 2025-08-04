"""
異步訊息排程系統使用範例
展示如何在實際場景中使用新的排程系統
"""

import asyncio
import logging
from typing import List
import time

# 設置日誌
logging.basicConfig(level=logging.INFO)


async def example_1_basic_usage():
    """範例 1：基本使用方式"""
    print("\n" + "="*50)
    print("📋 範例 1：基本使用方式")
    print("="*50)
    
    try:
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import create_enhanced_telegram_handler
        
        # 創建增強處理器
        async with await create_enhanced_telegram_handler(enable_queue=True) as handler:
            
            # 基本訊息發送（自動選擇是否使用排程）
            result = await handler.safe_send_message(
                chat_id="123456789",
                text="Hello! 這是一條測試訊息"
            )
            print(f"✅ 基本訊息發送結果: {result}")
            
            # 緊急訊息（高優先級，不排程）
            result = await handler.send_urgent_message(
                chat_id="123456789", 
                text="🚨 這是緊急訊息，需要立即發送！"
            )
            print(f"🚨 緊急訊息發送結果: {result}")
            
            # 完成訊息（高優先級）
            result = await handler.send_completion_message(
                chat_id="123456789",
                text="✅ 任務完成！",
                callback=lambda result: print(f"完成訊息發送成功: {result}")
            )
            print(f"✅ 完成訊息發送結果: {result}")
            
    except Exception as e:
        print(f"❌ 範例 1 執行失敗: {e}")


async def example_2_batch_processing():
    """範例 2：批次處理場景"""
    print("\n" + "="*50)
    print("📦 範例 2：批次處理場景")
    print("="*50)
    
    try:
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import create_enhanced_telegram_handler
        
        async with await create_enhanced_telegram_handler(enable_queue=True) as handler:
            
            # 使用批次上下文管理器
            async with handler.batch_context("card_processing_batch") as batch_id:
                print(f"📦 開始批次上下文: {batch_id}")
                
                # 模擬批次處理多張名片
                card_names = ["張三", "李四", "王五", "趙六", "錢七"]
                
                for i, name in enumerate(card_names, 1):
                    # 發送批次訊息（可能會被合併）
                    result = await handler.send_batch_message(
                        chat_id="123456789",
                        text=f"🔄 正在處理第 {i}/{len(card_names)} 張名片: {name}"
                    )
                    print(f"📤 批次訊息 {i}: {result.get('queued_message_id', 'N/A')}")
                    
                    # 模擬處理時間
                    await asyncio.sleep(0.5)
                    
                    # 發送完成通知
                    await handler.send_completion_message(
                        chat_id="123456789",
                        text=f"✅ 名片處理完成: {name}",
                        parse_mode="Markdown"
                    )
                    
                print(f"📦 批次上下文結束: {batch_id}")
                
            # 發送最終統計
            await handler.send_completion_message(
                chat_id="123456789",
                text=f"🎉 **批次處理完成**\n📊 總共處理 {len(card_names)} 張名片",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        print(f"❌ 範例 2 執行失敗: {e}")


async def example_3_high_load_simulation():
    """範例 3：高負載場景模擬"""
    print("\n" + "="*50)
    print("⚡ 範例 3：高負載場景模擬")
    print("="*50)
    
    try:
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import create_enhanced_telegram_handler
        
        async with await create_enhanced_telegram_handler(enable_queue=True) as handler:
            
            # 模擬高負載：快速發送大量訊息
            print("🚀 開始高負載測試...")
            start_time = time.time()
            
            tasks = []
            for i in range(100):  # 模擬100條訊息
                if i % 10 == 0:
                    # 每10條訊息中有1條緊急訊息
                    task = handler.send_urgent_message(
                        chat_id="123456789",
                        text=f"🚨 緊急訊息 #{i}"
                    )
                elif i % 5 == 0:
                    # 每5條訊息中有1條完成訊息
                    task = handler.send_completion_message(
                        chat_id="123456789",
                        text=f"✅ 完成訊息 #{i}"
                    )
                else:
                    # 其他為批次訊息
                    task = handler.send_batch_message(
                        chat_id="123456789",
                        text=f"📝 批次訊息 #{i}"
                    )
                    
                tasks.append(task)
                
            # 等待所有訊息排程完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 統計結果
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            print(f"📊 高負載測試結果:")
            print(f"   ⏱️  總耗時: {duration:.2f} 秒")
            print(f"   ✅ 成功排程: {successful} 條")
            print(f"   ❌ 失敗: {failed} 條")
            print(f"   📈 平均速度: {len(results)/duration:.1f} 條/秒")
            
            # 獲取系統狀態
            status = handler.get_enhanced_status_report()
            queue_stats = status.get("queue_stats", {})
            print(f"   🔄 當前佇列長度: {queue_stats.get('total_queued_now', 0)}")
            print(f"   ⚡ 當前併發數: {queue_stats.get('current_concurrent', 0)}")
            
            # 等待一段時間讓訊息處理完成
            print("⏳ 等待訊息處理完成...")
            await asyncio.sleep(10)
            
            # 獲取最終狀態
            final_status = handler.get_enhanced_status_report()
            final_queue_stats = final_status.get("queue_stats", {})
            final_stats = final_queue_stats.get("stats", {})
            
            print(f"📈 最終統計:")
            print(f"   📤 總發送: {final_stats.get('total_sent', 0)}")
            print(f"   ❌ 總失敗: {final_stats.get('total_failed', 0)}")
            print(f"   📦 總合併: {final_stats.get('total_batched', 0)}")
            print(f"   ⏱️  平均佇列時間: {final_stats.get('avg_queue_time', 0):.2f}s")
            
    except Exception as e:
        print(f"❌ 範例 3 執行失敗: {e}")


async def example_4_batch_integration():
    """範例 4：完整批次處理整合"""
    print("\n" + "="*50)
    print("🔧 範例 4：完整批次處理整合")
    print("="*50)
    
    try:
        from src.namecard.infrastructure.messaging.batch_message_integration import create_batch_processing_system
        
        # 創建批次處理系統
        batch_system = await create_batch_processing_system(enable_queue=True)
        
        # 模擬批次會話數據
        batch_session = {
            "start_time": "2025-01-01T12:00:00",
            "batch_id": "test_batch_001",
            "user_id": "123456789"
        }
        
        # 模擬名片圖片數據
        mock_card_images = [
            b"mock_image_data_1",
            b"mock_image_data_2", 
            b"mock_image_data_3",
            b"mock_image_data_4",
            b"mock_image_data_5"
        ]
        
        print(f"🚀 開始批次處理 {len(mock_card_images)} 張名片...")
        
        # 執行批次處理
        result = await batch_system.process_batch_cards(
            user_id="123456789",
            card_images=mock_card_images,
            batch_session=batch_session
        )
        
        print(f"📊 批次處理結果:")
        print(f"   📥 總數: {result['total_processed']}")
        print(f"   ✅ 成功: {result['successful']} ({result['success_rate']:.1%})")
        print(f"   ❌ 失敗: {result['failed']}")
        
        # 關閉系統
        await batch_system.telegram_handler.close()
        
    except Exception as e:
        print(f"❌ 範例 4 執行失敗: {e}")


async def example_5_performance_monitoring():
    """範例 5：效能監控和建議"""
    print("\n" + "="*50)
    print("📊 範例 5：效能監控和建議")
    print("="*50)
    
    try:
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import create_enhanced_telegram_handler
        
        async with await create_enhanced_telegram_handler(enable_queue=True) as handler:
            
            # 發送一些測試訊息
            for i in range(20):
                await handler.safe_send_message(
                    chat_id="123456789",
                    text=f"測試訊息 #{i}"
                )
                
            # 等待處理
            await asyncio.sleep(5)
            
            # 獲取狀態報告
            status = handler.get_enhanced_status_report()
            print("📋 系統狀態報告:")
            print(f"   🔄 排程系統啟動: {status['queue_system_started']}")
            print(f"   📦 當前批次ID: {status['current_batch_id']}")
            print(f"   📊 佇列統計: {status.get('queue_stats', {})}")
            
            # 獲取效能建議
            recommendations = handler.get_performance_recommendations()
            print(f"\n💡 效能建議:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
                
    except Exception as e:
        print(f"❌ 範例 5 執行失敗: {e}")


async def main():
    """主函數：執行所有範例"""
    print("🚀 異步訊息排程系統使用範例")
    print("=" * 60)
    
    # 注意：這些範例在沒有真實 TELEGRAM_BOT_TOKEN 的情況下會失敗
    # 但可以展示系統的使用方式和架構
    
    examples = [
        ("基本使用", example_1_basic_usage),
        ("批次處理", example_2_batch_processing),
        ("高負載模擬", example_3_high_load_simulation),
        ("批次整合", example_4_batch_integration),
        ("效能監控", example_5_performance_monitoring)
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n🔄 執行範例: {name}")
            await example_func()
            print(f"✅ 範例 {name} 執行完成")
        except Exception as e:
            print(f"❌ 範例 {name} 執行失敗: {e}")
            # 繼續執行下一個範例
            continue
            
    print("\n" + "="*60)
    print("🎉 所有範例執行完成")


if __name__ == "__main__":
    # 執行範例
    asyncio.run(main())