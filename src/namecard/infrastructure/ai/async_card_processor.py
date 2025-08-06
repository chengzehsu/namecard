"""
異步名片處理器 - 支援高並發、智能快取和效能監控
"""

import asyncio
import hashlib
import io
import json
import os
import sys
import time
import weakref
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from PIL import Image

# 添加專案根目錄到 path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 簡化的配置類
class SimpleConfig:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_API_KEY_FALLBACK = os.getenv("GOOGLE_API_KEY_FALLBACK", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


Config = SimpleConfig

# 匯入地址正規化器
try:
    from src.namecard.core.services.address_service import AddressNormalizer
except ImportError:
    # 簡化版地址正規化器
    class AddressNormalizer:
        def normalize_address(self, address: str) -> dict:
            return {
                "normalized": address,
                "original": address,
                "confidence": 0.8,
                "warnings": [],
            }


class ProcessingPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ProcessingMetadata:
    """處理元數據類別"""

    def __init__(self):
        self.start_time = time.time()
        self.cache_hit = False
        self.api_key_used = None
        self.processing_duration = 0.0
        self.queue_time = 0.0
        self.confidence_score = 0.0
        self.retry_count = 0
        self.memory_usage_mb = 0.0


class AsyncCardProcessor:
    """異步名片處理器，支援高並發和智能優化"""

    def __init__(self, max_concurrent: int = 10, enable_cache: bool = True):
        """
        初始化異步名片處理器

        Args:
            max_concurrent: 最大並發處理數量
            enable_cache: 是否啟用快取
        """
        self.max_concurrent = max_concurrent
        self.enable_cache = enable_cache

        # 並發控制
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks = weakref.WeakSet()

        # API 金鑰管理
        self.api_keys = [Config.GOOGLE_API_KEY, Config.GOOGLE_API_KEY_FALLBACK]
        self.current_key_index = 0
        self.api_quota_status = {}

        # 快取系統
        self.memory_cache = {} if enable_cache else None
        self.cache_hits = 0
        self.cache_misses = 0

        # 效能監控
        self.processing_stats = {
            "total_processed": 0,
            "total_errors": 0,
            "avg_processing_time": 0.0,
            "concurrent_peak": 0,
        }

        # 地址正規化器
        self.address_normalizer = AddressNormalizer()

        # 優化的 prompt
        self.optimized_prompt = self._create_optimized_prompt()

    def _create_optimized_prompt(self) -> str:
        """創建優化的 prompt，減少 token 數量提升效能"""
        return """
Extract namecard info. Return JSON only:

{
  "card_count": number,
  "cards": [{
    "card_index": 1,
    "confidence_score": 0.0-1.0,
    "name": "string",
    "company": "string", 
    "department": "string",
    "title": "string",
    "decision_influence": "高|中|低",
    "email": "string",
    "phone": "string",
    "address": "string",
    "contact_source": "名片交換",
    "notes": "string"
  }],
  "overall_quality": "good|partial|poor"
}

Rules:
- Use null for missing fields
- Phone format: +886XXXXXXXXX 
- decision_influence: 總經理/CEO/董事長="高", 經理/主管="中", 其他="低"
- confidence_score based on text clarity
"""

    async def process_image_async(
        self,
        image_bytes: bytes,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        user_id: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        timeout: float = 30.0,
    ) -> Tuple[Dict[str, Any], ProcessingMetadata]:
        """
        異步處理名片圖片

        Args:
            image_bytes: 圖片二進制數據
            priority: 處理優先級
            user_id: 用戶ID（用於快取和監控）
            enable_cache: 是否啟用快取（覆蓋全局設定）
            timeout: 處理超時時間（秒）

        Returns:
            Tuple[處理結果, 處理元數據]
        """
        metadata = ProcessingMetadata()

        # 檢查快取
        use_cache = enable_cache if enable_cache is not None else self.enable_cache
        cache_key = None

        if use_cache and image_bytes:
            cache_key = self._generate_cache_key(image_bytes)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                metadata.cache_hit = True
                metadata.processing_duration = time.time() - metadata.start_time
                self.cache_hits += 1
                return cached_result, metadata

        self.cache_misses += 1

        # 並發控制
        async with self.semaphore:
            try:
                # 更新並發統計
                current_concurrent = len(self.active_tasks) + 1
                if current_concurrent > self.processing_stats["concurrent_peak"]:
                    self.processing_stats["concurrent_peak"] = current_concurrent

                # 創建處理任務
                task = asyncio.create_task(
                    self._process_with_timeout(image_bytes, timeout, metadata)
                )
                self.active_tasks.add(task)

                result = await task

                # 快取結果
                if use_cache and cache_key and result.get("card_count", 0) > 0:
                    self._store_in_cache(cache_key, result)

                # 更新統計
                self._update_processing_stats(metadata)

                return result, metadata

            except asyncio.TimeoutError:
                return {"error": f"處理超時（{timeout}秒）"}, metadata
            except Exception as e:
                self.processing_stats["total_errors"] += 1
                return {"error": f"處理失敗: {str(e)}"}, metadata
            finally:
                metadata.processing_duration = time.time() - metadata.start_time

    async def _process_with_timeout(
        self, image_bytes: bytes, timeout: float, metadata: ProcessingMetadata
    ) -> Dict[str, Any]:
        """帶超時的實際處理邏輯"""
        return await asyncio.wait_for(
            self._process_image_core(image_bytes, metadata), timeout=timeout
        )

    async def _process_image_core(
        self, image_bytes: bytes, metadata: ProcessingMetadata
    ) -> Dict[str, Any]:
        """核心圖片處理邏輯"""
        try:
            # 轉換圖片格式（異步）
            img_pil = await self._convert_image_async(image_bytes)

            # 選擇可用的 API 金鑰
            api_key = await self._get_available_api_key()
            metadata.api_key_used = api_key

            # 配置 Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(Config.GEMINI_MODEL)

            # 發送請求到 Gemini（使用優化 prompt）
            response = await self._call_gemini_async(model, img_pil)

            # 解析回應
            result = await self._parse_response_async(response)

            # 地址正規化
            if result.get("cards"):
                for card in result["cards"]:
                    if card.get("address"):
                        await self._normalize_address_async(card)

            # 計算信心度
            metadata.confidence_score = self._calculate_overall_confidence(result)

            return result

        except Exception as e:
            metadata.retry_count += 1
            raise e

    async def _convert_image_async(self, image_bytes: bytes) -> Image.Image:
        """異步圖片轉換"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: Image.open(io.BytesIO(image_bytes))
        )

    async def _call_gemini_async(self, model, img_pil: Image.Image) -> str:
        """異步呼叫 Gemini API"""
        loop = asyncio.get_event_loop()

        def call_gemini():
            response = model.generate_content([self.optimized_prompt, img_pil])
            return response.text.strip()

        return await loop.run_in_executor(None, call_gemini)

    async def _parse_response_async(self, raw_response: str) -> Dict[str, Any]:
        """異步解析 Gemini 回應"""
        loop = asyncio.get_event_loop()

        def parse_json():
            # 清理回應
            cleaned = raw_response
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            return json.loads(cleaned.strip())

        return await loop.run_in_executor(None, parse_json)

    async def _normalize_address_async(self, card: Dict[str, Any]):
        """異步地址正規化"""
        loop = asyncio.get_event_loop()

        def normalize():
            result = self.address_normalizer.normalize_address(card["address"])
            card["address"] = result["normalized"]
            if result["warnings"]:
                warnings_text = f"地址處理警告: {', '.join(result['warnings'])}"
                current_notes = card.get("notes", "")
                card["notes"] = (
                    f"{current_notes}; {warnings_text}"
                    if current_notes
                    else warnings_text
                )
            card["_address_confidence"] = result["confidence"]
            card["_original_address"] = result["original"]

        await loop.run_in_executor(None, normalize)

    async def _get_available_api_key(self) -> str:
        """獲取可用的 API 金鑰"""
        for i in range(len(self.api_keys)):
            key_index = (self.current_key_index + i) % len(self.api_keys)
            api_key = self.api_keys[key_index]

            if api_key and not self.api_quota_status.get(api_key, {}).get(
                "exhausted", False
            ):
                self.current_key_index = key_index
                return api_key

        raise Exception("所有 API 金鑰都不可用")

    def _generate_cache_key(self, image_bytes: bytes) -> str:
        """生成快取鍵值"""
        return hashlib.md5(image_bytes).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """從快取獲取結果"""
        if not self.memory_cache:
            return None
        return self.memory_cache.get(cache_key)

    def _store_in_cache(self, cache_key: str, result: Dict[str, Any]):
        """存儲結果到快取"""
        if not self.memory_cache:
            return

        # 簡單的 LRU 快取（限制大小）
        if len(self.memory_cache) > 100:
            # 移除最舊的 20% 項目
            keys_to_remove = list(self.memory_cache.keys())[:20]
            for key in keys_to_remove:
                del self.memory_cache[key]

        self.memory_cache[cache_key] = result

    def _calculate_overall_confidence(self, result: Dict[str, Any]) -> float:
        """計算整體信心度"""
        cards = result.get("cards", [])
        if not cards:
            return 0.0

        total_confidence = sum(card.get("confidence_score", 0.5) for card in cards)
        return total_confidence / len(cards)

    def _update_processing_stats(self, metadata: ProcessingMetadata):
        """更新處理統計"""
        self.processing_stats["total_processed"] += 1

        # 更新平均處理時間
        current_avg = self.processing_stats["avg_processing_time"]
        new_avg = (
            current_avg * (self.processing_stats["total_processed"] - 1)
            + metadata.processing_duration
        ) / self.processing_stats["total_processed"]
        self.processing_stats["avg_processing_time"] = new_avg

    async def get_performance_stats(self) -> Dict[str, Any]:
        """獲取效能統計"""
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0.0
        )

        return {
            **self.processing_stats,
            "cache_hit_rate": cache_hit_rate,
            "active_tasks": len(self.active_tasks),
            "api_quota_status": self.api_quota_status,
            "memory_cache_size": len(self.memory_cache) if self.memory_cache else 0,
        }

    async def clear_cache(self):
        """清除快取"""
        if self.memory_cache:
            self.memory_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            # 檢查 API 金鑰可用性
            available_keys = sum(
                1
                for key in self.api_keys
                if key
                and not self.api_quota_status.get(key, {}).get("exhausted", False)
            )

            # 檢查系統負載
            current_load = len(self.active_tasks) / self.max_concurrent

            status = "healthy"
            if available_keys == 0:
                status = "critical"
            elif current_load > 0.8:
                status = "warning"

            return {
                "status": status,
                "available_api_keys": available_keys,
                "current_load": current_load,
                "cache_enabled": self.enable_cache,
                "max_concurrent": self.max_concurrent,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}
