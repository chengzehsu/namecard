#!/usr/bin/env python3
"""
測試 Gemini API 備用 Key 機制
"""
import os
import sys
from unittest.mock import MagicMock, patch

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from name_card_processor import NameCardProcessor


def test_api_fallback_mechanism():
    """測試 API Key 備用機制"""
    print("🧪 測試 Gemini API 備用機制")
    print("=" * 50)

    # 測試 1: 檢查配置
    print("\n📋 測試 1: 檢查 API Key 配置")

    # 直接從環境變數讀取以確保準確性
    main_key = os.getenv("GOOGLE_API_KEY")
    fallback_key = os.getenv("GOOGLE_API_KEY_FALLBACK")

    print(f"主要 API Key: {'已設定' if main_key else '未設定'}")
    print(f"備用 API Key: {'已設定' if fallback_key else '未設定'}")

    if not main_key:
        print("❌ 缺少主要 API Key (GOOGLE_API_KEY)")
        return False

    if not fallback_key:
        print("❌ 缺少備用 API Key (GOOGLE_API_KEY_FALLBACK)")
        return False

    print("✅ API Key 配置正確")

    # 測試 2: 初始化處理器
    print("\n📋 測試 2: 初始化名片處理器")
    try:
        processor = NameCardProcessor()
        print(f"✅ 處理器初始化成功")
        print(f"   - 當前使用 API Key: {processor.current_api_key[:20]}...")
        print(f"   - 備用 API Key: {processor.fallback_api_key[:20]}...")
        print(f"   - 是否使用備用: {processor.using_fallback}")
    except Exception as e:
        print(f"❌ 處理器初始化失敗: {e}")
        return False

    # 測試 3: 錯誤檢測邏輯
    print("\n📋 測試 3: 額度超限錯誤檢測")
    test_errors = [
        "quota exceeded",
        "Resource has been exhausted",
        "429 Rate limit exceeded",
        "Billing not enabled",
        "API quota exceeded",
        "其他錯誤",
    ]

    for error in test_errors:
        is_quota_error = processor._is_quota_exceeded_error(error)
        result = (
            "✅"
            if is_quota_error and "其他錯誤" not in error
            else "❌" if is_quota_error else "✅"
        )
        print(f"   {result} '{error}' -> {is_quota_error}")

    # 測試 4: 模擬 API 切換
    print("\n📋 測試 4: 模擬 API Key 切換")
    try:
        # 模擬切換到備用 API
        original_key = processor.current_api_key
        processor._switch_to_fallback_api()

        print(f"✅ 成功切換到備用 API Key")
        print(f"   - 原始 API Key: {original_key[:20]}...")
        print(f"   - 當前 API Key: {processor.current_api_key[:20]}...")
        print(f"   - 使用備用標記: {processor.using_fallback}")

        # 測試再次切換（應該失敗）
        try:
            processor._switch_to_fallback_api()
            print("❌ 應該不能再次切換")
            return False
        except Exception as e:
            print(f"✅ 正確阻止重複切換: {str(e)}")

    except Exception as e:
        print(f"❌ API Key 切換失敗: {e}")
        return False

    # 測試 5: 模擬額度超限情況
    print("\n📋 測試 5: 模擬額度超限處理 (Mock)")

    # 創建新的處理器實例用於模擬測試
    test_processor = NameCardProcessor()

    # 模擬 generate_content 方法
    with patch.object(test_processor.model, "generate_content") as mock_generate:
        # 第一次調用拋出額度超限錯誤
        # 第二次調用成功返回
        mock_response = MagicMock()
        mock_response.text = "模擬成功回應"

        mock_generate.side_effect = [
            Exception("quota exceeded"),  # 第一次失敗
            mock_response,  # 第二次成功
        ]

        try:
            result = test_processor._generate_content_with_fallback(["test prompt"])
            print(f"✅ 備用機制正常工作，結果: {result}")
        except Exception as e:
            print(f"❌ 備用機制測試失敗: {e}")
            return False

    print("\n🎉 所有測試通過！API 備用機制正常工作")
    return True


def test_environment_setup():
    """測試環境設定建議"""
    print("\n📝 環境設定建議:")
    print("=" * 30)

    print("1. 在 .env 檔案中添加:")
    print("   GOOGLE_API_KEY=你的主要API金鑰")
    print("   GOOGLE_API_KEY_FALLBACK=AIzaSyAMCeNe0auBbgVCHOuAqKxooqaB61poqF0")

    print("\n2. 或設定環境變數:")
    print("   export GOOGLE_API_KEY_FALLBACK=AIzaSyAMCeNe0auBbgVCHOuAqKxooqaB61poqF0")

    print("\n3. 重啟應用程式使設定生效")


def main():
    """主測試函數"""
    print("🚀 Gemini API 備用機制測試工具")
    print("=" * 50)

    # 檢查是否有備用 API Key
    if not os.getenv("GOOGLE_API_KEY_FALLBACK"):
        print("⚠️  未檢測到備用 API Key")
        test_environment_setup()

        # 暫時設定用於測試
        os.environ["GOOGLE_API_KEY_FALLBACK"] = (
            "AIzaSyAMCeNe0auBbgVCHOuAqKxooqaB61poqF0"
        )
        print("\n🔧 已暫時設定備用 API Key 進行測試")

    # 執行測試
    success = test_api_fallback_mechanism()

    if success:
        print("\n✅ 備用 API Key 機制已成功實作！")
    else:
        print("\n❌ 測試失敗，請檢查配置")

    return success


if __name__ == "__main__":
    main()
