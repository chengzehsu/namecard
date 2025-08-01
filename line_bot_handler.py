"""
LINE Bot API 錯誤處理包裝器
處理 API 速率限制、配額超限和其他網路錯誤
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage


class LineBotApiHandler:
    """LINE Bot API 包裝器，包含錯誤處理和降級機制"""

    def __init__(self, access_token: str):
        self.api = LineBotApi(access_token)
        self.logger = logging.getLogger(__name__)
        
        # 配額限制追蹤
        self.quota_exceeded = False
        self.quota_reset_time = None
        self.retry_count = 0
        self.max_retries = 3
        
        # 錯誤統計
        self.error_stats = {
            "rate_limit_429": 0,
            "quota_exceeded": 0,
            "network_errors": 0,
            "other_errors": 0
        }

    def _log_error(self, error_type: str, error: Exception, context: str = ""):
        """記錄錯誤並更新統計"""
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        self.logger.error(f"LINE Bot API 錯誤 [{error_type}]: {error} - {context}")

    def _handle_api_error(self, error: LineBotApiError, context: str = "") -> Dict[str, Any]:
        """處理 LINE Bot API 錯誤"""
        error_message = getattr(error, 'message', str(error))
        if hasattr(error, 'error') and error.error:
            error_message = error.error.message
            
        if error.status_code == 429:
            # 速率限制或配額超限
            if "monthly limit" in error_message:
                self._log_error("quota_exceeded", error, context)
                self.quota_exceeded = True
                # 設置重置時間為下個月1號
                now = datetime.now()
                next_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    next_month = next_month.replace(year=now.year + 1, month=1)
                else:
                    next_month = next_month.replace(month=now.month + 1)
                self.quota_reset_time = next_month
                
                return {
                    "success": False,
                    "error_type": "quota_exceeded",
                    "message": "LINE Bot API 月度配額已用完",
                    "reset_time": self.quota_reset_time.isoformat(),
                    "can_retry": False
                }
            else:
                self._log_error("rate_limit_429", error, context)
                return {
                    "success": False,
                    "error_type": "rate_limit",
                    "message": "LINE Bot API 速率限制",
                    "can_retry": True,
                    "retry_after": 60  # 建議等待60秒
                }
        
        elif error.status_code in [400, 401, 403]:
            self._log_error("other_errors", error, context)
            return {
                "success": False,
                "error_type": "client_error",
                "message": f"LINE Bot API 客戶端錯誤: {error_message}",
                "can_retry": False
            }
        
        elif error.status_code >= 500:
            self._log_error("network_errors", error, context)
            return {
                "success": False,
                "error_type": "server_error", 
                "message": f"LINE Bot API 伺服器錯誤: {error_message}",
                "can_retry": True,
                "retry_after": 30
            }
        
        else:
            self._log_error("other_errors", error, context)
            return {
                "success": False,
                "error_type": "unknown_error",
                "message": f"LINE Bot API 未知錯誤: {error_message}",
                "can_retry": False
            }

    def _check_quota_status(self) -> bool:
        """檢查配額狀態"""
        if not self.quota_exceeded:
            return True
            
        if self.quota_reset_time and datetime.now() >= self.quota_reset_time:
            self.quota_exceeded = False
            self.quota_reset_time = None
            self.logger.info("LINE Bot API 配額已重置")
            return True
            
        return False

    def safe_reply_message(self, reply_token: str, message: str, max_retries: int = 2) -> Dict[str, Any]:
        """安全發送回覆訊息，包含錯誤處理"""
        if not self._check_quota_status():
            return {
                "success": False,
                "error_type": "quota_exceeded",
                "message": "LINE Bot API 配額已用完，請等待下個月重置",
                "fallback_used": True
            }

        for attempt in range(max_retries + 1):
            try:
                self.api.reply_message(reply_token, TextSendMessage(text=message))
                return {"success": True, "message": "訊息發送成功"}
                
            except LineBotApiError as e:
                error_result = self._handle_api_error(e, f"reply_message attempt {attempt + 1}")
                
                if not error_result["can_retry"] or attempt == max_retries:
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", 30)
                self.logger.info(f"等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"reply_message 意外錯誤: {e}")
                return {
                    "success": False,
                    "error_type": "unexpected_error",
                    "message": f"發送訊息時發生意外錯誤: {str(e)}",
                    "can_retry": False
                }

        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"重試 {max_retries} 次後仍然失敗",
            "can_retry": False
        }

    def safe_push_message(self, user_id: str, message: str, max_retries: int = 2) -> Dict[str, Any]:
        """安全發送推播訊息，包含錯誤處理"""
        if not self._check_quota_status():
            return {
                "success": False,
                "error_type": "quota_exceeded", 
                "message": "LINE Bot API 配額已用完，請等待下個月重置",
                "fallback_used": True
            }

        for attempt in range(max_retries + 1):
            try:
                self.api.push_message(user_id, TextSendMessage(text=message))
                return {"success": True, "message": "訊息發送成功"}
                
            except LineBotApiError as e:
                error_result = self._handle_api_error(e, f"push_message attempt {attempt + 1}")
                
                if not error_result["can_retry"] or attempt == max_retries:
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", 30)
                self.logger.info(f"等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"push_message 意外錯誤: {e}")
                return {
                    "success": False,
                    "error_type": "unexpected_error",
                    "message": f"發送訊息時發生意外錯誤: {str(e)}",
                    "can_retry": False
                }

        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"重試 {max_retries} 次後仍然失敗",
            "can_retry": False
        }

    def safe_get_message_content(self, message_id: str) -> Dict[str, Any]:
        """安全獲取訊息內容"""
        if not self._check_quota_status():
            return {
                "success": False,
                "error_type": "quota_exceeded",
                "message": "LINE Bot API 配額已用完，無法下載圖片",
                "content": None
            }

        try:
            content = self.api.get_message_content(message_id)
            return {
                "success": True,
                "message": "內容獲取成功",
                "content": content
            }
            
        except LineBotApiError as e:
            error_result = self._handle_api_error(e, "get_message_content")
            error_result["content"] = None
            return error_result
            
        except Exception as e:
            self.logger.error(f"get_message_content 意外錯誤: {e}")
            return {
                "success": False,
                "error_type": "unexpected_error",
                "message": f"獲取訊息內容時發生意外錯誤: {str(e)}",
                "content": None
            }

    def get_status_report(self) -> Dict[str, Any]:
        """獲取 API 狀態報告"""
        return {
            "quota_exceeded": self.quota_exceeded,
            "quota_reset_time": self.quota_reset_time.isoformat() if self.quota_reset_time else None,
            "error_statistics": self.error_stats.copy(),
            "is_operational": not self.quota_exceeded
        }

    def create_fallback_message(self, original_message: str, error_type: str) -> str:
        """創建降級服務訊息"""
        fallback_messages = {
            "quota_exceeded": f"""🚨 **服務暫時受限**

由於 LINE Bot API 月度配額已用完，目前無法處理您的名片識別請求。

📝 **您的訊息已記錄**:
{original_message[:100]}{'...' if len(original_message) > 100 else ''}

🔄 **服務將於下個月1號恢復正常**

🙏 造成不便，敬請見諒！""",

            "rate_limit": f"""⏳ **服務暫時繁忙**

目前 LINE Bot 訊息處理量較大，請稍後再試。

💡 **建議**:
- 等待 1-2 分鐘後重新發送
- 或使用批次模式一次處理多張名片

🔄 服務將很快恢復正常""",

            "network_error": f"""🔧 **網路連接問題**

LINE Bot 服務暫時不穩定，正在嘗試重新連接。

💡 **您可以**:
- 稍後重新發送訊息
- 或聯繫系統管理員

📞 如問題持續，請回報此錯誤"""
        }

        return fallback_messages.get(error_type, f"""❌ **服務暫時無法使用**

系統遇到未預期的問題：{error_type}

🔄 請稍後再試，或聯繫系統管理員
📞 錯誤代碼: {error_type}""")