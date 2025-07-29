#!/usr/bin/env python3
"""
測試新的 ngrok webhook URL
按照 LINE Message API 規範進行測試
"""
import requests
import json
import hmac
import hashlib
import base64
from config import Config

def create_line_signature(body, secret):
    """創建正確的 LINE 簽名"""
    signature = base64.b64encode(
        hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    return signature

def test_ngrok_webhook():
    """測試 ngrok webhook URL"""
    webhook_url = "https://b04f9633c607.ngrok-free.app"
    
    print(f"🔍 測試 ngrok webhook URL: {webhook_url}")
    print("=" * 60)
    
    # 1. 測試健康檢查
    print("\n1️⃣ 測試健康檢查端點...")
    try:
        response = requests.get(
            f"{webhook_url}/health",
            headers={'ngrok-skip-browser-warning': 'true'},
            timeout=10
        )
        print(f"✅ GET /health: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 回應: {response.json()}")
        else:
            print(f"❌ 錯誤: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return False
    
    # 2. 測試 GET /callback（用於 LINE Console 驗證）
    print("\n2️⃣ 測試 GET /callback...")
    try:
        response = requests.get(
            f"{webhook_url}/callback",
            headers={'ngrok-skip-browser-warning': 'true'},
            timeout=10
        )
        print(f"✅ GET /callback: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 回應: {response.json()}")
    except Exception as e:
        print(f"❌ GET /callback 失敗: {e}")
    
    # 3. 測試 POST /callback（模擬 LINE webhook）
    print("\n3️⃣ 測試 POST /callback（模擬 LINE webhook）...")
    try:
        # 建構 LINE webhook 請求體
        webhook_body = {
            "destination": "test-destination",
            "events": [
                {
                    "type": "message",
                    "message": {"type": "text", "text": "hello"},
                    "source": {"type": "user", "userId": "test-user"},
                    "replyToken": "test-reply-token",
                    "mode": "active",
                    "timestamp": 1234567890,
                    "webhookEventId": "test-webhook-id"
                }
            ]
        }
        
        body_str = json.dumps(webhook_body)
        signature = create_line_signature(body_str, Config.LINE_CHANNEL_SECRET)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Line-Signature': signature,
            'User-Agent': 'LineBotWebhook/2.0',
            'ngrok-skip-browser-warning': 'true'
        }
        
        print(f"📤 發送 POST 請求...")
        print(f"📋 Headers: {headers}")
        print(f"📄 Body 長度: {len(body_str)} bytes")
        
        response = requests.post(
            f"{webhook_url}/callback",
            data=body_str,
            headers=headers,
            timeout=15
        )
        
        print(f"✅ POST /callback: {response.status_code}")
        print(f"📄 回應: {response.text}")
        
        if response.status_code == 200:
            print("🎉 Webhook 測試成功！")
            print(f"✅ 可以在 LINE Developers Console 中使用: {webhook_url}/callback")
            return True
        else:
            print(f"⚠️ 狀態碼不正確: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ POST /callback 失敗: {e}")
        return False

def main():
    """主函數"""
    print("🧪 LINE Bot Webhook 測試工具")
    print("📋 按照 LINE Message API 規範測試")
    
    success = test_ngrok_webhook()
    
    if success:
        print("\n" + "="*60)
        print("🎊 Webhook 測試完全成功！")
        print("\n📋 下一步：")
        print("1. 前往 LINE Developers Console")
        print("2. 設定 Webhook URL: https://b04f9633c607.ngrok-free.app/callback")
        print("3. 開啟 'Use webhook'")
        print("4. 點擊 'Verify' 按鈕")
        print("5. 應該會顯示成功 ✅")
    else:
        print("\n❌ 測試失敗，需要進一步調試")

if __name__ == "__main__":
    main()