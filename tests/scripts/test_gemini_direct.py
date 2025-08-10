#!/usr/bin/env python3
"""
直接測試 Gemini AI 調用
"""

import base64
import os
import sys

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def test_gemini_api_direct():
    """直接使用 Gemini API 測試"""
    print("🧪 直接測試 Gemini API...")

    # 測試配置
    from simple_config import Config

    print(f"📋 配置檢查:")
    print(f"  GOOGLE_API_KEY: {'已設置' if Config.GOOGLE_API_KEY else '未設置'}")
    print(
        f"  GOOGLE_API_KEY_FALLBACK: {'已設置' if Config.GOOGLE_API_KEY_FALLBACK else '未設置'}"
    )
    print(f"  GEMINI_MODEL: {Config.GEMINI_MODEL}")

    if not Config.GOOGLE_API_KEY:
        print("❌ 沒有 GOOGLE_API_KEY，無法測試")
        return False

    # 創建一個簡單的測試圖片 (base64 編碼的小 PNG)
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg=="

    try:
        # 使用 Gemini REST API 直接測試
        api_key = Config.GOOGLE_API_KEY
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "這是一張測試圖片。請告訴我你能看到什麼？"},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": test_image_base64,
                            }
                        },
                    ]
                }
            ]
        }

        print("📤 發送請求到 Gemini API...")
        response = requests.post(url, json=payload, timeout=30)

        print(f"📥 回應狀態: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Gemini 回應: {text[:100]}...")
                return True
            else:
                print(f"❌ Gemini 回應格式異常: {result}")
                return False
        else:
            print(f"❌ API 調用失敗: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 直接 API 測試失敗: {e}")
        return False


def test_name_card_processor():
    """測試名片處理器初始化和調用"""
    print("\n🔧 測試名片處理器...")

    try:
        from src.namecard.infrastructure.ai.card_processor import NameCardProcessor

        print("📦 初始化名片處理器...")
        processor = NameCardProcessor()
        print("✅ 名片處理器初始化成功")

        # 創建一個測試圖片 bytes
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg=="
        test_image_bytes = base64.b64decode(test_image_base64)

        print("🔍 測試圖片處理...")
        result = processor.extract_multi_card_info(test_image_bytes)

        if "error" in result:
            print(f"❌ 圖片處理失敗: {result['error']}")
            return False
        else:
            print(f"✅ 圖片處理成功: {result}")
            return True

    except Exception as e:
        print(f"❌ 名片處理器測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_telegram_photo_simulation():
    """模擬 Telegram 圖片處理流程"""
    print("\n📱 模擬 Telegram 圖片處理流程...")

    # 創建一個模擬的 webhook 請求
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg=="

    # 模擬 Telegram photo message
    mock_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": 1641024000,
            "chat": {"id": 123456789, "type": "private"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "photo": [
                {
                    "file_id": "test_file_id",
                    "file_unique_id": "test_unique",
                    "width": 1,
                    "height": 1,
                    "file_size": 100,
                }
            ],
        },
    }

    try:
        print("📤 發送模擬圖片訊息到 webhook...")
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=mock_update,
            headers={"Content-Type": "application/json"},
            timeout=60,  # 增加超時時間觀察處理過程
        )

        print(f"📥 Webhook 回應: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ Webhook 接受了圖片訊息")
            return True
        else:
            print(f"❌ Webhook 處理失敗: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Webhook 處理超時 - 這說明處理過程中可能卡住了")
        return False
    except Exception as e:
        print(f"❌ Webhook 測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔍 Gemini AI 調用診斷測試")
    print("=" * 50)

    # 測試順序
    tests = [
        ("Gemini API 直接調用", test_gemini_api_direct),
        ("名片處理器測試", test_name_card_processor),
        ("Telegram 圖片流程模擬", test_telegram_photo_simulation),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} 異常: {e}")
            results[test_name] = False

    print("\n" + "=" * 50)
    print("📊 測試結果摘要:")

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n💡 診斷結論:")
    if all_passed:
        print("🎉 所有測試通過，Gemini AI 調用正常")
    else:
        if not results.get("Gemini API 直接調用", False):
            print("🚨 Gemini API 配置有問題，請檢查 API Key")
        elif not results.get("名片處理器測試", False):
            print("🚨 名片處理器有問題，請檢查代碼邏輯")
        elif not results.get("Telegram 圖片流程模擬", False):
            print("🚨 Telegram 圖片處理流程有問題，可能是圖片下載或異步處理")


if __name__ == "__main__":
    main()
