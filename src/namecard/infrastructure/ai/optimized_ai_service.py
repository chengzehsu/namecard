"""
優化 AI 服務 - 統一的高效能名片處理服務
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.namecard.core.services.async_batch_service import AsyncBatchService
from src.namecard.infrastructure.ai.async_card_processor import (
    AsyncCardProcessor,
    ProcessingMetadata,
    ProcessingPriority,
)
from src.namecard.infrastructure.storage.async_notion_client import AsyncNotionManager


class OptimizedAIService:
    """
    優化 AI 服務 - 整合異步處理、批次處理和智能快取
    提供生產級別的高效能名片處理能力
    """

    def __init__(
        self,
        max_concurrent_ai: int = 15,
        max_concurrent_notion: int = 10,
        max_global_concurrent: int = 50,
        enable_cache: bool = True,
        auto_notion_save: bool = True,
    ):
        """
        初始化優化 AI 服務

        Args:
            max_concurrent_ai: AI 處理最大並發數
            max_concurrent_notion: Notion 寫入最大並發數
            max_global_concurrent: 全局最大並發數
            enable_cache: 是否啟用快取
            auto_notion_save: 是否自動保存到 Notion
        """
        # 初始化核心組件
        self.card_processor = AsyncCardProcessor(
            max_concurrent=max_concurrent_ai, enable_cache=enable_cache
        )

        self.batch_service = AsyncBatchService(
            card_processor=self.card_processor,
            max_global_concurrent=max_global_concurrent,
        )

        self.notion_manager = AsyncNotionManager(max_concurrent=max_concurrent_notion)

        self.auto_notion_save = auto_notion_save

        # 服務狀態
        self.is_running = False
        self.start_time = None

        # 統計資訊
        self.service_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "cache_hit_rate": 0.0,
            "notion_save_rate": 0.0,
        }

    async def start(self):
        """啟動服務"""
        self.is_running = True
        self.start_time = datetime.now()
        print("🚀 優化 AI 服務已啟動")

    async def stop(self):
        """停止服務"""
        self.is_running = False
        await self.batch_service.shutdown()
        print("⏹️ 優化 AI 服務已停止")

    async def process_image(
        self,
        image_bytes: bytes,
        user_id: str,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        enable_cache: Optional[bool] = None,
        save_to_notion: Optional[bool] = None,
        timeout: float = 30.0,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        處理單張圖片

        Args:
            image_bytes: 圖片二進制數據
            user_id: 用戶ID
            priority: 處理優先級
            enable_cache: 是否啟用快取
            save_to_notion: 是否保存到 Notion
            timeout: 處理超時時間

        Returns:
            Tuple[處理結果, 元數據]
        """
        start_time = time.time()
        self.service_stats["total_requests"] += 1

        try:
            # AI 處理
            result, ai_metadata = await self.card_processor.process_image_async(
                image_bytes=image_bytes,
                priority=priority,
                user_id=user_id,
                enable_cache=enable_cache,
                timeout=timeout,
            )

            # 檢查是否需要保存到 Notion
            should_save = (
                save_to_notion if save_to_notion is not None else self.auto_notion_save
            )
            notion_results = []

            if should_save and not result.get("error") and result.get("cards"):
                notion_results = await self._save_cards_to_notion(
                    result["cards"], image_bytes
                )

            # 組合最終結果
            final_result = {
                **result,
                "notion_results": notion_results if notion_results else None,
            }

            # 建構元數據
            processing_time = time.time() - start_time
            metadata = {
                "processing_time": processing_time,
                "user_id": user_id,
                "cache_hit": ai_metadata.cache_hit,
                "api_key_used": ai_metadata.api_key_used,
                "confidence_score": ai_metadata.confidence_score,
                "notion_saved": len(notion_results) if notion_results else 0,
                "priority": priority.name,
                "timestamp": datetime.now().isoformat(),
            }

            # 更新統計
            self._update_service_stats(
                processing_time, True, ai_metadata.cache_hit, len(notion_results) > 0
            )

            return final_result, metadata

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_service_stats(processing_time, False, False, False)

            error_result = {"error": f"處理失敗: {str(e)}"}
            error_metadata = {
                "processing_time": processing_time,
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            return error_result, error_metadata

    async def process_batch(
        self,
        image_batch: List[bytes],
        user_id: str,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        max_concurrent: Optional[int] = None,
        save_to_notion: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        批次處理多張圖片

        Args:
            image_batch: 圖片數據列表
            user_id: 用戶ID
            priority: 處理優先級
            max_concurrent: 最大並發數
            save_to_notion: 是否保存到 Notion

        Returns:
            Tuple[處理結果列表, 批次元數據]
        """
        start_time = time.time()
        batch_size = len(image_batch)

        # 創建批次會話
        session_id = await self.batch_service.create_batch_session(
            user_id=user_id, auto_process=True, max_concurrent=max_concurrent or 5
        )

        try:
            # 添加所有項目到批次
            for i, image_bytes in enumerate(image_batch):
                item_id = f"{user_id}_batch_{int(time.time() * 1000)}_{i}"
                await self.batch_service.add_item_to_batch(
                    session_id=session_id,
                    item_id=item_id,
                    image_bytes=image_bytes,
                    priority=priority,
                )

            # 處理批次
            batch_summary = await self.batch_service.process_batch(
                session_id=session_id, max_concurrent=max_concurrent
            )

            # 獲取處理結果
            results = await self.batch_service.get_batch_results(session_id)

            # 處理 Notion 保存
            should_save = (
                save_to_notion if save_to_notion is not None else self.auto_notion_save
            )
            if should_save:
                await self._save_batch_results_to_notion(results, image_batch)

            # 建構批次元數據
            processing_time = time.time() - start_time
            metadata = {
                "batch_size": batch_size,
                "processing_time": processing_time,
                "session_id": session_id,
                "user_id": user_id,
                "successful": batch_summary.get("successful", 0),
                "failed": batch_summary.get("failed", 0),
                "items_per_second": batch_summary.get("items_per_second", 0),
                "timestamp": datetime.now().isoformat(),
            }

            return results or [], metadata

        except Exception as e:
            return [], {
                "error": f"批次處理失敗: {str(e)}",
                "batch_size": batch_size,
                "session_id": session_id,
            }
        finally:
            # 清理會話
            await self.batch_service.remove_batch_session(session_id)

    async def _save_cards_to_notion(
        self, cards: List[Dict[str, Any]], image_bytes: bytes
    ) -> List[Dict[str, Any]]:
        """保存名片到 Notion"""
        try:
            return await self.notion_manager.create_batch_records(
                cards_data=cards, image_bytes_list=[image_bytes] * len(cards)
            )
        except Exception as e:
            print(f"保存到 Notion 失敗: {e}")
            return [{"success": False, "error": str(e)} for _ in cards]

    async def _save_batch_results_to_notion(
        self, results: List[Dict[str, Any]], image_batch: List[bytes]
    ):
        """批次保存結果到 Notion"""
        try:
            cards_to_save = []
            image_bytes_to_save = []

            for i, result in enumerate(results):
                if result.get("result") and result["result"].get("cards"):
                    for card in result["result"]["cards"]:
                        cards_to_save.append(card)
                        image_bytes_to_save.append(
                            image_batch[i] if i < len(image_batch) else None
                        )

            if cards_to_save:
                await self.notion_manager.create_batch_records(
                    cards_data=cards_to_save, image_bytes_list=image_bytes_to_save
                )

        except Exception as e:
            print(f"批次保存到 Notion 失敗: {e}")

    def _update_service_stats(
        self, processing_time: float, success: bool, cache_hit: bool, notion_saved: bool
    ):
        """更新服務統計"""
        if success:
            self.service_stats["successful_requests"] += 1
        else:
            self.service_stats["failed_requests"] += 1

        # 更新平均響應時間
        total_requests = self.service_stats["total_requests"]
        current_avg = self.service_stats["avg_response_time"]
        new_avg = (
            current_avg * (total_requests - 1) + processing_time
        ) / total_requests
        self.service_stats["avg_response_time"] = new_avg

        # 更新快取命中率
        if cache_hit:
            # 簡化的快取命中率計算
            self.service_stats["cache_hit_rate"] = (
                self.service_stats["cache_hit_rate"] * 0.9 + 0.1
            )

        # 更新 Notion 保存率
        if notion_saved:
            self.service_stats["notion_save_rate"] = (
                self.service_stats["notion_save_rate"] * 0.9 + 0.1
            )

    async def get_service_status(self) -> Dict[str, Any]:
        """獲取服務狀態"""
        uptime = (
            (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        )

        # 獲取各組件統計
        ai_stats = await self.card_processor.get_performance_stats()
        batch_stats = await self.batch_service.get_service_stats()
        notion_stats = await self.notion_manager.get_performance_stats()

        return {
            "service_running": self.is_running,
            "uptime_seconds": uptime,
            "service_stats": self.service_stats,
            "ai_processor_stats": ai_stats,
            "batch_service_stats": batch_stats,
            "notion_manager_stats": notion_stats,
        }

    async def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成效能報告"""
        service_status = await self.get_service_status()

        # 計算效能指標
        total_requests = self.service_stats["total_requests"]
        success_rate = (
            self.service_stats["successful_requests"] / total_requests
            if total_requests > 0
            else 0.0
        )

        # 計算吞吐量
        uptime_hours = service_status["uptime_seconds"] / 3600
        throughput = total_requests / uptime_hours if uptime_hours > 0 else 0.0

        return {
            "report_period_hours": hours,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "avg_response_time": self.service_stats["avg_response_time"],
            "cache_hit_rate": self.service_stats["cache_hit_rate"],
            "notion_save_rate": self.service_stats["notion_save_rate"],
            "throughput_per_hour": throughput,
            "component_health": await self._get_component_health(),
            "recommendations": await self._generate_performance_recommendations(),
        }

    async def _get_component_health(self) -> Dict[str, Any]:
        """獲取組件健康狀態"""
        return {
            "ai_processor": await self.card_processor.health_check(),
            "batch_service": await self.batch_service.health_check(),
            "notion_manager": await self.notion_manager.health_check(),
        }

    async def _generate_performance_recommendations(self) -> List[str]:
        """生成效能優化建議"""
        recommendations = []

        # 檢查快取命中率
        if self.service_stats["cache_hit_rate"] < 0.3:
            recommendations.append("考慮調整快取策略或增加快取大小")

        # 檢查響應時間
        if self.service_stats["avg_response_time"] > 10.0:
            recommendations.append("平均響應時間較高，考慮增加並發數或優化 AI 模型")

        # 檢查成功率
        total_requests = self.service_stats["total_requests"]
        success_rate = (
            self.service_stats["successful_requests"] / total_requests
            if total_requests > 0
            else 1.0
        )
        if success_rate < 0.95:
            recommendations.append("成功率偏低，檢查 API 金鑰配額和網路連接")

        return recommendations

    async def health_check(self) -> Dict[str, Any]:
        """綜合健康檢查"""
        try:
            component_health = await self._get_component_health()

            # 判斷整體健康狀態
            all_healthy = all(
                health.get("status") == "healthy"
                for health in component_health.values()
            )

            overall_status = "healthy" if all_healthy else "degraded"

            # 檢查服務負載
            if self.service_stats["total_requests"] > 0:
                success_rate = (
                    self.service_stats["successful_requests"]
                    / self.service_stats["total_requests"]
                )
                if success_rate < 0.8:
                    overall_status = "unhealthy"

            return {
                "status": overall_status,
                "service_running": self.is_running,
                "components": component_health,
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }


# 便利函數
async def create_optimized_ai_service(
    max_concurrent: int = 15,
    cache_memory_mb: int = 100,
    cache_disk_mb: int = 500,
    auto_start: bool = True,
) -> OptimizedAIService:
    """
    創建並配置優化 AI 服務

    Args:
        max_concurrent: 最大並發數
        cache_memory_mb: 記憶體快取大小（MB）
        cache_disk_mb: 磁碟快取大小（MB）
        auto_start: 是否自動啟動

    Returns:
        配置好的 OptimizedAIService 實例
    """
    service = OptimizedAIService(
        max_concurrent_ai=max_concurrent,
        max_concurrent_notion=max_concurrent // 2,
        max_global_concurrent=max_concurrent * 3,
        enable_cache=True,
        auto_notion_save=True,
    )

    if auto_start:
        await service.start()

    return service
