"""
簡化的 LINE Bot API 錯誤處理測試
直接測試錯誤處理邏輯，避免重試機制延遲
"""

from line_bot_handler import LineBotApiHandler
from linebot.exceptions import LineBotApiError
from linebot.models import Error


def test_error_handling_logic():
    """測試錯誤處理邏輯"""
    print("🧪 測試錯誤處理邏輯...")

    handler = LineBotApiHandler("test_token")

    # 測試配額超限錯誤
    error_obj = Error(message="You have reached your monthly limit.")
    mock_error = LineBotApiError(
        status_code=429, headers={}, request_id="test-request-id", error=error_obj
    )

    result = handler._handle_api_error(mock_error, "test context")
    assert result["error_type"] == "quota_exceeded"
    assert "月度配額已用完" in result["message"]
    assert handler.quota_exceeded == True
    print("✅ 配額超限錯誤處理正常")

    # 重置狀態
    handler.quota_exceeded = False

    # 測試速率限制錯誤
    error_obj2 = Error(message="Rate limit exceeded")
    mock_error2 = LineBotApiError(
        status_code=429, headers={}, request_id="test-request-id", error=error_obj2
    )

    result2 = handler._handle_api_error(mock_error2, "test context")
    assert result2["error_type"] == "rate_limit"
    assert result2["can_retry"] == True
    print("✅ 速率限制錯誤處理正常")

    # 測試客戶端錯誤
    error_obj3 = Error(message="Invalid request")
    mock_error3 = LineBotApiError(
        status_code=400, headers={}, request_id="test-request-id", error=error_obj3
    )

    result3 = handler._handle_api_error(mock_error3, "test context")
    assert result3["error_type"] == "client_error"
    assert result3["can_retry"] == False
    print("✅ 客戶端錯誤處理正常")

    # 測試伺服器錯誤
    error_obj4 = Error(message="Internal server error")
    mock_error4 = LineBotApiError(
        status_code=500, headers={}, request_id="test-request-id", error=error_obj4
    )

    result4 = handler._handle_api_error(mock_error4, "test context")
    assert result4["error_type"] == "server_error"
    assert result4["can_retry"] == True
    print("✅ 伺服器錯誤處理正常")


def test_fallback_messages():
    """測試降級服務訊息"""
    print("🧪 測試降級服務訊息...")

    handler = LineBotApiHandler("test_token")

    # 測試各種降級訊息
    quota_msg = handler.create_fallback_message("測試名片識別", "quota_exceeded")
    assert "服務暫時受限" in quota_msg
    print("✅ 配額超限降級訊息正常")

    rate_msg = handler.create_fallback_message("測試名片識別", "rate_limit")
    assert "服務暫時繁忙" in rate_msg
    print("✅ 速率限制降級訊息正常")

    network_msg = handler.create_fallback_message("測試名片識別", "network_error")
    assert "網路連接問題" in network_msg
    print("✅ 網路錯誤降級訊息正常")


def test_quota_tracking():
    """測試配額狀態追蹤"""
    print("🧪 測試配額狀態追蹤...")

    handler = LineBotApiHandler("test_token")

    # 初始狀態
    assert handler.quota_exceeded == False
    assert handler._check_quota_status() == True
    print("✅ 初始狀態正常")

    # 配額超限狀態
    handler.quota_exceeded = True
    assert handler._check_quota_status() == False
    print("✅ 配額超限狀態正常")

    # 狀態報告
    status = handler.get_status_report()
    assert status["quota_exceeded"] == True
    assert status["is_operational"] == False
    print("✅ 狀態報告正常")


def run_tests():
    """執行所有測試"""
    print("🚀 開始測試 LINE Bot API 錯誤處理機制\n")

    try:
        test_error_handling_logic()
        print()
        test_fallback_messages()
        print()
        test_quota_tracking()
        print()
        print("🎉 所有測試通過！API 錯誤處理機制正常工作")
        return True
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


if __name__ == "__main__":
    run_tests()
