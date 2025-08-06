"""
最佳化 AI 服務整合範例 - AI Engineer 實作
展示如何在生產環境中整合所有 AI 最佳化組件
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.namecard.infrastructure.ai.optimized_ai_service import (
    ProcessingPriority,
    create_optimized_ai_service,
)


class OptimizedNameCardBot:
    """最佳化名片 Bot - 生產環境整合範例"""

    def __init__(self):
        self.ai_service = None
        self.processing_stats = {
            "total_processed": 0,
            "cache_hits": 0,
            "errors": 0,
            "start_time": datetime.now(),
        }

    async def initialize(self):
        """初始化 Bot 和 AI 服務"""
        print("🚀 初始化最佳化名片 Bot...")

        # 建立 AI 服務（自動啟動）
        self.ai_service = await create_optimized_ai_service(
            max_concurrent=15,  # 支援15個併發請求
            cache_memory_mb=200,  # 200MB 記憶體快取
            cache_disk_mb=1000,  # 1GB 磁碟快取
            auto_start=True,
        )

        print("✅ Bot 初始化完成")

    async def process_single_namecard(
        self,
        image_bytes: bytes,
        user_id: str,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
    ) -> Dict[str, Any]:
        """處理單張名片 - 最佳化版本"""

        print(f"📸 處理用戶 {user_id} 的名片...")

        # 使用最佳化服務處理
        result, metadata = await self.ai_service.process_image(
            image_bytes=image_bytes,
            priority=priority,
            enable_cache=True,
            timeout=25.0,  # 25秒超時
            user_id=user_id,
        )

        # 更新統計
        self.processing_stats["total_processed"] += 1
        if metadata["cache_hit"]:
            self.processing_stats["cache_hits"] += 1
        if not metadata["success"]:
            self.processing_stats["errors"] += 1

        # 生成用戶友善回應
        response = self._generate_user_response(result, metadata)

        print(
            f"✅ 處理完成: {user_id} "
            f"({'快取命中' if metadata['cache_hit'] else '新處理'}) "
            f"({metadata.get('processing_time', 0):.2f}s)"
        )

        return {
            "user_response": response,
            "processing_metadata": metadata,
            "result": result,
        }

    async def process_batch_namecards(
        self, image_batch: List[bytes], user_id: str
    ) -> Dict[str, Any]:
        """批次處理名片 - 最佳化版本"""

        print(f"📸 批次處理用戶 {user_id} 的 {len(image_batch)} 張名片...")

        # 使用最佳化批次處理
        results, batch_metadata = await self.ai_service.process_batch(
            image_batch=image_batch,
            max_concurrent=8,  # 批次內最大併發
            enable_cache=True,
            user_id=user_id,
        )

        # 更新統計
        self.processing_stats["total_processed"] += len(image_batch)
        self.processing_stats["cache_hits"] += batch_metadata["processing_summary"][
            "cached"
        ]
        self.processing_stats["errors"] += batch_metadata["processing_summary"][
            "failed"
        ]

        # 生成批次摘要
        summary = self._generate_batch_summary(results, batch_metadata)

        print(
            f"✅ 批次處理完成: {user_id} "
            f"({batch_metadata['processing_summary']['successful']} 成功, "
            f"{batch_metadata['processing_summary']['failed']} 失敗, "
            f"{batch_metadata.get('total_processing_time', 0):.2f}s)"
        )

        return {
            "batch_summary": summary,
            "batch_metadata": batch_metadata,
            "individual_results": results,
        }

    def _generate_user_response(
        self, result: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """生成用戶友善的回應訊息"""

        if "error" in result:
            return f"❌ 名片處理失敗: {result['error']}\n請重新拍攝或稍後再試。"

        card_count = result.get("card_count", 0)
        overall_quality = result.get("overall_quality", "unknown")

        # 基本回應
        if card_count == 0:
            return "📸 未檢測到名片，請確認圖片清晰並重新拍攝。"

        elif card_count == 1:
            card = result["cards"][0]
            confidence = card.get("confidence_score", 0)

            response = f"✅ 名片識別完成！\n"
            response += f"👤 姓名: {card.get('name', '未識別')}\n"
            response += f"🏢 公司: {card.get('company', '未識別')}\n"

            if card.get("title"):
                response += f"💼 職稱: {card['title']}\n"
            if card.get("email"):
                response += f"📧 Email: {card['email']}\n"
            if card.get("phone"):
                response += f"📱 電話: {card['phone']}\n"

            # 品質提示
            if overall_quality == "good":
                response += f"\n🎯 識別品質: 優秀 (信心度: {confidence:.1%})"
            elif overall_quality == "partial":
                response += f"\n⚠️ 識別品質: 部分資訊可能不準確"
            else:
                response += f"\n❌ 識別品質較差，建議重新拍攝"

            # 快取提示
            if metadata.get("cache_hit"):
                response += f"\n⚡ 快速處理 (快取命中)"

            return response

        else:
            # 多張名片
            return (
                f"📸 檢測到 {card_count} 張名片\n"
                f"整體品質: {overall_quality}\n"
                f"請選擇如何處理這些名片。"
            )

    def _generate_batch_summary(
        self, results: List[Dict[str, Any]], batch_metadata: Dict[str, Any]
    ) -> str:
        """生成批次處理摘要"""

        successful = batch_metadata["processing_summary"]["successful"]
        failed = batch_metadata["processing_summary"]["failed"]
        cached = batch_metadata["processing_summary"]["cached"]
        total_time = batch_metadata.get("total_processing_time", 0)

        summary = f"📊 批次處理摘要\n"
        summary += f"✅ 成功處理: {successful} 張\n"
        summary += f"❌ 處理失敗: {failed} 張\n"
        summary += f"⚡ 快取命中: {cached} 張\n"
        summary += f"⏱️ 總處理時間: {total_time:.1f} 秒\n"
        summary += f"🚀 平均處理時間: {total_time/len(results):.1f} 秒/張"

        # 品質統計
        quality_stats = {"good": 0, "partial": 0, "poor": 0, "error": 0}
        for result in results:
            if "error" in result:
                quality_stats["error"] += 1
            else:
                quality = result.get("overall_quality", "unknown")
                if quality in quality_stats:
                    quality_stats[quality] += 1

        if any(quality_stats.values()):
            summary += f"\n\n📈 品質分布:\n"
            if quality_stats["good"]:
                summary += f"🟢 優秀: {quality_stats['good']} 張\n"
            if quality_stats["partial"]:
                summary += f"🟡 部分: {quality_stats['partial']} 張\n"
            if quality_stats["poor"]:
                summary += f"🔴 較差: {quality_stats['poor']} 張\n"

        return summary

    async def get_service_dashboard(self) -> Dict[str, Any]:
        """獲取服務儀表板資料"""

        if not self.ai_service:
            return {"error": "AI 服務未初始化"}

        # 獲取各組件狀態
        service_status = await self.ai_service.get_service_status()
        health_check = await self.ai_service.health_check()

        # Bot 統計
        uptime = datetime.now() - self.processing_stats["start_time"]
        bot_stats = {
            **self.processing_stats,
            "uptime_hours": uptime.total_seconds() / 3600,
            "success_rate": (
                (
                    self.processing_stats["total_processed"]
                    - self.processing_stats["errors"]
                )
                / max(self.processing_stats["total_processed"], 1)
            ),
            "cache_hit_rate": (
                self.processing_stats["cache_hits"]
                / max(self.processing_stats["total_processed"], 1)
            ),
        }

        return {
            "bot_statistics": bot_stats,
            "service_status": service_status,
            "health_check": health_check,
            "optimization_recommendations": self.ai_service.get_optimization_recommendations(),
        }

    async def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成效能報告"""
        if not self.ai_service:
            return {"error": "AI 服務未初始化"}

        return await self.ai_service.get_performance_report(hours)

    async def optimize_service(self) -> Dict[str, Any]:
        """執行服務最佳化"""
        if not self.ai_service:
            return {"error": "AI 服務未初始化"}

        return await self.ai_service.optimize_performance()

    async def shutdown(self):
        """關閉 Bot 和 AI 服務"""
        print("🔄 關閉最佳化名片 Bot...")

        if self.ai_service:
            await self.ai_service.stop_service()

        # 顯示最終統計
        uptime = datetime.now() - self.processing_stats["start_time"]
        print(f"📊 Bot 運行統計:")
        print(f"   - 運行時間: {uptime}")
        print(f"   - 處理總數: {self.processing_stats['total_processed']}")
        print(f"   - 快取命中: {self.processing_stats['cache_hits']}")
        print(f"   - 錯誤數量: {self.processing_stats['errors']}")

        print("✅ Bot 已關閉")


