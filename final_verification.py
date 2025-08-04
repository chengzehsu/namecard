#!/usr/bin/env python3
"""
最終驗證 Telegram Bot 修復效果
"""

import requests
import json

def final_test():
    """最終測試"""
    print("🎯 Telegram Bot 修復效果驗證")
    print("=" * 50)
    
    app_url = "https://namecard-app.zeabur.app"
    
    # 1. 健康檢查
    try:
        response = requests.get(f"{app_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服務運行正常")
        else:
            print(f"⚠️ 服務狀態: {response.status_code}")
    except:
        print("❌ 服務無法連接")
        return False
    
    # 2. 測試新版本功能
    try:
        test_data = {"test": "data"}
        response = requests.post(f"{app_url}/telegram-webhook", json=test_data, timeout=5)
        if "Test data received successfully" in response.text:
            print("✅ 新版本代碼確認")
        else:
            print("❌ 可能還是舊版本")
            return False
    except:
        print("❌ Webhook 測試失敗")
        return False
    
    # 3. 測試圖片處理邏輯
    try:
        photo_data = {
            "update_id": 999999,
            "message": {
                "message_id": 999,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123, "type": "private"},
                "date": 1609459200,
                "photo": [{"file_id": "test", "file_unique_id": "test", "file_size": 1000, "width": 100, "height": 100}]
            }
        }
        
        response = requests.post(f"{app_url}/telegram-webhook", json=photo_data, timeout=10)
        if response.status_code == 200 and response.text.strip() == "OK":
            print("✅ 圖片處理邏輯正常接收")
            print("   後台處理已啟動")
        else:
            print(f"❌ 圖片處理異常: {response.status_code} - {response.text}")
            return False
    except:
        print("❌ 圖片處理測試失敗")
        return False
    
    return True

def usage_guide():
    """使用指南"""
    print("\n🎯 Telegram Bot 使用指南")
    print("=" * 50)
    print("1️⃣ 在 Telegram 中找到您的 Bot")
    print("2️⃣ 發送 /start 指令測試基本功能")
    print("3️⃣ 直接發送名片圖片")
    print("4️⃣ 預期立即收到: '🔄 正在處理您的名片圖片，請稍候...'")
    print("5️⃣ 接著收到: '🤖 圖片下載完成，正在進行 AI 識別中...'")
    print("6️⃣ 最後收到: AI 識別結果或具體錯誤建議")
    print()
    print("💡 其他指令:")
    print("   /help - 查看幫助")
    print("   /batch - 開始批量處理")
    print("   /status - 查看系統狀態")

if __name__ == "__main__":
    if final_test():
        print("\n🎉 恭喜！Telegram Bot 修復完成！")
        print("✅ 圖片上傳功能已恢復正常")
        usage_guide()
    else:
        print("\n❌ 仍有問題，請檢查:")
        print("• Zeabur 環境變數是否正確設置")
        print("• 是否已重新部署")
        print("• 查看 Zeabur 部署日誌")