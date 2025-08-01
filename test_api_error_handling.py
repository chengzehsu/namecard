"""
測試 LINE Bot API 錯誤處理機制
模擬各種 API 錯誤狀況，驗證降級服務
"""

import time
from unittest.mock import Mock, patch

from line_bot_handler import LineBotApiHandler
from linebot.exceptions import LineBotApiError
from linebot.models import Error


def test_quota_exceeded_error():
    """測試配額超限錯誤處理"""
    print("🧪 測試配額超限錯誤處理...")
    
    handler = LineBotApiHandler("test_token")
    
    # 模擬 429 配額錯誤
    error_obj = Error(message="You have reached your monthly limit.")
    mock_error = LineBotApiError(
        status_code=429,
        headers={},
        request_id="test-request-id",
        error=error_obj
    )
    
    with patch.object(handler.api, 'reply_message', side_effect=mock_error), \
         patch('time.sleep'):  # 跳過延遲
        result = handler.safe_reply_message("test_token", "測試訊息", max_retries=0)
        
        assert not result["success"]
        assert result["error_type"] == "quota_exceeded"
        assert handler.quota_exceeded == True
        assert "月度配額已用完" in result["message"]
        
        print("✅ 配額超限錯誤處理正常")


def test_rate_limit_error():
    """測試速率限制錯誤處理"""
    print("🧪 測試速率限制錯誤處理...")
    
    handler = LineBotApiHandler("test_token")
    
    # 模擬 429 速率限制錯誤
    error_obj = Error(message="Rate limit exceeded")
    mock_error = LineBotApiError(
        status_code=429,
        headers={},
        request_id="test-request-id",
        error=error_obj
    )
    
    with patch.object(handler.api, 'reply_message', side_effect=mock_error):
        result = handler.safe_reply_message("test_token", "測試訊息")
        
        assert not result["success"]
        assert result["error_type"] == "rate_limit"
        assert result["can_retry"] == True
        assert "速率限制" in result["message"]
        
        print("✅ 速率限制錯誤處理正常")


def test_client_error():
    """測試客戶端錯誤處理"""
    print("🧪 測試客戶端錯誤處理...")
    
    handler = LineBotApiHandler("test_token")
    
    # 模擬 400 客戶端錯誤
    error_obj = Error(message="Invalid request")
    mock_error = LineBotApiError(
        status_code=400,
        headers={},
        request_id="test-request-id",
        error=error_obj
    )
    
    with patch.object(handler.api, 'reply_message', side_effect=mock_error):
        result = handler.safe_reply_message("test_token", "測試訊息")
        
        assert not result["success"]
        assert result["error_type"] == "client_error"
        assert result["can_retry"] == False
        assert "客戶端錯誤" in result["message"]
        
        print("✅ 客戶端錯誤處理正常")


def test_server_error():
    """測試伺服器錯誤處理"""
    print("🧪 測試伺服器錯誤處理...")
    
    handler = LineBotApiHandler("test_token")
    
    # 模擬 500 伺服器錯誤
    error_obj = Error(message="Internal server error")
    mock_error = LineBotApiError(
        status_code=500,
        headers={},
        request_id="test-request-id",
        error=error_obj
    )
    
    with patch.object(handler.api, 'reply_message', side_effect=mock_error):
        result = handler.safe_reply_message("test_token", "測試訊息")
        
        assert not result["success"]
        assert result["error_type"] == "server_error"
        assert result["can_retry"] == True
        assert "伺服器錯誤" in result["message"]
        
        print("✅ 伺服器錯誤處理正常")


def test_successful_message():
    """測試正常訊息發送"""
    print("🧪 測試正常訊息發送...")
    
    handler = LineBotApiHandler("test_token")
    
    with patch.object(handler.api, 'reply_message', return_value=None):
        result = handler.safe_reply_message("test_token", "測試訊息")
        
        assert result["success"] == True
        assert result["message"] == "訊息發送成功"
        
        print("✅ 正常訊息發送處理正常")


def test_fallback_messages():
    """測試降級服務訊息生成"""
    print("🧪 測試降級服務訊息生成...")
    
    handler = LineBotApiHandler("test_token")
    
    # 測試配額超限訊息
    quota_msg = handler.create_fallback_message("測試名片識別", "quota_exceeded")
    assert "服務暫時受限" in quota_msg
    assert "下個月1號恢復" in quota_msg
    
    # 測試速率限制訊息
    rate_msg = handler.create_fallback_message("測試名片識別", "rate_limit")
    assert "服務暫時繁忙" in rate_msg
    assert "等待 1-2 分鐘" in rate_msg
    
    # 測試網路錯誤訊息
    network_msg = handler.create_fallback_message("測試名片識別", "network_error")
    assert "網路連接問題" in network_msg
    assert "稍後重新發送" in network_msg
    
    print("✅ 降級服務訊息生成正常")


def test_quota_status_tracking():
    """測試配額狀態追蹤"""
    print("🧪 測試配額狀態追蹤...")
    
    handler = LineBotApiHandler("test_token")
    
    # 初始狀態
    assert handler.quota_exceeded == False
    assert handler._check_quota_status() == True
    
    # 設置配額超限
    handler.quota_exceeded = True
    assert handler._check_quota_status() == False
    
    # 模擬重置時間過期
    handler.quota_reset_time = None
    handler.quota_exceeded = False
    assert handler._check_quota_status() == True
    
    print("✅ 配額狀態追蹤正常")


def test_error_statistics():
    """測試錯誤統計功能"""
    print("🧪 測試錯誤統計功能...")
    
    handler = LineBotApiHandler("test_token")
    
    # 初始統計
    stats = handler.get_status_report()
    assert stats["is_operational"] == True
    assert stats["quota_exceeded"] == False
    
    # 模擬錯誤累積
    handler._log_error("rate_limit_429", Exception("Test"), "test context")
    handler._log_error("quota_exceeded", Exception("Test"), "test context")
    
    assert handler.error_stats["rate_limit_429"] == 1
    assert handler.error_stats["quota_exceeded"] == 1
    
    print("✅ 錯誤統計功能正常")


def run_all_tests():
    """執行所有測試"""
    print("🚀 開始測試 LINE Bot API 錯誤處理機制\n")
    
    tests = [
        test_quota_exceeded_error,
        test_rate_limit_error,
        test_client_error,
        test_server_error,
        test_successful_message,
        test_fallback_messages,
        test_quota_status_tracking,
        test_error_statistics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ 測試失敗: {test.__name__} - {e}")
            failed += 1
        print()
    
    print(f"📊 測試結果: {passed} 通過, {failed} 失敗")
    
    if failed == 0:
        print("🎉 所有測試通過！API 錯誤處理機制正常工作")
    else:
        print("⚠️ 部分測試失敗，請檢查錯誤處理邏輯")
    
    return failed == 0


if __name__ == "__main__":
    run_all_tests()