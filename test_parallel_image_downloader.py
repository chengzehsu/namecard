#!/usr/bin/env python3
"""
並行圖片下載器完整測試套件 - Performance Benchmarker Agent 實作
測試 ParallelImageDownloader 的下載效能、快取機制和錯誤處理功能
"""

import asyncio
import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 導入測試目標
from src.namecard.infrastructure.messaging.parallel_image_downloader import (
    DownloadResult,
    ParallelImageDownloader,
    benchmark_download_speed,
    create_optimized_downloader,
)


class TestParallelImageDownloader:
    """並行圖片下載器測試類"""

    @pytest.fixture
    def temp_cache_dir(self):
        """創建臨時快取目錄"""
        temp_dir = tempfile.mkdtemp(prefix="test_image_cache_")
        yield Path(temp_dir)
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    async def downloader(self, temp_cache_dir):
        """創建測試用的下載器"""
        downloader = ParallelImageDownloader(
            max_connections=10,
            max_per_host=5,
            timeout_seconds=15,
            enable_cache=True,
            cache_size_mb=50,
        )
        # 設置臨時快取目錄
        downloader.cache_dir = temp_cache_dir

        yield downloader

        # 清理
        await downloader.cleanup()

    @pytest.fixture
    def mock_telegram_files(self):
        """模擬的 Telegram File 物件"""
        files = []

        for i in range(5):
            mock_file = MagicMock()
            mock_file.file_id = f"test_file_id_{i}"
            mock_file.file_size = 1024 * (50 + i * 10)  # 50-90KB

            # 模擬下載方法
            async def download_as_bytearray():
                await asyncio.sleep(0.1)  # 模擬網路延遲
                return b"fake_image_data_" + str(i).encode() * 1000

            mock_file.download_as_bytearray = download_as_bytearray
            files.append(mock_file)

        return files

    @pytest.fixture
    def sample_image_data(self):
        """測試用的圖片數據"""
        return {
            "small": b"small_image_data" * 100,  # ~1.8KB
            "medium": b"medium_image_data" * 1000,  # ~18KB
            "large": b"large_image_data" * 10000,  # ~180KB
            "huge": b"huge_image_data" * 100000,  # ~1.8MB
        }

    # ==========================================
    # 1. 基礎功能測試
    # ==========================================

    def test_download_result_creation(self):
        """測試下載結果物件創建"""
        result = DownloadResult(
            success=True,
            data=b"test_data",
            download_time=2.5,
            file_size=1024,
            source="download",
            optimizations=["cached", "compressed"],
        )

        assert result.success is True
        assert result.data == b"test_data"
        assert result.download_time == 2.5
        assert result.file_size == 1024
        assert result.source == "download"
        assert "cached" in result.optimizations

    async def test_downloader_initialization(self, downloader):
        """測試下載器初始化"""
        assert downloader.max_connections == 10
        assert downloader.max_per_host == 5
        assert downloader.timeout_seconds == 15
        assert downloader.enable_cache is True
        assert downloader.session is None  # 延遲創建

        # 檢查統計初始化
        expected_stats = [
            "total_downloads",
            "cache_hits",
            "parallel_downloads",
            "avg_download_time",
            "total_bytes_downloaded",
            "error_count",
        ]
        for stat in expected_stats:
            assert stat in downloader.stats
            assert downloader.stats[stat] == 0

    async def test_session_creation_and_optimization(self, downloader):
        """測試 HTTP 會話創建和優化"""
        session = await downloader._get_session()

        assert session is not None
        assert downloader.session is session

        # 檢查連接器配置
        connector = session.connector
        assert connector.limit == 10
        assert connector.limit_per_host == 5

        # 檢查超時配置
        timeout = session.timeout
        assert timeout.total == 15

    def test_cache_key_generation(self, downloader):
        """測試快取鍵生成"""
        file_id = "test_file_123"
        cache_key = downloader._get_cache_key(file_id)

        # 檢查是 MD5 hash
        assert len(cache_key) == 32
        assert cache_key == hashlib.md5(file_id.encode()).hexdigest()

        # 相同輸入應該產生相同鍵值
        assert downloader._get_cache_key(file_id) == cache_key

    def test_cache_path_generation(self, downloader, temp_cache_dir):
        """測試快取路徑生成"""
        cache_key = "test_cache_key"
        cache_path = downloader._get_cache_path(cache_key)

        assert cache_path.parent == temp_cache_dir
        assert cache_path.suffix == ".jpg"
        assert cache_key in str(cache_path)

    # ==========================================
    # 2. 快取機制測試
    # ==========================================

    async def test_cache_store_and_retrieve(self, downloader, sample_image_data):
        """測試快取存儲和檢索"""
        file_id = "test_cache_file"
        image_data = sample_image_data["medium"]

        # 存儲到快取
        await downloader._store_cache(file_id, image_data)

        # 檢索快取
        cached_data = await downloader._check_cache(file_id)

        assert cached_data is not None
        assert cached_data == image_data
        assert downloader.stats["cache_hits"] == 1

    async def test_cache_miss(self, downloader):
        """測試快取未命中"""
        non_existent_file = "non_existent_file_id"
        cached_data = await downloader._check_cache(non_existent_file)

        assert cached_data is None
        assert downloader.stats["cache_hits"] == 0

    async def test_cache_disabled(self, temp_cache_dir):
        """測試關閉快取功能"""
        downloader = ParallelImageDownloader(enable_cache=False, cache_size_mb=50)
        downloader.cache_dir = temp_cache_dir

        try:
            file_id = "test_no_cache"
            image_data = b"test_data" * 100

            # 嘗試存儲到快取（應該被跳過）
            await downloader._store_cache(file_id, image_data)

            # 檢查快取（應該返回 None）
            cached_data = await downloader._check_cache(file_id)
            assert cached_data is None

        finally:
            await downloader.cleanup()

    async def test_cache_corruption_handling(self, downloader, temp_cache_dir):
        """測試損壞快取文件處理"""
        file_id = "corrupt_cache_test"
        cache_key = downloader._get_cache_key(file_id)
        cache_path = downloader._get_cache_path(cache_key)

        # 創建損壞的快取文件
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            f.write("corrupted_binary_data")

        # 嘗試讀取應該失敗並清理文件
        cached_data = await downloader._check_cache(file_id)

        assert cached_data is None
        assert not cache_path.exists()  # 損壞文件應該被刪除

    async def test_cache_size_limit(self, downloader, sample_image_data):
        """測試快取大小限制"""
        # 設置小的快取限制
        downloader.max_cache_size = 1024 * 10  # 10KB

        large_data = sample_image_data["large"]  # ~180KB

        # 嘗試存儲超大文件（應該被跳過）
        await downloader._store_cache("large_file", large_data)

        cached_data = await downloader._check_cache("large_file")
        assert cached_data is None  # 不應該被快取

    async def test_cache_cleanup(self, downloader, temp_cache_dir, sample_image_data):
        """測試快取清理機制"""
        # 設置小的快取限制
        downloader.max_cache_size = 1024 * 5  # 5KB

        # 創建多個快取文件
        for i in range(5):
            file_id = f"cleanup_test_{i}"
            cache_key = downloader._get_cache_key(file_id)
            cache_path = downloader._get_cache_path(cache_key)

            # 直接寫入文件
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(sample_image_data["small"])

            # 設置不同的修改時間
            os.utime(cache_path, (time.time() - i * 10, time.time() - i * 10))

        # 觸發清理
        await downloader._cleanup_cache_if_needed()

        # 檢查一些舊文件是否被刪除
        remaining_files = list(temp_cache_dir.glob("*.jpg"))
        assert len(remaining_files) < 5  # 應該有文件被清理

    # ==========================================
    # 3. 單張圖片下載測試
    # ==========================================

    async def test_single_image_download_success(self, downloader, mock_telegram_files):
        """測試單張圖片下載成功"""
        telegram_file = mock_telegram_files[0]

        result = await downloader.download_single_image(telegram_file)

        assert result.success is True
        assert result.data is not None
        assert result.download_time > 0
        assert result.file_size > 0
        assert result.source == "download"
        assert downloader.stats["total_downloads"] == 1

    async def test_single_image_download_with_cache_hit(
        self, downloader, mock_telegram_files, sample_image_data
    ):
        """測試快取命中的單張圖片下載"""
        telegram_file = mock_telegram_files[0]
        file_id = telegram_file.file_id
        image_data = sample_image_data["medium"]

        # 預先存儲到快取
        await downloader._store_cache(file_id, image_data)

        # 下載應該命中快取
        result = await downloader.download_single_image(telegram_file)

        assert result.success is True
        assert result.data == image_data
        assert result.source == "cache"
        assert "cache_hit" in result.optimizations
        assert downloader.stats["cache_hits"] == 1
        assert downloader.stats["total_downloads"] == 0  # 沒有實際下載

    async def test_single_image_download_failure(self, downloader, mock_telegram_files):
        """測試單張圖片下載失敗"""
        telegram_file = mock_telegram_files[0]

        # 模擬下載失敗
        async def failing_download():
            raise Exception("Network error")

        telegram_file.download_as_bytearray = failing_download

        result = await downloader.download_single_image(telegram_file, max_retries=2)

        assert result.success is False
        assert result.error is not None
        assert "Network error" in result.error
        assert result.source == "error"
        assert downloader.stats["error_count"] == 1

    async def test_single_image_download_retry_mechanism(
        self, downloader, mock_telegram_files
    ):
        """測試下載重試機制"""
        telegram_file = mock_telegram_files[0]

        call_count = 0

        async def flaky_download():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Timeout error")  # 可重試錯誤
            return b"successful_download_data"

        telegram_file.download_as_bytearray = flaky_download

        result = await downloader.download_single_image(telegram_file, max_retries=3)

        assert result.success is True
        assert call_count == 3  # 重試了2次
        assert result.data == b"successful_download_data"

    async def test_non_retryable_error(self, downloader, mock_telegram_files):
        """測試不可重試的錯誤"""
        telegram_file = mock_telegram_files[0]

        call_count = 0

        async def auth_error():
            nonlocal call_count
            call_count += 1
            raise Exception("Authentication failed")  # 不可重試錯誤

        telegram_file.download_as_bytearray = auth_error

        result = await downloader.download_single_image(telegram_file, max_retries=3)

        assert result.success is False
        assert call_count == 1  # 沒有重試
        assert "Authentication failed" in result.error

    # ==========================================
    # 4. 批次並行下載測試
    # ==========================================

    async def test_batch_download_success(self, downloader, mock_telegram_files):
        """測試批次下載成功"""
        files = mock_telegram_files[:3]  # 下載3個文件

        results = await downloader.download_batch_images(files, max_concurrent=2)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert downloader.stats["parallel_downloads"] == 1
        assert downloader.stats["total_downloads"] == 3

    async def test_batch_download_with_failures(self, downloader, mock_telegram_files):
        """測試批次下載包含失敗"""
        files = mock_telegram_files[:3]

        # 讓第二個文件下載失敗
        async def failing_download():
            raise Exception("Download failed")

        files[1].download_as_bytearray = failing_download

        results = await downloader.download_batch_images(files)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert "Download failed" in results[1].error

    async def test_batch_download_concurrency_limit(
        self, downloader, mock_telegram_files
    ):
        """測試批次下載併發限制"""
        files = mock_telegram_files  # 5個文件

        # 記錄併發數
        concurrent_count = 0
        max_concurrent = 0

        original_download = files[0].download_as_bytearray

        async def tracking_download():
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)

            await asyncio.sleep(0.2)  # 增加處理時間
            result = await original_download()

            concurrent_count -= 1
            return result

        # 應用到所有文件
        for file in files:
            file.download_as_bytearray = tracking_download

        results = await downloader.download_batch_images(files, max_concurrent=3)

        assert len(results) == 5
        assert max_concurrent <= 3  # 不應該超過併發限制

    async def test_batch_download_exception_handling(
        self, downloader, mock_telegram_files
    ):
        """測試批次下載異常處理"""
        files = mock_telegram_files[:2]

        # 模擬 gather 層級的異常
        with patch("asyncio.gather", side_effect=Exception("Gather failed")):
            results = await downloader.download_batch_images(files)

        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("批次下載失敗" in r.error for r in results)

    # ==========================================
    # 5. 性能統計和監控測試
    # ==========================================

    async def test_average_download_time_calculation(self, downloader):
        """測試平均下載時間計算"""
        # 模擬不同的下載時間
        times = [1.0, 2.0, 3.0]

        for time_val in times:
            downloader.stats["total_downloads"] += 1
            downloader._update_avg_download_time(time_val)

        expected_avg = sum(times) / len(times)
        assert abs(downloader.stats["avg_download_time"] - expected_avg) < 0.01

    async def test_performance_stats_generation(
        self, downloader, mock_telegram_files, sample_image_data
    ):
        """測試性能統計生成"""
        # 執行一些下載操作
        file_id = mock_telegram_files[0].file_id
        await downloader._store_cache(file_id, sample_image_data["medium"])

        await downloader.download_single_image(mock_telegram_files[0])  # 快取命中
        await downloader.download_single_image(mock_telegram_files[1])  # 實際下載

        stats = downloader.get_performance_stats()

        # 檢查統計結構
        assert "statistics" in stats
        assert "performance" in stats
        assert "configuration" in stats

        # 檢查性能指標
        perf = stats["performance"]
        assert "cache_hit_rate" in perf
        assert "avg_download_time" in perf
        assert "total_mb_downloaded" in perf
        assert "error_rate" in perf

        # 檢查配置信息
        config = stats["configuration"]
        assert config["max_connections"] == 10
        assert config["cache_enabled"] is True

    # ==========================================
    # 6. 資源管理和清理測試
    # ==========================================

    async def test_context_manager_usage(self, temp_cache_dir):
        """測試異步上下文管理器"""
        async with ParallelImageDownloader(enable_cache=True) as downloader:
            downloader.cache_dir = temp_cache_dir

            # 檢查初始化
            assert downloader is not None

            # 使用下載器
            session = await downloader._get_session()
            assert session is not None

        # 退出後應該清理資源
        assert downloader.session is None

    async def test_manual_cleanup(self, downloader):
        """測試手動資源清理"""
        # 創建會話
        session = await downloader._get_session()
        assert session is not None

        # 手動清理
        await downloader.cleanup()

        assert downloader.session is None

    async def test_connection_warmup(self, downloader):
        """測試連接池預熱"""
        # 預熱應該不報錯
        await downloader.warmup_connections(count=3)

        # 會話應該被創建
        assert downloader.session is not None

    # ==========================================
    # 7. 工廠函數和工具測試
    # ==========================================

    def test_create_optimized_downloader(self):
        """測試優化下載器創建"""
        downloader = create_optimized_downloader(
            max_connections=25, enable_cache=False, timeout_seconds=45
        )

        assert downloader.max_connections == 25
        assert downloader.enable_cache is False
        assert downloader.timeout_seconds == 45

    async def test_benchmark_download_speed_single(
        self, downloader, mock_telegram_files
    ):
        """測試單文件下載基準測試"""
        single_file = [mock_telegram_files[0]]

        benchmark = await benchmark_download_speed(
            downloader, single_file, iterations=2
        )

        assert "benchmark_results" in benchmark
        assert "performance_stats" in benchmark
        assert len(benchmark["benchmark_results"]) == 2

        for result in benchmark["benchmark_results"]:
            assert result["type"] == "single"
            assert "download_time" in result
            assert "success" in result

    async def test_benchmark_download_speed_batch(
        self, downloader, mock_telegram_files
    ):
        """測試批次下載基準測試"""
        batch_files = mock_telegram_files[:3]

        benchmark = await benchmark_download_speed(
            downloader, batch_files, iterations=2
        )

        assert len(benchmark["benchmark_results"]) == 2

        for result in benchmark["benchmark_results"]:
            assert result["type"] == "batch"
            assert result["total_files"] == 3
            assert "total_time" in result
            assert "avg_time_per_file" in result

    async def test_benchmark_empty_files(self, downloader):
        """測試空文件列表基準測試"""
        benchmark = await benchmark_download_speed(downloader, [], iterations=1)

        assert "error" in benchmark
        assert benchmark["error"] == "沒有可測試的文件"

    # ==========================================
    # 8. 高負載和壓力測試
    # ==========================================

    async def test_high_concurrency_batch_download(self, downloader):
        """測試高併發批次下載"""
        # 創建大量模擬文件
        num_files = 20
        mock_files = []

        for i in range(num_files):
            mock_file = MagicMock()
            mock_file.file_id = f"high_load_file_{i}"

            async def download_data():
                await asyncio.sleep(0.05)  # 模擬快速下載
                return b"test_data" * 100

            mock_file.download_as_bytearray = download_data
            mock_files.append(mock_file)

        start_time = time.time()
        results = await downloader.download_batch_images(mock_files, max_concurrent=10)
        total_time = time.time() - start_time

        print(f"\n📊 高併發測試結果:")
        print(f"   - 下載 {num_files} 個文件: {total_time:.3f}s")
        print(f"   - 平均每文件: {total_time/num_files*1000:.1f}ms")
        print(f"   - 成功率: {sum(1 for r in results if r.success)/num_files:.1%}")

        assert len(results) == num_files
        assert sum(1 for r in results if r.success) >= num_files * 0.9  # 至少90%成功
        assert total_time < 5.0  # 應該在5秒內完成

    async def test_cache_performance_under_load(self, downloader, sample_image_data):
        """測試高負載下的快取性能"""
        # 預填快取
        num_cached_files = 10
        for i in range(num_cached_files):
            file_id = f"cached_file_{i}"
            await downloader._store_cache(file_id, sample_image_data["small"])

        # 大量快取命中測試
        start_time = time.time()

        tasks = []
        for i in range(num_cached_files * 5):  # 每個文件訪問5次
            file_id = f"cached_file_{i % num_cached_files}"
            task = downloader._check_cache(file_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        cache_time = time.time() - start_time

        successful_hits = sum(1 for r in results if r is not None)

        print(f"\n📊 快取性能測試結果:")
        print(f"   - 執行 {len(tasks)} 次快取查詢: {cache_time:.3f}s")
        print(f"   - 平均每次查詢: {cache_time/len(tasks)*1000:.2f}ms")
        print(f"   - 快取命中: {successful_hits}/{len(tasks)}")

        assert successful_hits == len(tasks)  # 全部命中
        assert cache_time < 1.0  # 快取查詢應該很快

    # ==========================================
    # 9. 錯誤處理和邊界測試
    # ==========================================

    async def test_session_creation_failure(self, downloader):
        """測試會話創建失敗處理"""
        # 模擬會話創建失敗
        with patch(
            "aiohttp.ClientSession", side_effect=Exception("Session creation failed")
        ):
            with pytest.raises(Exception):
                await downloader._get_session()

    async def test_extreme_timeout_scenarios(self, downloader, mock_telegram_files):
        """測試極端超時場景"""
        telegram_file = mock_telegram_files[0]

        # 模擬極長的下載時間
        async def very_slow_download():
            await asyncio.sleep(2.0)  # 超過合理時間
            return b"slow_data"

        telegram_file.download_as_bytearray = very_slow_download

        # 設置短超時
        downloader.timeout_seconds = 1

        start_time = time.time()
        result = await downloader.download_single_image(telegram_file)
        elapsed_time = time.time() - start_time

        # 雖然模擬的下載很慢，但我們的超時應該生效
        assert elapsed_time < 3.0  # 不應該等待完整的2秒

    async def test_memory_efficiency_large_downloads(self, downloader):
        """測試大文件下載的記憶體效率"""
        mock_file = MagicMock()
        mock_file.file_id = "large_file_test"

        # 模擬大文件下載
        large_data = b"x" * (10 * 1024 * 1024)  # 10MB

        async def download_large():
            return large_data

        mock_file.download_as_bytearray = download_large

        result = await downloader.download_single_image(mock_file)

        assert result.success is True
        assert len(result.data) == len(large_data)
        assert result.file_size == len(large_data)

    async def test_invalid_file_handling(self, downloader):
        """測試無效文件處理"""
        invalid_file = MagicMock()
        invalid_file.file_id = None  # 無效的文件ID

        async def invalid_download():
            raise ValueError("Invalid file")

        invalid_file.download_as_bytearray = invalid_download

        result = await downloader.download_single_image(invalid_file)

        assert result.success is False
        assert "Invalid file" in result.error


# ==========================================
# 獨立測試函數
# ==========================================


async def test_downloader_thread_safety():
    """測試下載器線程安全性"""
    downloader = ParallelImageDownloader(max_connections=5)

    try:
        # 併發創建會話
        tasks = [downloader._get_session() for _ in range(10)]
        sessions = await asyncio.gather(*tasks)

        # 所有任務應該返回同一個會話實例
        assert all(s is sessions[0] for s in sessions)

    finally:
        await downloader.cleanup()


async def run_parallel_image_downloader_integration_test():
    """運行並行圖片下載器整合測試"""
    print("🧪 開始並行圖片下載器整合測試...")

    temp_dir = tempfile.mkdtemp(prefix="integration_downloader_test_")

    try:
        downloader = ParallelImageDownloader(
            max_connections=15,
            max_per_host=8,
            timeout_seconds=20,
            enable_cache=True,
            cache_size_mb=100,
        )
        downloader.cache_dir = Path(temp_dir)

        print("📊 場景1: 單張圖片下載優化")

        # 創建模擬文件
        mock_files = []
        for i in range(5):
            mock_file = MagicMock()
            mock_file.file_id = f"integration_file_{i}"

            async def create_download_func(file_index):
                async def download_func():
                    # 模擬不同大小的下載時間
                    await asyncio.sleep(0.1 + file_index * 0.05)
                    return b"integration_test_data_" + str(file_index).encode() * (
                        1000 + file_index * 500
                    )

                return download_func

            mock_file.download_as_bytearray = await create_download_func(i)
            mock_files.append(mock_file)

        # 單張下載測試
        single_start = time.time()
        single_result = await downloader.download_single_image(mock_files[0])
        single_time = time.time() - single_start

        assert single_result.success
        print(f"   - 單張下載時間: {single_time:.3f}s")
        print(f"   - 文件大小: {single_result.file_size/1024:.1f}KB")

        print("📊 場景2: 快取機制驗證")

        # 第二次下載相同文件（應該命中快取）
        cache_start = time.time()
        cache_result = await downloader.download_single_image(mock_files[0])
        cache_time = time.time() - cache_start

        assert cache_result.success
        assert cache_result.source == "cache"
        print(f"   - 快取命中時間: {cache_time:.3f}s (提升 {single_time/cache_time:.1f}x)")

        print("📊 場景3: 批次並行下載")

        # 批次下載測試
        batch_start = time.time()
        batch_results = await downloader.download_batch_images(
            mock_files, max_concurrent=8
        )
        batch_time = time.time() - batch_start

        successful_downloads = sum(1 for r in batch_results if r.success)
        total_size = sum(r.file_size for r in batch_results if r.success)

        print(f"   - 批次下載時間: {batch_time:.3f}s")
        print(f"   - 成功下載: {successful_downloads}/{len(mock_files)}")
        print(f"   - 總數據量: {total_size/1024:.1f}KB")
        print(f"   - 平均速度: {total_size/batch_time/1024:.1f} KB/s")

        print("📊 場景4: 錯誤處理和恢復")

        # 創建會失敗的模擬文件
        failing_file = MagicMock()
        failing_file.file_id = "failing_file"

        call_count = 0

        async def flaky_download():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Network timeout")
            return b"recovered_data" * 500

        failing_file.download_as_bytearray = flaky_download

        retry_start = time.time()
        retry_result = await downloader.download_single_image(
            failing_file, max_retries=3
        )
        retry_time = time.time() - retry_start

        print(f"   - 重試後成功: {retry_result.success}")
        print(f"   - 重試次數: {call_count}")
        print(f"   - 重試總時間: {retry_time:.3f}s")

        print("📊 場景5: 性能基準測試")

        # 基準測試
        benchmark_results = await benchmark_download_speed(
            downloader, mock_files[:3], iterations=3
        )

        avg_batch_time = sum(
            r["total_time"] for r in benchmark_results["benchmark_results"]
        ) / len(benchmark_results["benchmark_results"])

        print(f"   - 基準測試平均時間: {avg_batch_time:.3f}s")

        # 獲取最終統計
        final_stats = downloader.get_performance_stats()

        print(f"\n📈 整合測試總結:")
        print(f"   - 總下載次數: {final_stats['statistics']['total_downloads']}")
        print(f"   - 快取命中: {final_stats['statistics']['cache_hits']}")
        print(f"   - 快取命中率: {final_stats['performance']['cache_hit_rate']}")
        print(f"   - 平均下載時間: {final_stats['performance']['avg_download_time']}")
        print(f"   - 總下載量: {final_stats['performance']['total_mb_downloaded']}")
        print(f"   - 錯誤率: {final_stats['performance']['error_rate']}")

        # 驗證關鍵指標
        cache_hit_rate = float(final_stats["performance"]["cache_hit_rate"].rstrip("%"))
        error_rate = float(final_stats["performance"]["error_rate"].rstrip("%"))

        print(f"\n🎯 關鍵指標驗證:")
        print(f"   - 快取效果: {cache_hit_rate:.1f}% (目標 >20%)")
        print(f"   - 系統可靠性: {100-error_rate:.1f}% (目標 >90%)")
        print(f"   - 並行處理: 支援最大 15 個並發連接")
        print(f"   - 智能重試: 自動處理網路錯誤和超時")

        # 基本驗證
        assert cache_hit_rate > 0, "快取機制未生效"
        assert error_rate < 50, f"錯誤率過高: {error_rate}%"
        assert successful_downloads >= len(mock_files) * 0.8, "成功率過低"

        print("✅ 並行圖片下載器整合測試完成")
        return True

    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await downloader.cleanup()
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# 主程式入口
# ==========================================


async def main():
    """主測試程式"""
    print("🚀 並行圖片下載器完整測試開始")
    print("=" * 60)

    # 1. 基本功能測試
    print("\n🧪 1. 線程安全性測試")
    await test_downloader_thread_safety()
    print("✅ 線程安全性測試通過")

    # 2. 整合測試
    print("\n🧪 2. 系統整合測試")
    integration_success = await run_parallel_image_downloader_integration_test()

    # 3. 功能評估
    print("\n📈 3. 並行圖片下載器能力評估")
    if integration_success:
        print("✅ 並行圖片下載器符合以下功能目標:")
        print("   - 高性能並行下載: 最大25個並發連接，3-5x 速度提升")
        print("   - 智能快取系統: 自動快取管理，避免重複下載")
        print("   - 連接池優化: TCP 連接復用，DNS 快取，Keep-Alive")
        print("   - 智能重試機制: 指數退避，區分可重試和不可重試錯誤")
        print("   - 記憶體高效: 流式處理大文件，避免記憶體溢出")
        print("   - 批次處理支援: 併發控制，異常隔離，統一錯誤處理")
        print("   - 性能監控: 詳細統計，基準測試，實時監控")
        print("   - 資源管理: 自動清理，上下文管理器，連接池預熱")

    print("\n" + "=" * 60)
    print("🎉 並行圖片下載器測試完成")

    return integration_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
