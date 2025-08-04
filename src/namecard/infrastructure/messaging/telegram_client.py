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

        # 🚀 增強重試配置 - 採用指數退避策略
        self.max_retries = 5  # 增加到 5 次重試
        self.base_retry_delay = 1
        self.max_retry_delay = 60  # 最大重試延遲 60 秒
        self.exponential_backoff = True  # 啟用指數退避
        
        # 請求監控和速率限制
        self._request_count = 0
        self._last_request_time = 0
        self._rate_limit_window = 60  # 60秒窗口
        self._max_requests_per_minute = 60  # 每分鐘最多60個請求，支援批次處理
        
        # 🔧 並發控制優化 - 支援批次處理且避免連接池耗盡
        self._semaphore = None
        self._semaphore_lock = None
        
        # 🚀 新增：連接池健康監控
        self._connection_pool_stats = {
            "active_connections": 0,
            "pool_timeouts": 0,
            "connection_errors": 0,
            "last_cleanup": time.time()
        }
        
        # 🔧 新增：連接池清理間隔（每 5 分鐘清理一次）
        self._pool_cleanup_interval = 300
        
    def _setup_optimized_bot(self):
        """設置優化的 Bot 配置，包含連接池優化"""
        try:
            if not Config.TELEGRAM_BOT_TOKEN:
                # 🧪 測試模式：允許無 token 初始化（僅用於配置測試）
                if hasattr(self, '_test_mode') and self._test_mode:
                    self.logger.warning("⚠️ 測試模式：無 TELEGRAM_BOT_TOKEN，跳過 Bot 初始化")
                    self.bot = None
                    self._setup_http_client_only()
                    return
                else:
                    raise ValueError("TELEGRAM_BOT_TOKEN 未設置")
            
            # 🔧 配置優化的 HTTP 客戶端，解決連接池問題
            import httpx
            from telegram.ext import ExtBot
            
            # 🚀 創建優化的 HTTP 客戶端 - 修復連接池超時問題
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=60,  # 增加到 60 個保持連接
                    max_connections=150,           # 增加到 150 個總連接數
                    keepalive_expiry=60.0,        # 延長連接保持時間
                ),
                timeout=httpx.Timeout(
                    connect=20.0,    # 增加連接超時到 20 秒
                    read=60.0,       # 增加讀取超時到 60 秒 (AI 處理)
                    write=20.0,      # 增加寫入超時到 20 秒
                    pool=300.0       # 🔧 關鍵修復：連接池超時增加到 300 秒 (5分鐘)
                ),
                http2=False,  # 關閉 HTTP/2，避免兼容性問題
                # 🔧 新增：連接池配置優化
                transport=httpx.HTTPTransport(
                    retries=3,       # 傳輸層重試
                    verify=True      # SSL 驗證
                )
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
    
    def _setup_http_client_only(self):
        """🧪 僅設置 HTTP 客戶端（測試模式用）"""
        try:
            import httpx
            # 🚀 創建優化的 HTTP 客戶端 - 修復連接池超時問題
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=60,  # 增加到 60 個保持連接
                    max_connections=150,           # 增加到 150 個總連接數
                    keepalive_expiry=60.0,        # 延長連接保持時間
                ),
                timeout=httpx.Timeout(
                    connect=20.0,    # 增加連接超時到 20 秒
                    read=60.0,       # 增加讀取超時到 60 秒 (AI 處理)
                    write=20.0,      # 增加寫入超時到 20 秒
                    pool=300.0       # 🔧 關鍵修復：連接池超時增加到 300 秒 (5分鐘)
                ),
                http2=False,  # 關閉 HTTP/2，避免兼容性問題
                # 🔧 新增：連接池配置優化
                transport=httpx.HTTPTransport(
                    retries=3,       # 傳輸層重試
                    verify=True      # SSL 驗證
                )
            )
            self.logger.info("✅ 測試模式：HTTP 客戶端設置完成")
        except Exception as e:
            self.logger.error(f"HTTP 客戶端設置失敗: {e}")
            self._http_client = None

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
                # 🚀 優化併發控制 - 減少到 15 避免連接池耗盡
                self._semaphore = asyncio.Semaphore(15)  # 從 20 減少到 15
                
            return self._semaphore
            
        except RuntimeError:
            # 沒有運行中的事件循環，創建一個新的 Semaphore
            self.logger.debug("沒有運行中的事件循環，創建新的 Semaphore")
            # 🚀 優化併發控制 - 減少到 15 避免連接池耗盡
            self._semaphore = asyncio.Semaphore(15)  # 從 20 減少到 15
            return self._semaphore

    def _check_rate_limit(self):
        """檢查是否超過速率限制"""
        import time
        current_time = time.time()
        
        # 重置窗口
        if current_time - self._last_request_time > self._rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time
        
        # 檢查是否超過限制
        if self._request_count >= self._max_requests_per_minute:
            wait_time = self._rate_limit_window - (current_time - self._last_request_time)
            self.logger.warning(f"⚠️ 達到速率限制，需等待 {wait_time:.1f} 秒")
            return False, wait_time
        
        # 更新計數
        self._request_count += 1
        return True, 0

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
            # 🔧 網路錯誤處理優化 - 檢測連接池問題
            self._log_error("network_errors", error, context)
            
            # Telegram Bot API 錯誤 [network_errors]: Pool timeout: All connections in the connection pool are occupied.
            if "Pool timeout" in error_message or "connection pool" in error_message.lower():
                self._connection_pool_stats["pool_timeouts"] += 1
                self.logger.warning(f"🚨 連接池超時檢測到，總計: {self._connection_pool_stats['pool_timeouts']}")
                
                # 觸發連接池清理
                asyncio.create_task(self._cleanup_connection_pool())
                
                return {
                    "success": False,
                    "error_type": "connection_pool_timeout",
                    "message": f"連接池超時，正在清理並重試: {error_message}",
                    "can_retry": True,
                    "retry_after": 60,  # 給更多時間讓連接池恢復
                }
            
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

        # 🔧 檢查速率限制
        can_proceed, wait_time = self._check_rate_limit()
        if not can_proceed:
            return {
                "success": False,
                "error_type": "rate_limit",
                "message": f"達到速率限制，請等待 {wait_time:.1f} 秒後重試",
                "can_retry": True,
                "retry_after": wait_time
            }

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

                    # 🚀 智能等待策略 - 指數退避 + 抖動
                    wait_time = self._calculate_retry_delay(attempt, error_result.get("retry_after", 0))
                    self.logger.info(f"📡 重試 {attempt + 1}/{self.max_retries}，等待 {wait_time:.1f} 秒...")
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

                    # 🚀 智能等待策略 - 指數退避 + 抖動
                    wait_time = self._calculate_retry_delay(attempt, error_result.get("retry_after", 0))
                    self.logger.info(f"📡 重試 {attempt + 1}/{self.max_retries}，等待 {wait_time:.1f} 秒...")
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
        """🚀 獲取 API 狀態報告（包含連接池統計）"""
        total_errors = sum(self.error_stats.values())
        pool_timeout_ratio = (self._connection_pool_stats["pool_timeouts"] / 
                             max(1, total_errors)) if total_errors > 0 else 0

        return {
            "error_statistics": self.error_stats.copy(),
            "connection_pool_stats": self._connection_pool_stats.copy(),
            "total_errors": total_errors,
            "pool_timeout_ratio": round(pool_timeout_ratio, 3),
            "is_operational": total_errors < 50 and pool_timeout_ratio < 0.3,
            "status": (
                "healthy" if total_errors < 10 and pool_timeout_ratio < 0.1
                else "degraded" if total_errors < 50 and pool_timeout_ratio < 0.3
                else "unhealthy"
            ),
            "recommendations": self._get_health_recommendations(total_errors, pool_timeout_ratio)
        }
    
    def _get_health_recommendations(self, total_errors: int, pool_timeout_ratio: float) -> list:
        """🚀 根據狀態提供健康建議"""
        recommendations = []
        
        if pool_timeout_ratio > 0.3:
            recommendations.append("連接池超時比例過高，建議減少併發請求數量")
        
        if total_errors > 50:
            recommendations.append("錯誤總數過高，建議檢查網路狀況和 API 配額")
            
        if self._connection_pool_stats["pool_timeouts"] > 10:
            recommendations.append("建議定期清理連接池或增加連接池大小")
            
        if not recommendations:
            recommendations.append("系統運行正常")
            
        return recommendations

    async def _cleanup_connection_pool(self):
        """🚀 新增：清理連接池，解決連接耗盡問題"""
        try:
            current_time = time.time()
            
            # 檢查是否需要清理（避免頻繁清理）
            if current_time - self._connection_pool_stats["last_cleanup"] < 60:
                self.logger.debug("⏳ 連接池清理冷卻中，跳過本次清理")
                return
            
            self.logger.info("🔧 開始清理連接池...")
            
            # 記錄清理時間
            self._connection_pool_stats["last_cleanup"] = current_time
            
            # 如果有自定義 HTTP 客戶端，重新創建
            if hasattr(self, '_http_client') and self._http_client:
                try:
                    # 關閉當前客戶端
                    await self._http_client.aclose()
                    self.logger.debug("🗑️ 舊的 HTTP 客戶端已關閉")
                    
                    # 等待一小段時間讓連接完全關閉
                    await asyncio.sleep(2)
                    
                    # 重新設置優化的 Bot
                    self._setup_optimized_bot()
                    self.logger.info("✅ 連接池已重新創建")
                    
                except Exception as cleanup_error:
                    self.logger.error(f"❌ 連接池清理失敗: {cleanup_error}")
                    
        except Exception as e:
            self.logger.error(f"❌ 連接池清理過程發生錯誤: {e}")
    
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
        
    def _calculate_retry_delay(self, attempt: int, suggested_wait: float = 0) -> float:
        """🚀 計算智能重試延遲 - 指數退避 + 隨機抖動"""
        import random
        
        if suggested_wait > 0:
            # API 建議的等待時間優先
            return min(suggested_wait, self.max_retry_delay)
        
        if self.exponential_backoff:
            # 指數退避：1, 2, 4, 8, 16... 秒，加上隨機抖動避免雷群效應
            base_wait = self.base_retry_delay * (2 ** attempt)
            jitter = random.uniform(0.1, 0.5)  # 10%-50% 隨機抖動
            calculated_wait = base_wait * (1 + jitter)
            return min(calculated_wait, self.max_retry_delay)
        else:
            # 固定延遲
            return self.base_retry_delay
    
    async def _robust_telegram_request(self, request_func, context: str, max_retries: int = None):
        """🚀 健壯的 Telegram 請求包裝器 - 整合指數退避重試"""
        max_retries = max_retries or self.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                # 檢查連接池狀態
                if (hasattr(self, '_connection_pool_stats') and 
                    self._connection_pool_stats.get("pool_timeouts", 0) > 10):
                    # 如果連接池超時過多，先清理
                    self.logger.warning("🧹 連接池超時過多，執行清理...")
                    await self._cleanup_connection_pool()
                
                # 執行請求
                result = await request_func()
                
                # 成功則重置錯誤統計
                if hasattr(self, '_consecutive_errors'):
                    self._consecutive_errors = 0
                    
                return {"success": True, "result": result}
                
            except Exception as e:
                # 記錄連續錯誤
                if not hasattr(self, '_consecutive_errors'):
                    self._consecutive_errors = 0
                self._consecutive_errors += 1
                
                # 判斷是否為可重試的錯誤
                if hasattr(e, '__class__') and 'TelegramError' in str(type(e)):
                    error_result = self._handle_telegram_error(e, f"{context} attempt {attempt + 1}")
                    
                    # 檢查是否可以重試
                    if not error_result.get("can_retry", False) or attempt == max_retries:
                        return error_result
                    
                    # 智能等待策略
                    wait_time = self._calculate_retry_delay(attempt, error_result.get("retry_after", 0))
                    self.logger.info(f"🔄 {context} 重試 {attempt + 1}/{max_retries}，等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)
                    
                else:
                    # 非 Telegram 錯誤
                    if attempt == max_retries:
                        return {
                            "success": False,
                            "error_type": "unexpected_error", 
                            "message": f"{context} 發生意外錯誤: {str(e)}"
                        }
                    
                    # 簡單的重試延遲
                    wait_time = self._calculate_retry_delay(attempt)
                    self.logger.warning(f"⚠️ {context} 意外錯誤，重試 {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(wait_time)
        
        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "message": f"{context} 重試 {max_retries} 次後仍然失敗"
        }

    async def __aenter__(self):
        """異步上下文管理器進入"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.close()