async def main():
    """主要示範函數"""
    print("🚀 最佳化名片 Bot 示範")
    print("=" * 50)

    # 建立 Bot
    bot = OptimizedNameCardBot()

    try:
        # 初始化
        await bot.initialize()

        # 模擬處理 (這裡需要實際的圖片資料)
        print("\n📸 模擬名片處理...")

        # 生成測試圖片資料 (實際使用時替換為真實圖片)
        test_image = b"fake image data for testing"

        # 單張處理示範
        print("\n1️⃣ 單張名片處理示範:")
        single_result = await bot.process_single_namecard(
            image_bytes=test_image,
            user_id="test_user_001",
            priority=ProcessingPriority.HIGH,
        )
        print(f"回應: {single_result['user_response']}")

        # 批次處理示範
        print("\n2️⃣ 批次名片處理示範:")
        batch_images = [test_image, test_image, test_image]  # 3張測試圖片
        batch_result = await bot.process_batch_namecards(
            image_batch=batch_images, user_id="test_user_002"
        )
        print(f"批次摘要: {batch_result['batch_summary']}")

        # 服務儀表板
        print("\n3️⃣ 服務儀表板:")
        dashboard = await bot.get_service_dashboard()
        print(f"Bot 統計: 處理總數 {dashboard['bot_statistics']['total_processed']}")
        print(f"服務健康: {dashboard['health_check']['status']}")

        # 效能最佳化
        print("\n4️⃣ 執行效能最佳化:")
        optimization_result = await bot.optimize_service()
        print(f"最佳化結果: {optimization_result['success']}")
        if optimization_result["success"]:
            print(f"執行項目: {optimization_result['optimizations_performed']}")

        # 等待一段時間以觀察背景任務
        print("\n⏱️ 運行 30 秒以觀察背景任務...")
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\n⏹️ 收到中斷信號")
    except Exception as e:
        print(f"\n❌ 示範過程發生錯誤: {e}")
    finally:
        # 關閉服務
        await bot.shutdown()


if __name__ == "__main__":
    # 設定測試環境變數 (實際部署時使用真實 API Keys)
    os.environ.setdefault("GOOGLE_API_KEY", "test_api_key_1")
    os.environ.setdefault("GOOGLE_API_KEY_FALLBACK", "test_api_key_2")

    # 運行示範
    asyncio.run(main())
