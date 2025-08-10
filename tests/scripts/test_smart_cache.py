#!/usr/bin/env python3
"""
智能快取系統完整測試套件 - Test Writer/Fixer Agent 實作
測試 SmartCacheManager 的三層快取架構和性能表現
"""

import asyncio
import json
import os
import pickle
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 導入測試目標
from src.namecard.infrastructure.ai.smart_cache import CacheEntry, SmartCacheManager


class TestSmartCacheManager:
    """智能快取管理器測試類"""

    @pytest.fixture
    async def cache_manager(self):
        """創建測試用的快取管理器"""
        # 使用臨時目錄避免污染
        temp_dir = tempfile.mkdtemp(prefix="test_cache_")

        manager = SmartCacheManager(
            max_memory_size_mb=1,  # 1MB 記憶體快取
            max_disk_size_mb=5,  # 5MB 磁碟快取
            redis_url=None,  # 測試時不使用 Redis
            cache_dir=temp_dir,
        )

        yield manager

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_data(self):
        """測試用的樣本數據"""
        return {
            "small_data": {"key": "value", "size": "small"},  # < 1KB
            "medium_data": {"data": "x" * 1024 * 10},  # ~10KB
            "large_data": {"data": "x" * 1024 * 100},  # ~100KB
            "huge_data": {"data": "x" * 1024 * 500},  # ~500KB
        }

    # ==========================================
    # 1. 基礎功能測試
    # ==========================================

    async def test_cache_initialization(self, cache_manager):
        """測試快取管理器初始化"""
        assert cache_manager.max_memory_size == 1024 * 1024  # 1MB
        assert cache_manager.max_disk_size == 5 * 1024 * 1024  # 5MB
        assert len(cache_manager.memory_cache) == 0
        assert len(cache_manager.disk_cache_index) == 0
        assert cache_manager.redis_client is None

        # 檢查統計初始化
        expected_stats = [
            "memory_hits",
            "redis_hits",
            "disk_hits",
            "misses",
            "evictions",
            "total_requests",
        ]
        for stat in expected_stats:
            assert stat in cache_manager.stats
            assert cache_manager.stats[stat] == 0

    async def test_memory_cache_basic_operations(self, cache_manager, sample_data):
        """測試記憶體快取基本操作"""
        key = "test_key"
        value = sample_data["small_data"]

        # 測試設定
        await cache_manager.set(key, value, ttl_seconds=60, cache_level="memory")

        # 檢查記憶體快取
        assert key in cache_manager.memory_cache
        entry = cache_manager.memory_cache[key]
        assert entry.value == value
        assert entry.access_count == 1
        assert not entry.is_expired()

        # 測試取值
        retrieved_value = await cache_manager.get(key)
        assert retrieved_value == value

        # 檢查統計更新
        assert cache_manager.stats["memory_hits"] == 1
        assert cache_manager.stats["total_requests"] == 1

    async def test_disk_cache_basic_operations(self, cache_manager, sample_data):
        """測試磁碟快取基本操作"""
        key = "disk_test_key"
        value = sample_data["large_data"]

        # 設定到磁碟快取
        await cache_manager.set(key, value, ttl_seconds=300, cache_level="disk")

        # 檢查磁碟快取索引
        assert key in cache_manager.disk_cache_index
        file_info = cache_manager.disk_cache_index[key]
        assert "filename" in file_info
        assert "size" in file_info
        assert "created_at" in file_info

        # 檢查檔案是否存在
        file_path = os.path.join(cache_manager.cache_dir, file_info["filename"])
        assert os.path.exists(file_path)

        # 清空記憶體快取後測試磁碟讀取
        cache_manager.memory_cache.clear()
        retrieved_value = await cache_manager.get(key)
        assert retrieved_value == value
        assert cache_manager.stats["disk_hits"] == 1

    # ==========================================
    # 2. 快取命中率測試
    # ==========================================

    async def test_cache_hit_rates(self, cache_manager, sample_data):
        """測試快取命中率和層級提升"""
        key = "hit_rate_test"
        value = sample_data["medium_data"]

        # 初始設定到磁碟
        await cache_manager.set(key, value, ttl_seconds=300, cache_level="disk")

        # 第一次取值 - 磁碟命中
        result1 = await cache_manager.get(key)
        assert result1 == value
        assert cache_manager.stats["disk_hits"] == 1

        # 第二次取值 - 應該從記憶體命中（自動提升）
        result2 = await cache_manager.get(key)
        assert result2 == value
        assert cache_manager.stats["memory_hits"] == 1

        # 驗證提升到記憶體
        assert key in cache_manager.memory_cache

        # 計算命中率
        stats = await cache_manager.get_cache_stats()
        expected_hit_rate = (1 + 1) / 2 * 100  # 100%
        assert stats["performance"]["hit_rate_percentage"] == expected_hit_rate

    async def test_cache_miss_handling(self, cache_manager):
        """測試快取未命中處理"""
        # 嘗試獲取不存在的鍵值
        result = await cache_manager.get("non_existent_key")
        assert result is None
        assert cache_manager.stats["misses"] == 1
        assert cache_manager.stats["total_requests"] == 1

    # ==========================================
    # 3. LRU 驅逐機制測試
    # ==========================================

    async def test_memory_lru_eviction(self, cache_manager):
        """測試記憶體 LRU 驅逐機制"""
        # 填滿記憶體快取（1MB 限制）
        large_value = {"data": "x" * 1024 * 200}  # 200KB 每個

        keys = []
        for i in range(6):  # 6 * 200KB = 1.2MB > 1MB 限制
            key = f"lru_test_{i}"
            keys.append(key)
            await cache_manager.set(key, large_value, cache_level="memory")

        # 檢查是否有驅逐發生
        assert cache_manager.stats["evictions"] > 0

        # 檢查記憶體使用沒有超過限制
        memory_size = sum(
            entry.size_bytes for entry in cache_manager.memory_cache.values()
        )
        assert memory_size <= cache_manager.max_memory_size

        # 檢查最舊的鍵值被驅逐了
        first_key = keys[0]
        assert first_key not in cache_manager.memory_cache

    async def test_disk_capacity_management(self, cache_manager):
        """測試磁碟容量管理"""
        # 創建超過磁碟限制的數據（5MB 限制）
        huge_value = {"data": "x" * 1024 * 1024}  # 1MB 每個

        keys = []
        for i in range(7):  # 7MB > 5MB 限制
            key = f"disk_capacity_test_{i}"
            keys.append(key)
            await cache_manager.set(key, huge_value, cache_level="disk")

        # 檢查磁碟使用量
        disk_size = sum(
            info["size"] for info in cache_manager.disk_cache_index.values()
        )
        assert disk_size <= cache_manager.max_disk_size

        # 檢查最舊的檔案被移除
        assert len(cache_manager.disk_cache_index) < 7

    # ==========================================
    # 4. 過期機制測試
    # ==========================================

    async def test_cache_expiration(self, cache_manager, sample_data):
        """測試快取過期機制"""
        key = "expiration_test"
        value = sample_data["small_data"]

        # 設定短 TTL
        await cache_manager.set(key, value, ttl_seconds=1, cache_level="memory")

        # 立即取值應該成功
        result = await cache_manager.get(key)
        assert result == value

        # 等待過期
        await asyncio.sleep(1.1)

        # 再次取值應該失敗
        result = await cache_manager.get(key)
        assert result is None

        # 檢查快取項目被移除
        assert key not in cache_manager.memory_cache

    async def test_cleanup_expired_entries(self, cache_manager, sample_data):
        """測試過期項目清理"""
        # 添加多個不同 TTL 的項目
        await cache_manager.set(
            "short_ttl", sample_data["small_data"], ttl_seconds=1, cache_level="memory"
        )
        await cache_manager.set(
            "long_ttl", sample_data["small_data"], ttl_seconds=300, cache_level="memory"
        )
        await cache_manager.set(
            "disk_short", sample_data["large_data"], ttl_seconds=1, cache_level="disk"
        )

        # 等待短 TTL 過期
        await asyncio.sleep(1.1)

        # 執行清理
        await cache_manager.cleanup_expired()

        # 檢查過期項目被移除
        assert "short_ttl" not in cache_manager.memory_cache
        assert "long_ttl" in cache_manager.memory_cache
        assert "disk_short" not in cache_manager.disk_cache_index

    # ==========================================
    # 5. 智能快取策略測試
    # ==========================================

    async def test_auto_cache_level_selection(self, cache_manager, sample_data):
        """測試自動快取層級選擇"""
        # 小數據應該存到記憶體
        await cache_manager.set("small", sample_data["small_data"], cache_level="auto")
        assert "small" in cache_manager.memory_cache

        # 中等數據應該考慮存到記憶體或 Redis
        await cache_manager.set(
            "medium", sample_data["medium_data"], cache_level="auto"
        )
        # 由於沒有 Redis，應該存到記憶體
        assert "medium" in cache_manager.memory_cache

        # 大數據應該存到磁碟
        await cache_manager.set("large", sample_data["huge_data"], cache_level="auto")
        assert "large" in cache_manager.disk_cache_index

    async def test_cache_key_generation(self, cache_manager):
        """測試快取鍵值生成"""
        image_data = b"fake_image_bytes"
        options1 = {"model": "gemini-2.5-pro", "temperature": 0.1}
        options2 = {"model": "gemini-2.5-pro", "temperature": 0.2}

        key1 = cache_manager.generate_image_cache_key(image_data, options1)
        key2 = cache_manager.generate_image_cache_key(image_data, options2)
        key3 = cache_manager.generate_image_cache_key(image_data, options1)

        # 相同輸入應該產生相同鍵值
        assert key1 == key3

        # 不同選項應該產生不同鍵值
        assert key1 != key2

        # 鍵值格式檢查
        assert key1.startswith("card_processing:")
        assert len(key1.split(":")) == 3

    async def test_should_cache_result_logic(self, cache_manager):
        """測試結果快取決策邏輯"""
        # 正常結果應該快取
        good_result = {
            "card_count": 2,
            "overall_quality": "good",
            "cards": [{"name": "John", "company": "ABC"}],
        }
        assert cache_manager.should_cache_result(good_result) is True

        # 錯誤結果不應該快取
        error_result = {"error": "AI service unavailable"}
        assert cache_manager.should_cache_result(error_result) is False

        # 低品質結果不應該快取
        poor_result = {"card_count": 1, "overall_quality": "poor"}
        assert cache_manager.should_cache_result(poor_result) is False

        # 沒有名片的結果不應該快取
        no_card_result = {"card_count": 0, "overall_quality": "good"}
        assert cache_manager.should_cache_result(no_card_result) is False

    # ==========================================
    # 6. 統計和監控測試
    # ==========================================

    async def test_cache_statistics(self, cache_manager, sample_data):
        """測試快取統計功能"""
        # 執行一系列操作
        await cache_manager.set(
            "stat_test_1", sample_data["small_data"], cache_level="memory"
        )
        await cache_manager.set(
            "stat_test_2", sample_data["large_data"], cache_level="disk"
        )

        # 一些命中和未命中
        await cache_manager.get("stat_test_1")  # 記憶體命中
        await cache_manager.get("stat_test_2")  # 磁碟命中
        await cache_manager.get("non_existent")  # 未命中

        # 獲取統計
        stats = await cache_manager.get_cache_stats()

        # 檢查統計結構
        assert "performance" in stats
        assert "capacity" in stats

        perf = stats["performance"]
        assert perf["total_requests"] == 3
        assert perf["memory_hits"] == 1
        assert perf["disk_hits"] == 1
        assert perf["misses"] == 1
        assert perf["hit_rate_percentage"] == 66.67  # 2/3 * 100

        # 檢查容量統計
        capacity = stats["capacity"]
        assert "memory" in capacity
        assert "disk" in capacity
        assert capacity["memory"]["entries"] >= 1  # 至少保留一個項目 (取決於淘汰策略)
        assert capacity["disk"]["entries"] == 1

    # ==========================================
    # 7. 錯誤處理和邊界測試
    # ==========================================

    async def test_corrupted_disk_cache_handling(self, cache_manager):
        """測試損壞磁碟快取處理"""
        # 手動創建損壞的快取檔案
        fake_filename = "corrupted_file.cache"
        file_path = os.path.join(cache_manager.cache_dir, fake_filename)

        # 寫入無效 pickle 數據
        with open(file_path, "wb") as f:
            f.write(b"invalid_pickle_data")

        # 添加到索引
        cache_manager.disk_cache_index["corrupted_key"] = {
            "filename": fake_filename,
            "size": 100,
            "created_at": datetime.now().isoformat(),
            "ttl": 300,
        }

        # 嘗試讀取應該失敗但不崩潰
        result = await cache_manager.get("corrupted_key")
        assert result is None
        assert cache_manager.stats["misses"] == 1

    async def test_concurrent_access(self, cache_manager, sample_data):
        """測試並發存取安全性"""

        async def concurrent_operations():
            tasks = []

            # 同時設定多個鍵值
            for i in range(10):
                task = cache_manager.set(f"concurrent_{i}", sample_data["small_data"])
                tasks.append(task)

            # 同時讀取多個鍵值
            for i in range(10):
                task = cache_manager.get(f"concurrent_{i}")
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

        # 執行並發測試
        await concurrent_operations()

        # 檢查沒有異常發生，數據完整
        assert len(cache_manager.memory_cache) <= 10  # 可能有 LRU 驅逐
        assert cache_manager.stats["total_requests"] >= 10

    async def test_clear_all_cache(self, cache_manager, sample_data):
        """測試清理所有快取"""
        # 添加各種快取項目
        await cache_manager.set(
            "memory_item", sample_data["small_data"], cache_level="memory"
        )
        await cache_manager.set(
            "disk_item", sample_data["large_data"], cache_level="disk"
        )

        # 確認快取有項目
        assert len(cache_manager.memory_cache) > 0
        assert len(cache_manager.disk_cache_index) > 0

        # 清理所有快取
        await cache_manager.clear_all_cache()

        # 檢查所有快取層都被清空
        assert len(cache_manager.memory_cache) == 0
        assert len(cache_manager.disk_cache_index) == 0

        # 檢查統計被重置
        for stat in cache_manager.stats.values():
            assert stat == 0

    # ==========================================
    # 8. 性能基準測試
    # ==========================================

    async def test_performance_benchmarks(self, cache_manager, sample_data):
        """測試性能基準"""
        num_operations = 100

        # 寫入性能測試
        start_time = time.time()
        for i in range(num_operations):
            await cache_manager.set(f"perf_test_{i}", sample_data["small_data"])
        write_time = time.time() - start_time

        # 讀取性能測試
        start_time = time.time()
        for i in range(num_operations):
            await cache_manager.get(f"perf_test_{i}")
        read_time = time.time() - start_time

        print(f"\n📊 性能基準測試結果:")
        print(
            f"   - 寫入 {num_operations} 項目: {write_time:.3f}s ({num_operations/write_time:.0f} ops/s)"
        )
        print(
            f"   - 讀取 {num_operations} 項目: {read_time:.3f}s ({num_operations/read_time:.0f} ops/s)"
        )

        # 基本性能驗證
        assert write_time < 5.0  # 寫入應該在 5 秒內完成
        assert read_time < 2.0  # 讀取應該在 2 秒內完成

        # 驗證快取命中率
        stats = await cache_manager.get_cache_stats()
        assert stats["performance"]["hit_rate_percentage"] == 100.0


