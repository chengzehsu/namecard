#!/usr/bin/env python3
"""
測試 Telegram Bot 圖片上傳功能
"""

import requests
import json
import time

# 設置
BOT_TOKEN = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"
WEBHOOK_URL = "https://namecard-app.zeabur.app/telegram-webhook"

def test_webhook_connectivity():
    """測試 webhook 連通性"""
    print("🔍 測試 webhook 連通性...")
    
    test_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": int(time.time()),
            "chat": {
                "id": 123456789,
                "type": "private",
                "first_name": "Test"
            },
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test"
            },
            "text": "/start"
        }
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_update,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"✅ Webhook 回應狀態: {response.status_code}")
        print(f"📄 回應內容: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Webhook 測試失敗: {e}")
        return False

def test_bot_api():
    """測試 Telegram Bot API"""
    print("\n🤖 測試 Telegram Bot API...")
    
    try:
        # 獲取 bot 資訊
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        bot_info = response.json()
        
        if bot_info.get("ok"):
            print(f"✅ Bot 資訊: {bot_info['result']['first_name']} (@{bot_info['result']['username']})")
        else:
            print(f"❌ 無法獲取 Bot 資訊: {bot_info}")
            return False
        
        # 檢查 webhook 狀態
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
        webhook_info = response.json()
        
        if webhook_info.get("ok"):
            result = webhook_info["result"]
            print(f"📡 Webhook URL: {result.get('url', 'None')}")
            print(f"📊 待處理更新: {result.get('pending_update_count', 0)}")
            
            if result.get("last_error_message"):
                print(f"⚠️ 最後錯誤: {result['last_error_message']}")
                print(f"🕐 錯誤時間: {result.get('last_error_date', 'None')}")
            else:
                print("✅ 沒有錯誤記錄")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram API 測試失敗: {e}")
        return False

def test_app_services():
    """測試應用服務狀態"""
    print("\n🔧 測試應用服務狀態...")
    
    try:
        # 健康檢查
        response = requests.get("https://namecard-app.zeabur.app/health")
        health = response.json()
        print(f"💚 健康狀態: {health}")
        
        # 服務測試
        response = requests.get("https://namecard-app.zeabur.app/test")
        services = response.json()
        
        print("🔍 服務狀態:")
        for service, status in services.items():
            if status.get("success"):
                print(f"  ✅ {service}: {status.get('message', 'OK')}")
            else:
                print(f"  ❌ {service}: {status.get('error', 'Unknown error')}")
        
        return services
        
    except Exception as e:
        print(f"❌ 應用服務測試失敗: {e}")
        return None

def main():
    """主測試函數"""
    print("🧪 Telegram Bot 上傳功能診斷測試")
    print("=" * 50)
    
    # 測試順序
    webhook_ok = test_webhook_connectivity()
    bot_api_ok = test_bot_api()
    services = test_app_services()
    
    print("\n" + "=" * 50)
    print("📊 診斷結果摘要:")
    
    if webhook_ok:
        print("✅ Webhook 連通性正常")
    else:
        print("❌ Webhook 連通性有問題")
    
    if bot_api_ok:
        print("✅ Telegram Bot API 正常")
    else:
        print("❌ Telegram Bot API 有問題")
    
    if services:
        print("✅ 應用服務可訪問")
        
        # 檢查關鍵服務
        notion_ok = services.get("notion", {}).get("success", False)
        gemini_ok = services.get("gemini", {}).get("success", False)
        
        if not notion_ok:
            print("⚠️ Notion API 連接失敗 - 這會影響名片資料儲存")
        if not gemini_ok:
            print("⚠️ Gemini AI 連接失敗 - 這會影響名片識別")
            
        if notion_ok and gemini_ok:
            print("✅ 所有核心服務正常")
    else:
        print("❌ 應用服務不可訪問")
    
    print("\n💡 建議:")
    if not services or not services.get("notion", {}).get("success"):
        print("1. 更新 GitHub Secrets 中的 NOTION_API_KEY 和 NOTION_DATABASE_ID")
        print("2. 重新部署應用")
    
    if webhook_ok and bot_api_ok and services:
        print("1. 嘗試在 Telegram 中發送 /start 命令測試基本功能")
        print("2. 發送 /help 查看功能說明")
        print("3. 發送小尺寸的名片圖片測試上傳功能")
        print("4. 檢查圖片格式是否為 JPG/PNG")

if __name__ == "__main__":
    main()