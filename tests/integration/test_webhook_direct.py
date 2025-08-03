#!/usr/bin/env python3
"""
直接測試 LINE webhook URL 的腳本
模擬 LINE 平台發送的 webhook 請求
"""
import base64
import hashlib
import hmac
import json

import requests

from config import Config


def create_line_signature(body, secret):
    """創建 LINE 簽名"""
    signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")
    return signature


def test_webhook_url(webhook_url):
    """測試 webhook URL"""
    print(f"🔍 測試 Webhook URL: {webhook_url}")

    # 測試 GET 請求到 /callback
    try:
        response = requests.get(f"{webhook_url}/callback", timeout=10)
        print(f"✅ GET /callback: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ GET /callback 失敗: {e}")

    # 測試健康檢查
    try:
        response = requests.get(f"{webhook_url}/health", timeout=10)
        print(f"✅ GET /health: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ GET /health 失敗: {e}")

    # 測試模擬 LINE webhook POST 請求
    try:
        # 構造測試請求體
        webhook_body = {"destination": "test-destination", "events": []}

        body_str = json.dumps(webhook_body)
        signature = create_line_signature(body_str, Config.LINE_CHANNEL_SECRET)

        headers = {
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
            "User-Agent": "LineBotWebhook/1.0",
            "ngrok-skip-browser-warning": "true",
        }

        response = requests.post(
            f"{webhook_url}/callback", data=body_str, headers=headers, timeout=10
        )

        print(f"✅ POST /callback: {response.status_code} - {response.text[:100]}")

        if response.status_code == 200:
            print("🎉 Webhook 測試成功！可以在 LINE Console 中使用此 URL")
            return True
        else:
            print(f"⚠️ Webhook 返回狀態碼 {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ POST /callback 失敗: {e}")
        return False


def main():
    """主函數"""
    print("🧪 LINE Bot Webhook URL 測試工具")
    print("=" * 50)

    # 測試本地服務器
    local_urls = [
        "http://localhost:9000",
        "http://localhost:8080",
        "http://localhost:5001",
    ]

    print("\n📍 測試本地服務器...")
    for url in local_urls:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ 找到運行中的服務器: {url}")
                test_webhook_url(url)
                break
        except:
            continue
    else:
        print("❌ 沒有找到運行中的本地服務器")

    # 測試可能的 ngrok URLs
    ngrok_urls = [
        "https://0d366ce35fc5.ngrok-free.app",
        "https://7b58d8b8fac1.ngrok-free.app",
        "https://4ee9cac2f959.ngrok-free.app",
    ]

    print("\n🌐 測試 ngrok URLs...")
    for url in ngrok_urls:
        print(f"\n測試: {url}")
        if test_webhook_url(url):
            print(f"🎯 推薦使用此 URL 作為 LINE Webhook: {url}/callback")
            break
    else:
        print("\n💡 建議:")
        print("1. 確保本地服務器正在運行")
        print("2. 重新啟動 ngrok: ngrok http <port>")
        print("3. 或考慮部署到雲端平台")


if __name__ == "__main__":
    main()
