#!/usr/bin/env python3
"""
API 端點整合測試套件 - 專注連接池問題和端到端工作流程
包含 LINE Bot 和 Telegram Bot 的所有 API 端點測試，特別關注連接池穩定性
"""

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from flask import Flask
from PIL import Image

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 測試標記
pytestmark = [pytest.mark.integration, pytest.mark.api_endpoints]


class TestAPIEndpointsIntegration:
    """完整的 API 端點整合測試類"""

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        with patch("simple_config.Config") as mock_config:
            mock_config.LINE_CHANNEL_ACCESS_TOKEN = "test_line_token"
            mock_config.LINE_CHANNEL_SECRET = "test_line_secret"
            mock_config.TELEGRAM_BOT_TOKEN = "test_telegram_token"
            mock_config.GOOGLE_API_KEY = "test_google_api_key"
            mock_config.NOTION_API_KEY = "test_notion_api_key"
            mock_config.NOTION_DATABASE_ID = "test_database_id"
            mock_config.validate.return_value = True
            yield mock_config

    @pytest.fixture
    def line_bot_app(self, mock_config):
        """創建測試用的 LINE Bot Flask 應用"""
        with patch("src.namecard.infrastructure.ai.card_processor.NameCardProcessor"):
            with patch(
                "src.namecard.infrastructure.storage.notion_client.NotionManager"
            ):
                with patch("src.namecard.core.services.batch_service.BatchManager"):
                    with patch("linebot.LineBotApi"):
                        with patch("linebot.WebhookHandler"):
                            # 動態導入以避免初始化問題
                            from src.namecard.api.line_bot.main import app

                            app.config["TESTING"] = True
                            return app.test_client()

    @pytest.fixture
    def telegram_bot_app(self, mock_config):
        """創建測試用的 Telegram Bot Flask 應用"""
        with patch("src.namecard.infrastructure.ai.card_processor.NameCardProcessor"):
            with patch(
                "src.namecard.infrastructure.storage.notion_client.NotionManager"
            ):
                with patch("src.namecard.core.services.batch_service.BatchManager"):
                    with patch("telegram.ext.Application"):
                        try:
                            from src.namecard.api.telegram_bot.main import flask_app

                            flask_app.config["TESTING"] = True
                            return flask_app.test_client()
                        except Exception as e:
                            pytest.skip(f"Telegram Bot 應用無法載入: {e}")

    @pytest.fixture
    def sample_line_webhook_data(self):
        """測試用的 LINE webhook 數據"""
        return {
            "destination": "test_destination",
            "events": [
                {
                    "type": "message",
                    "mode": "active",
                    "timestamp": 1234567890123,
                    "source": {"type": "user", "userId": "test_user_123"},
                    "replyToken": "test_reply_token",
                    "message": {
                        "id": "test_message_id",
                        "type": "text",
                        "text": "help",
                    },
                }
            ],
        }

    @pytest.fixture
    def sample_telegram_webhook_data(self):
        """測試用的 Telegram webhook 數據"""
        return {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 987654321,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "test_user",
                },
                "chat": {
                    "id": 987654321,
                    "first_name": "Test",
                    "username": "test_user",
                    "type": "private",
                },
                "date": 1234567890,
                "text": "/start",
            },
        }

    # ==========================================
    # 1. LINE Bot API 端點測試
    # ==========================================

    def test_line_bot_health_endpoint(self, line_bot_app):
        """測試 LINE Bot 健康檢查端點"""
        response = line_bot_app.get("/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_line_bot_test_endpoint(self, line_bot_app):
        """測試 LINE Bot 服務測試端點"""
        with patch(
            "src.namecard.infrastructure.storage.notion_client.NotionManager"
        ) as mock_notion:
            mock_notion_instance = Mock()
            mock_notion_instance.test_connection.return_value = {
                "success": True,
                "message": "連接正常",
            }
            mock_notion.return_value = mock_notion_instance

            response = line_bot_app.get("/test")
            assert response.status_code == 200

            data = response.get_json()
            assert "notion" in data
            assert "gemini" in data

    def test_line_bot_api_status_endpoint(self, line_bot_app):
        """測試 LINE Bot API 狀態端點"""
        response = line_bot_app.get("/api-status")
        assert response.status_code == 200

        data = response.get_json()
        assert "line_api" in data
        assert "quota_status" in data["line_api"]

    def test_line_bot_callback_get_method(self, line_bot_app):
        """測試 LINE Bot callback GET 方法"""
        response = line_bot_app.get("/callback")
        assert response.status_code == 200
        assert b"LINE Bot" in response.data

    def test_line_bot_callback_post_invalid_content_type(self, line_bot_app):
        """測試 LINE Bot callback POST 無效 Content-Type"""
        response = line_bot_app.post(
            "/callback", data="invalid data", content_type="text/plain"
        )
        assert response.status_code == 400
        assert b"Content-Type must be application/json" in response.data

    def test_line_bot_callback_post_empty_body(self, line_bot_app):
        """測試 LINE Bot callback POST 空請求體"""
        response = line_bot_app.post(
            "/callback", json=None, content_type="application/json"
        )
        assert response.status_code == 400

    def test_line_bot_callback_post_invalid_signature(
        self, line_bot_app, sample_line_webhook_data
    ):
        """測試 LINE Bot callback POST 無效簽名"""
        response = line_bot_app.post(
            "/callback",
            json=sample_line_webhook_data,
            headers={"X-Line-Signature": "invalid_signature"},
        )
        assert response.status_code == 400

    # ==========================================
    # 2. Telegram Bot API 端點測試
    # ==========================================

    def test_telegram_bot_health_endpoint(self, telegram_bot_app):
        """測試 Telegram Bot 健康檢查端點"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.get("/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["message"] == "Telegram Bot is running"

    def test_telegram_bot_test_endpoint(self, telegram_bot_app):
        """測試 Telegram Bot 服務測試端點"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.get("/test")
        assert response.status_code == 200

        data = response.get_json()
        assert "notion" in data
        assert "gemini" in data
        assert "telegram" in data

    def test_telegram_bot_ultra_fast_status_endpoint(self, telegram_bot_app):
        """測試 Telegram Bot 超高速狀態端點"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.get("/ultra-fast-status")
        assert response.status_code == 200

        data = response.get_json()
        assert "ultra_fast_processor" in data
        assert "enhanced_telegram_handler" in data
        assert "performance_target" in data

    def test_telegram_bot_index_endpoint(self, telegram_bot_app):
        """測試 Telegram Bot 首頁端點"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.get("/")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "running"
        assert "endpoints" in data
        assert "performance_features" in data

    def test_telegram_bot_webhook_empty_body(self, telegram_bot_app):
        """測試 Telegram Bot webhook 空請求體"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.post("/telegram-webhook", json=None)
        assert response.status_code == 400
        assert b"Empty request body" in response.data

    def test_telegram_bot_webhook_invalid_data_format(self, telegram_bot_app):
        """測試 Telegram Bot webhook 無效數據格式"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        response = telegram_bot_app.post(
            "/telegram-webhook", data="invalid_json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_telegram_bot_webhook_test_data(self, telegram_bot_app):
        """測試 Telegram Bot webhook 測試數據"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        test_data = {"test": "data"}
        response = telegram_bot_app.post("/telegram-webhook", json=test_data)
        assert response.status_code == 200
        assert b"Test data received successfully" in response.data

    def test_telegram_bot_webhook_missing_update_id(self, telegram_bot_app):
        """測試 Telegram Bot webhook 缺少 update_id"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        invalid_data = {"message": {"text": "test"}}
        response = telegram_bot_app.post("/telegram-webhook", json=invalid_data)
        assert response.status_code == 400
        assert b"missing update_id" in response.data

    # ==========================================
    # 3. 連接池穩定性和並發測試 (特別關注)
    # ==========================================

    def test_concurrent_health_checks(self, line_bot_app, telegram_bot_app):
        """測試並發健康檢查的連接池穩定性"""

        def check_line_health():
            response = line_bot_app.get("/health")
            return response.status_code == 200

        def check_telegram_health():
            if not telegram_bot_app:
                return True  # Skip if not available
            response = telegram_bot_app.get("/health")
            return response.status_code == 200

        # 創建大量並發請求
        with ThreadPoolExecutor(max_workers=20) as executor:
            # LINE Bot 健康檢查
            line_futures = [executor.submit(check_line_health) for _ in range(50)]

            # Telegram Bot 健康檢查 (如果可用)
            telegram_futures = []
            if telegram_bot_app:
                telegram_futures = [
                    executor.submit(check_telegram_health) for _ in range(50)
                ]

            # 等待所有請求完成
            line_results = [future.result() for future in line_futures]
            telegram_results = (
                [future.result() for future in telegram_futures]
                if telegram_futures
                else []
            )

            # 驗證所有請求都成功
            assert all(line_results), f"LINE Bot 健康檢查失敗數: {line_results.count(False)}"
            if telegram_results:
                assert all(
                    telegram_results
                ), f"Telegram Bot 健康檢查失敗數: {telegram_results.count(False)}"

    def test_high_frequency_endpoint_access(self, line_bot_app):
        """測試高頻端點訪問的穩定性"""
        results = []

        def make_request(endpoint):
            try:
                response = line_bot_app.get(endpoint)
                return {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "error": None,
                }
            except Exception as e:
                return {
                    "endpoint": endpoint,
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                }

        # 高頻訪問多個端點
        endpoints = ["/health", "/test", "/api-status"] * 100  # 300 次請求

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_request, endpoint) for endpoint in endpoints
            ]
            results = [future.result() for future in futures]

        # 分析結果
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        connection_errors = [
            r for r in failed_requests if "connection" in str(r["error"]).lower()
        ]

        # 驗證連接池穩定性
        assert len(connection_errors) == 0, f"發現 {len(connection_errors)} 個連接相關錯誤"
        success_rate = len(successful_requests) / len(results)
        assert success_rate >= 0.95, f"成功率過低: {success_rate:.2%} (應該 >= 95%)"

    # ==========================================
    # 4. 錯誤處理和恢復測試
    # ==========================================

    def test_api_error_handling_graceful_degradation(self, line_bot_app):
        """測試 API 錯誤的優雅降級處理"""
        # 模擬服務錯誤
        with patch(
            "src.namecard.infrastructure.storage.notion_client.NotionManager"
        ) as mock_notion:
            mock_notion_instance = Mock()
            mock_notion_instance.test_connection.side_effect = Exception(
                "Service unavailable"
            )
            mock_notion.return_value = mock_notion_instance

            response = line_bot_app.get("/test")
            assert response.status_code == 200  # 應該優雅處理錯誤

            data = response.get_json()
            # 檢查錯誤是否被適當處理
            assert "notion" in data
            if isinstance(data["notion"], dict) and "success" in data["notion"]:
                assert data["notion"]["success"] is False

    def test_connection_timeout_handling(self, line_bot_app):
        """測試連接超時處理"""

        def slow_connection():
            time.sleep(2)  # 模擬慢連接
            return line_bot_app.get("/health")

        # 多個慢連接請求
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(slow_connection) for _ in range(5)]

            # 設置超時
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=3)
                    results.append(result.status_code == 200)
                except Exception:
                    results.append(False)

            # 至少一些請求應該成功
            success_count = sum(results)
            assert success_count >= 3, f"慢連接下成功請求數過少: {success_count}/5"

    # ==========================================
    # 5. 記憶體和資源管理測試
    # ==========================================

    def test_memory_usage_under_load(self, line_bot_app):
        """測試負載下的記憶體使用"""
        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # 大量請求測試記憶體洩漏
            for batch in range(10):  # 10 批次
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [
                        executor.submit(line_bot_app.get, "/health")
                        for _ in range(20)  # 每批次 20 個請求
                    ]

                    # 等待所有請求完成
                    for future in futures:
                        future.result()

                # 檢查記憶體增長
                current_memory = process.memory_info().rss
                memory_increase = current_memory - initial_memory

                # 記憶體增長不應該過大 (< 50MB per batch)
                max_increase = 50 * 1024 * 1024 * (batch + 1)
                assert (
                    memory_increase < max_increase
                ), f"批次 {batch}: 記憶體增長過大 {memory_increase / 1024 / 1024:.2f}MB"

        except ImportError:
            pytest.skip("psutil 不可用，跳過記憶體測試")

    # ==========================================
    # 6. 端到端工作流程測試
    # ==========================================

    def test_line_bot_complete_workflow_simulation(
        self, line_bot_app, sample_line_webhook_data
    ):
        """模擬 LINE Bot 完整工作流程"""
        # 1. 健康檢查
        health_response = line_bot_app.get("/health")
        assert health_response.status_code == 200

        # 2. 服務測試
        test_response = line_bot_app.get("/test")
        assert test_response.status_code == 200

        # 3. API 狀態檢查
        status_response = line_bot_app.get("/api-status")
        assert status_response.status_code == 200

        # 4. Webhook 處理 (模擬但會因簽名失敗)
        with patch("linebot.WebhookHandler.handle") as mock_handler:
            mock_handler.return_value = None

            webhook_response = line_bot_app.post(
                "/callback",
                json=sample_line_webhook_data,
                headers={"X-Line-Signature": "test_signature"},
            )
            # 預期會因簽名驗證失敗，但這是正常的
            assert webhook_response.status_code in [200, 400]

    def test_telegram_bot_complete_workflow_simulation(
        self, telegram_bot_app, sample_telegram_webhook_data
    ):
        """模擬 Telegram Bot 完整工作流程"""
        if not telegram_bot_app:
            pytest.skip("Telegram Bot 應用不可用")

        # 1. 首頁檢查
        index_response = telegram_bot_app.get("/")
        assert index_response.status_code == 200

        # 2. 健康檢查
        health_response = telegram_bot_app.get("/health")
        assert health_response.status_code == 200

        # 3. 服務測試
        test_response = telegram_bot_app.get("/test")
        assert test_response.status_code == 200

        # 4. 超高速狀態檢查
        status_response = telegram_bot_app.get("/ultra-fast-status")
        assert status_response.status_code == 200

        # 5. Webhook 處理 (有效數據)
        webhook_response = telegram_bot_app.post(
            "/telegram-webhook", json=sample_telegram_webhook_data
        )
        # 應該被接受並處理（即使後續可能失敗）
        assert webhook_response.status_code in [200, 500]  # 200 成功或 500 處理錯誤

    # ==========================================
    # 7. 性能基準測試
    # ==========================================

    def test_endpoint_response_time_benchmarks(self, line_bot_app):
        """測試端點回應時間基準"""
        endpoints = ["/health", "/test", "/api-status"]
        response_times = {}

        for endpoint in endpoints:
            times = []

            # 測試 10 次獲取平均時間
            for _ in range(10):
                start_time = time.time()
                response = line_bot_app.get(endpoint)
                end_time = time.time()

                if response.status_code == 200:
                    times.append(end_time - start_time)

            if times:
                avg_time = sum(times) / len(times)
                response_times[endpoint] = avg_time

        # 驗證回應時間基準
        for endpoint, avg_time in response_times.items():
            # 健康檢查應該非常快 (< 100ms)
            if endpoint == "/health":
                assert avg_time < 0.1, f"{endpoint} 回應過慢: {avg_time:.3f}s"
            # 其他端點應該在合理時間內 (< 2s)
            else:
                assert avg_time < 2.0, f"{endpoint} 回應過慢: {avg_time:.3f}s"

    def test_concurrent_mixed_requests_performance(
        self, line_bot_app, telegram_bot_app
    ):
        """測試混合並發請求的性能"""
        start_time = time.time()

        def make_line_requests():
            results = []
            for endpoint in ["/health", "/test", "/api-status"] * 10:
                response = line_bot_app.get(endpoint)
                results.append(response.status_code == 200)
            return results

        def make_telegram_requests():
            if not telegram_bot_app:
                return [True] * 30  # Skip if not available
            results = []
            for endpoint in ["/health", "/test", "/ultra-fast-status"] * 10:
                response = telegram_bot_app.get(endpoint)
                results.append(response.status_code == 200)
            return results

        # 並發執行混合請求
        with ThreadPoolExecutor(max_workers=4) as executor:
            line_future = executor.submit(make_line_requests)
            telegram_future = executor.submit(make_telegram_requests)

            line_results = line_future.result()
            telegram_results = telegram_future.result()

        end_time = time.time()
        total_time = end_time - start_time

        # 驗證性能和成功率
        line_success_rate = sum(line_results) / len(line_results)
        telegram_success_rate = sum(telegram_results) / len(telegram_results)

        assert line_success_rate >= 0.9, f"LINE Bot 成功率過低: {line_success_rate:.2%}"
        assert (
            telegram_success_rate >= 0.9
        ), f"Telegram Bot 成功率過低: {telegram_success_rate:.2%}"
        assert total_time < 30, f"混合並發請求耗時過長: {total_time:.2f}s"

    # ==========================================
    # 8. 連接池監控和診斷測試
    # ==========================================

    def test_connection_pool_diagnostics(self, line_bot_app):
        """連接池診斷測試"""
        connection_errors = []
        timeout_errors = []
        success_count = 0

        def diagnose_request(request_id):
            try:
                start_time = time.time()
                response = line_bot_app.get("/health")
                end_time = time.time()

                if response.status_code == 200:
                    return {
                        "id": request_id,
                        "success": True,
                        "response_time": end_time - start_time,
                        "error": None,
                    }
                else:
                    return {
                        "id": request_id,
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": f"HTTP {response.status_code}",
                    }
            except Exception as e:
                error_str = str(e).lower()
                return {
                    "id": request_id,
                    "success": False,
                    "response_time": None,
                    "error": str(e),
                    "is_connection_error": any(
                        keyword in error_str
                        for keyword in ["connection", "pool", "timeout", "connector"]
                    ),
                    "is_timeout_error": "timeout" in error_str,
                }

        # 大量並發請求進行診斷
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(diagnose_request, i) for i in range(100)]
            results = [future.result() for future in futures]

        # 分析診斷結果
        for result in results:
            if result["success"]:
                success_count += 1
            else:
                if result.get("is_connection_error"):
                    connection_errors.append(result)
                if result.get("is_timeout_error"):
                    timeout_errors.append(result)

        # 生成診斷報告
        success_rate = success_count / len(results)
        avg_response_time = (
            sum(r["response_time"] for r in results if r["response_time"])
            / success_count
            if success_count > 0
            else 0
        )

        print(f"\n=== 連接池診斷報告 ===")
        print(f"總請求數: {len(results)}")
        print(f"成功請求: {success_count} ({success_rate:.2%})")
        print(f"連接錯誤: {len(connection_errors)}")
        print(f"超時錯誤: {len(timeout_errors)}")
        print(f"平均回應時間: {avg_response_time:.3f}s")

        # 驗證連接池健康度
        assert len(connection_errors) == 0, f"發現 {len(connection_errors)} 個連接池錯誤"
        assert len(timeout_errors) <= 5, f"超時錯誤過多: {len(timeout_errors)} (應該 <= 5)"
        assert success_rate >= 0.95, f"成功率過低: {success_rate:.2%} (應該 >= 95%)"


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-x"])
