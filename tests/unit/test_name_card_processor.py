"""
Unit tests for NameCardProcessor - 名片處理器測試
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from name_card_processor import NameCardProcessor


class TestNameCardProcessor:
    """NameCardProcessor 單元測試"""

    def setup_method(self):
        """每個測試方法前的設置"""
        with (
            patch("google.generativeai.configure"),
            patch("google.generativeai.GenerativeModel"),
            patch("name_card_processor.AddressNormalizer"),
        ):
            self.processor = NameCardProcessor()

    @pytest.mark.unit
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    @patch("name_card_processor.AddressNormalizer")
    def test_init_success(self, mock_normalizer, mock_model, mock_configure):
        """測試成功初始化"""
        mock_model_instance = Mock()
        mock_model.return_value = mock_model_instance
        mock_normalizer_instance = Mock()
        mock_normalizer.return_value = mock_normalizer_instance

        processor = NameCardProcessor()

        mock_configure.assert_called_once()
        mock_model.assert_called_once()
        mock_normalizer.assert_called_once()
        assert processor.model == mock_model_instance
        assert processor.address_normalizer == mock_normalizer_instance

    @pytest.mark.unit
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_init_failure(self, mock_model, mock_configure):
        """測試初始化失敗"""
        mock_configure.side_effect = Exception("API key invalid")

        with pytest.raises(Exception) as exc_info:
            NameCardProcessor()

        assert "初始化 Gemini 模型失敗" in str(exc_info.value)

    @pytest.mark.unit
    def test_extract_info_from_image_no_data(self):
        """測試沒有圖像數據的情況"""
        result = self.processor.extract_info_from_image(None)
        assert result["error"] == "沒有圖像數據"

        result = self.processor.extract_info_from_image(b"")
        assert result["error"] == "沒有圖像數據"

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_success(self, mock_image):
        """測試成功提取名片資訊"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "name": "張三",
                "company": "測試公司",
                "title": "經理",
                "email": "zhang@test.com",
                "phone": "+886912345678",
                "address": "台北市信義區信義路五段7號",
            }
        )
        self.processor.model.generate_content.return_value = mock_response

        # Mock address normalizer
        self.processor.address_normalizer.normalize_address.return_value = {
            "normalized": "台北市信義區信義路五段7號",
            "original": "台北市信義區信義路五段7號",
            "confidence": 0.9,
            "warnings": [],
        }

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" not in result
        assert result["name"] == "張三"
        assert result["company"] == "測試公司"
        assert result["title"] == "經理"
        assert result["email"] == "zhang@test.com"
        assert result["phone"] == "+886912345678"
        assert result["address"] == "台北市信義區信義路五段7號"

        # 檢查是否調用了地址正規化
        self.processor.address_normalizer.normalize_address.assert_called_once()

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_with_address_warnings(self, mock_image):
        """測試帶有地址警告的名片處理"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(
            {"name": "李四", "address": "不完整地址", "notes": "原有備註"}
        )
        self.processor.model.generate_content.return_value = mock_response

        # Mock address normalizer with warnings
        self.processor.address_normalizer.normalize_address.return_value = {
            "normalized": "不完整地址",
            "original": "不完整地址",
            "confidence": 0.3,
            "warnings": ["無法識別縣市", "無法識別道路資訊"],
        }

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert result["name"] == "李四"
        assert "原有備註" in result["notes"]
        assert "地址處理警告" in result["notes"]
        assert "無法識別縣市" in result["notes"]
        assert result["_address_confidence"] == 0.3
        assert result["_original_address"] == "不完整地址"

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_no_address(self, mock_image):
        """測試沒有地址的名片處理"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock Gemini response without address
        mock_response = Mock()
        mock_response.text = json.dumps({"name": "王五", "company": "測試公司"})
        self.processor.model.generate_content.return_value = mock_response

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert result["name"] == "王五"
        assert result["company"] == "測試公司"
        # 沒有地址時不應該調用地址正規化
        self.processor.address_normalizer.normalize_address.assert_not_called()

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_gemini_error(self, mock_image):
        """測試 Gemini API 錯誤"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock Gemini API error
        self.processor.model.generate_content.side_effect = Exception(
            "Gemini API error"
        )

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" in result
        assert "Gemini API error" in result["error"]

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_invalid_json(self, mock_image):
        """測試無效的 JSON 回應"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        self.processor.model.generate_content.return_value = mock_response

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" in result
        assert "無法解析 Gemini 的 JSON 響應" in result["error"]
        assert result["raw_response"] == "Invalid JSON response"

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_non_dict_response(self, mock_image):
        """測試非字典格式的回應"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock response that's valid JSON but not a dict
        mock_response = Mock()
        mock_response.text = json.dumps(["not", "a", "dict"])
        self.processor.model.generate_content.return_value = mock_response

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" in result
        assert "Gemini 返回的不是有效的 JSON 對象" in result["error"]

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_json_with_code_blocks(self, mock_image):
        """測試包含程式碼區塊的 JSON 回應"""
        # Mock PIL Image
        mock_img = Mock()
        mock_image.open.return_value = mock_img

        # Mock response with code blocks
        mock_response = Mock()
        mock_response.text = '```json\n{"name": "測試用戶", "company": "公司"}\n```'
        self.processor.model.generate_content.return_value = mock_response

        # Mock address normalizer
        self.processor.address_normalizer.normalize_address.return_value = {
            "normalized": "",
            "original": "",
            "confidence": 0,
            "warnings": [],
        }

        image_bytes = b"fake_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" not in result
        assert result["name"] == "測試用戶"
        assert result["company"] == "公司"

    @pytest.mark.unit
    @patch("name_card_processor.Image")
    def test_extract_info_from_image_pil_error(self, mock_image):
        """測試 PIL 圖像處理錯誤"""
        # Mock PIL Image error
        mock_image.open.side_effect = Exception("Invalid image format")

        image_bytes = b"invalid_image_data"
        result = self.processor.extract_info_from_image(image_bytes)

        assert "error" in result
        assert "Invalid image format" in result["error"]

    @pytest.mark.unit
    def test_format_phone_number_taiwan_mobile(self):
        """測試台灣手機號碼格式化"""
        # 標準台灣手機號碼
        assert self.processor.format_phone_number("0912345678") == "+886912345678"
        assert self.processor.format_phone_number("09-1234-5678") == "+886912345678"
        assert self.processor.format_phone_number("091-234-5678") == "+886912345678"

    @pytest.mark.unit
    def test_format_phone_number_taiwan_landline(self):
        """測試台灣市話號碼格式化"""
        # 台北市話
        assert self.processor.format_phone_number("02-12345678") == "+8862-12345678"
        # 台中市話
        assert self.processor.format_phone_number("04-12345678") == "+8864-12345678"
        # 較短的市話
        assert self.processor.format_phone_number("02-1234567") == "+8862-1234567"

    @pytest.mark.unit
    def test_format_phone_number_international_format(self):
        """測試已是國際格式的號碼"""
        # 已經有 +886 開頭
        assert self.processor.format_phone_number("+886912345678") == "+886912345678"
        # 有 886 但沒有 +
        assert self.processor.format_phone_number("886912345678") == "+886912345678"

    @pytest.mark.unit
    def test_format_phone_number_invalid_format(self):
        """測試無法識別格式的號碼"""
        # 太短的號碼
        assert self.processor.format_phone_number("123") == "123"
        # 非台灣號碼格式
        assert self.processor.format_phone_number("1234567890") == "1234567890"
        # 包含字母
        assert self.processor.format_phone_number("09abc12345") == "09abc12345"

    @pytest.mark.unit
    def test_format_phone_number_empty_or_none(self):
        """測試空值或 None"""
        assert self.processor.format_phone_number(None) is None
        assert self.processor.format_phone_number("") is None
        assert self.processor.format_phone_number("   ") is None

    @pytest.mark.unit
    def test_format_phone_number_with_extensions(self):
        """測試帶分機的號碼"""
        # 帶分機的號碼應該保留原格式（無法標準化）
        phone_with_ext = "02-12345678 ext. 123"
        assert self.processor.format_phone_number(phone_with_ext) == phone_with_ext
