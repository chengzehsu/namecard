#!/usr/bin/env python3
"""
測試批次收集器修復效果

驗證修復後的批次收集器是否能正常處理媒體群組圖片。
"""

import asyncio
import os
import sys

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.namecard.core.services.batch_image_collector import (
    PendingImage,
    get_batch_collector,
)


async def test_batch_collector():
    """測試批次收集器功能"""
    print("🧪 開始測試批次收集器修復效果...\n")

    # 1. 獲取批次收集器
    collector = get_batch_collector()
    if not collector:
        print("❌ 批次收集器未初始化")
        return False

    print("✅ 批次收集器已初始化")

    # 2. 模擬處理回調函數
    processed_batches = []

    async def mock_batch_processor(user_id: str, images):
        """模擬批次處理器"""
        print(f"🚀 模擬處理用戶 {user_id} 的 {len(images)} 張圖片")
        processed_batches.append(
            {"user_id": user_id, "image_count": len(images), "images": images}
        )

    async def mock_progress_notifier(
        user_id: str, chat_id: int, image_count: int, action: str
    ):
        """模擬進度通知器"""
        print(f"📊 進度通知: 用戶 {user_id}, 動作 {action}, 圖片數 {image_count}")

    # 3. 設置回調函數
    collector.set_batch_processor(mock_batch_processor)
    collector.set_progress_notifier(mock_progress_notifier)

    # 檢查回調函數是否設置成功
    if collector.batch_processor is None:
        print("❌ 批次處理器回調函數設置失敗")
        return False

    if collector.progress_notifier is None:
        print("❌ 進度通知器回調函數設置失敗")
        return False

    print("✅ 回調函數設置成功")

    # 4. 啟動收集器
    await collector.start()
    print("✅ 批次收集器已啟動")

    # 5. 模擬添加圖片（模擬媒體群組）
    test_user_id = "test_user_123"
    test_chat_id = 123456789

    print(f"\n📸 模擬用戶 {test_user_id} 發送 5 張圖片的媒體群組...")

    # 添加 5 張模擬圖片
    for i in range(1, 6):
        mock_image_data = f"mock_image_data_{i}"
        file_id = f"mock_file_id_{i}"

        result = await collector.add_image(
            user_id=test_user_id,
            chat_id=test_chat_id,
            image_data=mock_image_data,
            file_id=file_id,
            metadata={"media_group_id": "test_media_group_123"},
        )

        print(f"📥 第 {i} 張圖片添加結果: {result}")

        # 短暫延遲模擬實際上傳間隔
        await asyncio.sleep(0.1)

    # 6. 等待批次處理完成（6秒超時）
    print(f"\n⏱️ 等待批次處理完成...")

    # 檢查批次狀態
    batch_status = collector.get_batch_status(test_user_id)
    if batch_status:
        print(f"📊 當前批次狀態: {batch_status}")
    else:
        print("❌ 找不到批次狀態")

    # 等待批次處理器執行
    for attempt in range(60):  # 最多等待6秒
        if len(processed_batches) > 0:
            break

        # 每秒輸出狀態
        if attempt % 10 == 0 and attempt > 0:
            current_status = collector.get_batch_status(test_user_id)
            if current_status:
                print(
                    f"📊 等待中... ({attempt/10:.0f}s) 狀態: 圖片數={current_status['image_count']}, "
                    f"處理中={current_status['is_processing']}, 有計時器={current_status['has_timer']}"
                )

        await asyncio.sleep(0.1)

    # 7. 檢查結果
    if len(processed_batches) == 0:
        print("❌ 批次處理器未被調用，嘗試手動觸發...")

        # 輸出最終狀態用於診斷
        final_status = collector.get_batch_status(test_user_id)
        if final_status:
            print(f"🔍 最終批次狀態: {final_status}")

        # 嘗試手動觸發批次處理
        print("🔧 手動觸發批次處理...")
        force_result = await collector.force_process_user_batch(test_user_id)
        print(f"📊 手動觸發結果: {force_result}")

        # 等待一下看是否處理完成
        await asyncio.sleep(1.0)

        if len(processed_batches) > 0:
            print("✅ 手動觸發成功，批次處理完成")
        else:
            print("❌ 手動觸發後仍未處理")

            stats = collector.stats
            print(f"🔍 收集器統計: {stats}")

            all_statuses = collector.get_all_batch_statuses()
            print(f"🔍 所有批次狀態: {all_statuses}")

            return False

    batch_result = processed_batches[0]
    expected_image_count = 5

    if batch_result["image_count"] != expected_image_count:
        print(
            f"❌ 批次圖片數量不正確: 期望 {expected_image_count}, 實際 {batch_result['image_count']}"
        )
        return False

    print(f"✅ 批次處理成功!")
    print(f"   - 用戶ID: {batch_result['user_id']}")
    print(f"   - 圖片數量: {batch_result['image_count']}")
    print(f"   - 處理批次數: {len(processed_batches)}")

    # 8. 檢查統計數據
    stats = collector.stats
    print(f"\n📊 收集器統計:")
    print(f"   - 總收集圖片數: {stats['total_images_collected']}")
    print(f"   - 總處理批次數: {stats['total_batches_processed']}")
    print(f"   - 平均批次大小: {stats['average_batch_size']:.1f}")

    # 9. 停止收集器
    await collector.stop()
    print("\n🛑 批次收集器已停止")

    return True


async def main():
    """主函數"""
    try:
        success = await test_batch_collector()

        if success:
            print("\n🎉 批次收集器修復測試成功!")
            print("✅ 媒體群組處理應該能正常工作了")
            return 0
        else:
            print("\n❌ 批次收集器修復測試失敗")
            return 1

    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
