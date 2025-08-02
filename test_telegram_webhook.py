#!/usr/bin/env python3
"""
Telegram Bot Webhook 測試工具
測試 Telegram Bot 各個端點和功能
"""

import json
import sys
import time
from datetime import datetime

import requests

# 測試配置
TELEGRAM_BOT_BASE_URL = "http://localhost:5003"  # 本地測試
# TELEGRAM_BOT_BASE_URL = "https://your-app.zeabur.app"  # 生產環境


def log_test(message, status="INFO"):
    """測試日誌輸出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    emoji = status_emoji.get(status, "🔍")
    print(f"[{timestamp}] {emoji} {message}")


def test_health_endpoint():
    """測試健康檢查端點"""
    log_test("測試健康檢查端點...", "INFO")
    try:
        response = requests.get(f"{TELEGRAM_BOT_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"健康檢查成功: {data}", "SUCCESS")
            return True
        else:
            log_test(f"健康檢查失敗: HTTP {response.status_code}", "ERROR")
    except Exception as e:
        log_test(f"健康檢查異常: {e}", "ERROR")
    return False


def test_service_status():
    """測試服務狀態端點"""
    log_test("測試服務狀態端點...", "INFO")
    try:
        response = requests.get(f"{TELEGRAM_BOT_BASE_URL}/test", timeout=15)
        if response.status_code == 200:
            data = response.json()
            log_test("服務狀態檢查結果:", "INFO")
            
            # 檢查各服務狀態
            services = ["notion", "gemini", "telegram"]
            for service in services:
                if service in data:
                    status = "SUCCESS" if data[service].get("success") else "ERROR"
                    message = data[service].get("message", data[service].get("error", "未知"))
                    log_test(f"  {service}: {message}", status)
                else:
                    log_test(f"  {service}: 未檢測到", "WARNING")
            return True
        else:
            log_test(f"服務狀態檢查失敗: HTTP {response.status_code}", "ERROR")
    except Exception as e:
        log_test(f"服務狀態檢查異常: {e}", "ERROR")
    return False


def test_webhook_get():
    """測試 GET webhook (應該返回錯誤或信息)"""
    log_test("測試 GET /telegram-webhook 端點...", "INFO")
    try:
        response = requests.get(f"{TELEGRAM_BOT_BASE_URL}/telegram-webhook", timeout=10)
        # GET 請求應該返回 405 Method Not Allowed 或其他錯誤
        if response.status_code == 405:
            log_test("GET webhook 正確返回 405 Method Not Allowed", "SUCCESS")
            return True
        else:
            log_test(f"GET webhook 返回: HTTP {response.status_code}", "WARNING")
            return True  # 不一定是錯誤
    except Exception as e:
        log_test(f"GET webhook 測試異常: {e}", "ERROR")
    return False


def test_webhook_post_invalid():
    """測試 POST webhook 無效數據"""
    log_test("測試 POST /telegram-webhook 無效數據...", "INFO")
    try:
        # 測試空數據
        response = requests.post(
            f"{TELEGRAM_BOT_BASE_URL}/telegram-webhook",
            json={},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("POST webhook 空數據正確返回 400", "SUCCESS")
        elif response.status_code == 200:
            log_test("POST webhook 接受了空數據 (可能正常)", "WARNING")
        else:
            log_test(f"POST webhook 返回: HTTP {response.status_code}", "INFO")
        
        return True
    except Exception as e:
        log_test(f"POST webhook 測試異常: {e}", "ERROR")
    return False


def test_webhook_post_mock():
    """測試 POST webhook 模擬 Telegram 更新"""
    log_test("測試 POST /telegram-webhook 模擬數據...", "INFO")
    
    # 模擬 Telegram 更新數據
    mock_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": int(time.time()),
            "chat": {
                "id": 12345,
                "type": "private"
            },
            "from": {
                "id": 12345,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "text": "/start"
        }
    }
    
    try:
        response = requests.post(
            f"{TELEGRAM_BOT_BASE_URL}/telegram-webhook",
            json=mock_update,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            log_test("POST webhook 模擬數據處理成功", "SUCCESS")
            return True
        else:
            log_test(f"POST webhook 模擬數據返回: HTTP {response.status_code}", "WARNING")
            if response.text:
                log_test(f"響應內容: {response.text[:200]}", "INFO")
    except Exception as e:
        log_test(f"POST webhook 模擬測試異常: {e}", "ERROR")
    return False


def test_index_endpoint():
    """測試首頁端點"""
    log_test("測試首頁端點...", "INFO")
    try:
        response = requests.get(f"{TELEGRAM_BOT_BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"首頁響應: {data.get('message', 'Unknown')}", "SUCCESS")
            return True
        else:
            log_test(f"首頁端點失敗: HTTP {response.status_code}", "ERROR")
    except Exception as e:
        log_test(f"首頁端點異常: {e}", "ERROR")
    return False


def run_all_tests():
    """運行所有測試"""
    log_test("🚀 開始 Telegram Bot Webhook 測試", "INFO")
    log_test(f"測試目標: {TELEGRAM_BOT_BASE_URL}", "INFO")
    print("=" * 60)
    
    tests = [
        ("健康檢查", test_health_endpoint),
        ("服務狀態", test_service_status),
        ("首頁端點", test_index_endpoint),
        ("GET Webhook", test_webhook_get),
        ("POST Webhook (無效)", test_webhook_post_invalid),
        ("POST Webhook (模擬)", test_webhook_post_mock),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 執行測試: {test_name}")
        try:
            if test_func():
                passed += 1
                log_test(f"測試 '{test_name}' 通過", "SUCCESS")
            else:
                log_test(f"測試 '{test_name}' 失敗", "ERROR")
        except Exception as e:
            log_test(f"測試 '{test_name}' 異常: {e}", "ERROR")
        
        print("-" * 40)
    
    print(f"\n📊 測試結果總結:")
    log_test(f"通過: {passed}/{total} 個測試", "SUCCESS" if passed == total else "WARNING")
    
    if passed == total:
        log_test("🎉 所有測試都通過了！Telegram Bot 運行正常", "SUCCESS")
        return True
    else:
        log_test(f"⚠️ 有 {total - passed} 個測試失敗，請檢查服務狀態", "WARNING")
        return False


def main():
    """主函數"""
    print(f"""
🤖 Telegram Bot Webhook 測試工具
================================
測試時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
測試目標: {TELEGRAM_BOT_BASE_URL}

注意事項:
1. 請確保 Telegram Bot 應用已經啟動
2. 如果測試生產環境，請更新 TELEGRAM_BOT_BASE_URL
3. 某些測試可能需要有效的 API 配置
""")
    
    try:
        success = run_all_tests()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        log_test("測試被用戶中斷", "WARNING")
        exit_code = 130
    except Exception as e:
        log_test(f"測試過程中發生未預期的錯誤: {e}", "ERROR")
        exit_code = 1
    
    print(f"\n🏁 測試完成，退出代碼: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()