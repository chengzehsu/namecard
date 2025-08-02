"""
Telegram Bot API 錯誤處理包裝器
處理 API 速率限制、網路錯誤和其他異常情況
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from telegram import Bot, File
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError
from config import Config


class TelegramBotHandler:
    """Telegram Bot API 包裝器，包含錯誤處理和重試機制"""

    def __init__(self):
        """初始化 Telegram Bot API 處理器"""
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.logger = logging.getLogger(__name__)
        
        # 錯誤統計
        self.error_stats = {
            "rate_limit_429": 0,
            "network_errors": 0,
            "bad_request_400": 0,
            "forbidden_403": 0,
            "other_errors": 0
        }
        
        # 重試配置
        self.max_retries = 3
        self.base_retry_delay = 1

    def _log_error(self, error_type: str, error: Exception, context: str = ""):
        """記錄錯誤並更新統計"""
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        self.logger.error(f"Telegram Bot API 錯誤 [{error_type}]: {error} - {context}")

    def _handle_telegram_error(self, error: TelegramError, context: str = "") -> Dict[str, Any]:
        """處理 Telegram Bot API 錯誤"""
        error_message = str(error)
        
        if isinstance(error, RetryAfter):
            # 速率限制錯誤
            self._log_error("rate_limit_429", error, context)
            return {
                "success": False,
                "error_type": "rate_limit",
                "message": f"Telegram API 速率限制，需等待 {error.retry_after} 秒",
                "can_retry": True,
                "retry_after": error.retry_after
            }
        
        elif isinstance(error, BadRequest):
            # 請求錯誤 (400)
            self._log_error("bad_request_400", error, context)
            return {
                "success": False,
                "error_type": "bad_request",
                "message": f"Telegram API 請求錯誤: {error_message}",
                "can_retry": False
            }
        
        elif isinstance(error, Forbidden):
            # 權限錯誤 (403)
            self._log_error("forbidden_403", error, context)
            return {
                "success": False,
                "error_type": "forbidden",
                "message": f"Telegram API 權限錯誤: {error_message}",
                "can_retry": False
            }
        
        elif isinstance(error, NetworkError):
            # 網路錯誤
            self._log_error("network_errors", error, context) 
            return {
                "success": False,
                "error_type": "network_error",
                "message": f"Telegram API 網路錯誤: {error_message}",
                "can_retry": True,
                "retry_after": 30
            }
        
        else:
            # 其他錯誤
            self._log_error("other_errors", error, context)
            return {
                "success": False,
                "error_type": "unknown_error",
                "message": f"Telegram API 未知錯誤: {error_message}",
                "can_retry": True,
                "retry_after": 10
            }

    async def safe_send_message(
        self, 
        chat_id: Union[int, str], 
        text: str, 
        parse_mode: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """安全發送訊息，包含錯誤處理和重試機制"""
        
        for attempt in range(max_retries + 1):
            try:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
                return {
                    "success": True,
                    "message": "訊息發送成功",
                    "message_id": message.message_id
                }
                
            except TelegramError as e:
                error_result = self._handle_telegram_error(e, f"send_message attempt {attempt + 1}")
                
                if not error_result.get("can_retry", False) or attempt == max_retries:
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", self.base_retry_delay * (2 ** attempt))
                self.logger.info(f"等待 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"send_message 意外錯誤: {e}")
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

    async def safe_get_file(self, file_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """安全獲取文件，包含錯誤處理"""
        
        for attempt in range(max_retries + 1):
            try:
                file_obj = await self.bot.get_file(file_id)
                return {
                    "success": True,
                    "message": "文件獲取成功",
                    "file": file_obj
                }
                
            except TelegramError as e:
                error_result = self._handle_telegram_error(e, f"get_file attempt {attempt + 1}")
                
                if not error_result.get("can_retry", False) or attempt == max_retries:
                    error_result["file"] = None
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", self.base_retry_delay * (2 ** attempt))
                self.logger.info(f"等待 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"get_file 意外錯誤: {e}")
                return {
                    "success": False,
                    "error_type": "unexpected_error",
                    "message": f"獲取文件時發生意外錯誤: {str(e)}",
                    "file": None
                }

        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"重試 {max_retries} 次後仍然失敗",
            "file": None
        }

    async def safe_edit_message(
        self, 
        chat_id: Union[int, str], 
        message_id: int, 
        text: str,
        parse_mode: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """安全編輯訊息"""
        
        for attempt in range(max_retries + 1):
            try:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode=parse_mode
                )
                return {"success": True, "message": "訊息編輯成功"}
                
            except TelegramError as e:
                error_result = self._handle_telegram_error(e, f"edit_message attempt {attempt + 1}")
                
                if not error_result.get("can_retry", False) or attempt == max_retries:
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", self.base_retry_delay * (2 ** attempt))
                self.logger.info(f"等待 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"edit_message 意外錯誤: {e}")
                return {
                    "success": False,
                    "error_type": "unexpected_error",
                    "message": f"編輯訊息時發生意外錯誤: {str(e)}",
                    "can_retry": False
                }

        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"重試 {max_retries} 次後仍然失敗",
            "can_retry": False
        }

    async def safe_delete_message(
        self, 
        chat_id: Union[int, str], 
        message_id: int,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """安全刪除訊息"""
        
        for attempt in range(max_retries + 1):
            try:
                await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return {"success": True, "message": "訊息刪除成功"}
                
            except TelegramError as e:
                error_result = self._handle_telegram_error(e, f"delete_message attempt {attempt + 1}")
                
                if not error_result.get("can_retry", False) or attempt == max_retries:
                    return error_result
                
                # 等待後重試
                wait_time = error_result.get("retry_after", self.base_retry_delay * (2 ** attempt))
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"delete_message 意外錯誤: {e}")
                return {
                    "success": False,
                    "error_type": "unexpected_error",
                    "message": f"刪除訊息時發生意外錯誤: {str(e)}",
                    "can_retry": False
                }

        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"重試 {max_retries} 次後仍然失敗",
            "can_retry": False
        }

    def get_status_report(self) -> Dict[str, Any]:
        """獲取 API 狀態報告"""
        total_errors = sum(self.error_stats.values())
        
        return {
            "error_statistics": self.error_stats.copy(),
            "total_errors": total_errors,
            "is_operational": total_errors < 50,  # 閾值可調整
            "status": "healthy" if total_errors < 10 else "degraded" if total_errors < 50 else "unhealthy"
        }

    def create_fallback_message(self, original_message: str, error_type: str) -> str:
        """創建降級服務訊息"""
        fallback_messages = {
            "rate_limit": f"""⏳ **服務暫時繁忙**

目前 Telegram Bot 訊息處理量較大，請稍後再試。

💡 **建議**：
• 等待 1-2 分鐘後重新發送
• 或使用 /batch 批次模式處理多張名片

🔄 服務將很快恢復正常""",

            "network_error": f"""🔧 **網路連接問題**

Telegram Bot 服務暫時不穩定，正在嘗試重新連接。

💡 **您可以**：
• 稍後重新發送訊息
• 或聯繫系統管理員

📞 如問題持續，請回報此錯誤""",

            "forbidden": f"""🚫 **權限問題**

Telegram Bot 遇到權限問題，可能是：
• Bot 被封鎖
• 群組權限不足
• API Token 無效

📞 請聯繫系統管理員解決""",

            "bad_request": f"""❌ **請求格式錯誤**

您的請求格式可能有問題：
• 訊息過長 (>4096 字符)
• 包含不支援的格式
• 無效的指令

💡 請檢查輸入格式或聯繫管理員"""
        }

        return fallback_messages.get(error_type, f"""❌ **服務暫時無法使用**

系統遇到未預期的問題：{error_type}

🔄 請稍後再試，或聯繫系統管理員
📞 錯誤代碼: {error_type}""")