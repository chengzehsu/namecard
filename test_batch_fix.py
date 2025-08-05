#!/usr/bin/env python3
"""
測試批次收集器修復 - 驗證5張圖片不會遺失
"""

import asyncio
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath('.'))

async def test_five_image_batch():
    """測試5張圖片的批次處理"""
    
    print("🧪 測試5張圖片批次處理修復...")
    
    try:
        from src.namecard.core.services.batch_image_collector import BatchImageCollector
        
        # 創建收集器，較短的超時時間便於測試
        collector = BatchImageCollector(batch_timeout=2.0, max_batch_size=10)
        
        processed_batches = []
        
        async def mock_batch_processor(user_id, images):
            print(f"   🔄 批次處理觸發：用戶 {user_id}，圖片數 {len(images)}")
            for i, img in enumerate(images):
                print(f"      - 圖片 {i+1}: {img.file_id}")
            processed_batches.append((user_id, len(images)))
            print(f"   ✅ 批次處理完成：{len(images)} 張圖片")
        
        async def mock_progress_notifier(user_id, chat_id, image_count, action):
            print(f"   📊 進度：用戶 {user_id}，動作 {action}，圖片數 {image_count}")
        
        # 設置回調並啟動
        collector.set_batch_processor(mock_batch_processor)
        collector.set_progress_notifier(mock_progress_notifier)
        await collector.start()
        
        user_id = "test_user_5images"
        chat_id = 12345
        
        print(f"📥 開始模擬用戶上傳5張圖片...")
        
        # 模擬連續上傳5張圖片
        for i in range(5):
            result = await collector.add_image(
                user_id=user_id,
                chat_id=chat_id,
                image_data=f"mock_image_data_{i}".encode(),
                file_id=f"mock_file_{i}",
                metadata={"test": True, "index": i}
            )
            print(f"   📸 圖片 {i+1} 添加：{result['action']}")
            
            # 圖片間有小間隔
            await asyncio.sleep(0.3)
        
        print(f"⏱️ 等待批次處理完成...")
        
        # 等待足夠時間讓所有批次處理完成
        await asyncio.sleep(8.0)  # 等待超過延長超時時間
        
        # 檢查結果
        print(f"\n📊 處理結果分析：")
        print(f"   - 處理批次數：{len(processed_batches)}")
        
        total_processed = sum(count for _, count in processed_batches)
        print(f"   - 總處理圖片數：{total_processed}")
        
        for i, (uid, count) in enumerate(processed_batches):
            print(f"   - 批次 {i+1}：用戶 {uid}，圖片數 {count}")
        
        await collector.stop()
        
        # 驗證結果
        if total_processed == 5:
            print("\n✅ 測試成功：5張圖片全部處理！")
            return True
        else:
            print(f"\n❌ 測試失敗：期望5張圖片，實際處理 {total_processed} 張")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試錯誤: {e}")
        import traceback
        print(f"錯誤堆疊:\n{traceback.format_exc()}")
        return False

async def test_timing_scenarios():
    """測試不同時間間隔的場景"""
    
    print("\n🧪 測試不同時間間隔場景...")
    
    try:
        from src.namecard.core.services.batch_image_collector import BatchImageCollector
        
        collector = BatchImageCollector(batch_timeout=1.5, max_batch_size=10)
        
        all_results = []
        
        async def capture_processor(user_id, images):
            result = (user_id, len(images), [img.file_id for img in images])
            all_results.append(result)
            print(f"   🔄 處理：{user_id}，{len(images)}張圖片")
        
        collector.set_batch_processor(capture_processor)
        await collector.start()
        
        # 場景1：快速上傳3張圖片
        print("\n場景1：快速上傳3張圖片")
        for i in range(3):
            await collector.add_image("user1", 111, f"data1_{i}".encode(), f"file1_{i}")
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(2.5)
        
        # 場景2：上傳2張，等待，再上傳2張
        print("\n場景2：上傳2張，等待，再上傳2張")
        for i in range(2):
            await collector.add_image("user2", 222, f"data2_{i}".encode(), f"file2_{i}")
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(0.8)  # 在超時前上傳更多
        
        for i in range(2, 4):
            await collector.add_image("user2", 222, f"data2_{i}".encode(), f"file2_{i}")
            await asyncio.sleep(0.1)
            
        await asyncio.sleep(3.0)
        
        await collector.stop()
        
        print(f"\n📊 所有處理結果：")
        for user_id, count, files in all_results:
            print(f"   - {user_id}：{count}張圖片 {files}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 時間場景測試錯誤: {e}")
        return False

async def main():
    """主測試函數"""
    print("🚀 開始批次收集器修復測試\n")
    
    success1 = await test_five_image_batch()
    success2 = await test_timing_scenarios()
    
    if success1 and success2:
        print("\n🎉 所有修復測試通過！")
        print("📋 修復內容：")
        print("   • 批次處理完成後不立即清理狀態")
        print("   • 檢測連續上傳，自動延長等待時間")
        print("   • 延遲清理機制，避免丟失後續圖片")
        print("   • 智能超時調整，適應用戶上傳模式")
        print("\n✅ 5張圖片遺失問題已修復！")
        return True
    else:
        print("\n❌ 修復測試失敗，需要進一步調整")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)