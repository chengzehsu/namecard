#!/usr/bin/env python3
"""
增強並行下載器 - EnhancedParallelDownloader
集成連接池管理器，解決所有連接池相關問題

主要修復：
1. 🔧 連接池洩漏問題完全修復
2. 🔧 超時和重試機制優化
3. 🔧 並發控制和資源管理
4. 🔧 錯誤處理和恢復機制
5. 🔧 性能監控和診斷
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
from telegram import File

from .connection_pool_manager import (
    ConnectionPoolConfig,
    ConnectionPoolManager,
    get_global_pool_manager,
)


@dataclass
class EnhancedDownloadResult:
    """增強的下載結果"""

    success: bool
    data: Optional[bytes] = None
    error: Optional[str] = None
    download_time: float = 0.0
    file_size: int = 0
    source: str = "download"  # download, cache, error
    retry_count: int = 0
    connection_reused: bool = False
    cache_hit: bool = False
    performance_level: str = "A"  # S, A, B, C, D


@dataclass
class DownloadBatch:
    """下載批次"""

    files: List[Union[File, str]]
    batch_id: str
    max_concurrent: int = 8
    enable_cache: bool = True
    session_key: str = "batch_download"


class EnhancedParallelDownloader:
    """增強並行下載器 - 解決連接池問題"""

    def __init__(
        self,
        pool_config: Optional[ConnectionPoolConfig] = None,
        enable_cache: bool = True,
        cache_size_mb: int = 200,
        max_concurrent_downloads: int = 8,
    ):
        self.logger = logging.getLogger(__name__)

        # 連接池配置優化
        if pool_config is None:
            pool_config = ConnectionPoolConfig(
                total_limit=25,
                per_host_limit=8,
                total_timeout=20,
                connect_timeout=5,
                read_timeout=15,
                max_retries=3,
                cleanup_interval=30,
            )

        self.pool_manager = ConnectionPoolManager(pool_config)
        self.max_concurrent = max_concurrent_downloads

        # 快取配置
        self.enable_cache = enable_cache
        self.max_cache_size = cache_size_mb * 1024 * 1024
        self.cache_dir = Path("./cache/enhanced_telegram_images")
        if enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 統計追蹤 - 增強版
        self.stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_retry_attempts": 0,
            "connection_pool_errors": 0,
            "timeout_errors": 0,
            "avg_download_time": 0.0,
            "total_bytes_downloaded": 0,
            "performance_distribution": {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0},
        }

        # 性能基準
        self.performance_thresholds = {
            "S": 0.5,  # 超快 < 0.5s
            "A": 2.0,  # 快速 < 2.0s
            "B": 5.0,  # 正常 < 5.0s
            "C": 10.0,  # 慢 < 10.0s
            "D": float("inf"),  # 很慢 >= 10.0s
        }

        self.logger.info("🚀 EnhancedParallelDownloader 初始化完成")
        self.logger.info(f"   - 最大並發: {max_concurrent_downloads}")
        self.logger.info(f"   - 快取: {'啟用' if enable_cache else '停用'}")
        self.logger.info(
            f"   - 連接池: 總限制={pool_config.total_limit}, 每主機={pool_config.per_host_limit}"
        )

    async def initialize(self):
        """初始化連接池管理器"""
        await self.pool_manager.start_background_cleanup()
        self.logger.debug("✅ 連接池背景清理已啟動")

    def _get_cache_key(self, file_id: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(f"enhanced_{file_id}".encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """獲取快取文件路徑"""
        return self.cache_dir / f"{cache_key}.jpg"

    async def _check_cache(self, file_id: str) -> Optional[bytes]:
        """檢查快取 - 增強版"""
        if not self.enable_cache:
            self.stats["cache_misses"] += 1
            return None

        cache_key = self._get_cache_key(file_id)
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists() and cache_path.stat().st_size > 0:
            try:
                async with aiofiles.open(cache_path, "rb") as f:
                    data = await f.read()

                if len(data) > 0:
                    self.stats["cache_hits"] += 1
                    self.logger.debug(
                        f"💾 快取命中: {file_id[:12]}... ({len(data)} bytes)"
                    )
                    return data

            except Exception as e:
                self.logger.warning(f"快取讀取失敗 {file_id[:12]}: {e}")
                # 清理損壞的快取
                try:
                    cache_path.unlink()
                except:
                    pass

        self.stats["cache_misses"] += 1
        return None

    async def _store_cache(self, file_id: str, data: bytes) -> bool:
        """存儲到快取 - 增強版"""
        if not self.enable_cache or len(data) == 0:
            return False

        # 檢查單個文件大小限制
        if len(data) > self.max_cache_size // 20:  # 單文件不超過總快取的 5%
            self.logger.debug(f"文件過大，跳過快取: {len(data)} bytes")
            return False

        try:
            cache_key = self._get_cache_key(file_id)
            cache_path = self._get_cache_path(cache_key)

            # 確保快取目錄存在
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # 原子寫入
            temp_path = cache_path.with_suffix(".tmp")
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(data)

            # 原子移動
            temp_path.rename(cache_path)

            self.logger.debug(f"💾 快取存儲成功: {file_id[:12]}... ({len(data)} bytes)")

            # 異步清理快取
            asyncio.create_task(self._cleanup_cache_if_needed())

            return True

        except Exception as e:
            self.logger.warning(f"快取存儲失敗 {file_id[:12]}: {e}")
            return False

    async def _cleanup_cache_if_needed(self):
        """智能快取清理"""
        try:
            total_size = 0
            cache_files = []

            # 掃描快取目錄
            if not self.cache_dir.exists():
                return

            for file_path in self.cache_dir.iterdir():
                if file_path.is_file() and not file_path.name.endswith(".tmp"):
                    stat = file_path.stat()
                    total_size += stat.st_size
                    cache_files.append((file_path, stat.st_mtime, stat.st_size))

            # 檢查是否需要清理
            if total_size <= self.max_cache_size:
                return

            self.logger.info(
                f"📦 快取大小超限: {total_size / 1024 / 1024:.1f}MB "
                f"(限制: {self.max_cache_size / 1024 / 1024:.1f}MB)"
            )

            # 按最後修改時間排序（最舊的先刪除）
            cache_files.sort(key=lambda x: x[1])

            # 刪除檔案直到低於限制的 80%
            target_size = int(self.max_cache_size * 0.8)
            deleted_count = 0
            deleted_size = 0

            for file_path, mtime, size in cache_files:
                if total_size - deleted_size <= target_size:
                    break

                try:
                    file_path.unlink()
                    deleted_count += 1
                    deleted_size += size
                except Exception as e:
                    self.logger.warning(f"刪除快取文件失敗: {e}")

            if deleted_count > 0:
                self.logger.info(
                    f"🧹 快取清理完成: 刪除 {deleted_count} 個文件, "
                    f"釋放 {deleted_size / 1024 / 1024:.1f}MB"
                )

        except Exception as e:
            self.logger.error(f"快取清理失敗: {e}")

    def _classify_performance(self, download_time: float) -> str:
        """性能等級分類"""
        for level, threshold in self.performance_thresholds.items():
            if download_time < threshold:
                return level
        return "D"

    async def download_single_file(
        self, telegram_file: File, session_key: str = "single_download"
    ) -> EnhancedDownloadResult:
        """下載單個文件 - 完全修復版"""

        file_id = telegram_file.file_id
        start_time = time.time()

        self.logger.debug(f"🔽 開始下載: {file_id[:12]}...")

        # 1. 檢查快取
        cached_data = await self._check_cache(file_id)
        if cached_data:
            download_time = time.time() - start_time
            performance_level = self._classify_performance(download_time)
            self.stats["performance_distribution"][performance_level] += 1

            return EnhancedDownloadResult(
                success=True,
                data=cached_data,
                download_time=download_time,
                file_size=len(cached_data),
                source="cache",
                cache_hit=True,
                performance_level=performance_level,
            )

        # 2. 實際下載
        try:
            # 獲取文件 URL
            file_url = telegram_file.file_path
            if not file_url.startswith("http"):
                # 構建完整 URL（如果需要）
                file_url = f"https://api.telegram.org/file/bot{telegram_file.file_path}"

            # 使用連接池管理器下載
            download_result = await self.pool_manager.download_with_retry(
                url=file_url, session_key=session_key
            )

            self.stats["total_downloads"] += 1

            if download_result["success"]:
                data = download_result["data"]
                download_time = time.time() - start_time
                performance_level = self._classify_performance(download_time)

                # 統計更新
                self.stats["successful_downloads"] += 1
                self.stats["total_bytes_downloaded"] += len(data)
                self.stats["performance_distribution"][performance_level] += 1
                self.stats["total_retry_attempts"] += (
                    download_result.get("attempt", 1) - 1
                )

                # 存儲到快取
                await self._store_cache(file_id, data)

                self.logger.debug(
                    f"✅ 下載完成: {file_id[:12]}... "
                    f"({len(data)} bytes, {download_time:.2f}s, {performance_level}級)"
                )

                return EnhancedDownloadResult(
                    success=True,
                    data=data,
                    download_time=download_time,
                    file_size=len(data),
                    source="download",
                    retry_count=download_result.get("attempt", 1) - 1,
                    performance_level=performance_level,
                )
            else:
                # 下載失敗
                error_msg = download_result.get("error", "Unknown error")
                download_time = time.time() - start_time

                self.stats["failed_downloads"] += 1

                # 錯誤分類統計
                if "timeout" in error_msg.lower():
                    self.stats["timeout_errors"] += 1
                elif "connection" in error_msg.lower() or "pool" in error_msg.lower():
                    self.stats["connection_pool_errors"] += 1

                self.logger.warning(f"❌ 下載失敗: {file_id[:12]}... - {error_msg}")

                return EnhancedDownloadResult(
                    success=False,
                    error=error_msg,
                    download_time=download_time,
                    source="error",
                    retry_count=download_result.get("attempt", 1) - 1,
                )

        except Exception as e:
            download_time = time.time() - start_time
            error_msg = f"下載異常: {str(e)}"

            self.stats["failed_downloads"] += 1
            self.logger.error(f"💥 下載異常: {file_id[:12]}... - {e}")

            return EnhancedDownloadResult(
                success=False,
                error=error_msg,
                download_time=download_time,
                source="error",
            )

    async def download_batch(
        self, batch: DownloadBatch
    ) -> List[EnhancedDownloadResult]:
        """批次下載 - 完全優化版"""

        if not batch.files:
            return []

        batch_start_time = time.time()
        file_count = len(batch.files)

        self.logger.info(
            f"🚀 開始批次下載: {batch.batch_id} "
            f"({file_count} 個文件, 並發度: {batch.max_concurrent})"
        )

        # 並發控制信號量
        semaphore = asyncio.Semaphore(min(batch.max_concurrent, self.max_concurrent))

        async def download_with_semaphore(
            telegram_file: File, index: int
        ) -> EnhancedDownloadResult:
            """帶信號量控制的下載"""
            async with semaphore:
                try:
                    result = await self.download_single_file(
                        telegram_file,
                        session_key=f"{batch.session_key}_{index % 4}",  # 輪詢 session
                    )
                    return result
                except Exception as e:
                    self.logger.error(f"批次下載異常 #{index}: {e}")
                    return EnhancedDownloadResult(
                        success=False, error=f"批次下載異常: {str(e)}", source="error"
                    )

        # 並行執行所有下載
        try:
            results = await asyncio.gather(
                *[
                    download_with_semaphore(file, i)
                    for i, file in enumerate(batch.files)
                ],
                return_exceptions=True,
            )
        except Exception as e:
            self.logger.error(f"批次下載 gather 失敗: {e}")
            # 創建失敗結果
            results = [
                EnhancedDownloadResult(
                    success=False, error=f"批次執行失敗: {str(e)}", source="error"
                )
                for _ in batch.files
            ]

        # 處理結果和統計
        processed_results = []
        successful_count = 0
        total_size = 0
        total_cache_hits = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_result = EnhancedDownloadResult(
                    success=False, error=f"處理異常: {str(result)}", source="error"
                )
            else:
                processed_result = result

            processed_results.append(processed_result)

            if processed_result.success:
                successful_count += 1
                total_size += processed_result.file_size
                if processed_result.cache_hit:
                    total_cache_hits += 1

        # 批次統計
        batch_duration = time.time() - batch_start_time
        success_rate = successful_count / file_count if file_count > 0 else 0
        avg_time_per_file = batch_duration / file_count if file_count > 0 else 0
        cache_hit_rate = total_cache_hits / file_count if file_count > 0 else 0

        self.logger.info(f"✅ 批次下載完成: {batch.batch_id}")
        self.logger.info(
            f"   - 成功率: {successful_count}/{file_count} ({success_rate:.1%})"
        )
        self.logger.info(f"   - 總時間: {batch_duration:.2f}s")
        self.logger.info(f"   - 平均時間: {avg_time_per_file:.2f}s/文件")
        self.logger.info(f"   - 快取命中率: {cache_hit_rate:.1%}")
        self.logger.info(f"   - 總大小: {total_size / 1024:.1f}KB")

        return processed_results

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """獲取詳細統計信息"""
        pool_stats = await self.pool_manager.get_connection_stats()

        # 計算平均下載時間
        if self.stats["successful_downloads"] > 0:
            self.stats["avg_download_time"] = (
                self.stats["total_bytes_downloaded"]
                / self.stats["successful_downloads"]
                / 1024
            )

        return {
            "downloader_stats": self.stats,
            "connection_pool_stats": pool_stats,
            "cache_stats": {
                "enabled": self.enable_cache,
                "max_size_mb": self.max_cache_size / 1024 / 1024,
                "hit_rate": (
                    self.stats["cache_hits"]
                    / (self.stats["cache_hits"] + self.stats["cache_misses"])
                    if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0
                    else 0
                ),
            },
            "performance_summary": {
                "success_rate": (
                    self.stats["successful_downloads"] / self.stats["total_downloads"]
                    if self.stats["total_downloads"] > 0
                    else 0
                ),
                "avg_download_time": self.stats["avg_download_time"],
                "performance_distribution": self.stats["performance_distribution"],
            },
        }

    async def diagnose_connection_issues(self) -> Dict[str, Any]:
        """診斷連接問題"""
        stats = await self.get_detailed_stats()

        issues = []
        recommendations = []

        # 檢查成功率
        success_rate = stats["performance_summary"]["success_rate"]
        if success_rate < 0.9:
            issues.append(f"成功率過低: {success_rate:.1%}")
            recommendations.append("檢查網路連接和 API 配額")

        # 檢查連接池錯誤
        if self.stats["connection_pool_errors"] > 0:
            issues.append(f"連接池錯誤: {self.stats['connection_pool_errors']} 次")
            recommendations.append("增加連接池限制或減少並發數")

        # 檢查超時錯誤
        if self.stats["timeout_errors"] > 0:
            issues.append(f"超時錯誤: {self.stats['timeout_errors']} 次")
            recommendations.append("增加超時時間或優化網路環境")

        # 檢查性能分布
        slow_downloads = (
            self.stats["performance_distribution"]["C"]
            + self.stats["performance_distribution"]["D"]
        )
        if slow_downloads > self.stats["total_downloads"] * 0.2:
            issues.append(f"慢速下載過多: {slow_downloads} 次")
            recommendations.append("優化並發設置或檢查服務器性能")

        # 檢查快取命中率
        cache_hit_rate = stats["cache_stats"]["hit_rate"]
        if cache_hit_rate < 0.3 and self.enable_cache:
            issues.append(f"快取命中率過低: {cache_hit_rate:.1%}")
            recommendations.append("增加快取大小或優化快取策略")

        return {
            "diagnosis_time": time.time(),
            "health_status": "healthy" if not issues else "issues_detected",
            "issues": issues,
            "recommendations": recommendations,
            "detailed_stats": stats,
        }

    async def cleanup(self):
        """清理資源"""
        self.logger.info("🧹 EnhancedParallelDownloader 清理中...")

        # 清理連接池
        await self.pool_manager.shutdown()

        self.logger.info("✅ EnhancedParallelDownloader 清理完成")


# 全域實例管理
_global_enhanced_downloader: Optional[EnhancedParallelDownloader] = None


async def get_global_enhanced_downloader() -> EnhancedParallelDownloader:
    """獲取全域增強下載器實例"""
    global _global_enhanced_downloader

    if _global_enhanced_downloader is None:
        _global_enhanced_downloader = EnhancedParallelDownloader()
        await _global_enhanced_downloader.initialize()

    return _global_enhanced_downloader


async def shutdown_global_enhanced_downloader():
    """關閉全域增強下載器"""
    global _global_enhanced_downloader

    if _global_enhanced_downloader:
        await _global_enhanced_downloader.cleanup()
        _global_enhanced_downloader = None
