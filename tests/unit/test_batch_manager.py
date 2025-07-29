"""
Unit tests for BatchManager - 批次處理管理器測試
"""
import pytest
import time
from unittest.mock import patch, Mock
from batch_manager import BatchManager


class TestBatchManager:
    """BatchManager 單元測試"""
    
    def setup_method(self):
        """每個測試方法前的設置"""
        self.batch_manager = BatchManager()
        self.test_user_id = "test_user_123"
    
    def teardown_method(self):
        """每個測試方法後的清理"""
        # 清理測試用戶的會話
        if self.test_user_id in self.batch_manager.user_sessions:
            del self.batch_manager.user_sessions[self.test_user_id]
    
    @pytest.mark.unit
    def test_start_batch_mode_new_user(self):
        """測試新用戶開始批次模式"""
        result = self.batch_manager.start_batch_mode(self.test_user_id)
        
        assert result["success"] is True
        assert "批次模式已啟動" in result["message"]
        assert self.batch_manager.is_in_batch_mode(self.test_user_id) is True
        
        # 檢查會話狀態
        session = self.batch_manager.get_session_info(self.test_user_id)
        assert session["total_count"] == 0
        assert session["processed_count"] == 0
        assert session["failed_count"] == 0
    
    @pytest.mark.unit
    def test_start_batch_mode_existing_user(self):
        """測試已在批次模式的用戶重新開始（重置會話）"""
        # 先啟動批次模式
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        # 添加一些數據
        self.batch_manager.add_processed_card(self.test_user_id, {"name": "test"})
        
        # 再次啟動（會重置會話）
        result = self.batch_manager.start_batch_mode(self.test_user_id)
        
        assert result["success"] is True
        assert "批次模式已啟動" in result["message"]
        
        # 會話應該被重置
        session = self.batch_manager.get_session_info(self.test_user_id)
        assert session["total_count"] == 0
    
    @pytest.mark.unit
    def test_is_in_batch_mode(self):
        """測試批次模式狀態檢查"""
        # 未開始批次模式
        assert self.batch_manager.is_in_batch_mode(self.test_user_id) is False
        
        # 開始批次模式
        self.batch_manager.start_batch_mode(self.test_user_id)
        assert self.batch_manager.is_in_batch_mode(self.test_user_id) is True
        
        # 結束批次模式
        self.batch_manager.end_batch_mode(self.test_user_id)
        assert self.batch_manager.is_in_batch_mode(self.test_user_id) is False
    
    @pytest.mark.unit
    def test_add_processed_card(self):
        """測試添加成功處理的名片"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        card_info = {
            "name": "張三",
            "company": "測試公司",
            "notion_url": "https://notion.so/test"
        }
        
        self.batch_manager.add_processed_card(self.test_user_id, card_info)
        
        session = self.batch_manager.get_session_info(self.test_user_id)
        assert session["total_count"] == 1
        assert session["processed_count"] == 1
        assert session["failed_count"] == 0
    
    @pytest.mark.unit
    def test_add_failed_card(self):
        """測試添加失敗處理的名片"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        error_message = "Gemini API 連接失敗"
        self.batch_manager.add_failed_card(self.test_user_id, error_message)
        
        session = self.batch_manager.get_session_info(self.test_user_id)
        assert session["total_count"] == 1
        assert session["processed_count"] == 0
        assert session["failed_count"] == 1
    
    @pytest.mark.unit
    def test_end_batch_mode_with_results(self):
        """測試結束有結果的批次模式"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        # 添加一些處理結果
        self.batch_manager.add_processed_card(self.test_user_id, {
            "name": "張三", "company": "公司A", "notion_url": "url1"
        })
        self.batch_manager.add_failed_card(self.test_user_id, "測試錯誤")
        
        result = self.batch_manager.end_batch_mode(self.test_user_id)
        
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["total_processed"] == 1
        assert stats["total_failed"] == 1
        assert stats["total_time_minutes"] > 0
        
        # 批次模式應該結束
        assert self.batch_manager.is_in_batch_mode(self.test_user_id) is False
    
    @pytest.mark.unit
    def test_end_batch_mode_empty(self):
        """測試結束空的批次模式"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        result = self.batch_manager.end_batch_mode(self.test_user_id)
        
        assert result["success"] is True
        stats = result["statistics"]
        assert stats["total_processed"] == 0
        assert stats["total_failed"] == 0
    
    @pytest.mark.unit
    def test_end_batch_mode_not_in_batch(self):
        """測試結束未開始的批次模式"""
        result = self.batch_manager.end_batch_mode(self.test_user_id)
        
        assert result["success"] is False
        assert "您目前不在批次模式中" in result["message"]
    
    @pytest.mark.unit
    def test_get_batch_progress_message(self):
        """測試批次進度訊息生成"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        # 添加一些結果
        self.batch_manager.add_processed_card(self.test_user_id, {
            "name": "張三", "company": "公司A", "notion_url": "url1"
        })
        self.batch_manager.add_failed_card(self.test_user_id, "錯誤訊息")
        
        progress_msg = self.batch_manager.get_batch_progress_message(self.test_user_id)
        
        assert "批次模式進行中" in progress_msg
        assert "已處理: 1 張" in progress_msg
        assert "失敗: 1 張" in progress_msg
        assert "總計: 2 張" in progress_msg
    
    @pytest.mark.unit
    def test_get_batch_progress_message_not_in_batch(self):
        """測試未在批次模式時的進度訊息"""
        progress_msg = self.batch_manager.get_batch_progress_message(self.test_user_id)
        assert progress_msg == ""
    
    @pytest.mark.unit
    def test_update_activity(self):
        """測試更新用戶活動時間"""
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        original_time = self.batch_manager.user_sessions[self.test_user_id]["last_activity"]
        time.sleep(0.1)  # 短暫延遲
        
        self.batch_manager.update_activity(self.test_user_id)
        new_time = self.batch_manager.user_sessions[self.test_user_id]["last_activity"]
        
        assert new_time > original_time
    
    @pytest.mark.unit
    def test_cleanup_expired_sessions(self):
        """測試清理過期會話"""
        # 創建一個過期的會話
        expired_user = "expired_user"
        self.batch_manager.start_batch_mode(expired_user)
        
        # 手動設置為過期時間
        from datetime import datetime, timedelta
        self.batch_manager.user_sessions[expired_user]["last_activity"] = datetime.now() - timedelta(minutes=15)  # 超過10分鐘
        
        # 創建一個正常的會話
        self.batch_manager.start_batch_mode(self.test_user_id)
        
        # 執行清理
        self.batch_manager.cleanup_expired_sessions()
        
        # 過期會話應該被清理
        assert expired_user not in self.batch_manager.user_sessions
        # 正常會話應該保留
        assert self.test_user_id in self.batch_manager.user_sessions
    
    @pytest.mark.unit
    def test_concurrent_users(self):
        """測試多用戶並發處理"""
        user1 = "user1"
        user2 = "user2"
        
        # 兩個用戶同時開始批次模式
        self.batch_manager.start_batch_mode(user1)
        self.batch_manager.start_batch_mode(user2)
        
        # 添加不同的處理結果
        self.batch_manager.add_processed_card(user1, {"name": "用戶1的名片", "company": "公司1", "notion_url": "url1"})
        self.batch_manager.add_processed_card(user2, {"name": "用戶2的名片", "company": "公司2", "notion_url": "url2"})
        
        # 檢查各自的會話獨立性
        session1 = self.batch_manager.get_session_info(user1)
        session2 = self.batch_manager.get_session_info(user2)
        
        assert session1["processed_count"] == 1
        assert session2["processed_count"] == 1
        
        # 清理
        del self.batch_manager.user_sessions[user1]
        del self.batch_manager.user_sessions[user2]
    
    @pytest.mark.unit
    def test_get_session_info_invalid_user(self):
        """測試獲取無效用戶的會話資訊"""
        session = self.batch_manager.get_session_info("nonexistent_user")
        assert session is None