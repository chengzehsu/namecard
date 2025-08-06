#!/usr/bin/env python3
"""
測試 Telegram Bot 修復效果
"""

import os
import sys
import time

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def test_webhook_endpoint():
    """測試 webhook 端點"""
    print("🧪 測試 Telegram Webhook 端點...")

    # 模擬一個簡單的文字訊息
    mock_text_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": 1641024000,
            "chat": {"id": 123456789, "type": "private"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "text": "/start",
        },
    }

    try:
        print("📤 發送測試 /start 指令...")
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=mock_text_update,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📥 回應狀態: {response.status_code}")
        print(f"📥 回應內容: {response.text}")

        if response.status_code == 200:
            print("✅ Webhook 基本功能正常")
            return True
        else:
            print(f"❌ Webhook 回應異常: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Webhook 處理超時 - 可能處理中")
        return False
    except Exception as e:
        print(f"❌ Webhook 測試失敗: {e}")
        return False


def test_photo_webhook():
    """測試圖片 webhook"""
    print("\n🧪 測試圖片處理 Webhook...")

    # 模擬圖片訊息
    mock_photo_update = {
        "update_id": 999998,
        "message": {
            "message_id": 2,
            "date": 1641024000,
            "chat": {"id": 123456789, "type": "private"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "photo": [
                {
                    "file_id": "test_file_id",
                    "file_unique_id": "test_unique",
                    "width": 100,
                    "height": 100,
                    "file_size": 1000,
                }
            ],
        },
    }

    try:
        print("📤 發送測試圖片訊息...")
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=mock_photo_update,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📥 回應狀態: {response.status_code}")
        print(f"📥 回應內容: {response.text}")

        if response.status_code == 200:
            print("✅ 圖片 Webhook 基本接收正常")
            print("💡 具體處理結果需要查看 Zeabur 日誌")
            return True
        else:
            print(f"❌ 圖片 Webhook 回應異常: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 圖片 Webhook 測試失敗: {e}")
        return False


def test_health_check():
    """測試健康檢查"""
    print("\n🧪 測試健康檢查端點...")

    try:
        response = requests.get("https://namecard-app.zeabur.app/health", timeout=10)

        print(f"📥 健康檢查狀態: {response.status_code}")
        print(f"📥 健康檢查回應: {response.text}")

        if response.status_code == 200:
            print("✅ 健康檢查正常")
            return True
        else:
            print(f"❌ 健康檢查異常: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return False


def test_service_status():
    """測試服務狀態"""
    print("\n🧪 測試服務狀態端點...")

    try:
        response = requests.get("https://namecard-app.zeabur.app/test", timeout=15)

        print(f"📥 服務狀態: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("📋 服務狀態詳情:")
            for service, status in data.items():
                if isinstance(status, dict):
                    success = status.get("success", False)
                    message = status.get("message", status.get("error", "Unknown"))
                    print(f"  {service}: {'✅' if success else '❌'} {message}")
                else:
                    print(f"  {service}: {status}")
            return True
        else:
            print(f"❌ 服務狀態檢查異常: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 服務狀態檢查失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔍 Telegram Bot 修復效果測試")
    print("=" * 50)

    # 測試順序
    tests = [
        ("健康檢查", test_health_check),
        ("服務狀態", test_service_status),
        ("文字 Webhook", test_webhook_endpoint),
        ("圖片 Webhook", test_photo_webhook),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            results[test_name] = test_func()
            time.sleep(2)  # 避免請求過於頻繁
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

    print(f"\n💡 總體結果: {'🎉 所有測試通過' if all_passed else '⚠️ 部分測試失敗'}")

    if not all_passed:
        print("\n🔧 故障排除建議:")
        print("1. 檢查 Zeabur Dashboard 中的環境變數設置")
        print("2. 查看 Zeabur 服務日誌了解詳細錯誤")
        print("3. 確認服務已重新部署並使用最新代碼")
        print("4. 驗證 API Keys 的有效性")


if __name__ == "__main__":
    main()
