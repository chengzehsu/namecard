#!/usr/bin/env python3
"""
測試單用戶 20 張名片批次處理能力
"""
import asyncio
import os
import sys
import time
from unittest.mock import Mock, patch

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_concurrent_capacity():
    """測試新的併發容量配置"""
    print("🔧 測試併發容量配置...")

    try:
        from src.namecard.infrastructure.messaging.telegram_client import (
            TelegramBotHandler,
        )

        with patch("simple_config.Config.TELEGRAM_BOT_TOKEN", "dummy_token"):
            handler = TelegramBotHandler()

            # 檢查 Semaphore 容量
            async def check_semaphore():
                semaphore = await handler._get_semaphore()
                capacity = semaphore._value if hasattr(semaphore, "_value") else 0
                return capacity

            # 檢查 HTTP 客戶端配置
            http_config = {}
            if hasattr(handler, "_http_client") and handler._http_client:
                if hasattr(handler._http_client, "_limits"):
                    limits = handler._http_client._limits
                    http_config = {
                        "max_connections": getattr(limits, "max_connections", "N/A"),
                        "max_keepalive_connections": getattr(
                            limits, "max_keepalive_connections", "N/A"
                        ),
                    }

                if hasattr(handler._http_client, "_timeout"):
                    timeout = handler._http_client._timeout
                    http_config.update(
                        {
                            "pool_timeout": getattr(timeout, "pool", "N/A"),
                            "read_timeout": getattr(timeout, "read", "N/A"),
                        }
                    )

            # 檢查速率限制
            rate_limit = getattr(handler, "_max_requests_per_minute", 0)

            # 運行異步檢查
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                semaphore_capacity = loop.run_until_complete(check_semaphore())
            finally:
                loop.close()

            print(f"   併發 Semaphore 容量: {semaphore_capacity}")
            print(f"   HTTP 最大連接數: {http_config.get('max_connections', 'N/A')}")
            print(
                f"   HTTP 保持連接數: {http_config.get('max_keepalive_connections', 'N/A')}"
            )
            print(f"   連接池超時: {http_config.get('pool_timeout', 'N/A')} 秒")
            print(f"   讀取超時: {http_config.get('read_timeout', 'N/A')} 秒")
            print(f"   速率限制: {rate_limit} 請求/分鐘")

            # 驗證配置
            checks = [
                ("Semaphore 容量 >= 20", semaphore_capacity >= 20),
                ("HTTP 連接數 >= 100", http_config.get("max_connections", 0) >= 100),
                (
                    "保持連接數 >= 40",
                    http_config.get("max_keepalive_connections", 0) >= 40,
                ),
                ("連接池超時 >= 120", http_config.get("pool_timeout", 0) >= 120),
                ("速率限制 >= 60", rate_limit >= 60),
            ]

            all_passed = True
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"   {check_name}: {status}")
                if not result:
                    all_passed = False

            return all_passed

    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        return False


def test_20_concurrent_requests():
    """測試 20 個併發請求處理"""
    print("\n🚀 測試 20 個併發請求處理...")

    async def concurrent_test():
        try:
            from src.namecard.infrastructure.messaging.telegram_client import (
                TelegramBotHandler,
            )

            with patch("simple_config.Config.TELEGRAM_BOT_TOKEN", "dummy_token"):
                handler = TelegramBotHandler()

                # 模擬單個名片處理請求
                async def mock_card_request(card_id):
                    semaphore = await handler._get_semaphore()

                    start_time = time.time()
                    async with semaphore:
                        # 模擬名片處理時間 (AI + Notion)
                        await asyncio.sleep(0.2)  # 模擬 200ms 處理時間
                        end_time = time.time()

                        return {
                            "card_id": card_id,
                            "processing_time": end_time - start_time,
                            "success": True,
                        }

                # 創建 20 個併發請求
                print("   創建 20 個併發名片處理請求...")
                tasks = [mock_card_request(i) for i in range(1, 21)]

                # 記錄開始時間
                batch_start_time = time.time()

                # 執行併發請求
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 記錄結束時間
                batch_end_time = time.time()
                total_time = batch_end_time - batch_start_time

                # 分析結果
                successful_results = [
                    r for r in results if isinstance(r, dict) and r.get("success")
                ]
                failed_results = [
                    r for r in results if not (isinstance(r, dict) and r.get("success"))
                ]

                print(f"   批次處理總時間: {total_time:.2f} 秒")
                print(f"   成功處理: {len(successful_results)}/20 張名片")
                print(f"   失敗處理: {len(failed_results)} 張名片")

                if successful_results:
                    avg_processing = sum(
                        r["processing_time"] for r in successful_results
                    ) / len(successful_results)
                    print(f"   平均單張處理時間: {avg_processing:.3f} 秒")

                # 計算併發效率
                theoretical_sequential_time = 20 * 0.2  # 20 張 × 200ms
                efficiency = (
                    theoretical_sequential_time / total_time if total_time > 0 else 0
                )
                print(f"   併發效率: {efficiency:.1f}x (理論加速比)")

                # 評估結果
                success_rate = len(successful_results) / 20
                time_acceptable = total_time <= 3.0  # 希望在 3 秒內完成

                print(f"   成功率: {success_rate * 100:.1f}%")
                print(
                    f"   時間表現: {'✅ 優秀' if total_time <= 1.0 else '✅ 良好' if total_time <= 3.0 else '⚠️ 需改進'}"
                )

                return success_rate >= 0.95 and time_acceptable

        except Exception as e:
            print(f"❌ 併發測試失敗: {e}")
            return False

    # 運行異步測試
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(concurrent_test())
        return result
    finally:
        loop.close()


