"""
Integration tests for end-to-end workflow - 端到端工作流程整合測試
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os


@pytest.mark.integration
class TestEndToEndWorkflow:
    """端到端工作流程整合測試"""
    
    def setup_method(self):
        """設置測試環境"""
        # Mock all external services but allow internal component interaction
        self.mock_patches = []
        
        # Mock LINE Bot API
        line_api_patch = patch('linebot.LineBotApi')
        self.mock_line_api = line_api_patch.start()
        self.mock_patches.append(line_api_patch)
        
        # Mock Webhook Handler
        handler_patch = patch('linebot.WebhookHandler')  
        self.mock_handler = handler_patch.start()
        self.mock_patches.append(handler_patch)
        
        # Mock Gemini AI
        gemini_patch = patch('google.generativeai.GenerativeModel')
        self.mock_gemini = gemini_patch.start()
        self.mock_patches.append(gemini_patch)
        
        # Mock Notion Client
        notion_patch = patch('notion_client.Client')
        self.mock_notion = notion_patch.start()
        self.mock_patches.append(notion_patch)
        
        # Configure mocks
        self.setup_mocks()
        
        # Import app after mocking
        import app
        self.app_module = app
        self.test_client = app.app.test_client()
        self.test_client.testing = True
    
    def teardown_method(self):
        """清理測試環境"""
        for patch_obj in self.mock_patches:
            patch_obj.stop()
    
    def setup_mocks(self):
        """配置模擬對象"""
        # Configure LINE Bot API mock
        self.mock_line_api_instance = Mock()
        self.mock_line_api.return_value = self.mock_line_api_instance
        
        # Configure Webhook Handler mock
        self.mock_handler_instance = Mock()
        self.mock_handler.return_value = self.mock_handler_instance
        
        # Configure Gemini AI mock
        self.mock_gemini_instance = Mock()
        self.mock_gemini.return_value = self.mock_gemini_instance
        
        # Mock successful name card extraction
        mock_gemini_response = Mock()
        mock_gemini_response.text = json.dumps({
            "name": "張三",
            "company": "測試科技公司",
            "department": "技術部",
            "title": "資深工程師",
            "decision_influence": "中",
            "email": "zhang.san@test.com",
            "phone": "+886912345678",
            "address": "台北市信義區信義路五段7號",
            "contact_source": "名片交換",
            "notes": "專精於軟體開發"
        })
        self.mock_gemini_instance.generate_content.return_value = mock_gemini_response
        
        # Configure Notion client mock
        self.mock_notion_instance = Mock()
        self.mock_notion.return_value = self.mock_notion_instance
        
        # Mock successful page creation
        self.mock_notion_instance.pages.create.return_value = {
            "id": "test_page_id_123",
            "url": "https://notion.so/test_page_id_123"
        }
        
        # Mock successful image content download
        mock_content = Mock()
        mock_content.iter_content.return_value = [b"fake_image_chunk1", b"fake_image_chunk2"]
        self.mock_line_api_instance.get_message_content.return_value = mock_content
    
    def test_single_card_processing_complete_workflow(self):
        """測試單張名片處理完整工作流程"""
        # 模擬 LINE image message event
        test_event = Mock()
        test_event.message.id = "test_image_message_id"
        test_event.message.type = "image"
        test_event.source.user_id = "test_user_id"
        test_event.reply_token = "test_reply_token"
        
        # 執行 image message handler
        self.app_module.handle_image_message(test_event)
        
        # 驗證完整流程
        # 1. 檢查是否下載了圖片
        self.mock_line_api_instance.get_message_content.assert_called_once_with("test_image_message_id")
        
        # 2. 檢查是否調用了 Gemini AI
        self.mock_gemini_instance.generate_content.assert_called_once()
        
        # 3. 檢查是否創建了 Notion 頁面
        self.mock_notion_instance.pages.create.assert_called_once()
        
        # 4. 檢查是否發送了回復訊息
        assert self.mock_line_api_instance.reply_message.call_count >= 1
        assert self.mock_line_api_instance.push_message.call_count >= 1
        
        # 5. 驗證最終成功訊息
        push_calls = self.mock_line_api_instance.push_message.call_args_list
        final_message = push_calls[-1][0][1].text
        assert "名片資訊已成功存入 Notion" in final_message
        assert "張三" in final_message
        assert "測試科技公司" in final_message
        assert "https://notion.so/test_page_id_123" in final_message
    
    def test_batch_processing_complete_workflow(self):
        """測試批次處理完整工作流程"""
        user_id = "batch_test_user"
        
        # 1. 開始批次模式
        start_event = Mock()
        start_event.message.text = "批次"
        start_event.source.user_id = user_id
        start_event.reply_token = "start_reply_token"
        
        self.app_module.handle_text_message(start_event)
        
        # 驗證批次模式已開始
        reply_calls = self.mock_line_api_instance.reply_message.call_args_list
        start_reply = reply_calls[-1][0][1].text
        assert "批次處理模式已啟動" in start_reply
        
        # 2. 處理第一張名片
        image_event1 = Mock()
        image_event1.message.id = "image1_id"
        image_event1.message.type = "image"
        image_event1.source.user_id = user_id
        image_event1.reply_token = "image1_reply_token"
        
        self.app_module.handle_image_message(image_event1)
        
        # 3. 處理第二張名片
        image_event2 = Mock()
        image_event2.message.id = "image2_id"
        image_event2.message.type = "image"
        image_event2.source.user_id = user_id
        image_event2.reply_token = "image2_reply_token"
        
        # 修改第二張名片的 Gemini 回應
        mock_gemini_response2 = Mock()
        mock_gemini_response2.text = json.dumps({
            "name": "李四",
            "company": "另一家公司",
            "title": "經理"
        })
        self.mock_gemini_instance.generate_content.return_value = mock_gemini_response2
        
        self.app_module.handle_image_message(image_event2)
        
        # 4. 結束批次模式
        end_event = Mock()
        end_event.message.text = "結束批次"
        end_event.source.user_id = user_id
        end_event.reply_token = "end_reply_token"
        
        self.app_module.handle_text_message(end_event)
        
        # 驗證批次處理結果
        final_reply_calls = self.mock_line_api_instance.reply_message.call_args_list
        final_reply = final_reply_calls[-1][0][1].text
        
        assert "批次處理完成" in final_reply
        assert "處理成功: 2 張" in final_reply
        assert "處理失敗: 0 張" in final_reply
        
        # 驗證 Gemini 和 Notion 被調用了兩次
        assert self.mock_gemini_instance.generate_content.call_count == 2
        assert self.mock_notion_instance.pages.create.call_count == 2
    
    def test_error_handling_workflow(self):
        """測試錯誤處理工作流程"""
        # 模擬 Gemini API 錯誤
        self.mock_gemini_instance.generate_content.side_effect = Exception("Gemini API 連接失敗")
        
        test_event = Mock()
        test_event.message.id = "error_test_image_id"
        test_event.message.type = "image"
        test_event.source.user_id = "error_test_user"
        test_event.reply_token = "error_reply_token"
        
        # 執行處理
        self.app_module.handle_image_message(test_event)
        
        # 驗證錯誤被正確處理
        push_calls = self.mock_line_api_instance.push_message.call_args_list
        error_message = push_calls[-1][0][1].text
        
        assert "名片識別失敗" in error_message
        assert "Gemini API 連接失敗" in error_message
        
        # Notion 不應該被調用
        self.mock_notion_instance.pages.create.assert_not_called()
    
    def test_webhook_signature_validation_workflow(self):
        """測試 webhook 簽名驗證工作流程"""
        # 模擬有效的 webhook 請求
        with patch.object(self.app_module.handler, 'handle') as mock_handle:
            response = self.test_client.post('/callback',
                data='{"events": [{"type": "message"}]}',
                headers={
                    'Content-Type': 'application/json',
                    'X-Line-Signature': 'valid_signature'
                }
            )
            
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'OK'
            mock_handle.assert_called_once()
        
        # 模擬無效簽名的請求
        with patch.object(self.app_module.handler, 'handle') as mock_handle:
            from linebot.exceptions import InvalidSignatureError
            mock_handle.side_effect = InvalidSignatureError("Invalid signature")
            
            response = self.test_client.post('/callback',
                data='{"events": [{"type": "message"}]}',
                headers={
                    'Content-Type': 'application/json',
                    'X-Line-Signature': 'invalid_signature'
                }
            )
            
            assert response.status_code == 400
    
    def test_service_health_check_workflow(self):
        """測試服務健康檢查工作流程"""
        # 配置健康的服務回應
        self.mock_notion_instance.databases.query.return_value = {
            "results": [],
            "has_more": False
        }
        
        # 測試健康檢查端點
        response = self.test_client.get('/health')
        assert response.status_code == 200
        
        health_data = json.loads(response.get_data(as_text=True))
        assert health_data['status'] == 'healthy'
        
        # 測試服務測試端點
        response = self.test_client.get('/test')
        assert response.status_code == 200
        
        test_data = json.loads(response.get_data(as_text=True))
        assert 'notion' in test_data
        assert 'gemini' in test_data
        assert test_data['notion']['success'] is True
    
    def test_address_normalization_integration(self):
        """測試地址正規化整合"""
        # 模擬包含需要正規化地址的名片
        mock_gemini_response = Mock()
        mock_gemini_response.text = json.dumps({
            "name": "王五",
            "address": "台北信義區信義路5段7號1F"  # 需要正規化的地址
        })
        self.mock_gemini_instance.generate_content.return_value = mock_gemini_response
        
        test_event = Mock()
        test_event.message.id = "address_test_id"
        test_event.message.type = "image"
        test_event.source.user_id = "address_test_user"
        test_event.reply_token = "address_reply_token"
        
        # 執行處理
        self.app_module.handle_image_message(test_event)
        
        # 驗證 Notion 頁面創建被調用
        self.mock_notion_instance.pages.create.assert_called_once()
        
        # 檢查傳給 Notion 的屬性是否包含正規化後的地址
        call_args = self.mock_notion_instance.pages.create.call_args
        properties = call_args[1]['properties']
        
        # 地址應該被正規化為標準格式
        address_text = properties['地址']['rich_text'][0]['text']['content']
        assert "台北市信義區信義路五段7號1樓" == address_text
        
        # 應該包含地址處理資訊
        notes_text = properties['聯繫注意事項']['rich_text'][0]['text']['content']
        assert "地址處理資訊" in notes_text