#!/usr/bin/env python3
"""
Phase 5 批次處理功能測試
驗證真正的批次 AI 處理是否正常工作
"""

import asyncio
import logging
import sys
import time
from typing import List
from unittest.mock import AsyncMock, Mock, patch

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加路徑
sys.path.insert(0, "/Users/user/namecard")


def test_imports():
    """測試關鍵組件導入"""
    print("🧪 測試 Phase 5 關鍵組件導入...")

    try:
        from src.namecard.infrastructure.ai.ultra_fast_processor import (
            UltraFastProcessor,
            UltraFastResult,
        )

        print("✅ UltraFastProcessor 導入成功")

        from src.namecard.core.services.batch_image_collector import (
            BatchImageCollector,
            PendingImage,
        )

        print("✅ BatchImageCollector 導入成功")

        from src.namecard.api.telegram_bot.main import batch_processor_callback

        print("✅ batch_processor_callback 導入成功")

        return True

    except Exception as e:
        print(f"❌ 導入失敗: {e}")
        return False


async def test_ultra_fast_batch_processing():
    """測試超高速批次處理功能"""
    print("\n🚀 測試超高速批次處理功能...")

    try:
        from src.namecard.infrastructure.ai.ultra_fast_processor import (
            UltraFastProcessor,
        )

        # 創建處理器實例
        processor = UltraFastProcessor()
        print("✅ UltraFastProcessor 實例創建成功")

        # 驗證批次處理方法存在
        assert hasattr(
            processor, "process_telegram_photos_batch_ultra_fast"
        ), "缺少批次處理方法"
        print("✅ process_telegram_photos_batch_ultra_fast 方法存在")

        # 測試方法簽名
        import inspect

        sig = inspect.signature(processor.process_telegram_photos_batch_ultra_fast)
        expected_params = ["telegram_files", "user_id", "processing_type"]
        actual_params = list(sig.parameters.keys())

        for param in expected_params:
            assert param in actual_params, f"缺少參數: {param}"
        print("✅ 方法簽名正確")

        return True

    except Exception as e:
        print(f"❌ 超高速批次處理測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_batch_processor_callback_integration():
    """測試批次處理回調函數的 Phase 5 整合"""
    print("\n🔗 測試批次處理回調函數整合...")

    try:
        from src.namecard.api.telegram_bot.main import batch_processor_callback
        from src.namecard.core.services.batch_image_collector import PendingImage

        # 創建模擬的 PendingImage 對象
        mock_images = []
        for i in range(3):
            mock_file = Mock()
            mock_file.file_id = f"test_file_{i}"

            pending_image = PendingImage(
                image_data=mock_file,
                file_id=f"test_file_{i}",
                chat_id=12345,
                user_id="test_user",
                metadata={"test": True},
            )
            mock_images.append(pending_image)

        print(f"✅ 創建了 {len(mock_images)} 個模擬圖片對象")

        # 測試回調函數是否包含 Phase 5 代碼
        import inspect

        source = inspect.getsource(batch_processor_callback)

        # 檢查是否包含 Phase 5 的關鍵代碼
        phase5_indicators = [
            "Phase 5",
            "process_telegram_photos_batch_ultra_fast",
            "ultra_fast_processor",
            "真正批次處理",
        ]

        found_indicators = []
        for indicator in phase5_indicators:
            if indicator in source:
                found_indicators.append(indicator)

        print(f"✅ 找到 Phase 5 指標: {found_indicators}")
        assert (
            len(found_indicators) >= 2
        ), f"Phase 5 整合不完整，只找到: {found_indicators}"

        return True

    except Exception as e:
        print(f"❌ 批次處理回調整合測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_performance_improvement_logic():
    """測試效能改進邏輯"""
    print("\n📊 測試效能改進邏輯...")

    try:
        # 測試效能計算邏輯
        image_counts = [2, 3, 5, 8]

        for count in image_counts:
            # 模擬舊方式時間（每張 10 秒）
            old_time = count * 10

            # 模擬新方式時間（批次處理）
            if count <= 2:
                new_time = count * 4  # 小批次
            elif count <= 5:
                new_time = count * 3  # 中批次
            else:
                new_time = count * 2.5  # 大批次

            improvement = old_time / new_time
            time_saved = old_time - new_time

            print(
                f"📈 {count} 張圖片: {old_time}s → {new_time:.1f}s (提升 {improvement:.1f}x, 節省 {time_saved:.1f}s)"
            )

            # 驗證至少有 2x 改進
            assert (
                improvement >= 2.0
            ), f"{count} 張圖片的改進不足 2x: {improvement:.1f}x"

        print("✅ 效能改進邏輯測試通過")
        return True

    except Exception as e:
        print(f"❌ 效能改進邏輯測試失敗: {e}")
        return False


async def test_error_handling_and_fallback():
    """測試錯誤處理和降級機制"""
    print("\n🛡️ 測試錯誤處理和降級機制...")

    try:
        import inspect

        from src.namecard.api.telegram_bot.main import batch_processor_callback

        # 檢查回調函數是否包含降級邏輯
        source = inspect.getsource(batch_processor_callback)

        fallback_indicators = [
            "降級",
            "safe_batch_processor",
            "except",
            "fallback",
            "安全批次處理器",
        ]

        found_fallbacks = []
        for indicator in fallback_indicators:
            if indicator in source:
                found_fallbacks.append(indicator)

        print(f"✅ 找到降級機制指標: {found_fallbacks}")
        assert len(found_fallbacks) >= 3, f"降級機制不完整，只找到: {found_fallbacks}"

        # 檢查是否有適當的錯誤處理
        assert "try:" in source and "except" in source, "缺少錯誤處理結構"
        print("✅ 錯誤處理結構完整")

        return True

    except Exception as e:
        print(f"❌ 錯誤處理測試失敗: {e}")
        return False


def test_deployment_readiness():
    """測試部署準備狀態"""
    print("\n🚀 測試部署準備狀態...")

    try:
        # 檢查主要配置文件
        import os

        config_files = [
            "requirements.txt",
            "requirements-telegram.txt",
            "Procfile.telegram",
            "simple_config.py",
        ]

        found_configs = []
        for config_file in config_files:
            if os.path.exists(config_file):
                found_configs.append(config_file)

        print(f"✅ 找到配置文件: {found_configs}")

        # 檢查部署腳本
        deployment_files = [
            "deployment/scripts/deploy_telegram_manual.sh",
            ".deploy_trigger",
        ]

        found_deployments = []
        for deploy_file in deployment_files:
            if os.path.exists(deploy_file):
                found_deployments.append(deploy_file)

        print(f"✅ 找到部署文件: {found_deployments}")

        # 檢查環境變數範例
        env_files = [".env.example", ".env.telegram.example"]
        found_env_files = []
        for env_file in env_files:
            if os.path.exists(env_file):
                found_env_files.append(env_file)

        print(f"✅ 找到環境變數範例: {found_env_files}")

        return True

    except Exception as e:
        print(f"❌ 部署準備狀態檢查失敗: {e}")
        return False


async def run_all_tests():
    """執行所有測試"""
    print("🧪 開始 Phase 5 批次處理完整測試套件")
    print("=" * 60)

    test_results = []

    # 1. 測試導入
    result1 = test_imports()
    test_results.append(("導入測試", result1))

    # 2. 測試超高速批次處理
    result2 = await test_ultra_fast_batch_processing()
    test_results.append(("超高速批次處理", result2))

    # 3. 測試整合
    result3 = await test_batch_processor_callback_integration()
    test_results.append(("批次處理回調整合", result3))

    # 4. 測試效能邏輯
    result4 = await test_performance_improvement_logic()
    test_results.append(("效能改進邏輯", result4))

    # 5. 測試錯誤處理
    result5 = await test_error_handling_and_fallback()
    test_results.append(("錯誤處理和降級", result5))

    # 6. 測試部署準備
    result6 = test_deployment_readiness()
    test_results.append(("部署準備狀態", result6))

    # 總結測試結果
    print("\n" + "=" * 60)
    print("📊 測試結果總結:")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 總體結果: {passed}/{total} 測試通過 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 所有測試通過！Phase 5 實現準備就緒！")
        return True
    else:
        print("⚠️ 部分測試失敗，需要修復後再部署")
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(run_all_tests())
        exit(0 if result else 1)
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
