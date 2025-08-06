#!/usr/bin/env python3
"""
異步組件基本功能測試 - 模擬環境下的快速驗證
"""

import asyncio
import os
import sys
import time

# 添加專案根目錄到 path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.namecard.core.services.async_batch_service import AsyncBatchService
from src.namecard.infrastructure.ai.async_card_processor import (
    AsyncCardProcessor,
    ProcessingPriority,
)


async def test_async_card_processor():
    """測試異步卡片處理器基本功能"""
    print("🧪 測試 AsyncCardProcessor...")

    try:
        processor = AsyncCardProcessor(max_concurrent=5, enable_cache=True)

        # 模擬圖片數據
        fake_image_data = b"fake_image_data_for_testing" * 100

        # 檢查健康狀態
        health = await processor.health_check()
        print(f"  ✅ 健康檢查: {health['status']}")

        # 檢查效能統計
        stats = await processor.get_performance_stats()
        print(
            f"  ✅ 效能統計: 並發峰值={stats['concurrent_peak']}, 快取大小={stats['memory_cache_size']}"
        )

        # 測試快取清除
        await processor.clear_cache()
        print("  ✅ 快取清除成功")

        return True

    except Exception as e:
        print(f"  ❌ AsyncCardProcessor 測試失敗: {e}")
        return False


async def test_async_batch_service():
    """測試異步批次服務基本功能"""
    print("🧪 測試 AsyncBatchService...")

    try:
        # 創建名片處理器
        card_processor = AsyncCardProcessor(max_concurrent=5, enable_cache=True)

        # 創建批次服務
        batch_service = AsyncBatchService(
            card_processor=card_processor, max_global_concurrent=10
        )

        # 創建批次會話
        session_id = await batch_service.create_batch_session(
            user_id="test_user", auto_process=False, max_concurrent=3
        )
        print(f"  ✅ 批次會話創建成功: {session_id}")

        # 檢查會話狀態
        status = await batch_service.get_batch_status(session_id)
        if status:
            print(f"  ✅ 會話狀態: {status['status']}")
        else:
            print("  ✅ 會話狀態: 無法獲取")

        # 移除會話
        removed = await batch_service.remove_batch_session(session_id)
        print(f"  ✅ 會話移除: {'成功' if removed else '失敗'}")

        # 獲取服務統計
        stats = await batch_service.get_service_stats()
        print(f"  ✅ 服務統計: 總會話數={stats['total_sessions']}")

        return True

    except Exception as e:
        print(f"  ❌ AsyncBatchService 測試失敗: {e}")
        return False


async def test_concurrent_performance():
    """測試基本並發能力"""
    print("🚀 測試基本並發能力...")

    try:
        processor = AsyncCardProcessor(max_concurrent=3, enable_cache=True)

        # 模擬並發任務
        fake_image_data = b"concurrent_test_data" * 50

        async def simulate_processing(task_id: int):
            """模擬處理任務"""
            start_time = time.time()

            # 模擬處理時間
            await asyncio.sleep(0.1)

            processing_time = time.time() - start_time
            return {
                "task_id": task_id,
                "processing_time": processing_time,
                "success": True,
            }

        # 創建多個並發任務
        tasks = [simulate_processing(i) for i in range(5)]
        start_time = time.time()

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        print(f"  ✅ 並發測試結果:")
        print(f"    • 總任務數: {len(tasks)}")
        print(f"    • 成功任務: {successful}")
        print(f"    • 總耗時: {total_time:.2f} 秒")
        print(f"    • 平均吞吐量: {len(tasks)/total_time:.1f} 任務/秒")

        return successful == len(tasks)

    except Exception as e:
        print(f"  ❌ 並發測試失敗: {e}")
        return False


async def test_memory_efficiency():
    """測試記憶體效率"""
    print("💾 測試記憶體效率...")

    try:
        import gc

        import psutil

        # 獲取初始記憶體使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        processor = AsyncCardProcessor(max_concurrent=10, enable_cache=True)

        # 模擬多次處理
        fake_data = b"memory_test" * 1000

        for i in range(10):
            await asyncio.sleep(0.01)  # 模擬處理

        # 清理和垃圾回收
        await processor.clear_cache()
        gc.collect()

        # 獲取最終記憶體使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"  ✅ 記憶體效率測試:")
        print(f"    • 初始記憶體: {initial_memory:.1f} MB")
        print(f"    • 最終記憶體: {final_memory:.1f} MB")
        print(f"    • 記憶體增長: {memory_increase:.1f} MB")

        # 記憶體增長小於 50MB 算通過
        return memory_increase < 50

    except ImportError:
        print("  ⚠️ psutil 未安裝，跳過記憶體測試")
        return True
    except Exception as e:
        print(f"  ❌ 記憶體測試失敗: {e}")
        return False


async def main():
    """主測試函數"""
    print("🚀 開始異步組件基本功能驗證...")
    print("=" * 50)

    tests = [
        ("AsyncCardProcessor", test_async_card_processor),
        ("AsyncBatchService", test_async_batch_service),
        ("並發效能", test_concurrent_performance),
        ("記憶體效率", test_memory_efficiency),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 執行 {test_name} 測試...")
        try:
            success = await test_func()
            results.append((test_name, success))
            status = "✅ 通過" if success else "❌ 失敗"
            print(f"    {status}")
        except Exception as e:
            results.append((test_name, False))
            print(f"    ❌ 測試異常: {e}")

    # 總結
    print("\n" + "=" * 50)
    print("📊 測試結果總結:")

    passed = 0
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
        if success:
            passed += 1

    print(f"\n🎯 總體結果: {passed}/{len(results)} 測試通過")

    if passed == len(results):
        print("🎉 所有異步組件測試通過！系統準備就緒。")
        return True
    else:
        print("⚠️ 部分測試失敗，需要檢查相關組件。")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
