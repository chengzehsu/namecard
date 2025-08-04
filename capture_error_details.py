#!/usr/bin/env python3
"""
實時捕獲 Telegram Bot 處理錯誤的詳細信息
"""

import os
import sys
import requests
import json
import time
from datetime import datetime

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)

def trigger_controlled_error():
    """觸發一個可控的錯誤來測試日誌系統"""
    print("🧪 觸發可控錯誤測試")
    print("=" * 50)
    
    # 使用真實的圖片數據結構，但使用無效的 file_id
    test_photo_update = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()) % 1000,
            "date": int(time.time()),
            "chat": {"id": 597988605, "type": "private"},
            "from": {"id": 597988605, "is_bot": False, "first_name": "TestUser"},
            "photo": [{
                "file_id": "INVALID_FILE_ID_FOR_TESTING",
                "file_unique_id": "invalid_unique_id",
                "width": 1280,
                "height": 720,
                "file_size": 50000
            }]
        }
    }
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ 測試時間: {current_time}")
    print(f"📤 發送帶有無效 file_id 的圖片請求...")
    print(f"   Update ID: {test_photo_update['update_id']}")
    print(f"   File ID: {test_photo_update['message']['photo'][0]['file_id']}")
    
    try:
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=test_photo_update,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"\n📥 服務器回應:")
        print(f"   狀態碼: {response.status_code}")
        print(f"   回應內容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 請求被接受，正在後臺處理")
            print("\n💡 現在請檢查 Zeabur 日誌，您應該看到:")
            print("   - [INFO] 📥 收到 Telegram webhook 請求")
            print("   - [INFO] 📄 Update data: {...}")
            print("   - [INFO] 📥 開始下載圖片字節數據...")
            print("   - [ERROR] ❌ 圖片下載失敗: ...")
            print("   - 或其他具體的錯誤信息")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 觸發測試失敗: {e}")
        return False

def analyze_possible_errors():
    """分析可能的錯誤原因"""
    print("\n🔍 分析「處理過程中發生錯誤」的具體原因")
    print("=" * 50)
    
    print("基於您看到「處理過程中發生錯誤」訊息，可能的問題:")
    
    print("\n1️⃣ **Telegram 圖片下載失敗**")
    print("   - 原因: Bot Token 權限不足或圖片 file_id 過期")
    print("   - 新錯誤訊息應該是: '❗ 圖片下載失敗: ...'")
    print("   - 日誌應該顯示: '[ERROR] ❌ 圖片下載失敗'")
    
    print("\n2️⃣ **Google Gemini AI 處理失敗**")
    print("   - 原因: API Key 問題或配額用盡")
    print("   - 新錯誤訊息應該是: '❌ AI 識別過程中發生錯誤'")
    print("   - 日誌應該顯示: '[ERROR] ❌ AI 識別過程發生錯誤'")
    
    print("\n3️⃣ **Notion 存儲失敗**")  
    print("   - 原因: API Key 無效或資料庫權限問題")
    print("   - 新錯誤訊息應該是: '❌ Notion 存入失敗'")
    print("   - 日誌應該顯示: Notion 相關錯誤")
    
    print("\n4️⃣ **處理超時**")
    print("   - 原因: 整個處理流程超過限制時間")
    print("   - 新錯誤訊息應該是: '⏰ 處理超時，請稍後重試'")
    print("   - 日誌應該顯示: timeout 相關錯誤")

def check_service_components():
    """檢查各服務組件狀態"""
    print("\n🔍 檢查服務組件狀態")
    print("=" * 50)
    
    try:
        print("📡 測試 /test 端點...")
        response = requests.get("https://namecard-app.zeabur.app/test", timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            print("📊 組件狀態:")
            
            for service, status in data.items():
                if isinstance(status, dict):
                    success = status.get('success', False)
                    message = status.get('message', status.get('error', 'Unknown'))
                    emoji = "✅" if success else "❌"
                    print(f"   {service}: {emoji} {message}")
                    
                    if not success:
                        print(f"      💡 這可能是導致錯誤的原因！")
            
            return data
        else:
            print(f"❌ 組件狀態檢查失敗: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ /test 端點超時")
        print("💡 這可能表明服務負載過高或某個組件卡住")
        return None
    except Exception as e:
        print(f"❌ 組件狀態檢查異常: {e}")
        return None

def provide_debugging_steps():
    """提供調試步驟"""
    print("\n🔧 立即調試步驟")
    print("=" * 50)
    
    print("📋 您現在需要做的:")
    
    print("\n1️⃣ **查看 Zeabur 詳細日誌**")
    print(f"   ⏰ 時間參考: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   - 前往 https://dash.zeabur.com/")
    print("   - 選擇正確的 Telegram Bot 服務")
    print("   - 查看 Logs 標籤中的詳細錯誤")
    print("   - 尋找我們剛才觸發的測試請求")
    
    print("\n2️⃣ **尋找關鍵錯誤信息**")
    print("   在日誌中查找:")
    print("   - [ERROR] 開頭的錯誤行")
    print("   - Python 異常堆疊信息")
    print("   - 'Traceback' 開頭的錯誤追蹤")
    
    print("\n3️⃣ **常見解決方案**")
    print("   根據錯誤類型:")
    print("   - 圖片下載錯誤 → 檢查 TELEGRAM_BOT_TOKEN")
    print("   - AI 處理錯誤 → 檢查 GOOGLE_API_KEY")
    print("   - Notion 錯誤 → 檢查 NOTION_API_KEY")
    print("   - 超時錯誤 → 重新部署或等待")
    
    print("\n4️⃣ **如果日誌中沒有詳細信息**")
    print("   這表明:")
    print("   - 可能在查看錯誤的服務日誌")
    print("   - 或者日誌級別設置問題")
    print("   - 需要確認正確的 Zeabur 服務")

def main():
    """主函數"""
    print("🚨 Telegram Bot 錯誤詳細診斷")
    print("=" * 70)
    
    # 分析錯誤原因
    analyze_possible_errors()
    
    # 檢查組件狀態
    components = check_service_components()
    
    # 觸發可控錯誤進行測試
    triggered = trigger_controlled_error()
    
    # 提供調試步驟
    provide_debugging_steps()
    
    print("\n" + "=" * 70)
    print("💡 總結:")
    
    if components:
        # 檢查是否有失敗的組件
        failed_components = []
        for service, status in components.items():
            if isinstance(status, dict) and not status.get('success', True):
                failed_components.append(service)
        
        if failed_components:
            print(f"🚨 發現失敗的組件: {', '.join(failed_components)}")
            print("💡 這很可能是導致錯誤的直接原因")
        else:
            print("✅ 所有組件狀態正常")
            print("💡 錯誤可能是暫時性的或特定條件觸發的")
    
    if triggered:
        print("✅ 測試請求已發送")
        print("📋 請現在查看 Zeabur 日誌獲取具體錯誤信息")
    else:
        print("❌ 測試請求失敗")
        print("📋 請直接在 Telegram 中測試並查看日誌")
    
    print(f"\n⏰ 參考時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 在 Zeabur 日誌中尋找這個時間前後的錯誤信息")

if __name__ == "__main__":
    main()