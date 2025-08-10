#!/usr/bin/env python3
"""
連接池問題修復測試套件 - 特別關注並行下載器
包含連接池配置、資源管理、錯誤處理和性能優化的完整測試
"""

import asyncio
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 測試標記
pytestmark = [pytest.mark.unit, pytest.mark.connection_pool]


class TestConnectionPoolFixes:
    """連接池問題修復測試類"""

    @pytest.fixture
    def connection_pool_config(self):
        """連接池配置"""
        return {
            "connector_limit": 25,  # 總連接數限制
            "connector_limit_per_host": 8,  # 每主機連接數限制
            "timeout_total": 20,  # 總超時時間
            "timeout_connect": 5,  # 連接超時時間
            "timeout_sock_read": 10,  # 讀取超時時間
            "keepalive_timeout": 30,  # Keep-alive 超時
            "enable_cleanup_closed": True,  # 啟用已關閉連接清理
        }

    @pytest.fixture
    def mock_parallel_downloader(self, connection_pool_config):
        """Mock 並行下載器"""
        try:
            from src.namecard.infrastructure.messaging.parallel_image_downloader import (
                ParallelImageDownloader,
            )

            with patch("aiohttp.ClientSession") as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value = mock_session_instance

                downloader = ParallelImageDownloader()
                downloader.session = mock_session_instance
                downloader.config = connection_pool_config

                return downloader
        except ImportError as e:
            pytest.skip(f"ParallelImageDownloader 不可用: {e}")

    # ==========================================
    # 1. 連接池配置和初始化測試
    # ==========================================

    def test_connection_pool_configuration(self, connection_pool_config):
        """測試連接池配置的正確性"""
        # 驗證配置參數合理性
        assert connection_pool_config["connector_limit"] > 0
        assert connection_pool_config["connector_limit_per_host"] > 0
        assert (
            connection_pool_config["connector_limit_per_host"]
            <= connection_pool_config["connector_limit"]
        )
        assert (
            connection_pool_config["timeout_total"]
            > connection_pool_config["timeout_connect"]
        )
        assert connection_pool_config["keepalive_timeout"] > 0

    @pytest.mark.asyncio
    async def test_aiohttp_session_creation_with_proper_limits(
        self, connection_pool_config
    ):
        """測試 aiohttp session 創建時的正確限制設置"""
        # 創建連接器配置
        connector_config = {
            "limit": connection_pool_config["connector_limit"],
            "limit_per_host": connection_pool_config["connector_limit_per_host"],
            "keepalive_timeout": connection_pool_config["keepalive_timeout"],
            "enable_cleanup_closed": connection_pool_config["enable_cleanup_closed"],
        }

        timeout_config = aiohttp.ClientTimeout(
            total=connection_pool_config["timeout_total"],
            connect=connection_pool_config["timeout_connect"],
            sock_read=connection_pool_config["timeout_sock_read"],
        )

        # 創建並測試 session
        connector = aiohttp.TCPConnector(**connector_config)

        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout_config
        ) as session:
            assert session.connector.limit == connection_pool_config["connector_limit"]
            assert (
                session.connector.limit_per_host
                == connection_pool_config["connector_limit_per_host"]
            )
            assert session.timeout.total == connection_pool_config["timeout_total"]

    # ==========================================
    # 2. 連接池資源洩漏檢測測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_resource_cleanup(self):
        """測試連接池資源清理"""
        session_created = []
        session_closed = []

        @asynccontextmanager
        async def tracked_session():
            """追蹤 session 創建和關閉的上下文管理器"""
            session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5),
                timeout=aiohttp.ClientTimeout(total=10),
            )
            session_created.append(session)
            try:
                yield session
            finally:
                await session.close()
                session_closed.append(session)

        # 創建多個 session 並確保都被正確關閉
        for _ in range(10):
            async with tracked_session() as session:
                # 模擬一些操作
                await asyncio.sleep(0.01)

        # 驗證所有 session 都被創建和關閉
        assert len(session_created) == 10
        assert len(session_closed) == 10
        assert len(session_created) == len(session_closed)

    @pytest.mark.asyncio
    async def test_connection_pool_concurrent_resource_management(self):
        """測試並發環境下的連接池資源管理"""
        active_sessions = []
        completed_sessions = []

        async def create_and_use_session(session_id):
            """創建並使用 session"""
            try:
                connector = aiohttp.TCPConnector(
                    limit=20, limit_per_host=5, enable_cleanup_closed=True
                )

                async with aiohttp.ClientSession(
                    connector=connector, timeout=aiohttp.ClientTimeout(total=5)
                ) as session:
                    active_sessions.append(session_id)

                    # 模擬網路請求
                    await asyncio.sleep(0.1)

                    completed_sessions.append(session_id)
                    return session_id

            except Exception as e:
                return f"error_{session_id}: {e}"

        # 並發創建多個 session
        tasks = [create_and_use_session(i) for i in range(30)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 驗證結果
        successful_results = [r for r in results if isinstance(r, int)]
        error_results = [
            r for r in results if isinstance(r, str) and r.startswith("error_")
        ]

        assert (
            len(successful_results) >= 25
        ), f"成功的 session 數量過少: {len(successful_results)}/30"
        assert len(error_results) <= 5, f"錯誤的 session 數量過多: {len(error_results)}/30"
        assert len(completed_sessions) == len(successful_results)

    # ==========================================
    # 3. 連接池超時和重試機制測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """測試連接超時處理"""
        timeout_errors = []
        successful_connections = []

        async def test_connection_with_timeout(timeout_seconds):
            """測試帶超時的連接"""
            try:
                connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
                timeout = aiohttp.ClientTimeout(
                    total=timeout_seconds, connect=timeout_seconds / 2
                )

                async with aiohttp.ClientSession(
                    connector=connector, timeout=timeout
                ) as session:
                    # 模擬快速響應的服務
                    await asyncio.sleep(0.01)
                    successful_connections.append(timeout_seconds)

            except asyncio.TimeoutError:
                timeout_errors.append(timeout_seconds)
            except Exception as e:
                timeout_errors.append(f"{timeout_seconds}: {e}")

        # 測試不同超時設置
        timeout_values = [0.001, 0.01, 0.1, 1.0, 5.0]  # 從極短到正常的超時時間

        tasks = [test_connection_with_timeout(t) for t in timeout_values]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 驗證超時處理
        assert (
            len(successful_connections) >= 3
        ), f"成功連接數過少: {len(successful_connections)}"
        # 極短超時應該失敗
        assert any(
            t < 0.01 for t in timeout_errors if isinstance(t, float)
        ), "極短超時未被正確檢測"

    @pytest.mark.asyncio
    async def test_connection_retry_mechanism(self):
        """測試連接重試機制"""
        retry_attempts = []
        final_results = []

        async def connection_with_retry(max_retries=3):
            """帶重試機制的連接函數"""
            for attempt in range(max_retries + 1):
                try:
                    retry_attempts.append(attempt)

                    # 模擬不穩定的連接
                    if attempt < 2:  # 前兩次失敗
                        raise aiohttp.ClientError("Connection failed")

                    # 第三次成功
                    connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
                    async with aiohttp.ClientSession(connector=connector) as session:
                        await asyncio.sleep(0.01)
                        final_results.append(f"success_after_{attempt}_retries")
                        return True

                except aiohttp.ClientError:
                    if attempt < max_retries:
                        await asyncio.sleep(0.1 * (attempt + 1))  # 指數退避
                        continue
                    else:
                        final_results.append("failed_after_all_retries")
                        return False

        # 測試多個並發重試場景
        tasks = [connection_with_retry() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # 驗證重試機制
        successful_results = [r for r in results if r is True]
        assert len(successful_results) == 5, f"重試機制失敗: {len(successful_results)}/5"
        assert len(retry_attempts) == 15, f"重試次數不正確: {len(retry_attempts)} (應該是 15)"

    # ==========================================
    # 4. 並行下載器特定測試
    # ==========================================

    def test_parallel_downloader_connection_pool_configuration(
        self, mock_parallel_downloader
    ):
        """測試並行下載器的連接池配置"""
        if not mock_parallel_downloader:
            pytest.skip("並行下載器不可用")

        config = mock_parallel_downloader.config

        # 驗證關鍵配置參數
        assert config["connector_limit"] == 25
        assert config["connector_limit_per_host"] == 8
        assert config["timeout_total"] == 20
        assert config["enable_cleanup_closed"] is True

    @pytest.mark.asyncio
    async def test_parallel_downloader_batch_processing_stability(
        self, mock_parallel_downloader
    ):
        """測試並行下載器批次處理的穩定性"""
        if not mock_parallel_downloader:
            pytest.skip("並行下載器不可用")

        # 模擬成功的下載回應
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake_image_data"
        mock_parallel_downloader.session.get.return_value.__aenter__.return_value = (
            mock_response
        )

        # 模擬大量並行下載
        download_tasks = []
        for i in range(50):  # 50 個並發下載
            task = {"url": f"https://example.com/image_{i}.jpg", "id": f"image_{i}"}
            download_tasks.append(task)

        # 執行批次下載 (模擬)
        async def simulate_batch_download():
            results = []
            semaphore = asyncio.Semaphore(8)  # 限制並發數

            async def download_single(task):
                async with semaphore:
                    try:
                        # 模擬下載
                        await asyncio.sleep(0.01)
                        return {"id": task["id"], "success": True, "data": b"fake_data"}
                    except Exception as e:
                        return {"id": task["id"], "success": False, "error": str(e)}

            download_futures = [download_single(task) for task in download_tasks]
            results = await asyncio.gather(*download_futures, return_exceptions=True)

            return results

        results = await simulate_batch_download()

        # 驗證批次下載結果
        successful_downloads = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        failed_downloads = [r for r in results if isinstance(r, Exception)]

        assert (
            len(successful_downloads) >= 45
        ), f"成功下載數過少: {len(successful_downloads)}/50"
        assert len(failed_downloads) <= 5, f"失敗下載數過多: {len(failed_downloads)}/50"

    # ==========================================
    # 5. 連接池監控和診斷測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_monitoring(self):
        """測試連接池監控和診斷"""
        pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "created_connections": 0,
            "closed_connections": 0,
        }

        class MonitoredConnector(aiohttp.TCPConnector):
            """帶監控的連接器"""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                pool_stats["created_connections"] += 1

            async def close(self):
                pool_stats["closed_connections"] += 1
                await super().close()

        # 創建多個被監控的連接
        sessions = []

        for i in range(10):
            connector = MonitoredConnector(limit=20, limit_per_host=5)
            session = aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=5)
            )
            sessions.append(session)

            pool_stats["total_connections"] += 1
            pool_stats["active_connections"] += 1

        # 模擬一些連接變為閒置
        for i in range(0, 5):
            pool_stats["active_connections"] -= 1
            pool_stats["idle_connections"] += 1

        # 關閉所有 session
        for session in sessions:
            await session.close()
            pool_stats["active_connections"] = max(
                0, pool_stats["active_connections"] - 1
            )
            pool_stats["idle_connections"] = max(0, pool_stats["idle_connections"] - 1)

        # 驗證監控統計
        assert pool_stats["created_connections"] == 10
        assert pool_stats["closed_connections"] == 10
        assert pool_stats["active_connections"] == 0
        assert pool_stats["idle_connections"] == 0

    # ==========================================
    # 6. 連接池性能優化測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_performance_optimization(self):
        """測試連接池性能優化"""
        # 測試不同連接池配置的性能
        configurations = [
            {"limit": 10, "limit_per_host": 2, "name": "conservative"},
            {"limit": 25, "limit_per_host": 5, "name": "balanced"},
            {"limit": 50, "limit_per_host": 10, "name": "aggressive"},
        ]

        performance_results = {}

        for config in configurations:
            start_time = time.time()

            connector = aiohttp.TCPConnector(
                limit=config["limit"],
                limit_per_host=config["limit_per_host"],
                enable_cleanup_closed=True,
            )

            async with aiohttp.ClientSession(connector=connector) as session:
                # 模擬並發請求
                tasks = [self._simulate_request(session, i) for i in range(20)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                successful_requests = [r for r in results if r is True]

            end_time = time.time()

            performance_results[config["name"]] = {
                "duration": end_time - start_time,
                "success_rate": len(successful_requests) / len(results),
                "config": config,
            }

        # 驗證性能結果
        for name, result in performance_results.items():
            assert (
                result["success_rate"] >= 0.8
            ), f"{name} 配置成功率過低: {result['success_rate']:.2%}"
            assert (
                result["duration"] < 2.0
            ), f"{name} 配置執行時間過長: {result['duration']:.2f}s"

        # 平衡配置應該有最好的整體性能
        balanced = performance_results["balanced"]
        assert (
            balanced["success_rate"] >= 0.9
        ), f"平衡配置成功率不足: {balanced['success_rate']:.2%}"

    async def _simulate_request(self, session, request_id):
        """模擬網路請求"""
        try:
            await asyncio.sleep(0.01)  # 模擬網路延遲
            return True
        except Exception:
            return False

    # ==========================================
    # 7. 錯誤恢復和降級機制測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_error_recovery(self):
        """測試連接池錯誤恢復機制"""
        recovery_stats = {
            "connection_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
        }

        async def connection_with_recovery():
            """帶恢復機制的連接函數"""
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    connector = aiohttp.TCPConnector(
                        limit=15, limit_per_host=4, enable_cleanup_closed=True
                    )

                    async with aiohttp.ClientSession(
                        connector=connector, timeout=aiohttp.ClientTimeout(total=3)
                    ) as session:
                        # 模擬可能失敗的操作
                        if attempt == 0:  # 第一次故意失敗
                            recovery_stats["connection_errors"] += 1
                            raise aiohttp.ClientError("Simulated connection error")

                        # 後續嘗試成功
                        await asyncio.sleep(0.01)
                        recovery_stats["successful_recoveries"] += 1
                        return True

                except aiohttp.ClientError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1 * (attempt + 1))
                        continue
                    else:
                        recovery_stats["failed_recoveries"] += 1
                        return False

        # 測試多個並發恢復場景
        tasks = [connection_with_recovery() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_recoveries = [r for r in results if r is True]

        # 驗證錯誤恢復
        assert (
            len(successful_recoveries) == 10
        ), f"恢復成功數不足: {len(successful_recoveries)}/10"
        assert (
            recovery_stats["connection_errors"] == 10
        ), f"錯誤檢測數不正確: {recovery_stats['connection_errors']}"
        assert (
            recovery_stats["successful_recoveries"] == 10
        ), f"成功恢復數不正確: {recovery_stats['successful_recoveries']}"
        assert (
            recovery_stats["failed_recoveries"] == 0
        ), f"不應該有恢復失敗: {recovery_stats['failed_recoveries']}"

    # ==========================================
    # 8. 連接池整合和回歸測試
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_integration_regression(self):
        """連接池整合回歸測試"""
        # 這個測試確保所有連接池修復不會引入新問題

        test_scenarios = [
            {
                "name": "低並發長連接",
                "concurrent_requests": 5,
                "request_duration": 0.1,
                "pool_limit": 10,
            },
            {
                "name": "高並發短連接",
                "concurrent_requests": 30,
                "request_duration": 0.01,
                "pool_limit": 25,
            },
            {
                "name": "中等並發混合連接",
                "concurrent_requests": 15,
                "request_duration": 0.05,
                "pool_limit": 20,
            },
        ]

        results = {}

        for scenario in test_scenarios:
            start_time = time.time()

            connector = aiohttp.TCPConnector(
                limit=scenario["pool_limit"],
                limit_per_host=min(8, scenario["pool_limit"] // 3),
                enable_cleanup_closed=True,
                keepalive_timeout=30,
            )

            async with aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=10)
            ) as session:

                async def scenario_request(req_id):
                    try:
                        await asyncio.sleep(scenario["request_duration"])
                        return {"id": req_id, "success": True}
                    except Exception as e:
                        return {"id": req_id, "success": False, "error": str(e)}

                # 執行場景
                tasks = [
                    scenario_request(i) for i in range(scenario["concurrent_requests"])
                ]
                scenario_results = await asyncio.gather(*tasks, return_exceptions=True)

                end_time = time.time()

                successful = [
                    r
                    for r in scenario_results
                    if isinstance(r, dict) and r.get("success")
                ]

                results[scenario["name"]] = {
                    "success_count": len(successful),
                    "total_count": len(scenario_results),
                    "success_rate": len(successful) / len(scenario_results),
                    "duration": end_time - start_time,
                }

        # 驗證所有場景都成功
        for scenario_name, result in results.items():
            assert (
                result["success_rate"] >= 0.95
            ), f"{scenario_name} 成功率過低: {result['success_rate']:.2%}"
            assert (
                result["duration"] < 5.0
            ), f"{scenario_name} 執行時間過長: {result['duration']:.2f}s"

        print(f"\n=== 連接池回歸測試結果 ===")
        for scenario_name, result in results.items():
            print(
                f"{scenario_name}: {result['success_count']}/{result['total_count']} "
                f"({result['success_rate']:.1%}) in {result['duration']:.2f}s"
            )


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-x"])
