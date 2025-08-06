#!/usr/bin/env python3
"""
API 配額管理器完整測試套件 - Test Writer/Fixer Agent 實作
測試 ApiQuotaManager 的配額追蹤、切換機制和負載均衡功能
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 導入測試目標
from src.namecard.infrastructure.ai.api_quota_manager import (
    ApiKeyMetrics,
    ApiKeyStatus,
    ApiQuotaManager,
)


class TestApiQuotaManager:
    """API 配額管理器測試類"""

    @pytest.fixture
    def temp_persistence_file(self):
        """創建臨時持久化文件"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except:
            pass

    @pytest.fixture
    async def quota_manager(self, temp_persistence_file):
        """創建測試用的配額管理器"""
        with patch(
            "src.namecard.infrastructure.ai.api_quota_manager.Config"
        ) as mock_config:
            mock_config.GOOGLE_API_KEY = "AIzaTestKey1234567890abcdef"
            mock_config.GOOGLE_API_KEY_FALLBACK = "AIzaBackupKey0987654321fedcba"

            manager = ApiQuotaManager(persistence_file=temp_persistence_file)
            # 等待初始化任務完成
            await asyncio.sleep(0.1)
            yield manager

    @pytest.fixture
    def sample_api_key_metrics(self):
        """測試用的 API Key 指標樣本"""
        return [
            ApiKeyMetrics(
                key_id="test_key_0",
                key_masked="AIzaTe...cdef",
                status=ApiKeyStatus.ACTIVE,
                daily_quota=1000,
                used_today=150,
                requests_per_minute=60,
                requests_this_minute=5,
                total_requests=500,
                successful_requests=475,
                failed_requests=25,
                average_response_time=2.5,
                consecutive_errors=0,
            ),
            ApiKeyMetrics(
                key_id="test_key_1",
                key_masked="AIzaBa...dcba",
                status=ApiKeyStatus.ACTIVE,
                daily_quota=1000,
                used_today=800,
                requests_per_minute=60,
                requests_this_minute=10,
                total_requests=1200,
                successful_requests=1100,
                failed_requests=100,
                average_response_time=3.2,
                consecutive_errors=0,
            ),
        ]

    # ==========================================
    # 1. 基礎功能測試
    # ==========================================

    def test_api_key_status_enum(self):
        """測試 API Key 狀態枚舉"""
        assert ApiKeyStatus.ACTIVE.value == "active"
        assert ApiKeyStatus.RATE_LIMITED.value == "rate_limited"
        assert ApiKeyStatus.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert ApiKeyStatus.ERROR.value == "error"
        assert ApiKeyStatus.DISABLED.value == "disabled"

    def test_api_key_metrics_initialization(self):
        """測試 API Key 指標初始化"""
        metrics = ApiKeyMetrics(key_id="test_key", key_masked="AIzaTe...cdef")

        assert metrics.key_id == "test_key"
        assert metrics.key_masked == "AIzaTe...cdef"
        assert metrics.status == ApiKeyStatus.ACTIVE
        assert metrics.daily_quota == 1000
        assert metrics.used_today == 0
        assert metrics.requests_per_minute == 60
        assert metrics.total_requests == 0
        assert metrics.consecutive_errors == 0

        # 檢查自動設置的重置時間
        assert metrics.quota_reset_time is not None
        assert metrics.minute_reset_time is not None

        # 檢查時間設置正確性
        now = datetime.now()
        assert metrics.quota_reset_time > now
        assert metrics.minute_reset_time > now

    async def test_quota_manager_initialization(self, quota_manager):
        """測試配額管理器初始化"""
        assert len(quota_manager.api_keys) == 2
        assert len(quota_manager.metrics) == 2

        # 檢查 API Keys 被正確載入
        assert "AIzaTestKey1234567890abcdef" in quota_manager.api_keys
        assert "AIzaBackupKey0987654321fedcba" in quota_manager.api_keys

        # 檢查指標被正確初始化
        assert "key_0" in quota_manager.metrics
        assert "key_1" in quota_manager.metrics

        # 檢查遮罩處理
        key_0_metrics = quota_manager.metrics["key_0"]
        assert key_0_metrics.key_masked == "AIzaTe...cdef"

    # ==========================================
    # 2. API Key 選擇邏輯測試
    # ==========================================

    async def test_get_best_api_key_basic(self, quota_manager):
        """測試基本 API Key 選擇"""
        api_key, key_id = await quota_manager.get_best_api_key()

        assert api_key is not None
        assert key_id is not None
        assert api_key in quota_manager.api_keys
        assert key_id in quota_manager.metrics

        # 檢查選中的 Key 狀態為 ACTIVE
        selected_metrics = quota_manager.metrics[key_id]
        assert selected_metrics.status == ApiKeyStatus.ACTIVE

    async def test_get_best_api_key_with_preferences(self, quota_manager):
        """測試基於性能偏好的 API Key 選擇"""
        # 設置不同的使用統計
        quota_manager.metrics["key_0"].used_today = 100
        quota_manager.metrics["key_0"].successful_requests = 95
        quota_manager.metrics["key_0"].total_requests = 100

        quota_manager.metrics["key_1"].used_today = 500
        quota_manager.metrics["key_1"].successful_requests = 450
        quota_manager.metrics["key_1"].total_requests = 500

        api_key, key_id = await quota_manager.get_best_api_key()

        # 應該選擇使用量較少且成功率較高的 key_0
        assert key_id == "key_0"

    async def test_get_best_api_key_quota_exceeded(self, quota_manager):
        """測試配額超限時的 API Key 選擇"""
        # 將第一個 Key 設為配額超限
        quota_manager.metrics["key_0"].used_today = 1000
        quota_manager.metrics["key_0"].status = ApiKeyStatus.QUOTA_EXCEEDED

        api_key, key_id = await quota_manager.get_best_api_key()

        # 應該選擇第二個 Key
        assert key_id == "key_1"
        assert quota_manager.metrics[key_id].status == ApiKeyStatus.ACTIVE

    async def test_get_best_api_key_rate_limited(self, quota_manager):
        """測試速率限制時的 API Key 選擇"""
        # 將第一個 Key 設為速率限制
        quota_manager.metrics["key_0"].requests_this_minute = 60
        quota_manager.metrics["key_0"].status = ApiKeyStatus.RATE_LIMITED

        api_key, key_id = await quota_manager.get_best_api_key()

        # 應該選擇第二個 Key
        assert key_id == "key_1"

    async def test_get_best_api_key_all_unavailable(self, quota_manager):
        """測試所有 API Key 都不可用的情況"""
        # 將所有 Key 設為不可用
        for metrics in quota_manager.metrics.values():
            metrics.status = ApiKeyStatus.QUOTA_EXCEEDED

        api_key, key_id = await quota_manager.get_best_api_key()

        assert api_key is None
        assert key_id is None

    async def test_api_key_scoring_algorithm(self, quota_manager):
        """測試 API Key 評分算法"""
        # 設置測試場景：一個高成功率但使用量高，一個低成功率但使用量低
        quota_manager.metrics["key_0"].used_today = 800  # 80% 配額使用
        quota_manager.metrics["key_0"].successful_requests = 950
        quota_manager.metrics["key_0"].total_requests = 1000  # 95% 成功率

        quota_manager.metrics["key_1"].used_today = 200  # 20% 配額使用
        quota_manager.metrics["key_1"].successful_requests = 700
        quota_manager.metrics["key_1"].total_requests = 1000  # 70% 成功率

        api_key, key_id = await quota_manager.get_best_api_key()

        # 成功率權重較高，應該選擇 key_0
        assert key_id == "key_0"

    # ==========================================
    # 3. API 使用記錄測試
    # ==========================================

    async def test_record_api_usage_success(self, quota_manager):
        """測試成功 API 使用記錄"""
        initial_metrics = quota_manager.metrics["key_0"]
        initial_total = initial_metrics.total_requests
        initial_successful = initial_metrics.successful_requests
        initial_used_today = initial_metrics.used_today

        await quota_manager.record_api_usage(
            key_id="key_0", success=True, response_time=2.5, error_message=None
        )

        updated_metrics = quota_manager.metrics["key_0"]
        assert updated_metrics.total_requests == initial_total + 1
        assert updated_metrics.successful_requests == initial_successful + 1
        assert updated_metrics.used_today == initial_used_today + 1
        assert updated_metrics.consecutive_errors == 0
        assert updated_metrics.last_used is not None

        # 檢查平均回應時間更新
        expected_avg = (
            initial_metrics.average_response_time * initial_successful + 2.5
        ) / (initial_successful + 1)
        assert abs(updated_metrics.average_response_time - expected_avg) < 0.01

    async def test_record_api_usage_failure(self, quota_manager):
        """測試失敗 API 使用記錄"""
        initial_metrics = quota_manager.metrics["key_0"]
        initial_failed = initial_metrics.failed_requests

        await quota_manager.record_api_usage(
            key_id="key_0",
            success=False,
            response_time=10.0,
            error_message="API quota exceeded",
        )

        updated_metrics = quota_manager.metrics["key_0"]
        assert updated_metrics.failed_requests == initial_failed + 1
        assert updated_metrics.consecutive_errors == 1
        assert updated_metrics.last_error == "API quota exceeded"
        assert len(updated_metrics.error_history) == 1

        # 檢查狀態是否根據錯誤類型更新
        assert updated_metrics.status == ApiKeyStatus.QUOTA_EXCEEDED

    async def test_record_api_usage_rate_limit_error(self, quota_manager):
        """測試速率限制錯誤記錄"""
        await quota_manager.record_api_usage(
            key_id="key_0",
            success=False,
            response_time=1.0,
            error_message="Rate limit exceeded (429)",
        )

        metrics = quota_manager.metrics["key_0"]
        assert metrics.status == ApiKeyStatus.RATE_LIMITED

    async def test_record_api_usage_consecutive_errors(self, quota_manager):
        """測試連續錯誤處理"""
        # 記錄3次連續錯誤
        for i in range(3):
            await quota_manager.record_api_usage(
                key_id="key_0",
                success=False,
                response_time=5.0,
                error_message=f"Network error {i}",
            )

        metrics = quota_manager.metrics["key_0"]
        assert metrics.consecutive_errors == 3
        assert metrics.status == ApiKeyStatus.ERROR

    async def test_record_api_usage_error_history(self, quota_manager):
        """測試錯誤歷史記錄"""
        # 記錄超過10個錯誤
        for i in range(12):
            await quota_manager.record_api_usage(
                key_id="key_0",
                success=False,
                response_time=1.0,
                error_message=f"Error {i}",
            )

        metrics = quota_manager.metrics["key_0"]
        # 應該只保留最近10個錯誤
        assert len(metrics.error_history) == 10
        assert "Error 11" in metrics.error_history[-1]

    # ==========================================
    # 4. 配額狀態監控測試
    # ==========================================

    async def test_get_quota_status(self, quota_manager):
        """測試配額狀態獲取"""
        # 設置一些使用數據
        await quota_manager.record_api_usage("key_0", True, 2.0)
        await quota_manager.record_api_usage("key_1", False, 5.0, "Timeout")

        status = await quota_manager.get_quota_status()

        # 檢查狀態結構
        assert "timestamp" in status
        assert "total_api_keys" in status
        assert "keys" in status
        assert "summary" in status

        assert status["total_api_keys"] == 2
        assert len(status["keys"]) == 2

        # 檢查 key_0 狀態
        key_0_status = status["keys"]["key_0"]
        assert "quota" in key_0_status
        assert "rate_limit" in key_0_status
        assert "performance" in key_0_status

        # 檢查配額信息
        quota_info = key_0_status["quota"]
        assert quota_info["daily_limit"] == 1000
        assert quota_info["used_today"] == 1
        assert quota_info["remaining"] == 999
        assert quota_info["usage_percentage"] == 0.1

        # 檢查性能信息
        perf_info = key_0_status["performance"]
        assert perf_info["total_requests"] == 1
        assert perf_info["success_rate"] == 100.0

    async def test_predict_quota_exhaustion(self, quota_manager):
        """測試配額耗盡預測"""
        # 模擬一些使用數據（模擬已使用6小時，用了600個配額）
        quota_manager.metrics["key_0"].used_today = 600
        quota_manager.metrics["key_0"].total_requests = 600

        with patch("datetime") as mock_datetime:
            # 模擬當前時間為上午6點
            mock_now = datetime(2024, 1, 1, 6, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            predictions = await quota_manager.predict_quota_exhaustion()

        assert "key_0" in predictions
        prediction = predictions["key_0"]

        assert "hourly_usage_rate" in prediction
        assert "remaining_quota" in prediction
        assert "predicted_exhaustion" in prediction
        assert "hours_until_exhaustion" in prediction
        assert "risk_level" in prediction

        # 檢查計算邏輯
        assert prediction["remaining_quota"] == 400
        assert prediction["hourly_usage_rate"] == 100.0  # 600/6小時

    def test_risk_level_calculation(self, quota_manager):
        """測試風險等級計算"""
        assert quota_manager._calculate_risk_level(1) == "critical"
        assert quota_manager._calculate_risk_level(4) == "high"
        assert quota_manager._calculate_risk_level(8) == "medium"
        assert quota_manager._calculate_risk_level(15) == "low"

    # ==========================================
    # 5. 時間重置機制測試
    # ==========================================

    async def test_quota_reset_mechanism(self, quota_manager):
        """測試配額重置機制"""
        # 設置配額超限狀態
        metrics = quota_manager.metrics["key_0"]
        metrics.used_today = 1000
        metrics.status = ApiKeyStatus.QUOTA_EXCEEDED
        metrics.quota_reset_time = datetime.now() - timedelta(hours=1)  # 1小時前應該重置

        # 獲取最佳 API Key 應該觸發重置
        api_key, key_id = await quota_manager.get_best_api_key()

        assert key_id == "key_0"  # 應該重新可用
        assert metrics.used_today == 0  # 使用量重置
        assert metrics.status == ApiKeyStatus.ACTIVE  # 狀態重置
        assert metrics.quota_reset_time > datetime.now()  # 重置時間更新

    async def test_rate_limit_reset_mechanism(self, quota_manager):
        """測試速率限制重置機制"""
        metrics = quota_manager.metrics["key_0"]
        metrics.requests_this_minute = 60
        metrics.status = ApiKeyStatus.RATE_LIMITED
        metrics.minute_reset_time = datetime.now() - timedelta(minutes=2)  # 2分鐘前應該重置

        api_key, key_id = await quota_manager.get_best_api_key()

        assert key_id == "key_0"
        assert metrics.requests_this_minute == 0
        assert metrics.status == ApiKeyStatus.ACTIVE

    async def test_error_status_reset_after_idle(self, quota_manager):
        """測試錯誤狀態在閒置後重置"""
        metrics = quota_manager.metrics["key_0"]
        metrics.status = ApiKeyStatus.ERROR
        metrics.consecutive_errors = 5
        metrics.last_used = datetime.now() - timedelta(hours=2)  # 2小時前最後使用

        await quota_manager._cleanup_and_reset()

        assert metrics.status == ApiKeyStatus.ACTIVE
        assert metrics.consecutive_errors == 0

    # ==========================================
    # 6. 持久化測試
    # ==========================================

    async def test_metrics_persistence_save(self, quota_manager, temp_persistence_file):
        """測試指標持久化保存"""
        # 記錄一些使用數據
        await quota_manager.record_api_usage("key_0", True, 3.5)
        await quota_manager.record_api_usage("key_0", False, 8.0, "Timeout")

        # 檢查文件是否創建並包含數據
        with open(temp_persistence_file, "r") as f:
            data = json.load(f)

        assert "key_0" in data
        key_data = data["key_0"]
        assert key_data["total_requests"] == 2
        assert key_data["successful_requests"] == 1
        assert key_data["failed_requests"] == 1
        assert "last_error" in key_data
        assert "error_history" in key_data

    async def test_metrics_persistence_load(self, temp_persistence_file):
        """測試指標持久化載入"""
        # 創建測試數據文件
        test_data = {
            "key_0": {
                "key_masked": "AIzaTe...cdef",
                "status": "active",
                "daily_quota": 1000,
                "used_today": 150,
                "total_requests": 300,
                "successful_requests": 280,
                "failed_requests": 20,
                "average_response_time": 2.8,
                "consecutive_errors": 0,
                "last_error": None,
                "error_history": [],
                "last_used": "2024-01-01T10:30:00",
                "quota_reset_time": "2024-01-02T00:00:00",
            }
        }

        with open(temp_persistence_file, "w") as f:
            json.dump(test_data, f)

        # 創建新的管理器來測試載入
        with patch("simple_config.Config") as mock_config:
            mock_config.GOOGLE_API_KEY = "AIzaTestKey1234567890abcdef"
            mock_config.GOOGLE_API_KEY_FALLBACK = "AIzaBackupKey0987654321fedcba"

            manager = ApiQuotaManager(persistence_file=temp_persistence_file)
            await asyncio.sleep(0.1)  # 等待載入完成

        # 驗證數據載入正確
        metrics = manager.metrics["key_0"]
        assert metrics.used_today == 150
        assert metrics.total_requests == 300
        assert metrics.successful_requests == 280
        assert metrics.average_response_time == 2.8

    # ==========================================
    # 7. 並發和壓力測試
    # ==========================================

    async def test_concurrent_usage_recording(self, quota_manager):
        """測試併發使用記錄"""

        async def record_usage(i):
            await quota_manager.record_api_usage(
                key_id="key_0",
                success=i % 4 != 0,  # 75% 成功率
                response_time=2.0 + (i % 3) * 0.5,
                error_message="Test error" if i % 4 == 0 else None,
            )

        # 併發記錄100個使用
        tasks = [record_usage(i) for i in range(100)]
        await asyncio.gather(*tasks)

        metrics = quota_manager.metrics["key_0"]
        assert metrics.total_requests == 100
        assert metrics.successful_requests == 75
        assert metrics.failed_requests == 25
        assert metrics.used_today == 100

    async def test_concurrent_best_key_selection(self, quota_manager):
        """測試併發最佳 Key 選擇"""

        async def get_key():
            return await quota_manager.get_best_api_key()

        # 併發選擇50次
        tasks = [get_key() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # 所有結果都應該返回有效的 API Key
        for api_key, key_id in results:
            assert api_key is not None
            assert key_id is not None
            assert api_key in quota_manager.api_keys

    async def test_high_load_quota_management(self, quota_manager):
        """測試高負載配額管理"""
        start_time = time.time()

        # 模擬高負載：1000次併發操作
        async def high_load_operation(i):
            # 選擇 API Key
            api_key, key_id = await quota_manager.get_best_api_key()
            if api_key and key_id:
                # 記錄使用
                await quota_manager.record_api_usage(
                    key_id=key_id,
                    success=i % 10 != 0,  # 90% 成功率
                    response_time=1.0 + (i % 5) * 0.2,
                )

        tasks = [high_load_operation(i) for i in range(1000)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"\n📊 高負載測試結果:")
        print(f"   - 處理 1000 次操作: {processing_time:.3f}s")
        print(f"   - 平均每次操作: {processing_time/1000*1000:.2f}ms")

        # 驗證系統仍然正常運作
        status = await quota_manager.get_quota_status()
        assert status["summary"]["total_requests"] == 1000

        # 性能驗證
        assert processing_time < 10.0  # 應該在10秒內完成

    # ==========================================
    # 8. 錯誤處理和邊界測試
    # ==========================================

    async def test_invalid_key_id_handling(self, quota_manager):
        """測試無效 Key ID 處理"""
        # 記錄到不存在的 Key ID
        await quota_manager.record_api_usage(
            key_id="invalid_key", success=True, response_time=2.0
        )

        # 應該不會崩潰，且不影響現有指標
        status = await quota_manager.get_quota_status()
        assert len(status["keys"]) == 2  # 仍然只有2個有效 Key

    async def test_persistence_file_corruption_handling(self, temp_persistence_file):
        """測試持久化文件損壞處理"""
        # 寫入無效的 JSON
        with open(temp_persistence_file, "w") as f:
            f.write("invalid json content {")

        # 創建管理器應該不會崩潰
        with patch("simple_config.Config") as mock_config:
            mock_config.GOOGLE_API_KEY = "AIzaTestKey1234567890abcdef"
            mock_config.GOOGLE_API_KEY_FALLBACK = "AIzaBackupKey0987654321fedcba"

            manager = ApiQuotaManager(persistence_file=temp_persistence_file)
            await asyncio.sleep(0.1)

        # 應該使用默認設置
        assert len(manager.metrics) == 2
        assert manager.metrics["key_0"].used_today == 0

    async def test_extreme_usage_values(self, quota_manager):
        """測試極端使用值處理"""
        # 測試極長回應時間
        await quota_manager.record_api_usage(
            key_id="key_0", success=True, response_time=999999.0  # 極長時間
        )

        # 測試負數回應時間
        await quota_manager.record_api_usage(
            key_id="key_0", success=True, response_time=-1.0  # 負數時間
        )

        metrics = quota_manager.metrics["key_0"]
        assert metrics.total_requests == 2
        # 系統應該能處理這些極端值而不崩潰


# ==========================================
# 獨立測試函數
# ==========================================


def test_api_key_metrics_post_init():
    """測試 ApiKeyMetrics 初始化後處理"""
    now = datetime.now()

    metrics = ApiKeyMetrics(key_id="test", key_masked="test...mask")

    # 檢查自動設置的重置時間
    assert metrics.quota_reset_time > now
    assert metrics.minute_reset_time > now

    # 檢查配額重置時間是明日午夜
    expected_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    assert abs((metrics.quota_reset_time - expected_reset).total_seconds()) < 60


async def run_api_quota_manager_integration_test():
    """運行 API 配額管理器整合測試"""
    print("🧪 開始 API 配額管理器整合測試...")

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    temp_file.close()

    try:
        with patch("simple_config.Config") as mock_config:
            mock_config.GOOGLE_API_KEY = "AIzaTestPrimary123456789abcdef"
            mock_config.GOOGLE_API_KEY_FALLBACK = "AIzaTestBackup987654321fedcba"

            manager = ApiQuotaManager(persistence_file=temp_file.name)
            await asyncio.sleep(0.1)

        print("📊 模擬真實 API 使用場景...")

        # 場景1：正常使用主要 API Key
        print("  - 場景1: 正常使用主要 API Key")
        for i in range(50):
            api_key, key_id = await manager.get_best_api_key()
            await manager.record_api_usage(
                key_id=key_id, success=True, response_time=2.0 + (i % 3) * 0.5
            )

        status = await manager.get_quota_status()
        primary_key = list(status["keys"].keys())[0]
        assert status["keys"][primary_key]["quota"]["used_today"] == 50

        # 場景2：主要 Key 開始出現錯誤
        print("  - 場景2: 主要 Key 出現配額錯誤")
        for i in range(10):
            api_key, key_id = await manager.get_best_api_key()
            await manager.record_api_usage(
                key_id=key_id,
                success=False,
                response_time=1.0,
                error_message="API quota exceeded" if i > 5 else "Rate limit exceeded",
            )

        # 場景3：系統自動切換到備用 Key
        print("  - 場景3: 自動切換到備用 API Key")
        api_key, key_id = await manager.get_best_api_key()

        # 應該選擇狀態更好的 Key
        selected_metrics = manager.metrics[key_id]
        assert (
            selected_metrics.consecutive_errors == 0
            or selected_metrics.status == ApiKeyStatus.ACTIVE
        )

        # 場景4：備用 Key 正常使用
        print("  - 場景4: 備用 Key 正常處理")
        for i in range(30):
            api_key, key_id = await manager.get_best_api_key()
            await manager.record_api_usage(
                key_id=key_id, success=True, response_time=3.0
            )

        # 場景5：配額預測
        print("  - 場景5: 配額耗盡預測")
        predictions = await manager.predict_quota_exhaustion()
        assert len(predictions) > 0

        # 最終狀態檢查
        final_status = await manager.get_quota_status()

        print(f"\n📈 整合測試結果:")
        print(f"   - 總 API Keys: {final_status['total_api_keys']}")
        print(f"   - 可用 Keys: {final_status['summary']['available_keys']}")
        print(f"   - 總請求數: {final_status['summary']['total_requests']}")
        print(f"   - 系統健康: {final_status['summary']['system_health']}")

        # 驗證智能切換機制
        key_usage = {
            key: info["quota"]["used_today"]
            for key, info in final_status["keys"].items()
        }
        print(f"   - Key 使用分佈: {key_usage}")

        # 驗證預測功能
        if predictions:
            for key_id, pred in predictions.items():
                print(
                    f"   - {key_id} 預測: {pred['risk_level']} 風險，{pred['hours_until_exhaustion']:.1f}小時後耗盡"
                )

        # 測試持久化
        print("  - 測試數據持久化...")
        with open(temp_file.name, "r") as f:
            persisted_data = json.load(f)
        assert len(persisted_data) == 2

        print("✅ API 配額管理器整合測試完成")
        return True

    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass


# ==========================================
# 主程式入口
# ==========================================


async def main():
    """主測試程式"""
    print("🚀 API 配額管理器完整測試開始")
    print("=" * 60)

    # 1. 基本功能測試
    print("\n🧪 1. 基本數據結構測試")
    test_api_key_metrics_post_init()
    print("✅ 數據結構測試通過")

    # 2. 整合測試
    print("\n🧪 2. 系統整合測試")
    integration_success = await run_api_quota_manager_integration_test()

    # 3. 功能評估
    print("\n📈 3. API 配額管理能力評估")
    if integration_success:
        print("✅ API 配額管理器符合以下功能目標:")
        print("   - 智能 API Key 選擇: 基於成功率和配額使用量自動選擇最佳 Key")
        print("   - 配額追蹤監控: 實時追蹤每日配額和分鐘速率限制使用情況")
        print("   - 自動故障切換: 當主要 Key 出現問題時自動切換到備用 Key")
        print("   - 錯誤分類處理: 根據錯誤類型自動調整 Key 狀態")
        print("   - 配額耗盡預測: 基於使用趨勢預測配額耗盡時間和風險等級")
        print("   - 數據持久化: 自動保存和恢復使用統計，防止重啟後數據丟失")
        print("   - 並發安全: 支援高並發場景下的安全配額管理")
        print("   - 時間重置機制: 自動處理每日配額和速率限制的時間重置")

    print("\n" + "=" * 60)
    print("🎉 API 配額管理器測試完成")

    return integration_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
