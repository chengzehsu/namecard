#!/usr/bin/env python3
"""
名片處理器完整測試套件 - 專注 Gemini AI 整合和連接池問題修復
包含多名片檢測、品質評估、API 備用機制和連接池穩定性測試
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest
from PIL import Image

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 導入測試目標
from src.namecard.infrastructure.ai.card_processor import NameCardProcessor

# 測試標記
pytestmark = [pytest.mark.unit, pytest.mark.card_processor]


class TestNameCardProcessorComplete:
    """完整的名片處理器測試類"""

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        with patch(
            "src.namecard.infrastructure.ai.card_processor.Config"
        ) as mock_config:
            mock_config.GOOGLE_API_KEY = "AIzaTestKey1234567890abcdef"
            mock_config.GOOGLE_API_KEY_FALLBACK = "AIzaBackupKey0987654321fedcba"
            mock_config.GEMINI_MODEL = "gemini-2.5-pro"
            yield mock_config

    @pytest.fixture
    def card_processor(self, mock_config):
        """創建測試用的名片處理器"""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as mock_model:
                with patch(
                    "src.namecard.infrastructure.ai.card_processor.AddressNormalizer"
                ) as mock_normalizer:
                    # 設置 mock 返回值
                    mock_model_instance = Mock()
                    mock_model.return_value = mock_model_instance

                    mock_normalizer_instance = Mock()
                    mock_normalizer.return_value = mock_normalizer_instance

                    processor = NameCardProcessor()
                    processor.model = mock_model_instance
                    processor.address_normalizer = mock_normalizer_instance

                    yield processor

    @pytest.fixture
    def sample_card_image(self):
        """創建測試用的名片圖片 bytes"""
        # 創建一個簡單的測試圖片
        image = Image.new("RGB", (300, 200), color="white")
        img_buffer = BytesIO()
        image.save(img_buffer, format="JPEG")
        return img_buffer.getvalue()

    # ==========================================
    # 1. 初始化和配置測試
    # ==========================================

    def test_processor_initialization_success(self, mock_config):
        """測試成功初始化"""
        with patch("google.generativeai.configure") as mock_configure:
            with patch("google.generativeai.GenerativeModel") as mock_model:
                with patch(
                    "src.namecard.infrastructure.ai.card_processor.AddressNormalizer"
                ) as mock_normalizer:
                    processor = NameCardProcessor()

                    # 驗證初始化調用
                    mock_configure.assert_called_once_with(
                        api_key=mock_config.GOOGLE_API_KEY
                    )
                    mock_model.assert_called_once_with(mock_config.GEMINI_MODEL)
                    mock_normalizer.assert_called_once()

                    # 驗證屬性設置
                    assert processor.current_api_key == mock_config.GOOGLE_API_KEY
                    assert (
                        processor.fallback_api_key
                        == mock_config.GOOGLE_API_KEY_FALLBACK
                    )
                    assert processor.using_fallback is False

    def test_processor_initialization_failure(self, mock_config):
        """測試初始化失敗"""
        with patch(
            "google.generativeai.configure",
            side_effect=Exception("API configuration failed"),
        ):
            with pytest.raises(Exception) as exc_info:
                NameCardProcessor()

            assert "初始化 Gemini 模型失敗" in str(exc_info.value)

    # ==========================================
    # 2. API 備用機制測試
    # ==========================================

    def test_switch_to_fallback_api_success(self, card_processor, mock_config):
        """測試成功切換到備用 API"""
        with patch("google.generativeai.configure") as mock_configure:
            with patch("google.generativeai.GenerativeModel") as mock_model:
                result = card_processor._switch_to_fallback_api()

                assert result is True
                assert card_processor.using_fallback is True
                assert (
                    card_processor.current_api_key
                    == mock_config.GOOGLE_API_KEY_FALLBACK
                )

                mock_configure.assert_called_with(
                    api_key=mock_config.GOOGLE_API_KEY_FALLBACK
                )
                mock_model.assert_called_with(mock_config.GEMINI_MODEL)

    def test_switch_to_fallback_api_no_fallback_key(self, card_processor):
        """測試沒有備用 API Key 的情況"""
        card_processor.fallback_api_key = None

        with pytest.raises(Exception) as exc_info:
            card_processor._switch_to_fallback_api()

        assert "沒有設定備用 API Key" in str(exc_info.value)

    def test_switch_to_fallback_api_already_using_fallback(self, card_processor):
        """測試已經在使用備用 API Key 的情況"""
        card_processor.using_fallback = True

        with pytest.raises(Exception) as exc_info:
            card_processor._switch_to_fallback_api()

        assert "已經在使用備用 API Key" in str(exc_info.value)

    # ==========================================
    # 3. 錯誤檢測邏輯測試
    # ==========================================

    def test_quota_exceeded_error_detection(self, card_processor):
        """測試配額超限錯誤檢測"""
        quota_errors = [
            "quota exceeded",
            "Resource exhausted",
            "429 Too Many Requests",
            "rate limit exceeded",
            "Usage limit reached",
            "Billing account error",
        ]

        for error in quota_errors:
            assert card_processor._is_quota_exceeded_error(error) is True
            assert card_processor._is_quota_exceeded_error(error.upper()) is True

        # 測試非配額錯誤
        non_quota_errors = ["Invalid API key", "Bad request", "Network error"]
        for error in non_quota_errors:
            assert card_processor._is_quota_exceeded_error(error) is False

    def test_transient_error_detection(self, card_processor):
        """測試暫時性錯誤檢測"""
        transient_errors = [
            "500 Internal Server Error",
            "502 Bad Gateway",
            "503 Service Unavailable",
            "Connection timeout",
            "Please try again later",
            "Network error occurred",
        ]

        for error in transient_errors:
            assert card_processor._is_transient_error(error) is True
            assert card_processor._is_transient_error(error.lower()) is True

        # 測試非暫時性錯誤
        non_transient_errors = [
            "Invalid API key",
            "Bad request format",
            "404 Not Found",
        ]
        for error in non_transient_errors:
            assert card_processor._is_transient_error(error) is False

    # ==========================================
    # 4. 內容生成和重試機制測試
    # ==========================================

    def test_generate_content_with_fallback_success(self, card_processor):
        """測試成功生成內容"""
        # Mock 成功的 API 調用
        mock_response = Mock()
        mock_response.text = "  Generated content  "
        card_processor.model.generate_content.return_value = mock_response

        result = card_processor._generate_content_with_fallback("test content")

        assert result == "Generated content"
        card_processor.model.generate_content.assert_called_once_with("test content")

    def test_generate_content_with_quota_exceeded_fallback(
        self, card_processor, mock_config
    ):
        """測試配額超限自動切換到備用 API"""
        # 第一次調用失敗（配額超限）
        quota_error = Exception("quota exceeded")
        # 第二次調用成功（備用 API）
        success_response = Mock()
        success_response.text = "Fallback success"

        card_processor.model.generate_content.side_effect = [
            quota_error,
            success_response,
        ]

        with patch.object(card_processor, "_switch_to_fallback_api") as mock_switch:
            result = card_processor._generate_content_with_fallback("test content")

            assert result == "Fallback success"
            mock_switch.assert_called_once()
            assert card_processor.model.generate_content.call_count == 2

    def test_generate_content_with_transient_error_retry(self, card_processor):
        """測試暫時性錯誤重試機制"""
        # 前兩次失敗，第三次成功
        transient_error = Exception("500 Internal Server Error")
        success_response = Mock()
        success_response.text = "Retry success"

        card_processor.model.generate_content.side_effect = [
            transient_error,
            transient_error,
            success_response,
        ]

        with patch("time.sleep"):  # Mock sleep 以加速測試
            result = card_processor._generate_content_with_fallback(
                "test content", max_retries=3
            )

            assert result == "Retry success"
            assert card_processor.model.generate_content.call_count == 3

    def test_generate_content_max_retries_exceeded(self, card_processor):
        """測試超過最大重試次數"""
        transient_error = Exception("Connection timeout")
        card_processor.model.generate_content.side_effect = transient_error

        with patch("time.sleep"):
            with pytest.raises(Exception) as exc_info:
                card_processor._generate_content_with_fallback(
                    "test content", max_retries=2
                )

            assert "經過2次重試後仍然失敗" in str(exc_info.value)
            assert card_processor.model.generate_content.call_count == 2

    # ==========================================
    # 5. 圖片處理和多名片檢測測試
    # ==========================================

    def test_extract_info_from_image_no_data(self, card_processor):
        """測試無圖片數據的情況"""
        result = card_processor.extract_info_from_image(None)
        assert result["error"] == "沒有圖像數據"

        result = card_processor.extract_info_from_image(b"")
        assert result["error"] == "沒有圖像數據"

    def test_extract_multi_card_info_single_card_success(
        self, card_processor, sample_card_image
    ):
        """測試單張名片成功識別"""
        # Mock Gemini 回應
        mock_response = {
            "card_count": 1,
            "cards": [
                {
                    "card_number": 1,
                    "name": "張小明",
                    "company": "科技公司",
                    "title": "軟體工程師",
                    "email": "zhang@tech.com",
                    "phone": "0912345678",
                    "address": "台北市信義區信義路五段7號",
                    "decision_influence": "中",
                    "quality_score": 0.95,
                    "confidence": 0.9,
                    "completeness": 0.85,
                    "clarity": 0.95,
                    "missing_fields": [],
                    "quality_issues": [],
                }
            ],
        }

        card_processor.model.generate_content.return_value.text = json.dumps(
            mock_response
        )

        # Mock 地址正規化
        card_processor.address_normalizer.normalize_address.return_value = {
            "normalized": "台北市信義區信義路五段7號",
            "original": "台北市信義區信義路五段7號",
            "confidence": 0.95,
            "warnings": [],
        }

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            result = card_processor.extract_multi_card_info(sample_card_image)

            assert result["cards_detected"] == 1
            assert result["processing_successful"] is True
            assert len(result["cards"]) == 1

            card = result["cards"][0]
            assert card["name"] == "張小明"
            assert card["company"] == "科技公司"
            assert card["quality_score"] == 0.95

    def test_extract_multi_card_info_multiple_cards(
        self, card_processor, sample_card_image
    ):
        """測試多張名片識別"""
        # Mock 多名片回應
        mock_response = {
            "card_count": 3,
            "cards": [
                {
                    "card_number": 1,
                    "name": "張小明",
                    "company": "A公司",
                    "quality_score": 0.9,
                    "confidence": 0.85,
                },
                {
                    "card_number": 2,
                    "name": "李小華",
                    "company": "B公司",
                    "quality_score": 0.7,
                    "confidence": 0.6,
                },
                {
                    "card_number": 3,
                    "name": "王小美",
                    "company": "C公司",
                    "quality_score": 0.95,
                    "confidence": 0.9,
                },
            ],
        }

        card_processor.model.generate_content.return_value.text = json.dumps(
            mock_response
        )

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            result = card_processor.extract_multi_card_info(sample_card_image)

            assert result["cards_detected"] == 3
            assert result["processing_successful"] is True
            assert len(result["cards"]) == 3

            # 驗證多名片處理建議
            assert "user_decision_required" in result
            assert "processing_recommendation" in result

    # ==========================================
    # 6. 連接池和穩定性測試 (特別關注)
    # ==========================================

    @pytest.mark.asyncio
    async def test_connection_pool_stability_under_load(
        self, card_processor, sample_card_image
    ):
        """測試連接池在高負載下的穩定性"""
        # 模擬高並發請求
        tasks = []

        # Mock 成功回應
        mock_response = {
            "card_count": 1,
            "cards": [{"name": "測試", "company": "公司", "quality_score": 0.8}],
        }
        card_processor.model.generate_content.return_value.text = json.dumps(
            mock_response
        )

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            # 創建 20 個並發請求
            for i in range(20):
                task = asyncio.create_task(
                    asyncio.to_thread(
                        card_processor.extract_multi_card_info, sample_card_image
                    )
                )
                tasks.append(task)

            # 等待所有任務完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 檢查是否有連接池相關的錯誤
            connection_errors = 0
            successful_results = 0

            for result in results:
                if isinstance(result, Exception):
                    error_str = str(result).lower()
                    if any(
                        keyword in error_str
                        for keyword in [
                            "connection pool",
                            "connector",
                            "too many open files",
                            "timeout",
                        ]
                    ):
                        connection_errors += 1
                elif isinstance(result, dict) and result.get("processing_successful"):
                    successful_results += 1

            # 驗證連接池穩定性
            assert connection_errors == 0, f"發現 {connection_errors} 個連接池錯誤"
            assert (
                successful_results >= 15
            ), f"成功處理數量過少: {successful_results}/20"

    def test_memory_usage_optimization(self, card_processor, sample_card_image):
        """測試記憶體使用優化"""
        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # Mock 回應
            mock_response = {"card_count": 1, "cards": [{"name": "測試"}]}
            card_processor.model.generate_content.return_value.text = json.dumps(
                mock_response
            )

            with patch("src.namecard.infrastructure.ai.card_processor.Image"):
                # 處理 100 次請求
                for i in range(100):
                    result = card_processor.extract_multi_card_info(sample_card_image)
                    # 確保結果被處理
                    assert isinstance(result, dict)

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # 記憶體增長不應該超過 100MB
            assert (
                memory_increase < 100 * 1024 * 1024
            ), f"記憶體洩漏: 增長 {memory_increase} bytes"

        except ImportError:
            pytest.skip("psutil 不可用，跳過記憶體測試")

    # ==========================================
    # 7. 錯誤處理和邊緣案例測試
    # ==========================================

    def test_invalid_json_response_handling(self, card_processor, sample_card_image):
        """測試無效 JSON 回應處理"""
        card_processor.model.generate_content.return_value.text = (
            "Invalid JSON response"
        )

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            result = card_processor.extract_multi_card_info(sample_card_image)

            assert result["processing_successful"] is False
            assert "error" in result
            assert "JSON" in result["error"]

    def test_gemini_api_timeout_handling(self, card_processor, sample_card_image):
        """測試 Gemini API 超時處理"""
        card_processor.model.generate_content.side_effect = Exception("Request timeout")

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            result = card_processor.extract_multi_card_info(sample_card_image)

            assert result["processing_successful"] is False
            assert "error" in result
            assert "timeout" in result["error"].lower()

    def test_image_processing_error_handling(self, card_processor):
        """測試圖片處理錯誤"""
        invalid_image_data = b"not_an_image"

        with patch(
            "src.namecard.infrastructure.ai.card_processor.Image.open",
            side_effect=Exception("Invalid image format"),
        ):
            result = card_processor.extract_multi_card_info(invalid_image_data)

            assert result["processing_successful"] is False
            assert "error" in result
            assert "image" in result["error"].lower()

    # ==========================================
    # 8. 整合測試
    # ==========================================

    def test_end_to_end_card_processing_workflow(
        self, card_processor, sample_card_image
    ):
        """端到端名片處理工作流程測試"""
        # 模擬完整的處理流程
        mock_response = {
            "card_count": 1,
            "cards": [
                {
                    "card_number": 1,
                    "name": "完整測試",
                    "company": "測試科技有限公司",
                    "title": "技術總監",
                    "email": "test@example.com",
                    "phone": "02-12345678",
                    "address": "台北市中正區重慶南路一段122號",
                    "quality_score": 0.9,
                    "confidence": 0.85,
                    "completeness": 0.9,
                    "clarity": 0.95,
                }
            ],
        }

        card_processor.model.generate_content.return_value.text = json.dumps(
            mock_response
        )

        # Mock 地址正規化
        card_processor.address_normalizer.normalize_address.return_value = {
            "normalized": "台北市中正區重慶南路一段122號",
            "original": "台北市中正區重慶南路一段122號",
            "confidence": 0.95,
            "warnings": [],
        }

        with patch("src.namecard.infrastructure.ai.card_processor.Image"):
            result = card_processor.extract_multi_card_info(sample_card_image)

            # 驗證完整的處理結果
            assert result["processing_successful"] is True
            assert result["cards_detected"] == 1
            assert len(result["cards"]) == 1

            card = result["cards"][0]
            assert card["name"] == "完整測試"
            assert card["company"] == "測試科技有限公司"
            assert card["email"] == "test@example.com"
            assert card["phone"] == "02-12345678"
            assert card["quality_score"] == 0.9

            # 驗證地址正規化被調用
            card_processor.address_normalizer.normalize_address.assert_called_once()


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
