"""
Unit tests for LINE Bot message handlers - LINE Bot 訊息處理器測試
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from linebot.models import MessageEvent, TextMessage, ImageMessage, FollowEvent
import json


class TestLineHandlers:
    """LINE Bot 訊息處理器單元測試"""
    
    def setup_method(self):
        """每個測試方法前的設置"""
        # Mock all external dependencies
        with patch('linebot.LineBotApi'), \
             patch('linebot.WebhookHandler'), \
             patch('name_card_processor.NameCardProcessor'), \
             patch('notion_manager.NotionManager'), \
             patch('batch_manager.BatchManager'), \
             patch('pr_creator.PRCreator'):
            
            # Import app after mocking dependencies
            import app
            self.app_module = app
            
            # Setup test client
            self.app = app.app.test_client()
            self.app.testing = True
    
    @pytest.mark.unit
    def test_callback_post_success(self):
        """測試成功的 webhook 回調"""
        with patch.object(self.app_module.handler, 'handle') as mock_handle:
            mock_handle.return_value = None
            
            response = self.app.post('/callback',
                data='{"events": []}',
                headers={
                    'Content-Type': 'application/json',
                    'X-Line-Signature': 'test_signature'
                }
            )
            
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'OK'
            mock_handle.assert_called_once()
    
    @pytest.mark.unit
    def test_callback_missing_signature(self):
        """測試缺少簽名的請求"""
        response = self.app.post('/callback',
            data='{"events": []}',
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        assert b'Missing X-Line-Signature header' in response.data
    
    @pytest.mark.unit
    def test_callback_wrong_content_type(self):
        """測試錯誤的 Content-Type"""
        response = self.app.post('/callback',
            data='{"events": []}',
            headers={
                'Content-Type': 'text/plain',
                'X-Line-Signature': 'test_signature'
            }
        )
        
        assert response.status_code == 400
        assert b'Content-Type must be application/json' in response.data
    
    @pytest.mark.unit
    def test_callback_empty_body(self):
        """測試空的請求體"""
        response = self.app.post('/callback',
            data='',
            headers={
                'Content-Type': 'application/json',
                'X-Line-Signature': 'test_signature'
            }
        )
        
        assert response.status_code == 400
        assert b'Empty request body' in response.data
    
    @pytest.mark.unit
    def test_callback_get_method(self):
        """測試 GET 方法的回調"""
        response = self.app.get('/callback')
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert data['message'] == 'LINE Bot webhook endpoint'
        assert data['method'] == 'POST only'
        assert data['status'] == 'ready'
    
    @pytest.mark.unit
    def test_health_endpoint(self):
        """測試健康檢查端點"""
        response = self.app.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert data['status'] == 'healthy'
        assert data['message'] == 'LINE Bot is running'
    
    @pytest.mark.unit
    def test_test_endpoint(self):
        """測試服務測試端點"""
        with patch.object(self.app_module.notion_manager, 'test_connection') as mock_notion:
            mock_notion.return_value = {"success": True, "message": "Notion 連接正常"}
            
            response = self.app.get('/test')
            
            assert response.status_code == 200
            data = json.loads(response.get_data(as_text=True))
            assert 'notion' in data
            assert 'gemini' in data
            assert data['notion']['success'] is True
            mock_notion.assert_called_once()


class TestTextMessageHandlers:
    """文字訊息處理器測試"""
    
    def setup_method(self):
        """設置測試環境"""
        self.mock_event = Mock()
        self.mock_event.source.user_id = "test_user_id"
        self.mock_event.reply_token = "test_reply_token"
        
        # Mock dependencies
        self.mock_line_bot_api = Mock()
        self.mock_batch_manager = Mock()
        
        with patch('app.line_bot_api', self.mock_line_bot_api), \
             patch('app.batch_manager', self.mock_batch_manager):
            import app
            self.handle_text_message = app.handle_text_message
    
    @pytest.mark.unit
    def test_batch_start_command(self):
        """測試批次模式開始指令"""
        self.mock_event.message.text = "批次"
        
        # Mock batch manager response
        self.mock_batch_manager.start_batch_mode.return_value = {
            "success": True,
            "message": "批次處理模式已啟動"
        }
        
        self.handle_text_message(self.mock_event)
        
        # 檢查是否調用了正確的方法
        self.mock_batch_manager.start_batch_mode.assert_called_once_with("test_user_id")
        self.mock_line_bot_api.reply_message.assert_called_once()
        
        # 檢查回復訊息
        call_args = self.mock_line_bot_api.reply_message.call_args
        assert call_args[0][0] == "test_reply_token"
        assert "批次處理模式已啟動" in call_args[0][1].text
    
    @pytest.mark.unit
    def test_batch_end_command_success(self):
        """測試成功結束批次模式"""
        self.mock_event.message.text = "結束批次"
        
        # Mock batch manager response with statistics
        self.mock_batch_manager.end_batch_mode.return_value = {
            "success": True,
            "statistics": {
                "total_processed": 2,
                "total_failed": 1,
                "total_time_minutes": 5.5,
                "processed_cards": [
                    {"name": "張三", "company": "公司A"},
                    {"name": "李四", "company": "公司B"}
                ],
                "failed_cards": [
                    {"error": "圖片識別失敗"}
                ]
            }
        }
        
        self.handle_text_message(self.mock_event)
        
        # 檢查是否調用了正確的方法
        self.mock_batch_manager.end_batch_mode.assert_called_once_with("test_user_id")
        self.mock_line_bot_api.reply_message.assert_called_once()
        
        # 檢查回復訊息包含統計資訊
        call_args = self.mock_line_bot_api.reply_message.call_args
        reply_text = call_args[0][1].text
        assert "批次處理完成" in reply_text
        assert "處理成功: 2 張" in reply_text
        assert "處理失敗: 1 張" in reply_text
        assert "總耗時: 5.5 分鐘" in reply_text
        assert "張三" in reply_text
        assert "李四" in reply_text
    
    @pytest.mark.unit
    def test_batch_status_command_in_batch(self):
        """測試批次狀態查詢（在批次模式中）"""
        self.mock_event.message.text = "狀態"
        
        # Mock batch manager responses
        self.mock_batch_manager.is_in_batch_mode.return_value = True
        self.mock_batch_manager.get_batch_progress_message.return_value = "目前處理了 3 張名片"
        
        self.handle_text_message(self.mock_event)
        
        # 檢查方法調用
        self.mock_batch_manager.is_in_batch_mode.assert_called_once_with("test_user_id")
        self.mock_batch_manager.get_batch_progress_message.assert_called_once_with("test_user_id")
        self.mock_line_bot_api.reply_message.assert_called_once()
        
        # 檢查回復訊息
        call_args = self.mock_line_bot_api.reply_message.call_args
        assert "目前處理了 3 張名片" in call_args[0][1].text
    
    @pytest.mark.unit
    def test_batch_status_command_not_in_batch(self):
        """測試批次狀態查詢（不在批次模式中）"""
        self.mock_event.message.text = "狀態"
        
        # Mock batch manager response
        self.mock_batch_manager.is_in_batch_mode.return_value = False
        
        self.handle_text_message(self.mock_event)
        
        # 檢查回復訊息
        call_args = self.mock_line_bot_api.reply_message.call_args
        assert "您目前不在批次模式中" in call_args[0][1].text
    
    @pytest.mark.unit
    def test_help_command(self):
        """測試幫助指令"""
        self.mock_event.message.text = "help"
        
        self.handle_text_message(self.mock_event)
        
        # 檢查回復訊息包含幫助內容
        call_args = self.mock_line_bot_api.reply_message.call_args
        reply_text = call_args[0][1].text
        assert "名片管理 LINE Bot - 完整使用指南" in reply_text
        assert "單張名片處理" in reply_text
        assert "批次處理模式" in reply_text
        assert "智能特色" in reply_text
    
    @pytest.mark.unit
    def test_create_pr_command_with_description(self):
        """測試創建 PR 指令（含描述）"""
        self.mock_event.message.text = "create pr: 添加用戶登入功能"
        
        with patch('app.pr_creator') as mock_pr_creator:
            mock_pr_creator.create_instant_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/test/repo/pull/123",
                "branch_name": "feature/login",
                "changes_applied": 5
            }
            
            self.handle_text_message(self.mock_event)
            
            # 檢查 PR 創建被調用
            mock_pr_creator.create_instant_pr.assert_called_once_with("添加用戶登入功能")
            
            # 檢查回復訊息
            self.mock_line_bot_api.reply_message.assert_called_once()
            reply_call = self.mock_line_bot_api.reply_message.call_args
            assert "正在創建 PR" in reply_call[0][1].text
            
            # 檢查推送訊息
            self.mock_line_bot_api.push_message.assert_called_once()
            push_call = self.mock_line_bot_api.push_message.call_args
            push_text = push_call[0][1].text
            assert "PR 創建成功" in push_text
            assert "https://github.com/test/repo/pull/123" in push_text
    
    @pytest.mark.unit
    def test_create_pr_command_no_description(self):
        """測試創建 PR 指令（無描述）"""
        self.mock_event.message.text = "create pr:"
        
        self.handle_text_message(self.mock_event)
        
        # 檢查錯誤回復
        call_args = self.mock_line_bot_api.reply_message.call_args
        assert "請提供 PR 描述" in call_args[0][1].text
    
    @pytest.mark.unit
    def test_unknown_text_message_not_in_batch(self):
        """測試未知文字訊息（不在批次模式）"""
        self.mock_event.message.text = "隨便說點什麼"
        
        # Mock batch manager response
        self.mock_batch_manager.is_in_batch_mode.return_value = False
        
        self.handle_text_message(self.mock_event)
        
        # 檢查回復包含使用指南
        call_args = self.mock_line_bot_api.reply_message.call_args
        reply_text = call_args[0][1].text
        assert "請上傳您的名片照片" in reply_text
        assert "單張處理：直接傳送圖片即可" in reply_text
    
    @pytest.mark.unit
    def test_unknown_text_message_in_batch(self):
        """測試未知文字訊息（在批次模式中）"""
        self.mock_event.message.text = "隨便說點什麼"
        
        # Mock batch manager responses
        self.mock_batch_manager.is_in_batch_mode.return_value = True
        self.mock_batch_manager.get_batch_progress_message.return_value = "目前進度：3/5"
        
        self.handle_text_message(self.mock_event)
        
        # 檢查回復包含批次模式提示
        call_args = self.mock_line_bot_api.reply_message.call_args
        reply_text = call_args[0][1].text
        assert "您目前在批次模式中" in reply_text
        assert "目前進度：3/5" in reply_text


class TestFollowEventHandler:
    """關注事件處理器測試"""
    
    def setup_method(self):
        """設置測試環境"""
        self.mock_event = Mock()
        self.mock_event.source.user_id = "new_user_id"
        self.mock_event.reply_token = "welcome_reply_token"
        
        self.mock_line_bot_api = Mock()
        
        with patch('app.line_bot_api', self.mock_line_bot_api):
            import app
            self.handle_follow_event = app.handle_follow_event
    
    @pytest.mark.unit
    def test_follow_event_success(self):
        """測試成功處理關注事件"""
        self.handle_follow_event(self.mock_event)
        
        # 檢查是否發送了歡迎訊息
        self.mock_line_bot_api.reply_message.assert_called_once()
        call_args = self.mock_line_bot_api.reply_message.call_args
        
        assert call_args[0][0] == "welcome_reply_token"
        welcome_text = call_args[0][1].text
        assert "歡迎使用名片管理 LINE Bot" in welcome_text
        assert "快速開始指南" in welcome_text
        assert "上傳單張名片" in welcome_text
        assert "批次處理多張名片" in welcome_text
    
    @pytest.mark.unit
    def test_follow_event_api_error(self):
        """測試關注事件 API 錯誤"""
        # Mock LINE API 錯誤
        self.mock_line_bot_api.reply_message.side_effect = Exception("LINE API error")
        
        # 應該不會拋出異常（已處理錯誤）
        self.handle_follow_event(self.mock_event)
        
        # 仍然嘗試發送歡迎訊息
        self.mock_line_bot_api.reply_message.assert_called_once()