#!/usr/bin/env python3
"""
測試連接池修復效果
模擬並發請求檢查是否還有 Pool timeout 錯誤
"""

import asyncio
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

def test_webhook_concurrency():
    """測試 webhook 並發處理能力"""
    print("🧪 測試 Telegram Bot 並發處理能力")
    print("=" * 50)
    
    app_url = "https://namecard-app.zeabur.app"
    webhook_url = f"{app_url}/telegram-webhook"
    
    # 模擬圖片上傳請求
    mock_photo_request = {
        "update_id": None,  # 會動態設置
        "message": {
            "message_id": None,  # 會動態設置
            "from": {"id": 123, "is_bot": False, "first_name": "Test"},
            "chat": {"id": 123, "type": "private"},
            "date": 1609459200,
            "photo": [
                {
                    "file_id": "test_file_id",
                    "file_unique_id": "test_unique_id",
                    "file_size": 1000,
                    "width": 100,
                    "height": 100
                }
            ]
        }
    }
    
    def send_single_request(request_id):
        """發送單個請求"""
        try:
            # 為每個請求設置唯一 ID
            request_data = mock_photo_request.copy()
            request_data["update_id"] = 999000 + request_id
            request_data["message"]["message_id"] = 1000 + request_id
            
            start_time = time.time()
            response = requests.post(
                webhook_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            end_time = time.time()
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_text": response.text[:50],
                "duration": round(end_time - start_time, 2),
                "success": response.status_code == 200
            }
            
        except Exception as e:
            return {
                "request_id": request_id,
                "status_code": 0,
                "response_text": f"Error: {str(e)[:50]}",
                "duration": 0,
                "success": False,
                "error": str(e)
            }
    
    # 測試不同並發級別
    concurrency_levels = [1, 3, 5, 10]
    
    for concurrency in concurrency_levels:
        print(f"\n📊 測試並發級別: {concurrency} 個同時請求")
        print("-" * 40)
        
        start_time = time.time()
        
        # 使用線程池發送並發請求
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(send_single_request, i) 
                for i in range(concurrency)
            ]
            
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = round(end_time - start_time, 2)
        
        # 分析結果
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = len(results) - successful_requests
        avg_duration = sum(r["duration"] for r in results) / len(results)
        
        print(f"   ✅ 成功請求: {successful_requests}/{len(results)}")
        print(f"   ❌ 失敗請求: {failed_requests}")
        print(f"   ⏱️  平均響應時間: {avg_duration:.2f} 秒")
        print(f"   🚀 總處理時間: {total_time} 秒")
        
        # 檢查是否有連接池錯誤
        pool_timeout_errors = [
            r for r in results 
            if "Pool timeout" in r.get("error", "") or "Pool timeout" in r["response_text"]
        ]
        
        if pool_timeout_errors:
            print(f"   🚨 發現 {len(pool_timeout_errors)} 個連接池超時錯誤！")
            for error in pool_timeout_errors:
                print(f"      - 請求 {error['request_id']}: {error.get('error', 'Unknown')}")
        else:
            print(f"   ✅ 沒有連接池超時錯誤")
        
        # 檢查其他錯誤
        other_errors = [r for r in results if not r["success"] and r not in pool_timeout_errors]
        if other_errors:
            print(f"   ⚠️  其他錯誤: {len(other_errors)} 個")
            for error in other_errors[:3]:  # 只顯示前3個
                print(f"      - 請求 {error['request_id']}: {error['response_text']}")

def test_health_check():
    """測試基本健康檢查"""
    print("\n🏥 基本健康檢查")
    print("=" * 30)
    
    try:
        response = requests.get("https://namecard-app.zeabur.app/health", timeout=10)
        if response.status_code == 200:
            print("✅ 服務運行正常")
            return True
        else:
            print(f"❌ 服務異常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 無法連接服務: {e}")
        return False

def main():
    print("🔍 Telegram Bot 連接池修復驗證")
    print("=" * 60)
    
    # 基本健康檢查
    if not test_health_check():
        print("❌ 基本健康檢查失敗，停止測試")
        return
    
    # 並發測試
    test_webhook_concurrency()
    
    print("\n" + "=" * 60)
    print("📊 測試完成！")
    print()
    print("🎯 修復效果評估:")
    print("• 如果沒有 'Pool timeout' 錯誤 → ✅ 修復成功")
    print("• 如果高並發成功率 > 80% → ✅ 性能正常")
    print("• 如果響應時間 < 10 秒 → ✅ 速度滿足要求")
    print()
    print("⏱️  建議等待 5 分鐘讓部署完成，然後重新測試")

if __name__ == "__main__":
    main()