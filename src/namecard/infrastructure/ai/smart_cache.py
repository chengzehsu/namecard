"""
智能快取系統 - AI Engineer 實作
針對 AI 圖片處理結果的多層次快取策略
"""

import asyncio
import hashlib
import io
import json
import os
import pickle
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import redis.asyncio as redis
from PIL import Image


@dataclass
class CacheEntry:
    """快取條目"""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: int

    def is_expired(self) -> bool:
        """檢查是否過期"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

    def should_evict(self, max_idle_time: int = 3600) -> bool:
        """檢查是否應該被驅逐"""
        idle_time = (datetime.now() - self.last_accessed).total_seconds()
        return idle_time > max_idle_time


class SmartCacheManager:
    """智能快取管理器 - 多層次快取策略"""

    def __init__(
        self,
        max_memory_size_mb: int = 100,
        max_disk_size_mb: int = 500,
        redis_url: Optional[str] = None,
        cache_dir: str = "./cache",
    ):
        """
        初始化智能快取管理器

        Args:
            max_memory_size_mb: 記憶體快取最大大小（MB）
            max_disk_size_mb: 磁碟快取最大大小（MB）
            redis_url: Redis 連接 URL（可選）
            cache_dir: 磁碟快取目錄
        """
        self.max_memory_size = max_memory_size_mb * 1024 * 1024  # 轉換為位元組
        self.max_disk_size = max_disk_size_mb * 1024 * 1024
        self.cache_dir = cache_dir

        # 三層快取架構
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.redis_client: Optional[redis.Redis] = None
        self.disk_cache_index: Dict[str, Dict[str, Any]] = {}

        # 統計資訊
        self.stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "disk_hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0,
        }

        # 初始化快取層
        self._init_cache_layers()

        print(f"✅ 智能快取管理器初始化完成")
        print(f"   - 記憶體快取: {max_memory_size_mb} MB")
        print(f"   - 磁碟快取: {max_disk_size_mb} MB")
        print(f"   - Redis: {'啟用' if redis_url else '停用'}")

    def _init_cache_layers(self):
        """初始化快取層"""
        # 建立磁碟快取目錄
        os.makedirs(self.cache_dir, exist_ok=True)

        # 載入磁碟快取索引
        asyncio.create_task(self._load_disk_cache_index())

        # 嘗試連接 Redis
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                print("✅ Redis 快取層已啟用")
            except Exception as e:
                print(f"⚠️ Redis 連接失敗: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值 - 智能三層快取查找

        Args:
            key: 快取鍵值

        Returns:
            快取值或 None
        """
        self.stats["total_requests"] += 1

        # 層級 1：記憶體快取（最快）
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired():
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                # 移到最前面（LRU）
                self.memory_cache.move_to_end(key, last=False)
                self.stats["memory_hits"] += 1
                return entry.value
            else:
                # 過期了，移除
                del self.memory_cache[key]

        # 層級 2：Redis 快取（中等速度）
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    value = pickle.loads(cached_data)
                    # 提升到記憶體快取
                    await self._promote_to_memory(key, value, ttl_seconds=3600)
                    self.stats["redis_hits"] += 1
                    return value
            except Exception as e:
                print(f"⚠️ Redis 讀取錯誤: {e}")

        # 層級 3：磁碟快取（較慢但容量大）
        if key in self.disk_cache_index:
            file_info = self.disk_cache_index[key]
            file_path = os.path.join(self.cache_dir, file_info["filename"])

            if os.path.exists(file_path):
                try:
                    # 檢查是否過期
                    created_at = datetime.fromisoformat(file_info["created_at"])
                    if datetime.now() < created_at + timedelta(
                        seconds=file_info["ttl"]
                    ):
                        async with aiofiles.open(file_path, "rb") as f:
                            content = await f.read()
                            value = pickle.loads(content)

                        # 提升到上層快取
                        await self._promote_to_redis(key, value, file_info["ttl"])
                        await self._promote_to_memory(key, value, file_info["ttl"])

                        self.stats["disk_hits"] += 1
                        return value
                    else:
                        # 過期，清理
                        await self._remove_from_disk(key)
                except Exception as e:
                    print(f"⚠️ 磁碟快取讀取錯誤: {e}")

        self.stats["misses"] += 1
        return None

    async def set(
        self, key: str, value: Any, ttl_seconds: int = 3600, cache_level: str = "auto"
    ):
        """
        設定快取值 - 智能存儲策略

        Args:
            key: 快取鍵值
            value: 快取值
            ttl_seconds: 生存時間（秒）
            cache_level: 快取層級 (auto/memory/redis/disk)
        """
        # 計算值的大小
        value_size = len(pickle.dumps(value))

        if cache_level == "auto":
            # 自動決定最適合的快取層級
            if value_size < 1024 * 50:  # < 50KB，存到記憶體
                cache_level = "memory"
            elif value_size < 1024 * 500:  # < 500KB，存到 Redis
                cache_level = "redis"
            else:  # >= 500KB，存到磁碟
                cache_level = "disk"

        # 根據策略存儲
        if cache_level == "memory" or cache_level == "auto":
            await self._set_memory(key, value, ttl_seconds, value_size)

        if cache_level == "redis" and self.redis_client:
            await self._set_redis(key, value, ttl_seconds)

        if cache_level == "disk":
            await self._set_disk(key, value, ttl_seconds, value_size)

    async def _set_memory(self, key: str, value: Any, ttl: int, size: int):
        """設定記憶體快取"""
        # 檢查記憶體容量
        await self._ensure_memory_capacity(size)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=size,
            ttl_seconds=ttl,
        )

        self.memory_cache[key] = entry
        # 新項目放到最前面
        self.memory_cache.move_to_end(key, last=False)

    async def _set_redis(self, key: str, value: Any, ttl: int):
        """設定 Redis 快取"""
        if not self.redis_client:
            return

        try:
            serialized = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"⚠️ Redis 寫入錯誤: {e}")

    async def _set_disk(self, key: str, value: Any, ttl: int, size: int):
        """設定磁碟快取"""
        # 檢查磁碟容量
        await self._ensure_disk_capacity(size)

        filename = f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        file_path = os.path.join(self.cache_dir, filename)

        try:
            serialized = pickle.dumps(value)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(serialized)

            # 更新索引
            self.disk_cache_index[key] = {
                "filename": filename,
                "size": size,
                "created_at": datetime.now().isoformat(),
                "ttl": ttl,
            }

            await self._save_disk_cache_index()

        except Exception as e:
            print(f"⚠️ 磁碟快取寫入錯誤: {e}")

    async def _promote_to_memory(self, key: str, value: Any, ttl_seconds: int):
        """提升到記憶體快取"""
        value_size = len(pickle.dumps(value))
        if value_size < 1024 * 100:  # 只有小於 100KB 的才提升到記憶體
            await self._set_memory(key, value, ttl_seconds, value_size)

    async def _promote_to_redis(self, key: str, value: Any, ttl_seconds: int):
        """提升到 Redis 快取"""
        if self.redis_client:
            await self._set_redis(key, value, ttl_seconds)

    async def _ensure_memory_capacity(self, needed_size: int):
        """確保記憶體容量足夠"""
        current_size = sum(entry.size_bytes for entry in self.memory_cache.values())

        while current_size + needed_size > self.max_memory_size and self.memory_cache:
            # LRU 驅逐：移除最久未使用的項目
            oldest_key = next(reversed(self.memory_cache))
            evicted_entry = self.memory_cache.pop(oldest_key)
            current_size -= evicted_entry.size_bytes
            self.stats["evictions"] += 1

    async def _ensure_disk_capacity(self, needed_size: int):
        """確保磁碟容量足夠"""
        current_size = sum(info["size"] for info in self.disk_cache_index.values())

        while current_size + needed_size > self.max_disk_size and self.disk_cache_index:
            # 找到最舊的檔案並移除
            oldest_key = min(
                self.disk_cache_index.keys(),
                key=lambda k: self.disk_cache_index[k]["created_at"],
            )
            await self._remove_from_disk(oldest_key)
            current_size = sum(info["size"] for info in self.disk_cache_index.values())

    async def _remove_from_disk(self, key: str):
        """從磁碟移除快取項目"""
        if key not in self.disk_cache_index:
            return

        file_info = self.disk_cache_index[key]
        file_path = os.path.join(self.cache_dir, file_info["filename"])

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            del self.disk_cache_index[key]
            await self._save_disk_cache_index()
        except Exception as e:
            print(f"⚠️ 移除磁碟快取錯誤: {e}")

    async def _load_disk_cache_index(self):
        """載入磁碟快取索引"""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        try:
            if os.path.exists(index_file):
                async with aiofiles.open(index_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    self.disk_cache_index = json.loads(content)
                print(f"✅ 載入磁碟快取索引: {len(self.disk_cache_index)} 項目")
        except Exception as e:
            print(f"⚠️ 載入磁碟快取索引失敗: {e}")
            self.disk_cache_index = {}

    async def _save_disk_cache_index(self):
        """儲存磁碟快取索引"""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        try:
            async with aiofiles.open(index_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(self.disk_cache_index, indent=2, ensure_ascii=False)
                )
        except Exception as e:
            print(f"⚠️ 儲存磁碟快取索引失敗: {e}")

    def generate_image_cache_key(
        self, image_bytes: bytes, processing_options: Dict[str, Any] = None
    ) -> str:
        """
        生成圖片快取鍵值 - 考慮圖片內容和處理選項

        Args:
            image_bytes: 圖片位元組資料
            processing_options: 處理選項

        Returns:
            快取鍵值
        """
        # 圖片內容雜湊
        image_hash = hashlib.md5(image_bytes).hexdigest()

        # 處理選項雜湊
        options_str = json.dumps(processing_options or {}, sort_keys=True)
        options_hash = hashlib.md5(options_str.encode()).hexdigest()

        return f"card_processing:{image_hash}:{options_hash}"

    def should_cache_result(self, result: Dict[str, Any]) -> bool:
        """
        判斷結果是否應該被快取

        Args:
            result: 處理結果

        Returns:
            是否應該快取
        """
        # 不快取錯誤結果
        if "error" in result:
            return False

        # 不快取低品質結果
        if result.get("overall_quality") == "poor":
            return False

        # 不快取沒有卡片的結果
        if result.get("card_count", 0) == 0:
            return False

        return True

    async def get_cache_stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        memory_size = sum(entry.size_bytes for entry in self.memory_cache.values())
        disk_size = sum(info["size"] for info in self.disk_cache_index.values())

        # Redis 統計
        redis_stats = {}
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
                redis_stats = {
                    "used_memory": redis_info.get("used_memory", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "N/A"),
                }
            except:
                redis_stats = {"error": "Unable to get Redis stats"}

        total_requests = self.stats["total_requests"]
        hit_rate = (
            (
                self.stats["memory_hits"]
                + self.stats["redis_hits"]
                + self.stats["disk_hits"]
            )
            / max(total_requests, 1)
            * 100
        )

        return {
            "performance": {
                "total_requests": total_requests,
                "hit_rate_percentage": round(hit_rate, 2),
                "memory_hits": self.stats["memory_hits"],
                "redis_hits": self.stats["redis_hits"],
                "disk_hits": self.stats["disk_hits"],
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
            },
            "capacity": {
                "memory": {
                    "used_bytes": memory_size,
                    "used_mb": round(memory_size / 1024 / 1024, 2),
                    "max_mb": round(self.max_memory_size / 1024 / 1024),
                    "usage_percentage": round(
                        memory_size / self.max_memory_size * 100, 2
                    ),
                    "entries": len(self.memory_cache),
                },
                "disk": {
                    "used_bytes": disk_size,
                    "used_mb": round(disk_size / 1024 / 1024, 2),
                    "max_mb": round(self.max_disk_size / 1024 / 1024),
                    "usage_percentage": round(disk_size / self.max_disk_size * 100, 2),
                    "entries": len(self.disk_cache_index),
                },
                "redis": redis_stats,
            },
        }

    async def cleanup_expired(self):
        """清理過期快取項目"""
        # 清理記憶體快取
        expired_keys = [
            key
            for key, entry in self.memory_cache.items()
            if entry.is_expired() or entry.should_evict()
        ]
        for key in expired_keys:
            del self.memory_cache[key]

        # 清理磁碟快取
        disk_expired = []
        for key, info in self.disk_cache_index.items():
            created_at = datetime.fromisoformat(info["created_at"])
            if datetime.now() > created_at + timedelta(seconds=info["ttl"]):
                disk_expired.append(key)

        for key in disk_expired:
            await self._remove_from_disk(key)

        if expired_keys or disk_expired:
            print(
                f"🧹 清理過期快取: 記憶體 {len(expired_keys)} 項，磁碟 {len(disk_expired)} 項"
            )

    async def clear_all_cache(self):
        """清理所有快取"""
        # 清理記憶體
        self.memory_cache.clear()

        # 清理 Redis
        if self.redis_client:
            try:
                # 只清理我們的 keys（以 card_processing: 開頭）
                keys = await self.redis_client.keys("card_processing:*")
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                print(f"⚠️ 清理 Redis 快取錯誤: {e}")

        # 清理磁碟
        for key in list(self.disk_cache_index.keys()):
            await self._remove_from_disk(key)

        # 重置統計
        self.stats = {k: 0 for k in self.stats}

        print("🧹 已清理所有快取層")
