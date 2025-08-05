#!/usr/bin/env python3
"""
批次收集器計時器調試

專門測試計時器是否正常觸發。
"""

import asyncio
import sys
import os
import logging

# 設置日誌級別為 DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.namecard.core.services.batch_image_collector import BatchImageCollector

async def test_timer_functionality():
    """專門測試計時器功能"""
    print("🔍 開始計時器調試測試...\n")
    
    # 創建新的收集器實例，使用較短的超時時間
    collector = BatchImageCollector(
        batch_timeout=2.0,  # 2秒超時，便於測試
        max_batch_size=10,
        cleanup_interval=60.0,
        max_batch_age=300.0
    )
    
    # 處理結果
    processed_batches = []
    
    async def debug_batch_processor(user_id: str, images):
        """調試批次處理器"""
        print(f"🎯 計時器觸發！處理用戶 {user_id} 的 {len(images)} 張圖片")
        processed_batches.append({
            'user_id': user_id,
            'image_count': len(images),
            'timestamp': asyncio.get_event_loop().time()
        })
    
    async def debug_progress_notifier(user_id: str, chat_id: int, image_count: int, action: str):
        """調試進度通知器"""
        print(f"📊 進度: 用戶 {user_id}, 動作 {action}, 圖片 {image_count}")
    
    # 設置處理器
    collector.set_batch_processor(debug_batch_processor)
    collector.set_progress_notifier(debug_progress_notifier)
    
    # 啟動收集器
    await collector.start()
    print("✅ 收集器已啟動")
    
    # 添加單張圖片並觀察計時器行為
    test_user_id = "timer_test_user"
    test_chat_id = 999999
    
    print(f"\n📸 添加第1張圖片，啟動計時器...")
    
    start_time = asyncio.get_event_loop().time()
    
    result = await collector.add_image(
        user_id=test_user_id,
        chat_id=test_chat_id,
        image_data="test_image_1",
        file_id="test_file_1",
        metadata={"test": True}
    )
    
    print(f"📝 添加結果: {result}")
    
    # 檢查批次狀態
    status = collector.get_batch_status(test_user_id)
    print(f"📊 批次狀態: {status}")
    
    # 等待計時器觸發（3秒超時）
    print(f"\n⏰ 等待計時器觸發（預期2秒後）...")
    
    for i in range(35):  # 3.5秒
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - start_time
        
        if len(processed_batches) > 0:
            process_time = processed_batches[0]['timestamp']
            trigger_delay = process_time - start_time
            print(f"✅ 計時器在 {trigger_delay:.2f} 秒後觸發！")
            break
        
        # 每0.5秒輸出狀態
        if i % 5 == 0:
            current_status = collector.get_batch_status(test_user_id)
            if current_status:
                print(f"📊 {elapsed:.1f}s: 圖片={current_status['image_count']}, "
                      f"計時器={current_status['has_timer']}, "
                      f"處理中={current_status['is_processing']}")
        
        await asyncio.sleep(0.1)
    
    # 檢查結果
    if len(processed_batches) == 0:
        print("❌ 計時器未觸發")
        
        # 檢查計時器任務狀態
        final_status = collector.get_batch_status(test_user_id)
        if final_status:
            print(f"🔍 最終狀態: {final_status}")
        
        # 檢查是否有異常或任務完成狀態
        if test_user_id in collector.pending_batches:
            batch_status = collector.pending_batches[test_user_id]
            if batch_status.timer_task:
                task = batch_status.timer_task
                print(f"🔍 計時器任務狀態:")
                print(f"   - 完成: {task.done()}")
                print(f"   - 取消: {task.cancelled()}")
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        print(f"   - 結果: {result}")
                    except Exception as e:
                        print(f"   - 異常: {e}")
        
        return False
    else:
        print("✅ 計時器正常觸發")
        return True
    
    # 清理
    await collector.stop()

async def main():
    """主函數"""
    try:
        success = await test_timer_functionality()
        
        if success:
            print("\n🎉 計時器調試測試成功!")
            return 0
        else:
            print("\n❌ 計時器調試測試失敗")
            return 1
            
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)