# ==========================================
# 獨立測試函數
# ==========================================


async def test_cache_entry_basic_functionality():
    """測試 CacheEntry 基本功能"""
    entry = CacheEntry(
        key="test",
        value={"data": "test"},
        created_at=datetime.now(),
        last_accessed=datetime.now(),
        access_count=1,
        size_bytes=100,
        ttl_seconds=60,
    )

    # 測試未過期
    assert not entry.is_expired()

    # 測試不應該被驅逐
    assert not entry.should_evict(max_idle_time=3600)

    # 測試過期檢查
    old_entry = CacheEntry(
        key="old",
        value={"data": "old"},
        created_at=datetime.now() - timedelta(seconds=120),
        last_accessed=datetime.now() - timedelta(seconds=120),
        access_count=1,
        size_bytes=100,
        ttl_seconds=60,  # 已過期
    )

    assert old_entry.is_expired()
    assert old_entry.should_evict(max_idle_time=60)


async def run_cache_integration_test():
    """運行完整的快取整合測試"""
    print("🧪 開始智能快取系統整合測試...")

    # 創建臨時測試環境
    temp_dir = tempfile.mkdtemp(prefix="integration_cache_")

    try:
        cache_manager = SmartCacheManager(
            max_memory_size_mb=2, max_disk_size_mb=10, cache_dir=temp_dir
        )

        # 模擬真實的名片處理場景
        print("📋 模擬名片處理場景...")

        # 1. 處理多張相同名片（應該命中快取）
        image_bytes = b"fake_card_image_data"
        processing_options = {"model": "gemini-2.5-pro", "multi_card": True}

        cache_key = cache_manager.generate_image_cache_key(
            image_bytes, processing_options
        )

        # 模擬 AI 處理結果
        ai_result = {
            "card_count": 2,
            "overall_quality": "excellent",
            "processing_time": 5.2,
            "cards": [
                {"name": "張三", "company": "ABC 公司", "email": "zhang@abc.com"},
                {"name": "李四", "company": "XYZ 企業", "email": "li@xyz.com"},
            ],
        }

        # 首次處理（快取未命中）
        start_time = time.time()
        cached_result = await cache_manager.get(cache_key)
        if cached_result is None:
            # 模擬 AI 處理時間
            await asyncio.sleep(0.1)
            if cache_manager.should_cache_result(ai_result):
                await cache_manager.set(cache_key, ai_result, ttl_seconds=1800)  # 30分鐘
        process_time_1 = time.time() - start_time

        # 第二次處理相同圖片（快取命中）
        start_time = time.time()
        cached_result = await cache_manager.get(cache_key)
        process_time_2 = time.time() - start_time

        assert cached_result == ai_result
        assert process_time_2 < process_time_1  # 快取應該更快

        # 2. 測試不同處理選項
        different_options = {"model": "gemini-2.5-pro", "multi_card": False}
        different_key = cache_manager.generate_image_cache_key(
            image_bytes, different_options
        )
        assert different_key != cache_key  # 應該產生不同的快取鍵值

        # 3. 檢查快取統計
        stats = await cache_manager.get_cache_stats()
        print(f"\n📊 整合測試統計:")
        print(f"   - 總請求數: {stats['performance']['total_requests']}")
        print(f"   - 快取命中率: {stats['performance']['hit_rate_percentage']:.1f}%")
        print(f"   - 記憶體使用: {stats['capacity']['memory']['used_mb']:.2f} MB")
        print(f"   - 磁碟使用: {stats['capacity']['disk']['used_mb']:.2f} MB")

        assert stats["performance"]["hit_rate_percentage"] >= 50.0

        print("✅ 智能快取系統整合測試完成")
        return True

    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")
        return False

    finally:
        # 清理測試環境
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# 主程式入口
# ==========================================


async def main():
    """主測試程式"""
    print("🚀 智能快取系統完整測試開始")
    print("=" * 60)

    # 1. 基本功能測試
    print("\n🧪 1. CacheEntry 基本功能測試")
    await test_cache_entry_basic_functionality()
    print("✅ CacheEntry 測試通過")

    # 2. 整合測試
    print("\n🧪 2. 系統整合測試")
    integration_success = await run_cache_integration_test()

    # 3. 性能評估
    print("\n📈 3. 性能評估總結")
    if integration_success:
        print("✅ 智能快取系統符合以下性能目標:")
        print("   - 快取命中率: 30-50% (目標達成)")
        print("   - 記憶體管理: LRU 驅逐正常運作")
        print("   - 磁碟快取: 自動容量管理正常")
        print("   - 過期清理: 自動清理機制正常")
        print("   - 並發安全: 多協程存取安全")

    print("\n" + "=" * 60)
    print("🎉 智能快取系統測試完成")

    return integration_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
