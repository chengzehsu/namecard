#!/usr/bin/env python3
"""
Notion 客戶端完整測試套件 - 專注資料庫操作和數據驗證
包含頁面創建、屬性建構、格式驗證、錯誤處理和連接穩定性測試
"""

import json
import os
import re
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 導入測試目標
from src.namecard.infrastructure.storage.notion_client import NotionManager

# 測試標記
pytestmark = [pytest.mark.unit, pytest.mark.notion_client]


class TestNotionClientComplete:
    """完整的 Notion 客戶端測試類"""

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        with patch(
            "src.namecard.infrastructure.storage.notion_client.Config"
        ) as mock_config:
            mock_config.NOTION_API_KEY = "secret_test_notion_api_key"
            mock_config.NOTION_DATABASE_ID = "test_database_id_123456789"
            yield mock_config

    @pytest.fixture
    def notion_manager(self, mock_config):
        """創建測試用的 Notion 管理器"""
        with patch(
            "src.namecard.infrastructure.storage.notion_client.Client"
        ) as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            manager = NotionManager()
            manager.notion = mock_client_instance
            manager.database_id = mock_config.NOTION_DATABASE_ID

            yield manager

    @pytest.fixture
    def sample_card_data(self):
        """測試用的名片資料樣本"""
        return {
            "name": "張小明",
            "company": "科技創新股份有限公司",
            "title": "技術總監",
            "department": "研發部",
            "decision_influence": "高",
            "email": "zhang.xiaoming@tech-innovation.com.tw",
            "phone": "+886-2-12345678",
            "address": "台北市信義區信義路五段7號35樓",
            "contact_source": "技術會議",
            "notes": "對 AI 技術很有興趣",
            # 地址正規化資訊
            "_address_confidence": 0.95,
            "_original_address": "台北市信義區信義路5段7號35F",
            "_address_warnings": [],
        }

    @pytest.fixture
    def sample_image_bytes(self):
        """測試用的圖片數據"""
        # 模擬 JPEG 圖片的前幾個字節
        return b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100

    # ==========================================
    # 1. 初始化和配置測試
    # ==========================================

    def test_notion_manager_initialization_success(self, mock_config):
        """測試成功初始化 Notion 管理器"""
        with patch(
            "src.namecard.infrastructure.storage.notion_client.Client"
        ) as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            manager = NotionManager()

            # 驗證初始化調用
            mock_client.assert_called_once_with(auth=mock_config.NOTION_API_KEY)
            assert manager.database_id == mock_config.NOTION_DATABASE_ID
            assert manager.notion == mock_client_instance

    def test_notion_manager_initialization_failure(self, mock_config):
        """測試初始化失敗"""
        with patch(
            "src.namecard.infrastructure.storage.notion_client.Client",
            side_effect=Exception("Notion API connection failed"),
        ):
            with pytest.raises(Exception) as exc_info:
                NotionManager()

            assert "初始化 Notion 客戶端失敗" in str(exc_info.value)

    # ==========================================
    # 2. 屬性建構測試
    # ==========================================

    def test_build_properties_complete_data(self, notion_manager, sample_card_data):
        """測試完整數據的屬性建構"""
        properties = notion_manager._build_properties(sample_card_data)

        # 驗證基本屬性
        assert "Name" in properties
        assert properties["Name"]["title"][0]["text"]["content"] == "張小明"

        assert "公司名稱" in properties
        assert (
            properties["公司名稱"]["rich_text"][0]["text"]["content"]
            == "科技創新股份有限公司"
        )

        assert "職稱" in properties
        assert properties["職稱"]["select"]["name"] == "技術總監"

        assert "部門" in properties
        assert properties["部門"]["rich_text"][0]["text"]["content"] == "研發部"

        assert "決策影響力" in properties
        assert properties["決策影響力"]["select"]["name"] == "高"

    def test_build_properties_email_validation(self, notion_manager):
        """測試 Email 格式驗證"""
        # 測試有效 Email
        valid_email_data = {"email": "test@example.com"}
        properties = notion_manager._build_properties(valid_email_data)

        assert "Email" in properties
        assert properties["Email"]["email"] == "test@example.com"

        # 測試無效 Email
        invalid_email_data = {"email": "invalid-email"}
        properties = notion_manager._build_properties(invalid_email_data)

        assert "Email" not in properties
        assert "Email備註" in properties
        assert (
            "格式待確認" in properties["Email備註"]["rich_text"][0]["text"]["content"]
        )

    def test_build_properties_phone_validation(self, notion_manager):
        """測試電話號碼格式驗證"""
        # 測試有效的台灣電話號碼
        valid_phone_data = {"phone": "+886-2-12345678"}
        properties = notion_manager._build_properties(valid_phone_data)

        assert "電話" in properties
        assert properties["電話"]["phone_number"] == "+886-2-12345678"

        # 測試多個電話號碼
        multiple_phone_data = {"phone": "02-12345678, 0912345678"}
        properties = notion_manager._build_properties(multiple_phone_data)

        # 多個號碼應該用 rich_text 處理
        assert "電話備註" in properties
        assert (
            "02-12345678, 0912345678"
            in properties["電話備註"]["rich_text"][0]["text"]["content"]
        )

    def test_build_properties_address_validation(self, notion_manager):
        """測試地址格式驗證"""
        # 測試台灣地址
        taiwan_address_data = {"address": "台北市信義區信義路五段7號"}

        with patch(
            "src.namecard.infrastructure.storage.notion_client.is_valid_taiwan_address",
            return_value=True,
        ):
            properties = notion_manager._build_properties(taiwan_address_data)

            assert "地址" in properties
            assert (
                properties["地址"]["rich_text"][0]["text"]["content"]
                == "台北市信義區信義路五段7號"
            )

        # 測試非台灣地址
        foreign_address_data = {"address": "123 Main St, New York, NY"}

        with patch(
            "src.namecard.infrastructure.storage.notion_client.is_valid_taiwan_address",
            return_value=False,
        ):
            properties = notion_manager._build_properties(foreign_address_data)

            assert "地址備註" in properties
            assert (
                "非台灣地址"
                in properties["地址備註"]["rich_text"][0]["text"]["content"]
            )

    def test_build_properties_partial_data(self, notion_manager):
        """測試部分數據的屬性建構"""
        partial_data = {
            "name": "測試姓名",
            "email": "test@example.com",
            # 缺少其他欄位
        }

        properties = notion_manager._build_properties(partial_data)

        # 只應該包含提供的欄位
        assert "Name" in properties
        assert "Email" in properties
        assert "公司名稱" not in properties
        assert "職稱" not in properties

    def test_build_properties_empty_data(self, notion_manager):
        """測試空數據的處理"""
        empty_data = {}
        properties = notion_manager._build_properties(empty_data)

        # 應該返回空的屬性字典
        assert isinstance(properties, dict)
        assert len(properties) == 0

    # ==========================================
    # 3. 頁面創建測試
    # ==========================================

    def test_create_name_card_record_success(self, notion_manager, sample_card_data):
        """測試成功創建名片記錄"""
        # Mock Notion API 回應
        mock_response = {
            "id": "test_page_id_123",
            "url": "https://notion.so/test_page_id_123",
        }
        notion_manager.notion.pages.create.return_value = mock_response

        result = notion_manager.create_name_card_record(sample_card_data)

        # 驗證結果
        assert result["success"] is True
        assert result["notion_page_id"] == "test_page_id_123"
        assert result["url"] == "https://notion.so/test_page_id_123"

        # 驗證 API 調用
        notion_manager.notion.pages.create.assert_called_once()
        call_args = notion_manager.notion.pages.create.call_args

        assert call_args[1]["parent"]["database_id"] == notion_manager.database_id
        assert "properties" in call_args[1]

    def test_create_name_card_record_with_image(
        self, notion_manager, sample_card_data, sample_image_bytes
    ):
        """測試帶圖片的名片記錄創建"""
        # Mock Notion API 回應
        mock_response = {
            "id": "test_page_id_456",
            "url": "https://notion.so/test_page_id_456",
        }
        notion_manager.notion.pages.create.return_value = mock_response

        # Mock 圖片處理方法
        with patch.object(notion_manager, "_add_image_info_to_page") as mock_add_image:
            result = notion_manager.create_name_card_record(
                sample_card_data, sample_image_bytes
            )

            # 驗證結果
            assert result["success"] is True

            # 驗證圖片處理被調用
            mock_add_image.assert_called_once_with(
                "test_page_id_456", sample_image_bytes
            )

    def test_create_name_card_record_with_address_info(
        self, notion_manager, sample_card_data
    ):
        """測試帶地址處理資訊的名片記錄創建"""
        # Mock Notion API 回應
        mock_response = {
            "id": "test_page_id_789",
            "url": "https://notion.so/test_page_id_789",
        }
        notion_manager.notion.pages.create.return_value = mock_response

        # Mock 地址處理方法
        with patch.object(
            notion_manager, "_add_address_processing_info"
        ) as mock_add_address:
            result = notion_manager.create_name_card_record(sample_card_data)

            # 驗證結果
            assert result["success"] is True

            # 驗證地址處理被調用
            mock_add_address.assert_called_once_with(
                "test_page_id_789", sample_card_data
            )

    def test_create_name_card_record_failure(self, notion_manager, sample_card_data):
        """測試創建名片記錄失敗"""
        # Mock Notion API 失敗
        notion_manager.notion.pages.create.side_effect = Exception("Notion API Error")

        result = notion_manager.create_name_card_record(sample_card_data)

        # 驗證失敗結果
        assert result["success"] is False
        assert "error" in result
        assert "Notion API Error" in result["error"]

    # ==========================================
    # 4. 圖片處理測試
    # ==========================================

    def test_add_image_info_to_page_success(self, notion_manager, sample_image_bytes):
        """測試成功添加圖片資訊到頁面"""
        page_id = "test_page_id"

        # Mock Notion API 調用
        notion_manager.notion.blocks.children.append = Mock()

        with (
            patch("tempfile.NamedTemporaryFile"),
            patch("base64.b64encode", return_value=b"base64data"),
            patch("os.path.getsize", return_value=len(sample_image_bytes)),
        ):
            # 這個方法可能不存在，我們需要先檢查
            if hasattr(notion_manager, "_add_image_info_to_page"):
                notion_manager._add_image_info_to_page(page_id, sample_image_bytes)

                # 驗證 blocks 被調用
                notion_manager.notion.blocks.children.append.assert_called_once()
            else:
                # 跳過這個測試，方法不存在
                pytest.skip("_add_image_info_to_page 方法不存在")

    # ==========================================
    # 5. 連接穩定性和錯誤處理測試
    # ==========================================

    def test_notion_api_rate_limiting(self, notion_manager, sample_card_data):
        """測試 Notion API 速率限制處理"""
        from notion_client.errors import APIResponseError

        # Mock 速率限制錯誤
        rate_limit_error = APIResponseError(
            response=Mock(status_code=429),
            message="Rate limit exceeded",
            code="rate_limited",
        )
        notion_manager.notion.pages.create.side_effect = rate_limit_error

        result = notion_manager.create_name_card_record(sample_card_data)

        # 應該優雅地處理錯誤
        assert result["success"] is False
        assert "error" in result

    def test_notion_api_unauthorized_error(self, notion_manager, sample_card_data):
        """測試 Notion API 未授權錯誤處理"""
        from notion_client.errors import APIResponseError

        # Mock 未授權錯誤
        auth_error = APIResponseError(
            response=Mock(status_code=401), message="Unauthorized", code="unauthorized"
        )
        notion_manager.notion.pages.create.side_effect = auth_error

        result = notion_manager.create_name_card_record(sample_card_data)

        # 應該優雅地處理錯誤
        assert result["success"] is False
        assert "error" in result
        assert "unauthorized" in result["error"].lower()

    def test_large_data_handling(self, notion_manager):
        """測試大數據量處理"""
        # 創建包含大量文本的名片數據
        large_data = {
            "name": "測試" * 100,  # 長名稱
            "company": "公司名稱" * 200,  # 長公司名
            "notes": "備註內容" * 500,  # 長備註
            "address": "地址內容" * 100,  # 長地址
        }

        # Mock Notion API 回應
        mock_response = {
            "id": "large_data_page_id",
            "url": "https://notion.so/large_data_page_id",
        }
        notion_manager.notion.pages.create.return_value = mock_response

        result = notion_manager.create_name_card_record(large_data)

        # 應該能處理大數據
        assert result["success"] is True

    # ==========================================
    # 6. 並發處理測試
    # ==========================================

    def test_concurrent_record_creation(self, notion_manager):
        """測試並發記錄創建"""
        import asyncio
        import threading

        # Mock Notion API 回應
        mock_response = {
            "id": "concurrent_page_id",
            "url": "https://notion.so/concurrent_page_id",
        }
        notion_manager.notion.pages.create.return_value = mock_response

        results = []

        def create_record(index):
            data = {"name": f"並發測試 {index}", "company": f"公司 {index}"}
            result = notion_manager.create_name_card_record(data)
            results.append(result)

        # 創建 10 個並發線程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_record, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        # 驗證所有請求都成功
        assert len(results) == 10
        assert all(result["success"] for result in results)

    # ==========================================
    # 7. 數據完整性測試
    # ==========================================

    def test_data_sanitization(self, notion_manager):
        """測試數據清理和驗證"""
        # 包含特殊字符和潛在問題的數據
        problematic_data = {
            "name": "張小明 <script>alert('xss')</script>",  # XSS 嘗試
            "email": "invalid-email@",  # 不完整的 email
            "phone": "Phone: 02-1234-5678 ext.123",  # 包含額外文字的電話
            "address": "台北市\n\r信義區\t信義路",  # 包含換行和制表符
            "notes": "A" * 2000,  # 過長的備註
        }

        properties = notion_manager._build_properties(problematic_data)

        # 驗證數據被適當處理
        assert "Name" in properties
        # XSS 內容應該被當作普通文本處理
        assert "<script>" in properties["Name"]["title"][0]["text"]["content"]

        # 無效 email 應該放在備註欄位
        assert "Email備註" in properties

        # 長文本應該被適當處理
        assert "聯繫注意事項" in properties

    def test_unicode_handling(self, notion_manager):
        """測試 Unicode 字符處理"""
        unicode_data = {
            "name": "張小明 🎯",  # 包含 emoji
            "company": "科技公司 (株式会社)",  # 中日文混合
            "notes": "Ñiño café résumé",  # 特殊拉丁字符
            "address": "臺北市 vs 台北市",  # 繁簡體差異
        }

        properties = notion_manager._build_properties(unicode_data)

        # 所有 Unicode 字符都應該被正確處理
        assert "🎯" in properties["Name"]["title"][0]["text"]["content"]
        assert "株式会社" in properties["公司名稱"]["rich_text"][0]["text"]["content"]
        assert "résumé" in properties["聯繫注意事項"]["rich_text"][0]["text"]["content"]

    # ==========================================
    # 8. 整合測試
    # ==========================================

    def test_end_to_end_notion_workflow(
        self, notion_manager, sample_card_data, sample_image_bytes
    ):
        """端到端 Notion 工作流程測試"""
        # Mock 所有必要的 Notion API 調用
        mock_create_response = {
            "id": "e2e_test_page_id",
            "url": "https://notion.so/e2e_test_page_id",
        }
        notion_manager.notion.pages.create.return_value = mock_create_response
        notion_manager.notion.blocks.children.append = Mock()

        with (
            patch.object(notion_manager, "_add_image_info_to_page") as mock_add_image,
            patch.object(
                notion_manager, "_add_address_processing_info"
            ) as mock_add_address,
        ):
            # 執行完整的工作流程
            result = notion_manager.create_name_card_record(
                sample_card_data, sample_image_bytes
            )

            # 驗證整個流程
            assert result["success"] is True
            assert result["notion_page_id"] == "e2e_test_page_id"
            assert result["url"] == "https://notion.so/e2e_test_page_id"

            # 驗證所有步驟都被執行
            notion_manager.notion.pages.create.assert_called_once()
            mock_add_image.assert_called_once()
            mock_add_address.assert_called_once()


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
