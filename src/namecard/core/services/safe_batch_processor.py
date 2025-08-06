#!/usr/bin/env python3
"""
安全批次處理器 - SafeBatchProcessor

整合修復的連接池邏輯，安全地處理批次圖片，避免連接池超限和協程重用問題。
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.namecard.core.services.multi_card_service import MultiCardProcessor
from src.namecard.infrastructure.ai.ultra_fast_processor import UltraFastProcessor

# 導入修復的組件
from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
    EnhancedTelegramBotHandler,
)
from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
from src.namecard.infrastructure.storage.notion_client import NotionManager

# 導入批次組件
from .batch_image_collector import PendingImage
from .unified_result_formatter import (
    BatchProcessingResult,
    ProcessingStatus,
    SingleCardResult,
    UnifiedResultFormatter,
    create_batch_result,
    create_single_card_result,
)


@dataclass
class SafeProcessingConfig:
    """安全處理配置"""

    max_concurrent_processing: int = 8  # 最大並發處理數，小於Semaphore限制(15)
    processing_timeout: float = 120.0  # 單張圖片處理超時時間
    batch_timeout: float = 600.0  # 整個批次超時時間
    enable_ultra_fast: bool = True  # 是否啟用超高速處理
    fallback_to_traditional: bool = True  # 是否降級到傳統處理
    use_connection_pool_cleanup: bool = True  # 是否使用連接池清理


class SafeBatchProcessor:
    """安全批次處理器"""

    def __init__(
        self,
        enhanced_telegram_handler: Optional[EnhancedTelegramBotHandler] = None,
        telegram_bot_handler: Optional[TelegramBotHandler] = None,
        ultra_fast_processor: Optional[UltraFastProcessor] = None,
        multi_card_processor: Optional[MultiCardProcessor] = None,
        notion_manager: Optional[NotionManager] = None,
        config: Optional[SafeProcessingConfig] = None,
    ):
        """
        初始化安全批次處理器

        Args:
            enhanced_telegram_handler: 增強型Telegram處理器
            telegram_bot_handler: 基礎Telegram處理器
            ultra_fast_processor: 超高速處理器
            multi_card_processor: 多名片處理器
            notion_manager: Notion管理器
            config: 安全處理配置
        """
        self.enhanced_telegram_handler = enhanced_telegram_handler
        self.telegram_bot_handler = telegram_bot_handler
        self.ultra_fast_processor = ultra_fast_processor
        self.multi_card_processor = multi_card_processor
        self.notion_manager = notion_manager
        self.config = config or SafeProcessingConfig()

        self.formatter = UnifiedResultFormatter()
        self.logger = logging.getLogger(__name__)

        # 統計信息
        self.stats = {
            "total_batches_processed": 0,
            "total_images_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_processing_time": 0.0,
            "connection_pool_cleanups": 0,
            "ultra_fast_usage": 0,
            "traditional_fallbacks": 0,
        }

        self.logger.info("✅ SafeBatchProcessor 初始化完成")
        self.logger.info(f"   - 最大並發: {self.config.max_concurrent_processing}")
        self.logger.info(f"   - 處理超時: {self.config.processing_timeout}秒")

    async def process_batch_safely(
        self,
        user_id: str,
        images: List[PendingImage],
        progress_callback: Optional[Callable] = None,
    ) -> BatchProcessingResult:
        """
        安全地處理一批圖片

        Args:
            user_id: 用戶ID
            images: 待處理圖片列表
            progress_callback: 進度回調函數

        Returns:
            批次處理結果
        """
        batch_start_time = time.time()
        total_images = len(images)
        results: List[SingleCardResult] = []

        self.logger.info(
            f"🚀 開始安全處理批次 - 用戶: {user_id}, 圖片數: {total_images}"
        )

        try:
            # 使用連接池安全上下文（如果可用）
            if (
                self.config.use_connection_pool_cleanup
                and self.enhanced_telegram_handler
                and hasattr(
                    self.enhanced_telegram_handler, "_connection_cleanup_context"
                )
            ):

                async with self.enhanced_telegram_handler._connection_cleanup_context():
                    results = await self._process_images_with_semaphore(
                        user_id, images, progress_callback
                    )
                    self.stats["connection_pool_cleanups"] += 1
            else:
                # 直接處理（無連接池上下文）
                results = await self._process_images_with_semaphore(
                    user_id, images, progress_callback
                )

        except Exception as e:
            self.logger.error(f"❌ 批次處理發生錯誤: {e}")
            import traceback

            self.logger.error(f"錯誤堆疊: {traceback.format_exc()}")

            # 創建失敗結果
            for i, image in enumerate(images):
                result = create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message=f"批次處理錯誤: {str(e)}",
                    image_index=i + 1,
                )
                results.append(result)

        # 計算統計信息
        total_processing_time = time.time() - batch_start_time
        batch_result = create_batch_result(
            user_id=user_id,
            results=results,
            total_processing_time=total_processing_time,
            started_at=batch_start_time,
        )

        # 更新全局統計
        self._update_stats(batch_result)

        self.logger.info(
            f"✅ 批次處理完成 - 成功: {len(batch_result.successful_results)}/{total_images}, 用時: {total_processing_time:.1f}秒"
        )

        return batch_result

    async def _process_images_with_semaphore(
        self,
        user_id: str,
        images: List[PendingImage],
        progress_callback: Optional[Callable],
    ) -> List[SingleCardResult]:
        """使用Semaphore控制並發的圖片處理"""

        # 創建並發控制Semaphore - 確保不超過連接池限制
        semaphore = asyncio.Semaphore(self.config.max_concurrent_processing)
        results: List[SingleCardResult] = []

        # 創建處理任務
        tasks = []
        for i, image in enumerate(images):
            task = self._process_single_image_safe(
                semaphore, image, i + 1, progress_callback
            )
            tasks.append(task)

        # 等待所有任務完成，使用修復的gather邏輯
        try:
            # 設置整體批次超時
            completed_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.batch_timeout,
            )

            # 處理結果
            for i, result in enumerate(completed_results):
                if isinstance(result, Exception):
                    # 任務執行出錯
                    self.logger.error(f"❌ 圖片 {i+1} 處理異常: {result}")
                    error_result = create_single_card_result(
                        status=ProcessingStatus.FAILED,
                        error_message=f"處理異常: {str(result)}",
                        image_index=i + 1,
                    )
                    results.append(error_result)
                else:
                    # 正常結果
                    results.append(result)

        except asyncio.TimeoutError:
            self.logger.error(f"❌ 批次處理超時 ({self.config.batch_timeout}秒)")

            # 取消所有未完成的任務
            for task in tasks:
                if not task.done():
                    task.cancel()

            # 為所有圖片創建超時錯誤結果
            for i in range(len(images)):
                if i >= len(results):
                    timeout_result = create_single_card_result(
                        status=ProcessingStatus.FAILED,
                        error_message="批次處理超時",
                        image_index=i + 1,
                    )
                    results.append(timeout_result)

        return results

    async def _process_single_image_safe(
        self,
        semaphore: asyncio.Semaphore,
        image: PendingImage,
        image_index: int,
        progress_callback: Optional[Callable],
    ) -> SingleCardResult:
        """安全處理單張圖片"""

        async with semaphore:  # 控制並發數量
            start_time = time.time()

            try:
                self.logger.debug(
                    f"🔍 開始處理圖片 {image_index} - 用戶: {image.user_id}"
                )

                # 通知進度開始
                if progress_callback:
                    try:
                        await progress_callback(
                            user_id=image.user_id,
                            chat_id=image.chat_id,
                            current_image=image_index,
                            action="processing_started",
                        )
                    except Exception as e:
                        self.logger.error(f"進度回調錯誤: {e}")

                # 嘗試超高速處理
                if self.config.enable_ultra_fast and self.ultra_fast_processor:
                    try:
                        result = await self._try_ultra_fast_processing(
                            image, image_index
                        )
                        if result.status == ProcessingStatus.SUCCESS:
                            self.stats["ultra_fast_usage"] += 1
                            return result
                        else:
                            self.logger.debug(
                                f"超高速處理失敗，降級到傳統處理: {result.error_message}"
                            )
                    except Exception as e:
                        self.logger.warning(f"超高速處理異常: {e}")

                # 降級到傳統處理
                if self.config.fallback_to_traditional and self.multi_card_processor:
                    result = await self._try_traditional_processing(image, image_index)
                    self.stats["traditional_fallbacks"] += 1
                    return result
                else:
                    # 無可用處理器
                    return create_single_card_result(
                        status=ProcessingStatus.FAILED,
                        error_message="無可用的處理器",
                        image_index=image_index,
                    )

            except asyncio.TimeoutError:
                self.logger.error(f"❌ 圖片 {image_index} 處理超時")
                return create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message="處理超時",
                    processing_time=time.time() - start_time,
                    image_index=image_index,
                )
            except Exception as e:
                self.logger.error(f"❌ 圖片 {image_index} 處理錯誤: {e}")
                return create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message=str(e),
                    processing_time=time.time() - start_time,
                    image_index=image_index,
                )

    async def _try_ultra_fast_processing(
        self, image: PendingImage, image_index: int
    ) -> SingleCardResult:
        """嘗試超高速處理"""
        try:
            # 設置處理超時
            ultra_result = await asyncio.wait_for(
                self.ultra_fast_processor.process_telegram_photo_ultra_fast(
                    image.image_data, image.user_id, processing_type="single_card"
                ),
                timeout=self.config.processing_timeout,
            )

            if ultra_result.success and ultra_result.data:
                # 存儲到Notion
                notion_url = None
                if self.notion_manager:
                    try:
                        notion_page = await self._save_to_notion(ultra_result.data)
                        notion_url = notion_page.get("url") if notion_page else None
                    except Exception as e:
                        self.logger.error(f"Notion存儲失敗: {e}")

                return create_single_card_result(
                    status=ProcessingStatus.SUCCESS,
                    card_data=ultra_result.data,
                    processing_time=ultra_result.total_time,
                    image_index=image_index,
                    notion_url=notion_url,
                    quality_grade=ultra_result.performance_grade,
                    confidence_score=0.95,  # 超高速處理通常高信心度
                )
            else:
                return create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message=ultra_result.error or "超高速處理失敗",
                    processing_time=ultra_result.total_time,
                    image_index=image_index,
                )

        except asyncio.TimeoutError:
            return create_single_card_result(
                status=ProcessingStatus.FAILED,
                error_message="超高速處理超時",
                image_index=image_index,
            )
        except Exception as e:
            return create_single_card_result(
                status=ProcessingStatus.FAILED,
                error_message=f"超高速處理異常: {str(e)}",
                image_index=image_index,
            )

    async def _try_traditional_processing(
        self, image: PendingImage, image_index: int
    ) -> SingleCardResult:
        """嘗試傳統處理"""
        try:
            # 下載圖片字節數據
            if hasattr(image.image_data, "download_as_bytearray"):
                image_bytes = await image.image_data.download_as_bytearray()
            else:
                # 假設已經是字節數據
                image_bytes = image.image_data

            # 設置處理超時，使用線程池避免阻塞
            processing_result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.multi_card_processor.process_image_with_quality_check,
                    bytes(image_bytes),
                ),
                timeout=self.config.processing_timeout,
            )

            if processing_result.get("error"):
                return create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message=processing_result["error"],
                    image_index=image_index,
                )

            # 處理成功的情況
            cards = processing_result.get("cards", [])
            if cards:
                card_data = cards[0]  # 取第一張名片

                # 存儲到Notion
                notion_url = None
                if self.notion_manager:
                    try:
                        notion_page = await self._save_to_notion(card_data)
                        notion_url = notion_page.get("url") if notion_page else None
                    except Exception as e:
                        self.logger.error(f"Notion存儲失敗: {e}")

                return create_single_card_result(
                    status=ProcessingStatus.SUCCESS,
                    card_data=card_data,
                    image_index=image_index,
                    notion_url=notion_url,
                    quality_grade=processing_result.get("overall_quality", "unknown"),
                )
            else:
                return create_single_card_result(
                    status=ProcessingStatus.FAILED,
                    error_message="未檢測到名片",
                    image_index=image_index,
                )

        except asyncio.TimeoutError:
            return create_single_card_result(
                status=ProcessingStatus.FAILED,
                error_message="傳統處理超時",
                image_index=image_index,
            )
        except Exception as e:
            return create_single_card_result(
                status=ProcessingStatus.FAILED,
                error_message=f"傳統處理異常: {str(e)}",
                image_index=image_index,
            )

    async def _save_to_notion(
        self, card_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """保存名片數據到Notion"""
        if not self.notion_manager:
            return None

        try:
            # 使用異步方式調用Notion API
            notion_page = await asyncio.get_event_loop().run_in_executor(
                None, self.notion_manager.create_namecard_page, card_data
            )
            return notion_page
        except Exception as e:
            self.logger.error(f"Notion保存錯誤: {e}")
            return None

    def _update_stats(self, batch_result: BatchProcessingResult):
        """更新統計信息"""
        self.stats["total_batches_processed"] += 1
        self.stats["total_images_processed"] += batch_result.total_images
        self.stats["total_successful"] += len(batch_result.successful_results)
        self.stats["total_failed"] += len(batch_result.failed_results)
        self.stats["total_processing_time"] += batch_result.total_processing_time

    def get_stats(self) -> Dict[str, Any]:
        """獲取處理統計信息"""
        total_processed = self.stats["total_images_processed"]
        if total_processed > 0:
            success_rate = (self.stats["total_successful"] / total_processed) * 100
            avg_processing_time = (
                self.stats["total_processing_time"]
                / self.stats["total_batches_processed"]
            )
        else:
            success_rate = 0
            avg_processing_time = 0

        return {
            **self.stats,
            "success_rate_percentage": success_rate,
            "average_batch_processing_time": avg_processing_time,
            "config": {
                "max_concurrent": self.config.max_concurrent_processing,
                "processing_timeout": self.config.processing_timeout,
                "ultra_fast_enabled": self.config.enable_ultra_fast,
                "connection_pool_cleanup_enabled": self.config.use_connection_pool_cleanup,
            },
        }


# 全局安全批次處理器實例
_global_safe_processor: Optional[SafeBatchProcessor] = None


def get_safe_batch_processor() -> Optional[SafeBatchProcessor]:
    """獲取全局安全批次處理器實例"""
    return _global_safe_processor


def initialize_safe_batch_processor(
    enhanced_telegram_handler: Optional[EnhancedTelegramBotHandler] = None,
    telegram_bot_handler: Optional[TelegramBotHandler] = None,
    ultra_fast_processor: Optional[UltraFastProcessor] = None,
    multi_card_processor: Optional[MultiCardProcessor] = None,
    notion_manager: Optional[NotionManager] = None,
    config: Optional[SafeProcessingConfig] = None,
) -> SafeBatchProcessor:
    """初始化全局安全批次處理器"""
    global _global_safe_processor

    _global_safe_processor = SafeBatchProcessor(
        enhanced_telegram_handler=enhanced_telegram_handler,
        telegram_bot_handler=telegram_bot_handler,
        ultra_fast_processor=ultra_fast_processor,
        multi_card_processor=multi_card_processor,
        notion_manager=notion_manager,
        config=config,
    )

    return _global_safe_processor
