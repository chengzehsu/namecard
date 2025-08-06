#!/usr/bin/env python3
"""
連接池管理器 - ConnectionPoolManager
專門解決並行下載器的連接池問題

核心修復：
1. 連接池洩漏問題
2. 超時和重試機制
3. 連接復用優化
4. 資源清理自動化
5. 並發控制優化
"""

import asyncio
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import aiohttp


@dataclass
class ConnectionPoolConfig:
    """連接池配置"""

    # 基本連接限制
    total_limit: int = 25
    per_host_limit: int = 8

    # 超時設置
    total_timeout: int = 20
    connect_timeout: int = 5
    read_timeout: int = 15

    # Keep-alive 設置
    keepalive_timeout: int = 30
    keepalive_expiry: int = 30

    # 清理和維護
    enable_cleanup_closed: bool = True
    cleanup_interval: int = 60

    # 重試設置
    max_retries: int = 3
    retry_backoff: float = 1.0

    # DNS 優化
    use_dns_cache: bool = True
    dns_cache_ttl: int = 300


@dataclass
class ConnectionStats:
    """連接統計"""

    active_connections: int = 0
    idle_connections: int = 0
    total_created: int = 0
    total_closed: int = 0
    total_failed: int = 0
    total_timeouts: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class ConnectionPoolManager:
    """連接池管理器 - 解決連接池相關問題"""

    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        self.config = config or ConnectionPoolConfig()
        self.logger = logging.getLogger(__name__)

        # 連接池實例管理
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._session_refs = weakref.WeakSet()

        # 統計和監控
        self.stats = ConnectionStats()
        self._last_cleanup = time.time()

        # 信號量控制並發
        self._semaphore = asyncio.Semaphore(self.config.total_limit)

        # 啟動清理任務
        self._cleanup_task = None
        self._shutdown = False

        self.logger.info("🔧 ConnectionPoolManager 初始化完成")
        self.logger.info(f"   - 總連接限制: {self.config.total_limit}")
        self.logger.info(f"   - 每主機限制: {self.config.per_host_limit}")
        self.logger.info(f"   - 總超時: {self.config.total_timeout}s")

    async def get_session(self, session_key: str = "default") -> aiohttp.ClientSession:
        """獲取優化的 HTTP 會話（單例模式）"""
        if session_key not in self._sessions:
            if session_key not in self._session_locks:
                self._session_locks[session_key] = asyncio.Lock()

            async with self._session_locks[session_key]:
                if session_key not in self._sessions:
                    session = await self._create_optimized_session()
                    self._sessions[session_key] = session
                    self._session_refs.add(session)

                    self.stats.total_created += 1
                    self.logger.debug(f"✅ 新建 HTTP Session: {session_key}")

        return self._sessions[session_key]

    async def _create_optimized_session(self) -> aiohttp.ClientSession:
        """創建優化的 HTTP 會話"""
        # 連接器配置 - 修復連接池問題
        connector_config = {
            "limit": self.config.total_limit,
            "limit_per_host": self.config.per_host_limit,
            "keepalive_timeout": self.config.keepalive_timeout,
            "enable_cleanup_closed": self.config.enable_cleanup_closed,
            # 🔧 關鍵修復：啟用連接復用和優化
            "use_dns_cache": self.config.use_dns_cache,
            "ttl_dns_cache": self.config.dns_cache_ttl,
            "ssl": None,  # 讓 aiohttp 自動決定
            # 🔧 修復：連接池維護設置
            "force_close": False,  # 避免強制關閉連接
        }

        connector = aiohttp.TCPConnector(**connector_config)

        # 超時配置 - 修復超時問題
        timeout = aiohttp.ClientTimeout(
            total=self.config.total_timeout,
            connect=self.config.connect_timeout,
            sock_read=self.config.read_timeout,
        )

        # 請求頭優化
        headers = {
            "User-Agent": "NameCard-Bot/2.0 (Connection-Pool-Optimized)",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Keep-Alive": f"timeout={self.config.keepalive_timeout}",
        }

        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            auto_decompress=True,
            raise_for_status=False,  # 手動處理錯誤
        )

        return session

    @asynccontextmanager
    async def request_context(
        self, url: str, method: str = "GET", session_key: str = "default", **kwargs
    ):
        """請求上下文管理器 - 確保資源正確釋放"""
        session = await self.get_session(session_key)

        async with self._semaphore:  # 控制並發
            start_time = time.time()

            try:
                async with session.request(method, url, **kwargs) as response:
                    self.stats.active_connections += 1
                    yield response

            except asyncio.TimeoutError:
                self.stats.total_timeouts += 1
                self.logger.warning(f"⏰ 請求超時: {url}")
                raise

            except aiohttp.ClientError as e:
                self.stats.total_failed += 1
                self.logger.warning(f"❌ 請求失敗: {url} - {e}")
                raise

            finally:
                self.stats.active_connections = max(
                    0, self.stats.active_connections - 1
                )
                duration = time.time() - start_time
                if duration > 5.0:  # 警告慢請求
                    self.logger.warning(f"🐌 慢請求: {url} ({duration:.2f}s)")

    async def download_with_retry(
        self, url: str, max_retries: Optional[int] = None, session_key: str = "default"
    ) -> Dict[str, Any]:
        """帶重試機制的下載 - 修復不穩定連接問題"""
        max_retries = max_retries or self.config.max_retries
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                async with self.request_context(
                    url, session_key=session_key
                ) as response:
                    if response.status == 200:
                        data = await response.read()
                        return {
                            "success": True,
                            "data": data,
                            "size": len(data),
                            "attempt": attempt + 1,
                            "url": url,
                        }
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                        )

            except Exception as e:
                last_error = e

                if attempt < max_retries:
                    # 指數退避重試
                    delay = self.config.retry_backoff * (2**attempt)
                    self.logger.debug(
                        f"🔄 重試 {attempt + 1}/{max_retries}: {url} "
                        f"(延遲 {delay:.1f}s)"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"❌ 所有重試失敗: {url} - {last_error}")

        return {
            "success": False,
            "error": str(last_error),
            "attempt": max_retries + 1,
            "url": url,
        }

    async def batch_download(
        self, urls: List[str], max_concurrent: int = 8, session_key: str = "batch"
    ) -> List[Dict[str, Any]]:
        """批次下載 - 優化並發控制"""
        if not urls:
            return []

        self.logger.info(
            f"🚀 開始批次下載 {len(urls)} 個 URL (並發度: {max_concurrent})"
        )

        # 創建信號量控制並發
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.download_with_retry(url, session_key=session_key)

        # 並行執行所有下載
        start_time = time.time()
        results = await asyncio.gather(
            *[download_with_semaphore(url) for url in urls], return_exceptions=True
        )

        # 處理結果
        processed_results = []
        successful_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "success": False,
                        "error": str(result),
                        "url": urls[i] if i < len(urls) else "unknown",
                    }
                )
            else:
                processed_results.append(result)
                if result.get("success"):
                    successful_count += 1

        duration = time.time() - start_time
        success_rate = successful_count / len(urls) if urls else 0

        self.logger.info(
            f"✅ 批次下載完成: {successful_count}/{len(urls)} "
            f"({success_rate:.1%}) in {duration:.2f}s"
        )

        return processed_results

    async def get_connection_stats(self) -> Dict[str, Any]:
        """獲取連接池統計信息"""
        total_sessions = len(self._sessions)

        # 計算每個 session 的連接統計
        session_stats = {}
        for key, session in self._sessions.items():
            if hasattr(session.connector, "_conns"):
                active = len(
                    [
                        conn
                        for conns in session.connector._conns.values()
                        for conn in conns
                    ]
                )
                session_stats[key] = {
                    "active_connections": active,
                    "closed": session.closed,
                }

        return {
            "total_sessions": total_sessions,
            "session_details": session_stats,
            "global_stats": {
                "active_connections": self.stats.active_connections,
                "total_created": self.stats.total_created,
                "total_closed": self.stats.total_closed,
                "total_failed": self.stats.total_failed,
                "total_timeouts": self.stats.total_timeouts,
            },
            "config": {
                "total_limit": self.config.total_limit,
                "per_host_limit": self.config.per_host_limit,
                "total_timeout": self.config.total_timeout,
            },
        }

    async def cleanup_idle_connections(self):
        """清理閒置連接 - 修復連接池洩漏"""
        current_time = time.time()

        if current_time - self._last_cleanup < self.config.cleanup_interval:
            return  # 還不需要清理

        self.logger.debug("🧹 開始清理閒置連接")

        cleanup_count = 0
        for session_key, session in list(self._sessions.items()):
            if session.closed:
                # 移除已關閉的 session
                del self._sessions[session_key]
                if session_key in self._session_locks:
                    del self._session_locks[session_key]
                cleanup_count += 1
                self.stats.total_closed += 1
                continue

            # 清理 session 的閒置連接
            if hasattr(session.connector, "_cleanup_closed_disabled"):
                # 強制啟用清理
                session.connector._cleanup_closed_disabled = False

            # 調用連接器的清理方法
            if hasattr(session.connector, "_cleanup_closed"):
                try:
                    await session.connector._cleanup_closed()
                except Exception as e:
                    self.logger.warning(f"清理連接失敗: {e}")

        self._last_cleanup = current_time

        if cleanup_count > 0:
            self.logger.info(f"🧹 清理完成，移除 {cleanup_count} 個閒置 session")

    async def force_cleanup_all(self):
        """強制清理所有連接"""
        self.logger.info("🧹 強制清理所有連接池")

        for session_key, session in list(self._sessions.items()):
            try:
                if not session.closed:
                    await session.close()
                    self.stats.total_closed += 1
            except Exception as e:
                self.logger.warning(f"關閉 session {session_key} 失敗: {e}")

        self._sessions.clear()
        self._session_locks.clear()
        self.logger.info("✅ 所有連接池已清理")

    async def start_background_cleanup(self):
        """啟動背景清理任務"""
        if self._cleanup_task is not None:
            return  # 已經啟動

        async def cleanup_loop():
            while not self._shutdown:
                try:
                    await self.cleanup_idle_connections()
                    await asyncio.sleep(self.config.cleanup_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"背景清理錯誤: {e}")
                    await asyncio.sleep(10)  # 錯誤後等待 10 秒

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        self.logger.info("🔄 背景清理任務已啟動")

    async def shutdown(self):
        """關閉連接池管理器"""
        self.logger.info("🛑 關閉連接池管理器")

        self._shutdown = True

        # 取消背景任務
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 強制清理所有連接
        await self.force_cleanup_all()

        self.logger.info("✅ 連接池管理器已關閉")

    def __del__(self):
        """析構函數 - 確保資源釋放"""
        if not self._shutdown and self._sessions:
            self.logger.warning("⚠️ ConnectionPoolManager 未正確關閉，存在資源洩漏風險")


# 全域連接池管理器實例
_global_pool_manager: Optional[ConnectionPoolManager] = None


async def get_global_pool_manager() -> ConnectionPoolManager:
    """獲取全域連接池管理器"""
    global _global_pool_manager

    if _global_pool_manager is None:
        _global_pool_manager = ConnectionPoolManager()
        await _global_pool_manager.start_background_cleanup()

    return _global_pool_manager


async def shutdown_global_pool_manager():
    """關閉全域連接池管理器"""
    global _global_pool_manager

    if _global_pool_manager:
        await _global_pool_manager.shutdown()
        _global_pool_manager = None


# 方便的裝飾器
def with_connection_pool(session_key: str = "default"):
    """連接池裝飾器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            pool_manager = await get_global_pool_manager()
            session = await pool_manager.get_session(session_key)

            # 將 session 注入到 kwargs 中
            kwargs["session"] = session
            kwargs["pool_manager"] = pool_manager

            return await func(*args, **kwargs)

        return wrapper

    return decorator
