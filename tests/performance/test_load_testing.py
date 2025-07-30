"""
效能測試套件 - Test Engineer 實作
測試系統在高負載下的表現和穩定性
"""

import pytest
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from batch_manager import BatchManager
from enhanced_session_manager import EnhancedSessionManager


class TestPerformanceLoad:
    """效能和負載測試類別"""
    
    @pytest.fixture
    def batch_manager(self):
        """提供測試用的批次管理器"""
        return BatchManager()
    
    @pytest.fixture
    def enhanced_session_manager(self):
        """提供測試用的增強會話管理器"""
        return EnhancedSessionManager("test_sessions.json")
    
    def test_concurrent_batch_sessions(self, batch_manager):
        """測試併發批次會話處理能力"""
        num_users = 50
        user_ids = [f"test_user_{i}" for i in range(num_users)]
        results = []
        
        def start_batch_session(user_id):
            """模擬用戶開始批次會話"""
            try:
                result = batch_manager.start_batch_mode(user_id)
                return {"user_id": user_id, "success": result["success"], "error": None}
            except Exception as e:
                return {"user_id": user_id, "success": False, "error": str(e)}
        
        # 使用線程池併發執行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(start_batch_session, uid) for uid in user_ids]
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 驗證結果
        successful_sessions = [r for r in results if r["success"]]
        failed_sessions = [r for r in results if not r["success"]]
        
        print(f"⏱️ 併發測試結果:")
        print(f"   - 用戶數量: {num_users}")
        print(f"   - 執行時間: {execution_time:.2f} 秒")
        print(f"   - 成功會話: {len(successful_sessions)}")
        print(f"   - 失敗會話: {len(failed_sessions)}")
        print(f"   - 每秒處理量: {num_users / execution_time:.2f} sessions/sec")
        
        # 性能基準測試
        assert execution_time < 10.0, f"併發處理時間過長: {execution_time:.2f}s"
        assert len(successful_sessions) >= num_users * 0.95, "成功率低於95%"
        
        # 清理測試會話
        for user_id in user_ids:
            try:
                batch_manager.end_batch_mode(user_id)
            except:
                pass
    
    def test_session_memory_usage(self, enhanced_session_manager):
        """測試會話記憶體使用情況"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 創建大量會話
        num_sessions = 1000
        for i in range(num_sessions):
            user_id = f"memory_test_user_{i}"
            enhanced_session_manager.start_batch_mode(user_id)
            
            # 添加一些處理數據
            for j in range(10):
                enhanced_session_manager.add_processed_card(user_id, {
                    "name": f"測試名片 {j}",
                    "company": f"測試公司 {j}",
                    "data_size": "x" * 100  # 添加一些數據
                })
        
        gc.collect()  # 強制垃圾回收
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        print(f"📊 記憶體使用測試:")
        print(f"   - 初始記憶體: {initial_memory:.2f} MB")
        print(f"   - 峰值記憶體: {peak_memory:.2f} MB")
        print(f"   - 記憶體增長: {memory_increase:.2f} MB")
        print(f"   - 每會話記憶體: {memory_increase / num_sessions:.4f} MB")
        
        # 記憶體使用基準
        assert memory_increase < 500, f"記憶體使用過高: {memory_increase:.2f} MB"
        
        # 清理會話
        enhanced_session_manager.force_cleanup()
    
    def test_high_throughput_card_processing(self, batch_manager):
        """測試高吞吐量名片處理"""
        user_id = "throughput_test_user"
        batch_manager.start_batch_mode(user_id)
        
        num_cards = 100
        processing_times = []
        
        # 模擬快速名片處理
        for i in range(num_cards):
            start_time = time.time()
            
            # 模擬名片處理
            card_data = {
                "name": f"測試姓名 {i}",
                "company": f"測試公司 {i}",
                "email": f"test{i}@example.com",
                "phone": f"0912-345-{i:03d}"
            }
            
            batch_manager.add_processed_card(user_id, card_data)
            
            end_time = time.time()
            processing_times.append(end_time - start_time)
        
        # 計算性能指標
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        throughput = num_cards / sum(processing_times)
        
        print(f"🚀 高吞吐量測試結果:")
        print(f"   - 處理卡片數: {num_cards}")
        print(f"   - 平均處理時間: {avg_processing_time*1000:.2f} ms")
        print(f"   - 最大處理時間: {max_processing_time*1000:.2f} ms")
        print(f"   - 吞吐量: {throughput:.2f} cards/sec")
        
        # 性能基準
        assert avg_processing_time < 0.1, f"平均處理時間過長: {avg_processing_time:.4f}s"
        assert throughput > 50, f"吞吐量過低: {throughput:.2f} cards/sec"
        
        batch_manager.end_batch_mode(user_id)
    
    def test_session_persistence_reliability(self, tmp_path):
        """測試會話持久化可靠性"""
        session_file = tmp_path / "reliability_test_sessions.json"
        
        # 創建第一個管理器實例
        manager1 = EnhancedSessionManager(str(session_file))
        
        # 創建多個會話
        test_users = ["user1", "user2", "user3"]
        for user_id in test_users:
            result = manager1.start_batch_mode(user_id)
            assert result["success"]
            
            # 添加一些處理數據
            manager1.add_processed_card(user_id, {"name": f"測試 {user_id}"})
        
        # 強制保存
        manager1._save_sessions()
        
        # 創建第二個管理器實例（模擬重啟）
        manager2 = EnhancedSessionManager(str(session_file))
        
        # 驗證會話是否正確載入
        for user_id in test_users:
            assert manager2.is_in_batch_mode(user_id), f"會話 {user_id} 載入失敗"
            session_info = manager2.get_session_info(user_id)
            assert session_info["total_count"] > 0, f"會話數據 {user_id} 遺失"
        
        print("✅ 會話持久化可靠性測試通過")
    
    @pytest.mark.slow
    def test_long_running_session_stability(self, enhanced_session_manager):
        """測試長時間運行的會話穩定性"""
        user_id = "long_running_test_user"
        enhanced_session_manager.start_batch_mode(user_id)
        
        # 模擬長時間運行（壓縮時間版本）
        total_operations = 1000
        operations_per_batch = 50
        
        for batch in range(total_operations // operations_per_batch):
            # 批次處理操作
            for i in range(operations_per_batch):
                if i % 2 == 0:
                    enhanced_session_manager.add_processed_card(user_id, {
                        "name": f"Card {batch*operations_per_batch + i}"
                    })
                else:
                    enhanced_session_manager.add_failed_card(user_id, {
                        "error": f"Test error {batch*operations_per_batch + i}"
                    })
            
            # 檢查會話健康狀態
            health = enhanced_session_manager.get_session_health(user_id)
            assert health["healthy"], f"會話在第 {batch} 批次後不健康"
            
            # 模擬短暫延遲
            time.sleep(0.01)
        
        # 最終驗證
        session_info = enhanced_session_manager.get_session_info(user_id)
        assert session_info["total_count"] == total_operations
        
        print(f"✅ 長時間運行穩定性測試完成 ({total_operations} 操作)")


@pytest.mark.benchmark
def test_comparison_batch_managers():
    """比較原始和增強版批次管理器的性能"""
    original_manager = BatchManager()
    enhanced_manager = EnhancedSessionManager("benchmark_test.json")
    
    num_operations = 100
    user_id = "benchmark_user"
    
    # 測試原始管理器
    start_time = time.time()
    original_manager.start_batch_mode(user_id)
    for i in range(num_operations):
        original_manager.add_processed_card(user_id, {"test": f"data_{i}"})
    original_time = time.time() - start_time
    original_manager.end_batch_mode(user_id)
    
    # 測試增強管理器
    start_time = time.time()
    enhanced_manager.start_batch_mode(user_id)
    for i in range(num_operations):
        enhanced_manager.add_processed_card(user_id, {"test": f"data_{i}"})
    enhanced_time = time.time() - start_time
    enhanced_manager.end_batch_mode(user_id)
    
    print(f"⚖️ 性能比較:")
    print(f"   - 原始管理器: {original_time:.4f}s ({num_operations/original_time:.2f} ops/sec)")
    print(f"   - 增強管理器: {enhanced_time:.4f}s ({num_operations/enhanced_time:.2f} ops/sec)")
    print(f"   - 性能差異: {((enhanced_time - original_time) / original_time * 100):.1f}%")
    
    # 清理
    if os.path.exists("benchmark_test.json"):
        os.remove("benchmark_test.json")


if __name__ == "__main__":
    # 直接運行性能測試
    pytest.main([__file__, "-v", "-s", "--tb=short"])