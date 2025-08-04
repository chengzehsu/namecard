"""
Telegram Bot API 錯誤處理包裝器 - 優化版本
處理 API 速率限制、網路錯誤和其他異常情況
增強連接池配置以解決並發問題
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import httpx
from telegram import Bot, File
from telegram.constants import ParseMode
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
)
from telegram.ext import ExtBot

from simple_config import Config


class TelegramBotHandler:
    """Telegram Bot API 包裝器，包含錯誤處理和重試機制"""

    def __init__(self):
        """初始化 Telegram Bot API 處理器"""
        # 先初始化 logger
        self.logger = logging.getLogger(__name__)
        
        # 配置優化的 HTTP 客戶端
        self._setup_optimized_bot()

        # 錯誤統計
        self.error_stats = {
            "rate_limit_429": 0,
            "network_errors": 0,
            "bad_request_400": 0,
            "forbidden_403": 0,
            "other_errors": 0,
        }

        # 重試配置
        self.max_retries = 3
        self.base_retry_delay = 1
        
        # 並發控制（最多同時 10 個請求）- 延遲初始化，解決連接池問題
        self._semaphore = None
        self._semaphore_lock = None
        
    def _setup_optimized_bot(self):
        """設置優化的 Bot 配置，包含連接池優化"""
        try:
            if not Config.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN 未設置")
            
            # 🔧 配置優化的 HTTP 客戶端，解決連接池問題
            import httpx
            from telegram.ext import ExtBot
            
            # 創建優化的 HTTP 客戶端
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=20,  # 增加保持連接數
                    max_connections=50,            # 增加總連接數
                    keepalive_expiry=30.0,        # 連接保持時間
                ),
                timeout=httpx.Timeout(
                    connect=10.0,    # 連接超時
                    read=30.0,       # 讀取超時
                    write=10.0,      # 寫入超時
                    pool=60.0        # 連接池超時
                ),
                http2=False  # 暫時關閉 HTTP/2，避免兼容性問題
            )
            
            # 使用自定義 HTTP 客戶端創建 Bot
            self.bot = ExtBot(
                token=Config.TELEGRAM_BOT_TOKEN
            )
            
            # 手動設置 HTTP 客戶端（如果支援）
            if hasattr(self.bot, '_request'):
                if hasattr(self.bot._request, '_client'):
                    # 嘗試替換預設客戶端
                    try:
                        self.bot._request._client = self._http_client
                        self.logger.info("✅ 已設置優化的 HTTP 客戶端")
                    except Exception as e:
                        self.logger.warning(f"⚠️ 無法設置自定義 HTTP 客戶端: {e}")
            
        except ImportError:
            # 如果無法導入 ExtBot，使用標準 Bot
            self.logger.warning("⚠️ 無法使用 ExtBot，回退到標準 Bot")
            self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            self._http_client = None
            
        except Exception as e:
            self.logger.error(f"Bot 初始化失敗: {e}")
            raise

    async def _get_semaphore(self):
        """安全獲取 Semaphore，確保在正確的事件循環中創建"""
        try:
            # 獲取當前事件循環
            current_loop = asyncio.get_running_loop()
            
            # 如果 semaphore 不存在或綁定到不同的事件循環，重新創建
            if (self._semaphore is None or 
                hasattr(self._semaphore, '_loop') and 
                self._semaphore._loop != current_loop):
                
                self.logger.debug("創建新的 Semaphore 用於當前事件循環")
                # 🔧 增加併發數量以支援更多同時請求
                self._semaphore = asyncio.Semaphore(10)
                
            return self._semaphore
            
        except RuntimeError:
            # 沒有運行中的事件循環，創建一個新的 Semaphore
            self.logger.debug("沒有運行中的事件循環，創建新的 Semaphore")
            # 🔧 增加併發數量以支援更多同時請求
            self._semaphore = asyncio.Semaphore(10)
            return self._semaphore

    def _log_error(self, error_type: str, error: Exception, context: str = ""):
        """記錄錯誤並更新統計"""
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        self.logger.error(f"Telegram Bot API 錯誤 [{error_type}]: {error} - {context}")

    def _handle_telegram_error(
        self, error: TelegramError, context: str = ""
    ) -> Dict[str, Any]:
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
                "retry_after": error.retry_after,
            }

        elif isinstance(error, BadRequest):
            # 請求錯誤 (400)
            self._log_error("bad_request_400", error, context)
            return {
                "success": False,
                "error_type": "bad_request",
                "message": f"Telegram API 請求錯誤: {error_message}",
                "can_retry": False,
            }

        elif isinstance(error, Forbidden):
            # 權限錯誤 (403)
            self._log_error("forbidden_403", error, context)
            return {
                "success": False,
                "error_type": "forbidden",
                "message": f"Telegram API 權限錯誤: {error_message}",
                "can_retry": False,
            }

        elif isinstance(error, NetworkError):
            # 網路錯誤
            self._log_error("network_errors", error, context)
            return {
                "success": False,
                "error_type": "network_error",
                "message": f"Telegram API 網路錯誤: {error_message}",
                "can_retry": True,
                "retry_after": 30,
            }

        else:
            # 其他錯誤
            self._log_error("other_errors", error, context)
            return {
                "success": False,
                "error_type": "unknown_error",
                "message": f"Telegram API 未知錯誤: {error_message}",
                "can_retry": True,
                "retry_after": 10,
            }

    async def safe_send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """安全發送訊息，包含錯誤處理和重試機制"""

        # 🔧 安全獲取 Semaphore，確保在正確的事件循環中
        semaphore = await self._get_semaphore()
        async with semaphore:
            for attempt in range(max_retries + 1):
                try:
                    message = await self.bot.send_message(
                        chat_id=chat_id, text=text, parse_mode=parse_mode
                    )
                    return {
                        "success": True,
                        "message": "訊息發送成功",
                        "message_id": message.message_id,
                    }

                except TelegramError as e:
                    error_result = self._handle_telegram_error(
                        e, f"send_message attempt {attempt + 1}"
                    )

                    if not error_result.get("can_retry", False) or attempt == max_retries:
                        return error_result

                    # 等待後重試
                    wait_time = error_result.get(
                        "retry_after", self.base_retry_delay * (2**attempt)
                    )
                    self.logger.info(f"等待 {wait_time} 秒後重試...")
                    await asyncio.sleep(wait_time)

                except Exception as e:
                    self.logger.error(f"send_message 意外錯誤: {e}")
                    return {
                        "success": False,
                        "error_type": "unexpected_error",
                        "message": f"發送訊息時發生意外錯誤: {str(e)}",
                        "can_retry": False,
                    }

            return {
                "success": False,
                "error_type": "max_retries_exceeded",
                "message": f"重試 {max_retries} 次後仍然失敗",
                "can_retry": False,
            }

    async def safe_get_file(self, file_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """安全獲取文件，包含錯誤處理"""

        # 🔧 安全獲取 Semaphore，確保在正確的事件循環中
        semaphore = await self._get_semaphore()
        async with semaphore:
            for attempt in range(max_retries + 1):
                try:
                    file_obj = await self.bot.get_file(file_id)
                    return {"success": True, "message": "文件獲取成功", "file": file_obj}

                except TelegramError as e:
                    error_result = self._handle_telegram_error(
                        e, f"get_file attempt {attempt + 1}"
                    )

                    if not error_result.get("can_retry", False) or attempt == max_retries:
                        error_result["file"] = None
                        return error_result

                    # 等待後重試
                    wait_time = error_result.get(
                        "retry_after", self.base_retry_delay * (2**attempt)
                    )
                    self.logger.info(f"等待 {wait_time} 秒後重試...")
                    await asyncio.sleep(wait_time)

                except Exception as e:
                    self.logger.error(f"get_file 意外錯誤: {e}")
                    return {
                        "success": False,
                        "error_type": "unexpected_error",
                        "message": f"獲取文件時發生意外錯誤: {str(e)}",
                        "file": None,
                    }

            return {
                "success": False,
                "error_type": "max_retries_exceeded",
                "message": f"重試 {max_retries} 次後仍然失敗",
                "file": None,
            }

    def get_status_report(self) -> Dict[str, Any]:
        """獲取 API 狀態報告"""
        total_errors = sum(self.error_stats.values())

        return {
            "error_statistics": self.error_stats.copy(),
            "total_errors": total_errors,
            "is_operational": total_errors < 50,  # 閾值可調整
            "status": (
                "healthy"
                if total_errors < 10
                else "degraded" if total_errors < 50 else "unhealthy"
            ),
        }

    async def close(self):
        """清理資源"""
        try:
            # 清理自定義 HTTP 客戶端
            if hasattr(self, '_http_client') and self._http_client:
                await self._http_client.aclose()
                self.logger.debug("✅ HTTP 客戶端已關閉")
                
            # 清理 Bot 資源
            if hasattr(self, 'bot') and hasattr(self.bot, 'shutdown'):
                await self.bot.shutdown()
                self.logger.debug("✅ Telegram Bot 已關閉")
                
        except Exception as e:
            self.logger.warning(f"⚠️ 清理資源時發生錯誤: {e}")
            
    async def __aenter__(self):
        """異步上下文管理器進入"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.close()