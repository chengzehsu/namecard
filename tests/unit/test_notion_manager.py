"""
Unit tests for NotionManager - Notion 資料庫管理器測試
"""
import pytest
from unittest.mock import Mock, patch, call
from notion_manager import NotionManager


class TestNotionManager:
    """NotionManager 單元測試"""
    
    def setup_method(self):
        """每個測試方法前的設置"""
        with patch('notion_client.Client'):
            self.notion_manager = NotionManager()
    
    @pytest.mark.unit
    @patch('notion_client.Client')
    def test_init_success(self, mock_client):
        """測試成功初始化"""
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        manager = NotionManager()
        
        mock_client.assert_called_once()
        assert manager.client == mock_instance
    
    @pytest.mark.unit
    @patch('notion_client.Client')
    def test_init_failure(self, mock_client):
        """測試初始化失敗"""
        mock_client.side_effect = Exception("API key invalid")
        
        with pytest.raises(Exception) as exc_info:
            NotionManager()
        
        assert "初始化 Notion 客戶端失敗" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_build_properties_complete_data(self, sample_card_data):
        """測試建立完整資料的屬性"""
        properties = self.notion_manager._build_properties(sample_card_data)
        
        # 檢查基本屬性
        assert properties["Name"]["title"][0]["text"]["content"] == "張三"
        assert properties["公司名稱"]["rich_text"][0]["text"]["content"] == "測試科技公司"
        assert properties["部門"]["rich_text"][0]["text"]["content"] == "技術部"
        assert properties["職稱"]["select"]["name"] == "資深工程師"
        assert properties["決策影響力"]["select"]["name"] == "中"
        assert properties["Email"]["email"] == "zhang.san@test.com"
        assert properties["電話"]["phone_number"] == "+886912345678"
        assert properties["地址"]["rich_text"][0]["text"]["content"] == "台北市信義區信義路五段7號"
        assert properties["取得聯繫來源"]["rich_text"][0]["text"]["content"] == "名片交換"
        assert properties["聯繫注意事項"]["rich_text"][0]["text"]["content"] == "專精於軟體開發"
    
    @pytest.mark.unit
    def test_build_properties_minimal_data(self):
        """測試建立最小資料的屬性"""
        minimal_data = {"name": "李四"}
        properties = self.notion_manager._build_properties(minimal_data)
        
        # 只有名稱應該有值
        assert properties["Name"]["title"][0]["text"]["content"] == "李四"
        
        # 其他欄位應該為空或預設值
        assert properties["公司名稱"]["rich_text"] == []
        assert properties["部門"]["rich_text"] == []
        assert properties["職稱"]["select"] is None
        assert properties["決策影響力"]["select"] is None
        assert properties["Email"]["email"] is None
        assert properties["電話"]["phone_number"] is None
        assert properties["地址"]["rich_text"] == []
        assert properties["取得聯繫來源"]["rich_text"] == []
        assert properties["聯繫注意事項"]["rich_text"] == []
    
    @pytest.mark.unit
    def test_build_properties_invalid_email(self):
        """測試無效 email 的處理"""
        data_with_invalid_email = {
            "name": "測試用戶",
            "email": "invalid-email-format"
        }
        
        properties = self.notion_manager._build_properties(data_with_invalid_email)
        
        # 無效 email 應該被設為 None，錯誤資訊加入備註
        assert properties["Email"]["email"] is None
        assert "Email 格式錯誤" in properties["聯繫注意事項"]["rich_text"][0]["text"]["content"]
    
    @pytest.mark.unit
    def test_build_properties_invalid_phone(self):
        """測試無效電話號碼的處理"""
        data_with_invalid_phone = {
            "name": "測試用戶",
            "phone": "invalid-phone"
        }
        
        properties = self.notion_manager._build_properties(data_with_invalid_phone)
        
        # 無效電話應該被設為 None，錯誤資訊加入備註
        assert properties["電話"]["phone_number"] is None
        assert "電話格式錯誤" in properties["聯繫注意事項"]["rich_text"][0]["text"]["content"]
    
    @pytest.mark.unit
    def test_build_properties_address_processing_info(self):
        """測試地址處理資訊的加入"""
        data_with_address_info = {
            "name": "測試用戶",
            "address": "台北市信義區信義路五段7號",
            "_address_confidence": 0.8,
            "_original_address": "台北信義區信義路5段7號",
            "notes": "原有備註"
        }
        
        properties = self.notion_manager._build_properties(data_with_address_info)
        
        notes_content = properties["聯繫注意事項"]["rich_text"][0]["text"]["content"]
        assert "原有備註" in notes_content
        assert "地址處理資訊" in notes_content
        assert "信心度: 80%" in notes_content
        assert "原始地址: 台北信義區信義路5段7號" in notes_content
    
    @pytest.mark.unit
    def test_create_name_card_record_success(self, sample_card_data):
        """測試成功創建名片記錄"""
        # Mock Notion client response
        mock_response = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page_id"
        }
        self.notion_manager.client.pages.create.return_value = mock_response
        
        image_bytes = b"fake_image_data"
        result = self.notion_manager.create_name_card_record(sample_card_data, image_bytes)
        
        assert result["success"] is True
        assert result["page_id"] == "test_page_id"
        assert result["url"] == "https://notion.so/test_page_id"
        
        # 檢查是否調用了正確的 API
        self.notion_manager.client.pages.create.assert_called_once()
        call_args = self.notion_manager.client.pages.create.call_args
        assert call_args[1]["parent"]["database_id"] == "test_db_id"
    
    @pytest.mark.unit
    def test_create_name_card_record_notion_api_error(self, sample_card_data):
        """測試 Notion API 錯誤處理"""
        # Mock API 錯誤
        self.notion_manager.client.pages.create.side_effect = Exception("Notion API error")
        
        image_bytes = b"fake_image_data"
        result = self.notion_manager.create_name_card_record(sample_card_data, image_bytes)
        
        assert result["success"] is False
        assert "Notion API error" in result["error"]
    
    @pytest.mark.unit
    @patch('notion_manager.NotionManager._add_image_info_to_page')
    def test_create_name_card_record_with_image(self, mock_add_image, sample_card_data):
        """測試包含圖片的記錄創建"""
        # Mock successful page creation
        mock_response = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page_id"
        }
        self.notion_manager.client.pages.create.return_value = mock_response
        
        image_bytes = b"fake_image_data"
        result = self.notion_manager.create_name_card_record(sample_card_data, image_bytes)
        
        assert result["success"] is True
        # 應該調用添加圖片資訊的方法
        mock_add_image.assert_called_once_with("test_page_id", image_bytes)
    
    @pytest.mark.unit
    @patch('notion_manager.NotionManager._add_image_info_to_page')
    def test_create_name_card_record_image_error(self, mock_add_image, sample_card_data):
        """測試圖片處理錯誤的情況"""
        # Mock successful page creation
        mock_response = {
            "id": "test_page_id", 
            "url": "https://notion.so/test_page_id"
        }
        self.notion_manager.client.pages.create.return_value = mock_response
        
        # Mock image processing error
        mock_add_image.side_effect = Exception("Image upload failed")
        
        image_bytes = b"fake_image_data"
        result = self.notion_manager.create_name_card_record(sample_card_data, image_bytes)
        
        # 頁面創建成功，但有圖片處理警告
        assert result["success"] is True
        assert "圖片處理失敗" in result.get("warning", "")
    
    @pytest.mark.unit
    def test_add_image_info_to_page(self):
        """測試添加圖片資訊到頁面"""
        page_id = "test_page_id"
        image_bytes = b"fake_image_data"
        
        # Mock successful block append
        self.notion_manager.client.blocks.children.append.return_value = {"results": []}
        
        self.notion_manager._add_image_info_to_page(page_id, image_bytes)
        
        # 檢查是否正確調用了 API
        self.notion_manager.client.blocks.children.append.assert_called_once()
        call_args = self.notion_manager.client.blocks.children.append.call_args
        
        assert call_args[1]["block_id"] == page_id
        # 檢查是否包含圖片處理資訊的區塊
        children = call_args[1]["children"]
        assert len(children) >= 2  # 至少有標題和內容區塊
    
    @pytest.mark.unit
    def test_add_image_info_to_page_api_error(self):
        """測試添加圖片資訊時的 API 錯誤"""
        page_id = "test_page_id"
        image_bytes = b"fake_image_data"
        
        # Mock API 錯誤
        self.notion_manager.client.blocks.children.append.side_effect = Exception("Block append failed")
        
        with pytest.raises(Exception) as exc_info:
            self.notion_manager._add_image_info_to_page(page_id, image_bytes)
        
        assert "Block append failed" in str(exc_info.value)
    
    @pytest.mark.unit 
    def test_test_connection_success(self):
        """測試連接測試成功"""
        # Mock successful database query
        self.notion_manager.client.databases.query.return_value = {
            "results": [],
            "has_more": False
        }
        
        result = self.notion_manager.test_connection()
        
        assert result["success"] is True
        assert "Notion 連接正常" in result["message"]
        
        # 檢查是否調用了資料庫查詢
        self.notion_manager.client.databases.query.assert_called_once_with(
            database_id="test_db_id",
            page_size=1
        )
    
    @pytest.mark.unit
    def test_test_connection_failure(self):
        """測試連接測試失敗"""
        # Mock API 錯誤
        self.notion_manager.client.databases.query.side_effect = Exception("Database not found")
        
        result = self.notion_manager.test_connection()
        
        assert result["success"] is False
        assert "Database not found" in result["error"]
    
    @pytest.mark.unit
    def test_validate_email_format(self):
        """測試 email 格式驗證"""
        # 有效 email
        assert self.notion_manager._is_valid_email("test@example.com") is True
        assert self.notion_manager._is_valid_email("user.name+tag@domain.co.uk") is True
        
        # 無效 email
        assert self.notion_manager._is_valid_email("invalid-email") is False
        assert self.notion_manager._is_valid_email("@domain.com") is False
        assert self.notion_manager._is_valid_email("user@") is False
        assert self.notion_manager._is_valid_email("") is False
        assert self.notion_manager._is_valid_email(None) is False
    
    @pytest.mark.unit
    def test_validate_phone_format(self):
        """測試電話號碼格式驗證"""
        # 有效電話號碼 (E.164 格式)
        assert self.notion_manager._is_valid_phone("+886912345678") is True
        assert self.notion_manager._is_valid_phone("+1234567890") is True
        
        # 無效電話號碼
        assert self.notion_manager._is_valid_phone("0912345678") is False  # 沒有國碼
        assert self.notion_manager._is_valid_phone("invalid-phone") is False
        assert self.notion_manager._is_valid_phone("") is False
        assert self.notion_manager._is_valid_phone(None) is False