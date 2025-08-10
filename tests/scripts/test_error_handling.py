#!/usr/bin/env python3
"""
測試名片處理器的錯誤處理和重試機制
"""
import os
import sys
import traceback

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_config import Config
from src.namecard.infrastructure.ai.card_processor import NameCardProcessor


def test_api_configuration():
    """測試 API 配置"""
    print("🔧 檢查 API 配置...")

    # 顯示配置狀態
    Config.show_config()

    # 檢查主要 API Key
    if not Config.GOOGLE_API_KEY:
        print("❌ 主要 GOOGLE_API_KEY 未設置")
        return False

    # 檢查備用 API Key（可選）
    if Config.GOOGLE_API_KEY_FALLBACK:
        print("✅ 備用 API Key 已設置")
    else:
        print("⚠️ 備用 API Key 未設置 (可選)")

    return True


def test_processor_initialization():
    """測試處理器初始化"""
    print("\n🤖 測試名片處理器初始化...")

    try:
        processor = NameCardProcessor()
        print("✅ 名片處理器初始化成功")
        print(f"   - 當前使用的 API Key: {'主要' if not processor.using_fallback else '備用'}")
        print(f"   - 備用 API Key 可用: {'是' if processor.fallback_api_key else '否'}")
        return processor
    except Exception as e:
        print(f"❌ 名片處理器初始化失敗: {e}")
        return None


def test_error_detection():
    """測試錯誤檢測邏輯"""
    print("\n🔍 測試錯誤檢測邏輯...")

    processor = NameCardProcessor()

    # 測試額度超限錯誤檢測
    quota_errors = [
        "quota exceeded",
        "Resource has been exhausted (e.g. check quota).",
        "429 Too Many Requests",
        "Rate limit exceeded",
    ]

    for error in quota_errors:
        result = processor._is_quota_exceeded_error(error)
        print(f"   額度錯誤 '{error[:30]}...': {'✅ 檢測到' if result else '❌ 未檢測到'}")

    # 測試暫時性錯誤檢測
    transient_errors = [
        "500 An internal error has occurred",
        "502 Bad Gateway",
        "503 Service Unavailable",
        "Network timeout",
        "Connection error",
    ]

    for error in transient_errors:
        result = processor._is_transient_error(error)
        print(f"   暫時錯誤 '{error[:30]}...': {'✅ 檢測到' if result else '❌ 未檢測到'}")


def create_test_image():
    """創建測試圖片數據"""
    import io

    from PIL import Image

    # 創建簡單的測試圖片
    img = Image.new("RGB", (300, 200), color="white")

    # 轉換為 bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def test_api_call_with_retry():
    """測試 API 調用和重試機制"""
    print("\n🚀 測試 API 調用和重試機制...")

    processor = NameCardProcessor()

    # 創建測試圖片
    test_image = create_test_image()

    try:
        print("   正在調用 Gemini API...")
        result = processor.extract_multi_card_info(test_image)

        if "error" in result:
            print(f"❌ API 調用失敗: {result['error']}")
            return False
        else:
            print("✅ API 調用成功")
            print(f"   - 檢測到 {result.get('card_count', 0)} 張名片")
            print(f"   - 整体品質: {result.get('overall_quality', 'unknown')}")
            return True

    except Exception as e:
        print(f"❌ API 調用異常: {e}")
        print(f"   錯誤類型: {type(e).__name__}")

        # 檢查錯誤類型
        error_str = str(e)
        if processor._is_quota_exceeded_error(error_str):
            print("   🔍 這是額度超限錯誤")
        elif processor._is_transient_error(error_str):
            print("   🔍 這是暫時性錯誤，會自動重試")
        else:
            print("   🔍 這是其他類型錯誤")

        return False


def main():
    """主測試函數"""
    print("🧪 名片處理器錯誤處理測試")
    print("=" * 50)

    try:
        # 測試 1: API 配置
        if not test_api_configuration():
            print("\n❌ API 配置測試失敗，請檢查環境變數")
            return False

        # 測試 2: 處理器初始化
        processor = test_processor_initialization()
        if not processor:
            print("\n❌ 處理器初始化測試失敗")
            return False

        # 測試 3: 錯誤檢測邏輯
        test_error_detection()

        # 測試 4: API 調用和重試
        success = test_api_call_with_retry()

        print("\n" + "=" * 50)
        if success:
            print("🎉 所有測試通過！錯誤處理機制正常工作")
        else:
            print("⚠️ 部分測試失敗，請檢查 API 狀態和配置")

        return success

    except Exception as e:
        print(f"\n💥 測試過程中發生意外錯誤: {e}")
        print("詳細錯誤信息:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