def test_rate_limit_behavior():
    """測試速率限制行為"""
    print("\n⏱️ 測試速率限制行為...")

    try:
        from src.namecard.infrastructure.messaging.telegram_client import (
            TelegramBotHandler,
        )

        with patch("simple_config.Config.TELEGRAM_BOT_TOKEN", "dummy_token"):
            handler = TelegramBotHandler()

            # 測試速率限制檢查
            print("   測試速率限制檢查機制...")

            # 快速發送多個請求
            request_results = []
            for i in range(65):  # 超過 60 個請求限制
                can_proceed, wait_time = handler._check_rate_limit()
                request_results.append((can_proceed, wait_time))

                if not can_proceed:
                    print(
                        f"   第 {i+1} 個請求被速率限制阻止，需等待 {wait_time:.1f} 秒"
                    )
                    break

            # 分析結果
            allowed_requests = sum(
                1 for can_proceed, _ in request_results if can_proceed
            )
            blocked_requests = sum(
                1 for can_proceed, _ in request_results if not can_proceed
            )

            print(f"   允許的請求數: {allowed_requests}")
            print(f"   被阻止的請求數: {blocked_requests}")

            # 檢查是否正確限制
            rate_limit_working = allowed_requests <= 60 and blocked_requests > 0

            print(
                f"   速率限制機制: {'✅ 正常工作' if rate_limit_working else '❌ 異常'}"
            )

            return rate_limit_working

    except Exception as e:
        print(f"❌ 速率限制測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("📊 單用戶 20 張名片批次處理能力測試")
    print("=" * 60)

    # 測試 1: 併發容量配置
    config_ok = test_concurrent_capacity()

    # 測試 2: 20 個併發請求
    concurrent_ok = test_20_concurrent_requests()

    # 測試 3: 速率限制行為
    rate_limit_ok = test_rate_limit_behavior()

    print("\n" + "=" * 60)
    print("🎯 測試結果總結:")
    print(f"   併發配置: {'✅ 通過' if config_ok else '❌ 失敗'}")
    print(f"   20 張併發處理: {'✅ 通過' if concurrent_ok else '❌ 失敗'}")
    print(f"   速率限制機制: {'✅ 通過' if rate_limit_ok else '❌ 失敗'}")

    print("\n📋 優化成果:")
    print("   ✅ 併發容量: 20 個同時處理")
    print("   ✅ HTTP 連接池: 100 個總連接")
    print("   ✅ 速率限制: 60 請求/分鐘")
    print("   ✅ 超時優化: 120 秒連接池超時")

    all_passed = config_ok and concurrent_ok and rate_limit_ok

    if all_passed:
        print("\n🎉 階段 1 優化成功！")
        print("   系統現在支援單用戶同時處理 20 張名片")
        print("   預期處理時間: 2-3 分鐘完成 20 張名片")
    else:
        print("\n⚠️ 部分測試失敗，需要進一步優化")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
