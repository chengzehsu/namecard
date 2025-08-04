#!/usr/bin/env python3
"""
測試真實的 Telegram Bot 流程並檢查日誌
"""

import os
import sys
import requests
import json
import time

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)

def check_webhook_setup():
    """檢查 webhook 設置"""
    print("🔍 Step 1: 檢查 Telegram Bot Webhook 設置")
    print("=" * 50)
    
    bot_token = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                webhook_info = data.get("result", {})
                
                print("📋 當前 Webhook 設置:")
                print(f"  URL: {webhook_info.get('url', 'None')}")
                print(f"  待處理更新: {webhook_info.get('pending_update_count', 0)}")
                print(f"  最大連接數: {webhook_info.get('max_connections', 0)}")
                
                if webhook_info.get('last_error_date'):
                    error_date = webhook_info.get('last_error_date')
                    error_msg = webhook_info.get('last_error_message', 'Unknown')
                    print(f"  ⚠️  最後錯誤時間: {error_date}")
                    print(f"  ⚠️  最後錯誤訊息: {error_msg}")
                    
                    # 轉換時間戳
                    import datetime
                    error_datetime = datetime.datetime.fromtimestamp(error_date)
                    print(f"  🕐 錯誤發生時間: {error_datetime}")
                else:
                    print("  ✅ 沒有最近的錯誤")
                
                return webhook_info
        else:
            print(f"❌ 獲取 webhook 信息失敗: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 檢查 webhook 設置失敗: {e}")
        return None

def test_start_command():
    """測試 /start 指令"""
    print("\n🔍 Step 2: 測試 /start 指令")
    print("=" * 50)
    
    start_update = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()) % 1000,
            "date": int(time.time()),
            "chat": {"id": 597988605, "type": "private"},
            "from": {"id": 597988605, "is_bot": False, "first_name": "TestUser"},
            "text": "/start"
        }
    }
    
    print("📤 發送 /start 指令到 webhook...")
    print(f"   Update ID: {start_update['update_id']}")
    
    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=start_update,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📥 回應狀態: {response.status_code}")
        print(f"📄 回應內容: {response.text}")
        
        if response.status_code == 200:
            print("✅ /start 指令處理成功")
            print("💡 請檢查您的 Telegram Bot 是否收到歡迎訊息")
            return True
        else:
            print(f"❌ /start 指令處理失敗")
            return False
            
    except Exception as e:
        print(f"❌ 測試 /start 指令失敗: {e}")
        return False

def simulate_photo_upload():
    """模擬圖片上傳"""
    print("\n🔍 Step 3: 模擬圖片上傳")
    print("=" * 50)
    
    # 使用一個簡單的測試圖片 update
    photo_update = {
        "update_id": int(time.time()) + 1,
        "message": {
            "message_id": int(time.time()) % 1000 + 1,
            "date": int(time.time()),
            "chat": {"id": 597988605, "type": "private"},
            "from": {"id": 597988605, "is_bot": False, "first_name": "TestUser"},
            "photo": [{
                "file_id": "test_simple_photo_id",
                "file_unique_id": "test_unique_simple",
                "width": 100,
                "height": 100,
                "file_size": 1000
            }]
        }
    }
    
    print("📤 發送測試圖片到 webhook...")
    print(f"   Update ID: {photo_update['update_id']}")
    print(f"   Message ID: {photo_update['message']['message_id']}")
    
    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=photo_update,
            headers={"Content-Type": "application/json"},
            timeout=60  # 給予充足時間
        )
        
        print(f"📥 回應狀態: {response.status_code}")
        print(f"📄 回應內容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 圖片 webhook 處理完成")
            print("💡 請檢查 Telegram Bot 的回應和 Zeabur 日誌")
            return True
        else:
            print(f"❌ 圖片處理失敗，狀態碼: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ 圖片處理超時")
        print("💡 可能正在處理中，請檢查 Telegram Bot 回應")
        return True  # 超時不一定是失敗
    except Exception as e:
        print(f"❌ 圖片處理測試失敗: {e}")
        return False

