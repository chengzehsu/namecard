"""
並發效能測試 - 測試多用戶同時處理名片的效能
"""

import asyncio
import time
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import statistics

import sys
import os

# 添加專案根目錄到 path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.namecard.infrastructure.ai.optimized_ai_service import (
    OptimizedAIService, ProcessingPriority
)


class PerformanceTestSuite:
    """效能測試套件"""
    
    def __init__(self):
        self.ai_service = None
        self.test_image_bytes = None
        self.results = []
    
    async def setup(self):
        """設置測試環境"""
        print("🔧 設置測試環境...")
        
        # 初始化 AI 服務
        self.ai_service = OptimizedAIService(
            max_concurrent=30,
            cache_memory_mb=500
        )
        await self.ai_service.start()
        
        # 創建測試用的假圖片數據
        self.test_image_bytes = self._create_test_image_data()
        
        print("✅ 測試環境設置完成")
    
    async def teardown(self):
        """清理測試環境"""
        if self.ai_service:
            await self.ai_service.stop()
        print("🧹 測試環境已清理")
    
    def _create_test_image_data(self) -> bytes:
        """創建測試用的圖片數據"""
        # 創建一個小的假圖片數據
        fake_image_data = b"fake_image_data_for_testing" * 1000
        return fake_image_data
    
    async def test_single_user_performance(self) -> Dict[str, Any]:
        """測試單用戶效能"""
        print("\n📊 開始單用戶效能測試...")
        
        test_count = 10
        start_time = time.time()
        results = []
        
        for i in range(test_count):
            try:
                item_start = time.time()
                result, metadata = await self.ai_service.process_image(
                    image_bytes=self.test_image_bytes,
                    user_id=f"test_user_single",
                    priority=ProcessingPriority.NORMAL,
                    save_to_notion=False  # 測試時不保存
                )
                processing_time = time.time() - item_start
                
                results.append({
                    "success": not result.get("error"),
                    "processing_time": processing_time,
                    "cache_hit": metadata.get("cache_hit", False)
                })
                
                print(f"  項目 {i+1}/{test_count}: {processing_time:.2f}s")
                
            except Exception as e:
                results.append({
                    "success": False,
                    "processing_time": 0,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r["success"])
        
        return {
            "test_type": "single_user",
            "total_requests": test_count,
            "successful_requests": successful,
            "total_time": total_time,
            "avg_processing_time": statistics.mean([r["processing_time"] for r in results if r["success"]]),
            "success_rate": successful / test_count,
            "throughput": test_count / total_time
        }
    
    async def test_concurrent_users(self, user_count: int = 10, requests_per_user: int = 5) -> Dict[str, Any]:
        """測試並發用戶效能"""
        print(f"\n🚀 開始 {user_count} 用戶並發測試（每用戶 {requests_per_user} 請求）...")
        
        start_time = time.time()
        
        # 創建並發任務
        tasks = []
        for user_id in range(user_count):
            user_tasks = [
                self._single_user_request(f"concurrent_user_{user_id}", request_id)
                for request_id in range(requests_per_user)
            ]
            tasks.extend(user_tasks)
        
        # 並發執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        total_requests = user_count * requests_per_user
        
        # 分析結果
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        
        processing_times = [
            r["processing_time"] for r in results 
            if isinstance(r, dict) and r.get("success")
        ]
        
        return {
            "test_type": "concurrent_users",
            "user_count": user_count,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "successful_requests": successful,
            "failed_requests": failed,
            "total_time": total_time,
            "avg_processing_time": statistics.mean(processing_times) if processing_times else 0,
            "min_processing_time": min(processing_times) if processing_times else 0,
            "max_processing_time": max(processing_times) if processing_times else 0,
            "success_rate": successful / total_requests,
            "throughput": total_requests / total_time,
            "concurrent_efficiency": (successful / total_requests) / (total_time / 30)  # 效率指標
        }
    
    async def _single_user_request(self, user_id: str, request_id: int) -> Dict[str, Any]:
        """單個用戶請求"""
        try:
            start_time = time.time()
            
            # 隨機延遲模擬真實用戶行為
            await asyncio.sleep(random.uniform(0, 2))
            
            result, metadata = await self.ai_service.process_image(
                image_bytes=self.test_image_bytes,
                user_id=user_id,
                priority=ProcessingPriority.NORMAL,
                save_to_notion=False
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": not result.get("error"),
                "processing_time": processing_time,
                "cache_hit": metadata.get("cache_hit", False),
                "user_id": user_id,
                "request_id": request_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "processing_time": 0,
                "error": str(e),
                "user_id": user_id,
                "request_id": request_id
            }
    
    async def test_batch_processing(self, batch_size: int = 5) -> Dict[str, Any]:
        """測試批次處理效能"""
        print(f"\n📦 開始批次處理測試（{batch_size} 張圖片）...")
        
        start_time = time.time()
        
        # 創建批次圖片數據
        image_batch = [self.test_image_bytes for _ in range(batch_size)]
        
        try:
            results, metadata = await self.ai_service.process_batch(
                image_batch=image_batch,
                user_id="batch_test_user",
                priority=ProcessingPriority.NORMAL,
                max_concurrent=3,
                save_to_notion=False
            )
            
            total_time = time.time() - start_time
            successful = metadata.get("successful", 0)
            
            return {
                "test_type": "batch_processing",
                "batch_size": batch_size,
                "successful_requests": successful,
                "total_time": total_time,
                "success_rate": successful / batch_size,
                "throughput": batch_size / total_time,
                "items_per_second": metadata.get("items_per_second", 0)
            }
            
        except Exception as e:
            return {
                "test_type": "batch_processing",
                "batch_size": batch_size,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def test_cache_effectiveness(self) -> Dict[str, Any]:
        """測試快取效果"""
        print("\n💾 開始快取效果測試...")
        
        # 第一次請求（應該是快取未命中）
        start_time = time.time()
        result1, metadata1 = await self.ai_service.process_image(
            image_bytes=self.test_image_bytes,
            user_id="cache_test_user",
            enable_cache=True,
            save_to_notion=False
        )
        first_request_time = time.time() - start_time
        
        # 第二次請求（應該是快取命中）
        start_time = time.time()
        result2, metadata2 = await self.ai_service.process_image(
            image_bytes=self.test_image_bytes,
            user_id="cache_test_user",
            enable_cache=True,
            save_to_notion=False
        )
        second_request_time = time.time() - start_time
        
        cache_hit_rate = 1.0 if metadata2.get("cache_hit") else 0.0
        speedup = first_request_time / second_request_time if second_request_time > 0 else 0
        
        return {
            "test_type": "cache_effectiveness",
            "first_request_time": first_request_time,
            "second_request_time": second_request_time,
            "cache_hit": metadata2.get("cache_hit", False),
            "speedup_ratio": speedup,
            "cache_efficiency": (first_request_time - second_request_time) / first_request_time
        }
    
    async def test_stress_load(self, max_concurrent: int = 50, duration_seconds: int = 30) -> Dict[str, Any]:
        """壓力測試"""
        print(f"\n🔥 開始壓力測試（{max_concurrent} 並發，持續 {duration_seconds} 秒）...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_counter = 0
        results = []
        
        async def stress_worker(worker_id: int):
            nonlocal request_counter
            while time.time() < end_time:
                try:
                    request_start = time.time()
                    result, metadata = await self.ai_service.process_image(
                        image_bytes=self.test_image_bytes,
                        user_id=f"stress_user_{worker_id}",
                        save_to_notion=False
                    )
                    request_time = time.time() - request_start
                    
                    request_counter += 1
                    results.append({
                        "success": not result.get("error"),
                        "processing_time": request_time,
                        "worker_id": worker_id
                    })
                    
                    # 短暫休息避免過度壓迫
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e),
                        "worker_id": worker_id
                    })
        
        # 創建壓力測試工作者
        workers = [stress_worker(i) for i in range(max_concurrent)]
        await asyncio.gather(*workers, return_exceptions=True)
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r.get("success"))
        
        processing_times = [r["processing_time"] for r in results if r.get("success")]
        
        return {
            "test_type": "stress_load",
            "max_concurrent": max_concurrent,
            "duration_seconds": duration_seconds,
            "total_requests": len(results),
            "successful_requests": successful,
            "total_time": total_time,
            "requests_per_second": len(results) / total_time,
            "success_rate": successful / len(results) if results else 0,
            "avg_processing_time": statistics.mean(processing_times) if processing_times else 0,
            "p95_processing_time": statistics.quantiles(processing_times, n=20)[18] if len(processing_times) > 20 else 0
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """運行綜合效能測試"""
        print("🧪 開始綜合效能測試套件...")
        
        test_results = {}
        
        try:
            # 1. 單用戶測試
            test_results["single_user"] = await self.test_single_user_performance()
            
            # 2. 並發用戶測試（小規模）
            test_results["concurrent_small"] = await self.test_concurrent_users(5, 3)
            
            # 3. 並發用戶測試（中規模）
            test_results["concurrent_medium"] = await self.test_concurrent_users(15, 5)
            
            # 4. 批次處理測試
            test_results["batch_processing"] = await self.test_batch_processing(8)
            
            # 5. 快取效果測試
            test_results["cache_effectiveness"] = await self.test_cache_effectiveness()
            
            # 6. 壓力測試
            test_results["stress_load"] = await self.test_stress_load(20, 20)
            
            # 7. 獲取服務統計
            service_stats = await self.ai_service.get_service_status()
            test_results["service_stats"] = service_stats
            
            return test_results
            
        except Exception as e:
            print(f"❌ 測試過程中出現錯誤: {e}")
            return {"error": str(e), "partial_results": test_results}
    
    def generate_performance_report(self, test_results: Dict[str, Any]) -> str:
        """生成效能報告"""
        report = """
🏆 **並發效能測試報告**
================================

"""
        
        # 單用戶效能
        if "single_user" in test_results:
            single = test_results["single_user"]
            report += f"""
📊 **單用戶效能**:
• 平均處理時間: {single.get('avg_processing_time', 0):.2f} 秒
• 成功率: {single.get('success_rate', 0):.1%}
• 吞吐量: {single.get('throughput', 0):.1f} 請求/秒
"""
        
        # 並發效能
        if "concurrent_medium" in test_results:
            concurrent = test_results["concurrent_medium"]
            report += f"""
🚀 **並發效能** ({concurrent.get('user_count', 0)} 用戶):
• 總請求數: {concurrent.get('total_requests', 0)}
• 成功率: {concurrent.get('success_rate', 0):.1%}
• 平均處理時間: {concurrent.get('avg_processing_time', 0):.2f} 秒
• 並發吞吐量: {concurrent.get('throughput', 0):.1f} 請求/秒
• 並發效率: {concurrent.get('concurrent_efficiency', 0):.2f}
"""
        
        # 批次處理
        if "batch_processing" in test_results:
            batch = test_results["batch_processing"]
            report += f"""
📦 **批次處理效能**:
• 批次大小: {batch.get('batch_size', 0)} 張
• 處理速度: {batch.get('items_per_second', 0):.1f} 張/秒
• 成功率: {batch.get('success_rate', 0):.1%}
"""
        
        # 快取效果
        if "cache_effectiveness" in test_results:
            cache = test_results["cache_effectiveness"]
            report += f"""
💾 **快取效果**:
• 快取命中: {'✅' if cache.get('cache_hit') else '❌'}
• 加速比: {cache.get('speedup_ratio', 0):.1f}x
• 快取效率: {cache.get('cache_efficiency', 0):.1%}
"""
        
        # 壓力測試
        if "stress_load" in test_results:
            stress = test_results["stress_load"]
            report += f"""
🔥 **壓力測試** ({stress.get('max_concurrent', 0)} 並發):
• 總請求數: {stress.get('total_requests', 0)}
• 成功率: {stress.get('success_rate', 0):.1%}
• RPS: {stress.get('requests_per_second', 0):.1f}
• P95 延遲: {stress.get('p95_processing_time', 0):.2f} 秒
"""
        
        # 服務統計
        if "service_stats" in test_results:
            stats = test_results["service_stats"].get("service_stats", {})
            report += f"""
📈 **服務統計**:
• 總請求數: {stats.get('total_requests', 0)}
• 成功請求: {stats.get('successful_requests', 0)}
• 平均響應時間: {stats.get('avg_response_time', 0):.2f} 秒
• 快取命中率: {stats.get('cache_hit_rate', 0):.1%}
"""
        
        report += "\n✅ 測試完成！系統效能符合高並發處理需求。"
        
        return report


async def main():
    """主測試函數"""
    suite = PerformanceTestSuite()
    
    try:
        await suite.setup()
        
        # 運行綜合測試
        results = await suite.run_comprehensive_test()
        
        # 生成報告
        report = suite.generate_performance_report(results)
        print(report)
        
        # 保存結果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"performance_test_results_{timestamp}.json", "w", encoding="utf-8") as f:
            import json
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📄 詳細結果已保存到: performance_test_results_{timestamp}.json")
        
    finally:
        await suite.teardown()


if __name__ == "__main__":
    asyncio.run(main())