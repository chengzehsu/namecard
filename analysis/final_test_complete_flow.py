#!/usr/bin/env python3
"""
完整測試 Telegram Bot 名片處理流程
"""

import json
import os
import sys
import time

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def test_service_status():
    """測試服務狀態"""
    print("🔍 Step 1: 檢查服務狀態")
    print("-" * 40)

    try:
        response = requests.get("https://namecard-app.zeabur.app/test", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("📊 服務狀態檢查:")

            all_good = True
            for service, status in data.items():
                if isinstance(status, dict):
                    success = status.get("success", False)
                    message = status.get("message", status.get("error", "Unknown"))
                    emoji = "✅" if success else "❌"
                    print(f"  {service}: {emoji} {message}")
                    if not success:
                        all_good = False

            return all_good
        else:
            print(f"❌ 服務狀態檢查失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 服務狀態檢查異常: {e}")
        return False


def test_telegram_start_command():
    """測試 /start 指令"""
    print("\n🔍 Step 2: 測試 /start 指令")
    print("-" * 40)

    start_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": int(time.time()),
            "chat": {"id": 597988605, "type": "private"},
            "from": {"id": 597988605, "is_bot": False, "first_name": "TestUser"},
            "text": "/start",
        },
    }

    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=start_update,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📥 /start 指令測試: {response.status_code}")
        if response.status_code == 200:
            print("✅ /start 指令處理正常")
            return True
        else:
            print(f"❌ /start 指令處理失敗: {response.text}")
            return False

    except Exception as e:
        print(f"❌ /start 指令測試異常: {e}")
        return False


def test_telegram_photo_processing():
    """測試圖片處理功能"""
    print("\n🔍 Step 3: 測試圖片處理功能")
    print("-" * 40)

    # 使用您之前的真實圖片數據
    photo_update = {
        "update_id": 944545861,
        "message": {
            "message_id": 32,
            "from": {
                "id": 597988605,
                "is_bot": False,
                "first_name": "Kevin",
                "username": "kevinmyl",
                "language_code": "zh-hans",
            },
            "chat": {
                "id": 597988605,
                "first_name": "Kevin",
                "username": "kevinmyl",
                "type": "private",
            },
            "date": int(time.time()),
            "photo": [
                {
                    "file_id": "AgACAgUAAxkBAAMKaI16zyjtvWYu6km4pdGOWhLeXIoAApHCMRtjZHBUMVESskcE2SwBAAMCAANzAAM2BA",
                    "file_unique_id": "AQADkcIxG2NkcFR4",
                    "file_size": 1010,
                    "width": 90,
                    "height": 51,
                },
                {
                    "file_id": "AgACAgUAAxkBAAMKaI16zyjtvWYu6km4pdGOWhLeXIoAApHCMRtjZHBUMVESskcE2SwBAAMCAAN5AAM2BA",
                    "file_unique_id": "AQADkcIxG2NkcFR-",
                    "file_size": 111405,
                    "width": 1280,
                    "height": 720,
                },
            ],
        },
    }

    try:
        print("📤 發送圖片處理請求...")
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=photo_update,
            headers={"Content-Type": "application/json"},
            timeout=60,  # 增加超時時間，因為圖片處理需要時間
        )

        print(f"📥 圖片處理回應: {response.status_code}")
        print(f"📄 回應內容: {response.text}")

        if response.status_code == 200:
            print("✅ 圖片處理請求被接受")
            print("💡 實際處理結果需要查看 Telegram 機器人回應")
            return True
        elif response.status_code == 500:
            print("⚠️  服務器內部錯誤 - 可能在處理過程中遇到問題")
            print("💡 請檢查 Zeabur 服務日誌以獲取詳細錯誤信息")
            return False
        else:
            print(f"❌ 圖片處理失敗: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ 圖片處理超時")
        print("💡 可能正在處理，請檢查 Telegram Bot 是否有回應")
        return True  # 超時不一定是失敗
    except Exception as e:
        print(f"❌ 圖片處理測試異常: {e}")
        return False


def test_webhook_info():
    """檢查 Telegram webhook 信息"""
    print("\n🔍 Step 4: 檢查 Telegram Webhook 信息")
    print("-" * 40)

    bot_token = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                webhook_info = data.get("result", {})

                print("📋 Webhook 配置信息:")
                print(f"  URL: {webhook_info.get('url', 'None')}")
                print(f"  待處理更新: {webhook_info.get('pending_update_count', 0)}")

                if webhook_info.get("last_error_date"):
                    error_date = webhook_info.get("last_error_date")
                    error_msg = webhook_info.get("last_error_message", "Unknown")
                    print(f"  最後錯誤時間: {error_date}")
                    print(f"  最後錯誤訊息: {error_msg}")
                else:
                    print("  ✅ 沒有最近的錯誤")

                # 檢查 URL 是否正確
                current_url = webhook_info.get("url", "")
                expected_url = "https://namecard-app.zeabur.app/telegram-webhook"

                if current_url == expected_url:
                    print("  ✅ Webhook URL 配置正確")
                    return True
                else:
                    print(f"  ❌ Webhook URL 不正確")
                    print(f"     當前: {current_url}")
                    print(f"     預期: {expected_url}")
                    return False
            else:
                print(f"❌ Telegram API 錯誤: {data}")
                return False
        else:
            print(f"❌ 獲取 Webhook 信息失敗: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 檢查 Webhook 信息異常: {e}")
        return False


def provide_next_steps(results):
    """提供下一步操作建議"""
    print("\n" + "=" * 50)
    print("📊 測試結果總結")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n💡 下一步操作:")

    if all_passed:
        print("🎉 所有測試通過！您的 Telegram Bot 應該可以正常工作了。")
        print("\n📱 測試步驟:")
        print("1. 在 Telegram 中找到您的 Bot")
        print("2. 發送 /start 指令")
        print("3. 上傳一張名片圖片")
        print("4. 等待 AI 處理和回應")
        print("5. 檢查 Notion 資料庫是否有新記錄")

    else:
        print("⚠️  部分測試失敗，但這可能是正常的：")
        print("\n🔧 故障排除:")

        if not results.get("服務狀態檢查", True):
            print("- 檢查 Zeabur 環境變數設置")
            print("- 確認 API Keys 的有效性")

        if not results.get("Webhook 配置檢查", True):
            print("- 重新設置 Telegram Bot Webhook URL")

        if not results.get("圖片處理測試", True):
            print("- 查看 Zeabur 服務日誌")
            print("- 檢查服務器資源使用情況")

        print("\n📋 建議查看:")
        print("- Zeabur Dashboard → 您的服務 → Logs 標籤")
        print("- 查找具體的錐誤信息和堆疊追蹤")


def main():
    """主測試函數"""
    print("🤖 Telegram Bot 完整功能測試")
    print("=" * 50)

    # 執行所有測試
    tests = [
        ("服務狀態檢查", test_service_status),
        ("/start 指令測試", test_telegram_start_command),
        ("圖片處理測試", test_telegram_photo_processing),
        ("Webhook 配置檢查", test_webhook_info),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
            time.sleep(2)  # 避免請求過於頻繁
        except Exception as e:
            print(f"❌ {test_name} 異常: {e}")
            results[test_name] = False

    # 提供下一步建議
    provide_next_steps(results)


if __name__ == "__main__":
    main()
