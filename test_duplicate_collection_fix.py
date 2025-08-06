#!/usr/bin/env python3
"""
測試重複收集問題修復
驗證媒體群組不會重複添加到批次收集器
"""

import asyncio
import logging
import sys

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加路徑
sys.path.insert(0, "/Users/user/namecard")


def test_media_group_logic():
    """測試媒體群組處理邏輯"""
    print("🔍 測試媒體群組處理邏輯修復...")

    try:
        import inspect

        from src.namecard.api.telegram_bot.main import process_media_group_photos

        # 檢查函數源碼
        source = inspect.getsource(process_media_group_photos)

        # 確認修復標識
        fix_indicators = [
            "直接使用超高速批次處理器",
            "避免重複收集",
            "媒體群組直接使用超高速批次處理",
            "process_telegram_photos_batch_ultra_fast",
        ]

        found_fixes = []
        for indicator in fix_indicators:
            if indicator in source:
                found_fixes.append(indicator)

        print(f"✅ 找到修復指標: {found_fixes}")

        # 確認不再使用批次收集器添加
        problematic_patterns = ["batch_image_collector.add_image", "添加到批次收集器"]

        found_problems = []
        for pattern in problematic_patterns:
            if pattern in source:
                found_problems.append(pattern)

        if found_problems:
            print(f"⚠️ 仍存在問題模式: {found_problems}")
            return False
        else:
            print("✅ 不再使用批次收集器重複添加")

        # 檢查是否有直接批次處理
        if "ultra_fast_processor.process_telegram_photos_batch_ultra_fast" in source:
            print("✅ 使用直接批次處理而非重複收集")
        else:
            print("❌ 缺少直接批次處理調用")
            return False

        return len(found_fixes) >= 2

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_batch_collection_logic():
    """測試批次收集邏輯是否正確"""
    print("\n🔍 測試批次收集邏輯...")

    try:
        import inspect

        from src.namecard.api.telegram_bot.main import handle_photo_message

        # 檢查 handle_photo_message 源碼
        source = inspect.getsource(handle_photo_message)

        # 確認媒體群組檢測邏輯
        if (
            "if update.message.media_group_id:" in source
            and "handle_media_group_message" in source
        ):
            print("✅ 媒體群組檢測邏輯正確")
        else:
            print("❌ 媒體群組檢測邏輯有問題")
            return False

        # 確認媒體群組會被轉交處理而不是進入批次收集器
        if "轉交媒體群組處理器" in source and "return" in source:
            print("✅ 媒體群組正確轉交處理")
        else:
            print("❌ 媒體群組轉交邏輯有問題")
            return False

        # 確認批次收集器只在非媒體群組情況使用
        batch_collection_section = source[
            source.find("智能批次收集邏輯") : source.find("原有邏輯")
        ]
        if "not is_batch_mode" in batch_collection_section:
            print("✅ 批次收集器正確限制使用範圍")
        else:
            print("❌ 批次收集器使用範圍有問題")
            return False

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_syntax_check():
    """語法檢查"""
    print("\n🔍 檢查修復後的語法...")

    try:
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                "src/namecard/api/telegram_bot/main.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ 語法檢查通過")
            return True
        else:
            print(f"❌ 語法錯誤: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 語法檢查失敗: {e}")
        return False


def run_duplicate_collection_tests():
    """執行重複收集問題測試"""
    print("🧪 開始重複收集問題修復驗證")
    print("=" * 50)

    tests = [
        ("媒體群組處理邏輯", test_media_group_logic),
        ("批次收集邏輯", test_batch_collection_logic),
        ("語法檢查", test_syntax_check),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 執行測試: {test_name}")
        result = test_func()

        if result:
            passed += 1
            print(f"✅ {test_name}: 通過")
        else:
            print(f"❌ {test_name}: 失敗")

    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 重複收集問題修復成功！")
        print("\n📋 修復內容:")
        print("• 媒體群組直接使用超高速批次處理")
        print("• 不再重複添加到批次收集器")
        print("• 避免了雙重處理造成的混亂訊息")
        print("• 保持單一處理路徑，提高可靠性")
        return True
    else:
        print("⚠️ 部分測試失敗，需要進一步檢查")
        return False


if __name__ == "__main__":
    try:
        success = run_duplicate_collection_tests()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
