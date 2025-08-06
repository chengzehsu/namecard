#!/usr/bin/env python3
"""
分析 webhook 端點差異的原因
"""

import json
import os
import sys

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def analyze_webhook_discrepancy():
    """分析為什麼日誌顯示 /callback 但 webhook 設置是 /telegram-webhook"""
    print("🔍 分析 Webhook 端點差異...")

    print("\n📋 可能的原因:")
    print("1. 🤔 部署了多個服務 (LINE Bot + Telegram Bot)")
    print("2. 🤔 日誌來自不同的服務")
    print("3. 🤔 有舊的 webhook 設置仍在運行")
    print("4. 🤔 Zeabur 路由配置問題")

    return True


def test_specific_webhook_behavior():
    """測試具體的 webhook 行為"""
    print("\n🧪 測試具體 webhook 行為...")

    # 測試真實的圖片訊息
    real_photo_update = {
        "update_id": 944545860,
        "message": {
            "message_id": 31,
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
            "date": 1754267738,
            "photo": [
                {
                    "file_id": "AgACAgUAAxkBAAMKaI16zyjtvWYu6km4pdGOWhLeXIoAApHCMRtjZHBUMVESskcE2SwBAAMCAANzAAM2BA",
                    "file_unique_id": "AQADkcIxG2NkcFR4",
                    "file_size": 1010,
                    "width": 90,
                    "height": 51,
                }
            ],
        },
    }

    try:
        print("📤 發送真實圖片更新到 /telegram-webhook...")
        response = requests.post(
            "https://namecard-app.zeabur.app/telegram-webhook",
            json=real_photo_update,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📥 回應狀態: {response.status_code}")
        print(f"📄 回應內容: {response.text}")

        if response.status_code == 200:
            print("✅ Telegram webhook 接受了圖片訊息")
        elif response.status_code == 500:
            print("❌ 內部服務器錯誤 - 這可能是處理過程中的問題")
        else:
            print(f"⚠️  意外的回應狀態: {response.status_code}")

    except requests.exceptions.Timeout:
        print("⏰ 請求超時 - 服務可能在處理但回應太慢")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")


def check_zeabur_service_logs():
    """提供檢查 Zeabur 服務日誌的建議"""
    print("\n📋 檢查 Zeabur 服務日誌建議:")

    print("\n🔍 在 Zeabur Dashboard:")
    print("1. 前往您的專案")
    print("2. 點擊服務名稱")
    print("3. 查看 'Logs' 標籤")
    print("4. 查找最近的錯誤信息")

    print("\n🔍 要查找的關鍵信息:")
    print("- 處理器初始化錯誤")
    print("- Notion API 連接錯誤")
    print("- Telegram Bot 處理錯誤")
    print("- Python 異常堆疊信息")


def provide_troubleshooting_steps():
    """提供故障排除步驟"""
    print("\n🔧 故障排除步驟:")

    print("\n1️⃣ 檢查服務狀態:")
    print("   curl https://namecard-app.zeabur.app/test")

    print("\n2️⃣ 檢查 Notion 連接:")
    print("   - 重新創建 Notion Integration")
    print("   - 更新 NOTION_API_KEY 環境變數")
    print("   - 重新部署服務")

    print("\n3️⃣ 檢查日誌中的具體錯誤:")
    print("   - 查看 Zeabur Dashboard 日誌")
    print("   - 尋找 Python 異常信息")
    print("   - 確認哪個步驟失敗了")

    print("\n4️⃣ 測試修復效果:")
    print("   - 修復後重新上傳圖片")
    print("   - 觀察是否收到預期回應")


def simulate_expected_behavior():
    """模擬預期的行為"""
    print("\n💭 預期的完整流程:")

    print("\n📱 用戶上傳圖片時應該發生:")
    print("1. 📸 Bot 回應: '收到名片圖片！正在使用 AI 識別中，請稍候...'")
    print("2. 🔍 Gemini AI 處理圖片內容")
    print("3. 💾 嘗試存入 Notion 資料庫")
    print("4a. ✅ 成功: 回傳處理結果和 Notion 頁面連結")
    print("4b. ❌ 失敗: 回傳錯誤訊息 (目前應該是這個情況)")

    print("\n🚨 目前的問題:")
    print("- Telegram webhook 返回 500 錯誤")
    print("- 用戶沒有收到任何回應")
    print("- 處理過程中某個地方出錯了")


def main():
    """主函數"""
    print("🔍 Webhook 差異分析")
    print("=" * 50)

    analyze_webhook_discrepancy()
    test_specific_webhook_behavior()
    check_zeabur_service_logs()
    provide_troubleshooting_steps()
    simulate_expected_behavior()

    print("\n" + "=" * 50)
    print("💡 總結:")
    print("✅ Webhook URL 設置正確")
    print("❌ 但服務處理時返回 500 錯誤")
    print("🔧 需要修復 Notion API 連接")
    print("📋 需要查看詳細的服務日誌")


if __name__ == "__main__":
    main()
