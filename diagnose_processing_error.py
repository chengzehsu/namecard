#!/usr/bin/env python3
"""
診斷 Telegram Bot 處理過程中的錯誤
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

def analyze_potential_issues():
    """分析潛在的問題原因"""
    print("🔍 分析「處理過程中發生錯誤」的可能原因")
    print("=" * 50)
    
    print("💡 可能的錯誤原因:")
    print("\n1️⃣ **Telegram 圖片下載問題**")
    print("   - Bot Token 權限不足")
    print("   - 圖片 file_id 無效或過期")
    print("   - 網路連接問題")
    print("   - Telegram API 速率限制")
    
    print("\n2️⃣ **Google Gemini AI 處理問題**")
    print("   - API Key 無效或過期")
    print("   - API 配額用盡")
    print("   - 圖片格式不支援")
    print("   - 圖片太大或太小")
    print("   - 網路連接超時")
    
    print("\n3️⃣ **Notion 存儲問題**")
    print("   - API Key 無效")
    print("   - 資料庫權限不足")
    print("   - 資料格式驗證失敗")
    print("   - 網路連接問題")
    
    print("\n4️⃣ **系統資源問題**")
    print("   - 記憶體不足")
    print("   - 處理超時")
    print("   - 伺服器負載過高")
    
    print("\n5️⃣ **代碼邏輯問題**")
    print("   - 異常處理不完整")
    print("   - 數據類型錯誤")
    print("   - 模組導入問題")

def test_individual_components():
    """測試各個組件的狀態"""
    print("\n🔍 測試各個組件狀態")
    print("=" * 50)
    
    try:
        response = requests.get("https://namecard-app.zeabur.app/test", timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            print("📊 組件狀態檢查:")
            for service, status in data.items():
                if isinstance(status, dict):
                    success = status.get('success', False)
                    message = status.get('message', status.get('error', 'Unknown'))
                    emoji = "✅" if success else "❌"
                    print(f"  {service}: {emoji} {message}")
                    
                    # 詳細分析失敗原因
                    if not success and isinstance(status, dict):
                        error = status.get('error', '')
                        if 'API token is invalid' in error:
                            print(f"    💡 建議: 檢查 {service.upper()} API Key 設置")
                        elif 'not found' in error.lower():
                            print(f"    💡 建議: 檢查 {service.upper()} 資源 ID")
                        elif 'timeout' in error.lower():
                            print(f"    💡 建議: 檢查網路連接和服務狀態")
                        elif 'permission' in error.lower():
                            print(f"    💡 建議: 檢查 {service.upper()} 權限設置")
            
            return data
        else:
            print(f"❌ 組件狀態檢查失敗: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 組件狀態檢查異常: {e}")
        return None

def simulate_real_photo_processing():
    """模擬真實的圖片處理流程"""
    print("\n🔍 模擬真實圖片處理流程")
    print("=" * 50)
    
    # 使用真實的圖片數據
    real_photo_update = {
        "update_id": 944545862,
        "message": {
            "message_id": 33,
            "from": {
                "id": 597988605,
                "is_bot": False,
                "first_name": "Kevin",
                "username": "kevinmyl",
                "language_code": "zh-hans"
            },
            "chat": {
                "id": 597988605,
                "first_name": "Kevin", 
                "username": "kevinmyl",
                "type": "private"
            },
            "date": int(time.time()),
            "photo": [{
                "file_id": "AgACAgUAAxkBAAMKaI16zyjtvWYu6km4pdGOWhLeXIoAApHCMRtjZHBUMVESskcE2SwBAAMCAANzAAM2BA",
                "file_unique_id": "AQADkcIxG2NkcFR4",
                "file_size": 1010,
                "width": 90,
                "height": 51
            }, {
                "file_id": "AgACAgUAAxkBAAMKaI16zyjtvWYu6km4pdGOWhLeXIoAApHCMRtjZHBUMVESskcE2SwBAAMCAAN5AAM2BA",
                "file_unique_id": "AQADkcIxG2NkcFR-",
                "file_size": 111405,
                "width": 1280,
                "height": 720
            }]
        }
    }
    
    print("📤 發送真實圖片處理請求...")
    print(f"   文件 ID: {real_photo_update['message']['photo'][-1]['file_id'][:30]}...")
    print(f"   圖片尺寸: {real_photo_update['message']['photo'][-1]['width']}x{real_photo_update['message']['photo'][-1]['height']}")
    print(f"   文件大小: {real_photo_update['message']['photo'][-1]['file_size']} bytes")
    
    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=real_photo_update,
            headers={"Content-Type": "application/json"},
            timeout=90  # 給予充足的處理時間
        )
        
        print(f"\n📥 處理回應:")
        print(f"   狀態碼: {response.status_code}")
        print(f"   回應內容: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ 請求被接受，正在後臺處理")
            print("   💡 請檢查 Telegram Bot 是否有回應")
            return True
        elif response.status_code == 500:
            print("   ❌ 伺服器內部錯誤")
            print("   💡 建議檢查 Zeabur 服務日誌")
            return False
        else:
            print(f"   ❌ 處理失敗，狀態碼: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ⏰ 處理超時")
        print("   💡 可能正在處理中，請檢查 Telegram Bot 回應")
        return True  # 超時不一定是失敗
    except Exception as e:
        print(f"   ❌ 請求異常: {e}")
        return False

def check_telegram_bot_api():
    """檢查 Telegram Bot API 狀態"""
    print("\n🔍 檢查 Telegram Bot API 狀態")
    print("=" * 50)
    
    bot_token = "8026190410:AAHpj5CBPP-eXpo-WJs6uwWRw22kUVdf3d4"
    
    try:
        # 檢查 Bot 基本信息
        print("📡 測試 Bot 基本連接...")
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"   ✅ Bot 連接正常")
                print(f"   🤖 Bot 名稱: {bot_info.get('first_name', 'Unknown')}")
                print(f"   📛 用戶名: @{bot_info.get('username', 'Unknown')}")
            else:
                print(f"   ❌ Bot API 錯誤: {data}")
                return False
        else:
            print(f"   ❌ Bot API 連接失敗: {response.status_code}")
            return False
            
        # 檢查 Webhook 狀態
        print("\n📡 檢查 Webhook 狀態...")
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                webhook_info = data.get("result", {})
                print(f"   📍 Webhook URL: {webhook_info.get('url', 'None')}")
                print(f"   📊 待處理更新: {webhook_info.get('pending_update_count', 0)}")
                
                if webhook_info.get('last_error_date'):
                    print(f"   ⚠️  最後錯誤: {webhook_info.get('last_error_message', 'Unknown')}")
                else:
                    print(f"   ✅ 沒有最近錯誤")
                    
                return True
            else:
                print(f"   ❌ Webhook 檢查失敗: {data}")
                return False
        else:
            print(f"   ❌ Webhook 檢查連接失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Telegram API 檢查異常: {e}")
        return False

def provide_debugging_suggestions():
    """提供調試建議"""
    print("\n🔧 調試建議")
    print("=" * 50)
    
    print("📋 立即檢查事項:")
    print("\n1️⃣ **查看 Zeabur 服務日誌**")
    print("   - 前往 https://dash.zeabur.com/")
    print("   - 選擇專案 → 服務 → Logs 標籤")
    print("   - 查找具體的錯誤堆疊信息")
    
    print("\n2️⃣ **檢查環境變數**")
    print("   - TELEGRAM_BOT_TOKEN: 確保有效")
    print("   - GOOGLE_API_KEY: 確保有配額")
    print("   - NOTION_API_KEY: 確保有權限")
    print("   - NOTION_DATABASE_ID: 確保正確")
    
    print("\n3️⃣ **測試步驟**")
    print("   - 先發送 /start 指令測試基本功能")
    print("   - 再上傳小尺寸的清晰名片圖片")
    print("   - 觀察 Telegram Bot 的具體回應")
    
    print("\n4️⃣ **常見解決方案**")
    print("   - 重新生成並更新 API Keys")
    print("   - 重新部署服務")
    print("   - 檢查服務器資源使用情況")
    print("   - 確認 Notion 資料庫權限")

def main():
    """主診斷函數"""
    print("🚨 Telegram Bot 處理錯誤診斷")
    print("=" * 70)
    
    # 分析可能原因
    analyze_potential_issues()
    
    # 測試各組件
    component_status = test_individual_components()
    
    # 檢查 Telegram API
    telegram_ok = check_telegram_bot_api()
    
    # 模擬圖片處理
    processing_ok = simulate_real_photo_processing()
    
    # 提供建議
    provide_debugging_suggestions()
    
    print("\n" + "=" * 70)
    print("💡 診斷總結:")
    
    if component_status:
        notion_ok = component_status.get('notion', {}).get('success', False)
        gemini_ok = component_status.get('gemini', {}).get('success', False)
        
        print(f"  Telegram API: {'✅' if telegram_ok else '❌'}")
        print(f"  Gemini AI: {'✅' if gemini_ok else '❌'}")
        print(f"  Notion 資料庫: {'✅' if notion_ok else '❌'}")
        print(f"  圖片處理測試: {'✅' if processing_ok else '❌'}")
        
        if not notion_ok:
            print("\n🚨 主要問題: Notion 連接失敗")
            print("   建議: 重新生成 Notion API Key 並更新環境變數")
        elif not gemini_ok:
            print("\n🚨 主要問題: Gemini AI 連接失敗")
            print("   建議: 檢查 Google API Key 和配額")
        elif not telegram_ok:
            print("\n🚨 主要問題: Telegram Bot API 失敗")
            print("   建議: 檢查 Bot Token 和 Webhook 設置")
        else:
            print("\n💡 所有組件看起來正常，可能是暫時性問題")
            print("   建議: 查看 Zeabur 日誌獲取詳細錯誤信息")

if __name__ == "__main__":
    main()