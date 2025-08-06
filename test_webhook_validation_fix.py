#!/usr/bin/env python3
"""
測試 Telegram webhook 驗證修復效果
"""

import json
import os
import sys
import time

import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def test_invalid_data_handling():
    """測試無效數據處理"""
    print("🔍 Step 1: 測試無效數據處理")
    print("-" * 40)

    test_cases = [
        {
            "name": "測試數據 (應該正常處理)",
            "data": {"test": "data"},
            "expected_status": 200,
        },
        {
            "name": "缺少 update_id 的數據",
            "data": {"message": {"text": "hello"}},
            "expected_status": 400,
        },
        {"name": "空數據", "data": {}, "expected_status": 400},
        {"name": "非字典數據", "data": "invalid", "expected_status": 400},
    ]

    results = {}

    for test_case in test_cases:
        print(f"\n🧪 測試: {test_case['name']}")

        try:
            response = requests.post(
                "https://namecard-app.zeabur.app/telegram-webhook",
                json=test_case["data"],
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            print(f"   回應狀態: {response.status_code}")
            print(f"   回應內容: {response.text}")

            # 檢查是否符合預期
            expected = test_case["expected_status"]
            if response.status_code == expected:
                print(f"   ✅ 符合預期 (預期: {expected})")
                results[test_case["name"]] = True
            else:
                print(
                    f"   ❌ 不符合預期 (預期: {expected}, 實際: {response.status_code})"
                )
                results[test_case["name"]] = False

        except Exception as e:
            print(f"   ❌ 請求失敗: {e}")
            results[test_case["name"]] = False

        time.sleep(1)  # 避免請求過於頻繁

    return results


def test_valid_telegram_updates():
    """測試有效的 Telegram 更新"""
    print("\n🔍 Step 2: 測試有效的 Telegram 更新")
    print("-" * 40)

    valid_updates = [
        {
            "name": "文字訊息",
            "data": {
                "update_id": 999998,
                "message": {
                    "message_id": 1,
                    "date": int(time.time()),
                    "chat": {"id": 597988605, "type": "private"},
                    "from": {"id": 597988605, "is_bot": False, "first_name": "Test"},
                    "text": "/start",
                },
            },
        },
        {
            "name": "圖片訊息",
            "data": {
                "update_id": 999997,
                "message": {
                    "message_id": 2,
                    "date": int(time.time()),
                    "chat": {"id": 597988605, "type": "private"},
                    "from": {"id": 597988605, "is_bot": False, "first_name": "Test"},
                    "photo": [
                        {
                            "file_id": "test_file_id",
                            "file_unique_id": "test_unique",
                            "width": 100,
                            "height": 100,
                            "file_size": 1000,
                        }
                    ],
                },
            },
        },
    ]

    results = {}

    for test_case in valid_updates:
        print(f"\n🧪 測試: {test_case['name']}")

        try:
            response = requests.post(
                "https://namecard-app.zeabur.app/telegram-webhook",
                json=test_case["data"],
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            print(f"   回應狀態: {response.status_code}")
            print(f"   回應內容: {response.text}")

            if response.status_code == 200:
                print(f"   ✅ 有效更新處理正常")
                results[test_case["name"]] = True
            else:
                print(f"   ❌ 有效更新處理失敗")
                results[test_case["name"]] = False

        except Exception as e:
            print(f"   ❌ 請求失敗: {e}")
            results[test_case["name"]] = False

        time.sleep(2)  # 給處理一些時間

    return results


def test_service_health():
    """測試服務健康狀態"""
    print("\n🔍 Step 3: 測試服務健康狀態")
    print("-" * 40)

    endpoints = [
        ("健康檢查", "https://namecard-app.zeabur.app/health"),
        ("服務測試", "https://namecard-app.zeabur.app/test"),
        ("首頁", "https://namecard-app.zeabur.app/"),
    ]

    results = {}

    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            print(f"   {name}: {response.status_code}")

            if response.status_code == 200:
                results[name] = True

                # 對於服務測試，檢查 JSON 內容
                if "test" in url:
                    data = response.json()
                    print(
                        f"      Notion: {'✅' if data.get('notion', {}).get('success') else '❌'}"
                    )
                    print(
                        f"      Gemini: {'✅' if data.get('gemini', {}).get('success') else '❌'}"
                    )
                    print(
                        f"      Telegram: {'✅' if data.get('telegram', {}).get('success') else '❌'}"
                    )
            else:
                results[name] = False

        except Exception as e:
            print(f"   {name}: ❌ {e}")
            results[name] = False

    return results


def main():
    """主測試函數"""
    print("🔧 Telegram Webhook 驗證修復測試")
    print("=" * 50)

    # 執行所有測試
    all_results = {}

    # 測試無效數據處理
    invalid_results = test_invalid_data_handling()
    all_results.update(invalid_results)

    # 測試有效更新處理
    valid_results = test_valid_telegram_updates()
    all_results.update(valid_results)

    # 測試服務健康
    health_results = test_service_health()
    all_results.update(health_results)

    # 總結結果
    print("\n" + "=" * 50)
    print("📊 測試結果總結")
    print("=" * 50)

    passed = 0
    total = len(all_results)

    for test_name, result in all_results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n📈 總體結果: {passed}/{total} 測試通過")

    if passed == total:
        print("🎉 所有測試通過！Webhook 驗證修復成功！")
        print("\n📱 您現在可以安全地測試 Telegram Bot:")
        print("1. 發送 /start 指令")
        print("2. 上傳名片圖片")
        print("3. 檢查是否收到正確回應")
    else:
        print("⚠️  部分測試失敗，可能需要進一步檢查")

    return passed == total


if __name__ == "__main__":
    main()
