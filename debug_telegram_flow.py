#!/usr/bin/env python3
"""
調試 Telegram Bot 圖片處理流程
"""

import requests
import json
import time
import base64

# 創建一個最小的測試圖片（1x1 像素的 PNG）
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg=="

def test_webhook_with_photo():
    """測試圖片處理流程"""
    
    print("🧪 測試 Telegram Bot 圖片處理流程...")
    
    # 模擬 Telegram 發送的圖片訊息
    test_update = {
        "update_id": 999998,
        "message": {
            "message_id": 2,
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
            "photo": [
                {
                    "file_id": "test_file_id_123",
                    "file_unique_id": "test_unique_123", 
                    "width": 1,
                    "height": 1,
                    "file_size": 100
                }
            ]
        }
    }
    
    try:
        print("📤 發送圖片訊息到 webhook...")
        
        # 設置更長的超時時間來觀察處理過程
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=test_update,
            headers={"Content-Type": "application/json"},
            timeout=30  # 30秒超時
        )
        
        print(f"✅ Webhook 回應狀態: {response.status_code}")
        print(f"📄 回應內容: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook 成功處理圖片訊息")
        else:
            print(f"❌ Webhook 處理失敗: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時 - 這可能就是問題所在！")
        print("💡 Bot 處理圖片的時間超過了 30 秒")
        
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

def test_individual_services():
    """測試各個服務的回應時間"""
    
    print("\n🔍 測試各服務回應時間...")
    
    services = {
        "健康檢查": "https://namecard-app.zeabur.app/health",
        "服務測試": "https://namecard-app.zeabur.app/test"
    }
    
    for name, url in services.items():
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            duration = (end_time - start_time) * 1000  # 轉換為毫秒
            
            print(f"  ✅ {name}: {response.status_code} ({duration:.0f}ms)")
            
        except Exception as e:
            print(f"  ❌ {name}: {e}")

def check_telegram_bot_commands():
    """測試基本 Telegram Bot 命令"""
    
    print("\n🤖 測試 Telegram Bot 基本命令...")
    
    commands = [
        {"text": "/start", "desc": "開始命令"},
        {"text": "/help", "desc": "幫助命令"},
        {"text": "hello", "desc": "普通文字"}
    ]
    
    for cmd in commands:
        try:
            test_update = {
                "update_id": 999997,
                "message": {
                    "message_id": 3,
                    "date": int(time.time()),
                    "chat": {"id": 123456789, "type": "private"},
                    "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                    "text": cmd["text"]
                }
            }
            
            start_time = time.time()
            response = requests.post(
                "https://namecard-app.zeabur.app/telegram-webhook",
                json=test_update,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            end_time = time.time()
            
            duration = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                print(f"  ✅ {cmd['desc']}: {duration:.0f}ms")
            else:
                print(f"  ❌ {cmd['desc']}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ⏰ {cmd['desc']}: 超時")
        except Exception as e:
            print(f"  ❌ {cmd['desc']}: {e}")

def main():
    """主測試函數"""
    print("🔍 Telegram Bot 沒有回覆問題診斷")
    print("=" * 50)
    
    # 測試基本服務
    test_individual_services()
    
    # 測試基本命令
    check_telegram_bot_commands()
    
    # 測試圖片處理（這個可能會超時）
    test_webhook_with_photo()
    
    print("\n" + "=" * 50)
    print("📊 診斷建議:")
    print("1. 如果基本命令正常但圖片處理超時，問題在圖片處理流程")
    print("2. 如果所有命令都超時，問題在 webhook 處理機制")
    print("3. 檢查 Gemini AI 和 Notion API 的回應時間")

if __name__ == "__main__":
    main()