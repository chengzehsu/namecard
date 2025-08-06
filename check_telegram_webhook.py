#!/usr/bin/env python3
"""
檢查和修復 Telegram Bot Webhook 設置
"""

import json
import os
import sys
from urllib.parse import urlparse

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def get_current_webhook_info():
    """獲取當前 webhook 設置信息"""
    print("🔍 Step 1: 檢查當前 Telegram Bot Webhook 設置...")

    # 由於本地沒有 Bot Token，我們用已知的來測試
    # 實際的 Token 在生產環境中
    bot_token = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get("ok"):
                webhook_info = data.get("result", {})
                current_url = webhook_info.get("url", "")

                print(f"✅ 成功獲取 Webhook 信息:")
                print(f"   📍 當前 URL: {current_url}")
                print(
                    f"   🔄 待處理更新: {webhook_info.get('pending_update_count', 0)}"
                )
                print(
                    f"   🕐 最後錯誤時間: {webhook_info.get('last_error_date', 'None')}"
                )

                if webhook_info.get("last_error_message"):
                    print(f"   ❌ 最後錯誤: {webhook_info.get('last_error_message')}")

                # 分析當前 URL
                if current_url:
                    parsed_url = urlparse(current_url)
                    print(f"\n📋 URL 分析:")
                    print(f"   Domain: {parsed_url.netloc}")
                    print(f"   Path: {parsed_url.path}")

                    # 檢查是否是正確的端點
                    if parsed_url.path == "/callback":
                        print(f"   🚨 問題發現: 使用了 LINE Bot 端點 '/callback'")
                        print(f"   💡 應該使用: '/telegram-webhook'")
                        return False, current_url
                    elif parsed_url.path == "/telegram-webhook":
                        print(f"   ✅ 端點正確: '/telegram-webhook'")
                        return True, current_url
                    else:
                        print(f"   ⚠️  未知端點: {parsed_url.path}")
                        return False, current_url
                else:
                    print(f"   ⚠️  沒有設置 Webhook URL")
                    return False, ""

            else:
                print(f"❌ Telegram API 錯誤: {data}")
                return False, ""
        else:
            print(f"❌ HTTP 錯誤: {response.status_code} - {response.text}")
            return False, ""

    except Exception as e:
        print(f"❌ 檢查 Webhook 信息失敗: {e}")
        return False, ""


def set_correct_webhook():
    """設置正確的 webhook URL"""
    print("\n🔧 Step 2: 設置正確的 Webhook URL...")

    bot_token = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"
    correct_url = "https://namecard-app.zeabur.app/telegram-webhook"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {"url": correct_url}

        print(f"📤 設置 Webhook URL: {correct_url}")
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get("ok"):
                print(f"✅ Webhook URL 設置成功!")
                print(f"   📍 新 URL: {correct_url}")
                return True
            else:
                print(f"❌ Telegram API 錯誤: {data}")
                return False
        else:
            print(f"❌ HTTP 錯誤: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ 設置 Webhook 失敗: {e}")
        return False


def verify_webhook_endpoints():
    """驗證服務端點是否存在"""
    print("\n🔍 Step 3: 驗證服務端點...")

    endpoints_to_check = [
        ("Telegram Webhook", "https://namecard-app.zeabur.app/telegram-webhook"),
        ("LINE Callback", "https://namecard-app.zeabur.app/callback"),
        ("Health Check", "https://namecard-app.zeabur.app/health"),
        ("Service Test", "https://namecard-app.zeabur.app/test"),
    ]

    for name, url in endpoints_to_check:
        try:
            if "telegram-webhook" in url or "callback" in url:
                # POST 請求測試
                response = requests.post(url, json={"test": "data"}, timeout=5)
                print(f"   {name} (POST): {response.status_code}")
            else:
                # GET 請求測試
                response = requests.get(url, timeout=5)
                print(f"   {name} (GET): {response.status_code}")

        except Exception as e:
            print(f"   {name}: ❌ {e}")


def test_webhook_with_message():
    """用測試訊息驗證 webhook"""
    print("\n🧪 Step 4: 測試 Webhook 功能...")

    # 模擬 Telegram 更新
    test_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": 1641024000,
            "chat": {"id": 597988605, "type": "private"},
            "from": {"id": 597988605, "is_bot": False, "first_name": "Test"},
            "text": "/start",
        },
    }

    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=test_update,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"📥 測試回應: {response.status_code}")
        print(f"📄 回應內容: {response.text}")

        if response.status_code == 200:
            print("✅ Webhook 功能測試通過")
            return True
        else:
            print(f"❌ Webhook 功能測試失敗")
            return False

    except Exception as e:
        print(f"❌ Webhook 測試失敗: {e}")
        return False


def main():
    """主函數"""
    print("🔍 Telegram Bot Webhook 診斷和修復")
    print("=" * 50)

    # Step 1: 檢查當前設置
    is_correct, current_url = get_current_webhook_info()

    # Step 2: 如果不正確，修復它
    if not is_correct:
        print(f"\n💡 需要修復 Webhook URL")
        success = set_correct_webhook()
        if success:
            print(f"✅ Webhook URL 已修復")
        else:
            print(f"❌ Webhook URL 修復失敗")
    else:
        print(f"\n✅ Webhook URL 已經正確設置")

    # Step 3: 驗證端點
    verify_webhook_endpoints()

    # Step 4: 測試功能
    test_webhook_with_message()

    print("\n" + "=" * 50)
    print("💡 診斷總結:")
    print("1. 檢查 Webhook URL 是否正確指向 /telegram-webhook")
    print("2. 驗證服務端點是否可訪問")
    print("3. 測試基本 webhook 功能")
    print("\n📋 下一步:")
    print("- 如果 webhook 已修復，請測試上傳圖片")
    print("- 如果仍有問題，需要檢查 Zeabur 服務配置")


if __name__ == "__main__":
    main()