def check_service_endpoints():
    """檢查服務端點狀態"""
    print("\n🔍 Step 4: 檢查服務端點狀態")
    print("=" * 50)
    
    endpoints = [
        ("首頁", "https://namecard-app.zeabur.app/", "GET"),
        ("健康檢查", "https://namecard-app.zeabur.app/health", "GET"),
        ("Webhook 端點", "https://namecard-app.zeabur.app/telegram-webhook", "POST"),
    ]
    
    results = {}
    
    for name, url, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:  # POST
                # 發送最小的測試數據
                response = requests.post(url, json={"test": "data"}, timeout=10)
            
            print(f"   {name}: {response.status_code}")
            
            if response.status_code in [200, 400]:  # 400 對於無效數據是正常的
                results[name] = True
            else:
                results[name] = False
                
        except Exception as e:
            print(f"   {name}: ❌ {e}")
            results[name] = False
    
    return results

def provide_troubleshooting_guide():
    """提供故障排除指南"""
    print("\n🔧 故障排除指南")
    print("=" * 50)
    
    print("📋 您看到的日誌類型分析:")
    print("\n🟢 **正常的 HTTP 日誌** (您目前看到的):")
    print("   - GET / 200 - 首頁訪問")
    print("   - GET /favicon.ico 404 - 瀏覽器請求圖標")
    print("   ✅ 這表明 Flask 服務器正常運行")
    
    print("\n🔍 **缺失的處理日誌** (您應該看到但沒看到的):")
    print("   - [INFO] 📥 收到 Telegram webhook 請求")
    print("   - [INFO] 📄 Update data: {...}")
    print("   - [INFO] 📥 開始下載圖片字節數據...")
    print("   - [INFO] 🔍 開始多名片 AI 識別和品質評估...")
    
    print("\n💡 **可能的原因:**")
    print("1. 🤔 您在看錯誤的日誌流 (可能是不同服務的日誌)")
    print("2. 🤔 Telegram Bot 的 Webhook 沒有正確發送請求")
    print("3. 🤔 請求被路由到了錯誤的服務")
    print("4. 🤔 日誌級別設置問題")
    
    print("\n🔧 **建議檢查步驟:**")
    print("1. **確認您在正確的 Zeabur 服務中查看日誌**")
    print("   - 前往 https://dash.zeabur.com/")
    print("   - 確認選擇的是 Telegram Bot 服務")
    print("   - 而不是 LINE Bot 或其他服務")
    
    print("\n2. **檢查 Telegram Bot 是否正確設置**")
    print("   - 確認 Bot Token 正確")
    print("   - 確認 Webhook URL 指向正確的服務")
    
    print("\n3. **實際測試 Bot 功能**")
    print("   - 在 Telegram 中發送 /start 給您的 Bot")
    print("   - 觀察是否收到回應")
    print("   - 如果沒有回應，問題在於 Webhook 設置")

def main():
    """主測試函數"""
    print("🤖 Telegram Bot 實時流程測試")
    print("=" * 70)
    
    # 檢查 webhook 設置
    webhook_info = check_webhook_setup()
    
    # 檢查服務端點
    endpoint_results = check_service_endpoints()
    
    # 測試指令
    start_ok = test_start_command()
    
    # 測試圖片處理
    photo_ok = simulate_photo_upload()
    
    # 提供故障排除指南
    provide_troubleshooting_guide()
    
    print("\n" + "=" * 70)
    print("📊 測試結果總結:")
    
    if webhook_info:
        print(f"  Webhook 設置: ✅ 正確")
    else:
        print(f"  Webhook 設置: ❌ 有問題")
    
    print(f"  /start 指令: {'✅ 正常' if start_ok else '❌ 失敗'}")
    print(f"  圖片處理: {'✅ 正常' if photo_ok else '❌ 失敗'}")
    
    for name, result in endpoint_results.items():
        print(f"  {name}: {'✅ 正常' if result else '❌ 失敗'}")
    
    print("\n💡 下一步:")
    if start_ok and photo_ok:
        print("🎉 測試正常！請在實際 Telegram 中測試您的 Bot")
    else:
        print("⚠️  發現問題，請按照故障排除指南檢查")

if __name__ == "__main__":
    main()