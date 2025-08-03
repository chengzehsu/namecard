"""
最佳化 AI 服務效能測試 - AI Engineer 實作  
測試生產環境下的 AI 處理管線效能
"""

import asyncio
import time
import pytest
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.namecard.infrastructure.ai.optimized_ai_service import (
    create_optimized_ai_service,
    ProcessingPriority
)


class TestOptimizedAIPerformance:
    """最佳化 AI 服務效能測試套件"""

    @pytest.fixture
    async def ai_service(self):
        """提供測試用的 AI 服務"""
        # 模擬環境變數
        os.environ['GOOGLE_API_KEY'] = 'test_key_1'
        os.environ['GOOGLE_API_KEY_FALLBACK'] = 'test_key_2'
        
        service = await create_optimized_ai_service(
            max_concurrent=5,
            cache_memory_mb=50,
            cache_disk_mb=100,
            auto_start=True
        )
        
        yield service
        
        await service.stop_service()

    @pytest.fixture
    def mock_image_data(self):
        """提供測試用的圖片資料"""
        return [
            b"fake_image_data_1" + b"x" * 1000,  # 1KB
            b"fake_image_data_2" + b"x" * 5000,  # 5KB  
            b"fake_image_data_3" + b"x" * 10000, # 10KB
        ]

    @pytest.fixture
    def mock_ai_response(self):
        """模擬 AI 回應"""
        return {
            "card_count": 1,
            "cards": [{
                "card_index": 1,
                "confidence_score": 0.85,
                "name": "測試用戶",
                "company": "測試公司",
                "email": "test@example.com",
                "phone": "+886912345678"
            }],
            "overall_quality": "good"
        }

    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self, ai_service, mock_image_data, mock_ai_response):
        """測試併發請求效能"""
        
        # 模擬 Gemini API 呼叫
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            mock_response = MagicMock()
            mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
            mock_instance.generate_content.return_value = mock_response
            
            # 併發請求測試
            concurrent_requests = 20
            start_time = time.time()
            
            tasks = []
            for i in range(concurrent_requests):
                task = ai_service.process_image(
                    image_bytes=mock_image_data[i % len(mock_image_data)],
                    priority=ProcessingPriority.NORMAL,
                    user_id=f"test_user_{i}"
                )
                tasks.append(task)
            
            # 執行所有併發請求
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 分析結果
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            total_time = end_time - start_time
            avg_time_per_request = total_time / concurrent_requests
            throughput = concurrent_requests / total_time
            
            print(f"\n🚀 併發效能測試結果:")
            print(f"   - 併發請求數: {concurrent_requests}")
            print(f"   - 總執行時間: {total_time:.2f}s")
            print(f"   - 平均每請求時間: {avg_time_per_request:.2f}s")
            print(f"   - 吞吐量: {throughput:.2f} requests/sec")
            print(f"   - 成功率: {len(successful_results)}/{concurrent_requests}")
            
            # 效能基準測試
            assert len(successful_results) >= concurrent_requests * 0.95, "成功率低於95%"
            assert total_time < 30, f"總執行時間過長: {total_time:.2f}s"
            assert throughput > 1.0, f"吞吐量過低: {throughput:.2f} req/s"

    @pytest.mark.asyncio  
    async def test_cache_performance_impact(self, ai_service, mock_image_data):
        """測試快取對效能的影響"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            mock_response = MagicMock()
            mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
            mock_instance.generate_content.return_value = mock_response
            
            test_image = mock_image_data[0]
            
            # 第一次請求 (應該會呼叫 API)
            start_time = time.time()  
            result1, metadata1 = await ai_service.process_image(
                image_bytes=test_image,
                enable_cache=True,
                user_id="cache_test_user"
            )
            first_request_time = time.time() - start_time
            
            # 第二次請求相同圖片 (應該命中快取)
            start_time = time.time()
            result2, metadata2 = await ai_service.process_image(  
                image_bytes=test_image,
                enable_cache=True,
                user_id="cache_test_user"
            )
            second_request_time = time.time() - start_time
            
            print(f"\n⚡ 快取效能測試結果:")
            print(f"   - 第一次請求時間: {first_request_time:.3f}s (快取: {metadata1['cache_hit']})")
            print(f"   - 第二次請求時間: {second_request_time:.3f}s (快取: {metadata2['cache_hit']})")
            print(f"   - 效能提升: {(first_request_time / second_request_time):.1f}x")
            
            # 驗證快取行為
            assert not metadata1['cache_hit'], "第一次請求不應該命中快取"
            assert metadata2['cache_hit'], "第二次請求應該命中快取"
            assert second_request_time < first_request_time * 0.1, "快取請求應該顯著更快"

    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, ai_service, mock_image_data):
        """測試批次處理效率"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            mock_response = MagicMock()
            mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
            mock_instance.generate_content.return_value = mock_response
            
            # 建立批次測試資料
            batch_size = 10
            batch_images = mock_image_data * (batch_size // len(mock_image_data) + 1)
            batch_images = batch_images[:batch_size]
            
            # 批次處理測試
            start_time = time.time()
            results, batch_metadata = await ai_service.process_batch(
                image_batch=batch_images,
                max_concurrent=5,
                user_id="batch_test_user"
            )
            batch_time = time.time() - start_time
            
            # 單獨處理測試（比較基準）
            start_time = time.time()
            individual_results = []
            for image in batch_images:
                result, _ = await ai_service.process_image(
                    image_bytes=image,
                    user_id="individual_test_user"
                )
                individual_results.append(result)
            individual_time = time.time() - start_time
            
            efficiency_gain = individual_time / batch_time
            
            print(f"\n📦 批次處理效率測試:")
            print(f"   - 批次大小: {batch_size}")
            print(f"   - 批次處理時間: {batch_time:.2f}s")
            print(f"   - 個別處理時間: {individual_time:.2f}s")
            print(f"   - 效率提升: {efficiency_gain:.1f}x")
            print(f"   - 批次成功率: {batch_metadata['processing_summary']['successful']}/{batch_size}")
            
            # 驗證批次處理效率
            assert len(results) == batch_size, "批次結果數量不正確"
            assert efficiency_gain > 1.5, f"批次處理效率提升不足: {efficiency_gain:.1f}x"
            assert batch_metadata['processing_summary']['successful'] >= batch_size * 0.9, "批次成功率低於90%"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, ai_service, mock_image_data):
        """測試高負載下的記憶體使用"""
        
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available for memory testing")
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            mock_response = MagicMock()
            mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
            mock_instance.generate_content.return_value = mock_response
            
            # 記錄初始記憶體
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 高負載測試
            high_load_requests = 50
            tasks = []
            
            for i in range(high_load_requests):
                task = ai_service.process_image(
                    image_bytes=mock_image_data[i % len(mock_image_data)],
                    user_id=f"memory_test_user_{i}"
                )
                tasks.append(task)
            
            # 執行所有請求
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 強制垃圾回收
            import gc
            gc.collect()
            await asyncio.sleep(1)  # 讓背景任務有時間清理
            
            # 記錄峰值記憶體
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            print(f"\n🧠 記憶體使用測試:")
            print(f"   - 初始記憶體: {initial_memory:.1f} MB")
            print(f"   - 峰值記憶體: {peak_memory:.1f} MB")
            print(f"   - 記憶體增長: {memory_increase:.1f} MB")
            print(f"   - 每請求記憶體: {memory_increase / high_load_requests:.3f} MB")
            
            # 記憶體使用基準
            assert memory_increase < 200, f"記憶體增長過多: {memory_increase:.1f} MB"
            assert memory_increase / high_load_requests < 2, "每請求記憶體使用過高"

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, ai_service, mock_image_data):
        """測試錯誤恢復效能"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            
            # 模擬間歇性錯誤
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 3 == 0:  # 每3次呼叫失敗一次
                    raise Exception("Simulated API error")
                
                mock_response = MagicMock()
                mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
                return mock_response
            
            mock_instance.generate_content.side_effect = side_effect
            
            # 錯誤恢復測試
            error_test_requests = 15
            start_time = time.time()
            
            tasks = []
            for i in range(error_test_requests):
                task = ai_service.process_image(
                    image_bytes=mock_image_data[i % len(mock_image_data)],
                    user_id=f"error_test_user_{i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 分析結果
            successful_results = []
            error_results = []
            
            for result in results:
                if isinstance(result, tuple):
                    result_data, metadata = result
                    if 'error' in result_data:
                        error_results.append(result)
                    else:
                        successful_results.append(result)
                else:
                    error_results.append(result)
            
            total_time = end_time - start_time
            success_rate = len(successful_results) / error_test_requests
            
            print(f"\n🔄 錯誤恢復效能測試:")
            print(f"   - 總請求數: {error_test_requests}")
            print(f"   - 成功請求: {len(successful_results)}")
            print(f"   - 失敗請求: {len(error_results)}")
            print(f"   - 成功率: {success_rate:.1%}")
            print(f"   - 總處理時間: {total_time:.2f}s")
            print(f"   - API 呼叫次數: {call_count}")
            
            # 驗證錯誤恢復
            assert success_rate > 0.6, f"錯誤恢復成功率過低: {success_rate:.1%}"
            assert total_time < 60, f"錯誤恢復時間過長: {total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, ai_service):
        """測試服務健康監控"""
        
        # 獲取服務狀態
        service_status = await ai_service.get_service_status()
        health_check = await ai_service.health_check()
        
        print(f"\n🏥 服務健康監控測試:")
        print(f"   - 服務運行狀態: {service_status['service_info']['running']}")
        print(f"   - 背景任務數: {service_status['service_info']['background_tasks']}")
        print(f"   - 健康狀態: {health_check['status']}")
        print(f"   - 可用 API Keys: {service_status['quota_status']['summary']['available_keys']}")
        
        # 驗證健康狀態
        assert service_status['service_info']['running'], "服務應該處於運行狀態"
        assert service_status['quota_status']['summary']['available_keys'] > 0, "應該有可用的 API Keys"
        assert health_check['status'] in ['healthy', 'degraded'], f"健康狀態異常: {health_check['status']}"

    @pytest.mark.asyncio
    async def test_performance_optimization(self, ai_service):
        """測試效能最佳化功能"""
        
        # 執行效能最佳化
        optimization_result = await ai_service.optimize_performance()
        
        print(f"\n⚡ 效能最佳化測試:")
        print(f"   - 最佳化成功: {optimization_result['success']}")
        print(f"   - 執行項目: {optimization_result.get('optimizations_performed', [])}")
        
        # 獲取最佳化建議
        recommendations = ai_service.get_optimization_recommendations()
        print(f"   - 建議數量: {len(recommendations)}")
        
        # 驗證最佳化功能
        assert optimization_result['success'], "效能最佳化應該成功"
        assert 'optimizations_performed' in optimization_result, "應該包含最佳化項目"

    @pytest.mark.asyncio
    async def test_load_testing_stability(self, ai_service, mock_image_data):
        """負載測試穩定性"""
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = mock_model.return_value
            mock_response = MagicMock()
            mock_response.text = '{"card_count": 1, "cards": [{"name": "Test"}], "overall_quality": "good"}'
            mock_instance.generate_content.return_value = mock_response
            
            # 模擬持續負載
            duration_seconds = 30
            requests_per_second = 5
            total_requests = duration_seconds * requests_per_second
            
            print(f"\n🔥 負載測試 ({total_requests} 請求, {duration_seconds}s):")
            
            start_time = time.time()
            completed_requests = 0
            errors = 0
            
            # 分批執行以控制負載
            batch_size = 10
            for batch_start in range(0, total_requests, batch_size):
                batch_end = min(batch_start + batch_size, total_requests)
                batch_tasks = []
                
                for i in range(batch_start, batch_end):
                    task = ai_service.process_image(
                        image_bytes=mock_image_data[i % len(mock_image_data)],
                        user_id=f"load_test_user_{i}"
                    )
                    batch_tasks.append(task)
                
                # 執行批次
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 統計結果
                for result in batch_results:
                    completed_requests += 1
                    if isinstance(result, Exception):
                        errors += 1
                
                # 控制請求速率
                elapsed = time.time() - start_time
                expected_time = batch_end / requests_per_second
                if elapsed < expected_time:
                    await asyncio.sleep(expected_time - elapsed)
            
            total_time = time.time() - start_time
            actual_rps = completed_requests / total_time
            error_rate = errors / completed_requests
            
            print(f"   - 完成請求: {completed_requests}")
            print(f"   - 錯誤數量: {errors}")
            print(f"   - 實際 RPS: {actual_rps:.2f}")
            print(f"   - 錯誤率: {error_rate:.1%}")
            print(f"   - 總時間: {total_time:.1f}s")
            
            # 穩定性驗證
            assert error_rate < 0.05, f"負載測試錯誤率過高: {error_rate:.1%}"
            assert completed_requests >= total_requests * 0.95, "完成率低於95%"
            assert actual_rps >= requests_per_second * 0.8, f"實際 RPS 過低: {actual_rps:.2f}"


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """效能基準測試"""
    
    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self):
        """回應時間基準測試"""
        
        # 這裡可以添加與原始實作的比較測試
        # 目標：證明最佳化版本的效能提升
        
        print("📊 效能基準測試結果:")
        print("   - 預期平均回應時間: < 5s")
        print("   - 預期 P95 回應時間: < 15s") 
        print("   - 預期併發吞吐量: > 5 req/s")
        print("   - 預期快取命中率: > 30%")
        print("   - 預期錯誤率: < 5%")


if __name__ == "__main__":
    # 執行效能測試
    pytest.main([__file__, "-v", "-s", "--tb=short"])