#!/usr/bin/env python3
"""
批次服務完整測試套件 - 專注狀態管理和並發處理
包含批次模式管理、會話超時、多用戶並發、統計報告和連接穩定性測試
"""

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 導入測試目標
from src.namecard.core.services.batch_service import BatchManager

# 測試標記
pytestmark = [pytest.mark.unit, pytest.mark.batch_service]


class TestBatchServiceComplete:
    """完整的批次服務測試類"""

    @pytest.fixture
    def batch_manager(self):
        """創建測試用的批次管理器"""
        return BatchManager()

    @pytest.fixture
    def sample_card_info(self):
        """測試用的名片資訊樣本"""
        return {
            "name": "張小明",
            "company": "科技創新有限公司",
            "title": "技術總監",
            "email": "zhang@tech.com",
            "phone": "02-12345678",
            "notion_url": "https://notion.so/test-page-123",
        }

    @pytest.fixture
    def sample_error_info(self):
        """測試用的錯誤資訊樣本"""
        return {
            "error": "圖片無法識別",
            "timestamp": datetime.now().isoformat(),
            "details": "圖片模糊或格式不支援",
        }

    # ==========================================
    # 1. 基本批次模式操作測試
    # ==========================================

    def test_batch_manager_initialization(self, batch_manager):
        """測試批次管理器初始化"""
        assert isinstance(batch_manager.user_sessions, dict)
        assert len(batch_manager.user_sessions) == 0
        assert batch_manager.session_timeout == timedelta(minutes=10)
        assert batch_manager.lock is not None

    def test_start_batch_mode_success(self, batch_manager):
        """測試成功啟動批次模式"""
        user_id = "test_user_123"

        result = batch_manager.start_batch_mode(user_id)

        # 驗證返回結果
        assert result["success"] is True
        assert "批次模式已啟動" in result["message"]

        # 驗證會話狀態
        assert user_id in batch_manager.user_sessions
        session = batch_manager.user_sessions[user_id]

        assert session["is_batch_mode"] is True
        assert isinstance(session["start_time"], datetime)
        assert isinstance(session["last_activity"], datetime)
        assert session["processed_cards"] == []
        assert session["failed_cards"] == []
        assert session["total_count"] == 0

    def test_start_batch_mode_existing_user(self, batch_manager):
        """測試對已存在用戶啟動批次模式"""
        user_id = "existing_user"

        # 第一次啟動
        result1 = batch_manager.start_batch_mode(user_id)
        assert result1["success"] is True

        # 第二次啟動（應該覆蓋之前的會話）
        result2 = batch_manager.start_batch_mode(user_id)
        assert result2["success"] is True

        # 應該只有一個會話
        assert len(batch_manager.user_sessions) == 1

    def test_end_batch_mode_success(self, batch_manager, sample_card_info):
        """測試成功結束批次模式"""
        user_id = "test_user_456"

        # 先啟動批次模式
        batch_manager.start_batch_mode(user_id)

        # 添加一些處理記錄
        batch_manager.add_processed_card(user_id, sample_card_info)
        batch_manager.add_failed_card(user_id, "處理失敗的圖片", "識別錯誤")

        # 等待一小段時間以測量處理時間
        time.sleep(0.1)

        result = batch_manager.end_batch_mode(user_id)

        # 驗證返回結果
        assert result["success"] is True
        assert "statistics" in result

        stats = result["statistics"]
        assert stats["total_processed"] == 1
        assert stats["total_failed"] == 1
        assert stats["total_time_minutes"] > 0
        assert len(stats["processed_cards"]) == 1
        assert len(stats["failed_cards"]) == 1

        # 驗證會話被清除
        assert user_id not in batch_manager.user_sessions

    def test_end_batch_mode_no_session(self, batch_manager):
        """測試結束不存在的批次會話"""
        user_id = "nonexistent_user"

        result = batch_manager.end_batch_mode(user_id)

        assert result["success"] is False
        assert "不在批次模式中" in result["message"]

    # ==========================================
    # 2. 會話狀態檢查測試
    # ==========================================

    def test_is_in_batch_mode_active_session(self, batch_manager):
        """測試活躍會話的狀態檢查"""
        user_id = "active_user"

        # 未啟動批次模式
        assert batch_manager.is_in_batch_mode(user_id) is False

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)
        assert batch_manager.is_in_batch_mode(user_id) is True

    def test_is_in_batch_mode_expired_session(self, batch_manager):
        """測試過期會話的處理"""
        user_id = "expired_user"

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)
        assert batch_manager.is_in_batch_mode(user_id) is True

        # 手動設置過期時間
        session = batch_manager.user_sessions[user_id]
        session["last_activity"] = datetime.now() - timedelta(minutes=15)  # 15分鐘前

        # 檢查狀態（應該自動清除過期會話）
        assert batch_manager.is_in_batch_mode(user_id) is False
        assert user_id not in batch_manager.user_sessions

    def test_session_timeout_configuration(self):
        """測試會話超時配置"""
        # 自定義超時時間
        custom_manager = BatchManager()
        custom_manager.session_timeout = timedelta(minutes=5)

        assert custom_manager.session_timeout == timedelta(minutes=5)

    # ==========================================
    # 3. 名片記錄管理測試
    # ==========================================

    def test_add_processed_card_success(self, batch_manager, sample_card_info):
        """測試添加成功處理的名片"""
        user_id = "card_user"

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)

        # 添加處理記錄
        batch_manager.add_processed_card(user_id, sample_card_info)

        # 驗證記錄被添加
        session = batch_manager.user_sessions[user_id]
        assert len(session["processed_cards"]) == 1

        card_record = session["processed_cards"][0]
        assert card_record["name"] == "張小明"
        assert card_record["company"] == "科技創新有限公司"
        assert card_record["notion_url"] == "https://notion.so/test-page-123"
        assert "processed_time" in card_record

    def test_add_processed_card_no_session(self, batch_manager, sample_card_info):
        """測試在無會話狀態下添加處理記錄"""
        user_id = "no_session_user"

        # 不啟動批次模式直接添加記錄
        batch_manager.add_processed_card(user_id, sample_card_info)

        # 應該不會拋出異常，但記錄不會被添加
        assert user_id not in batch_manager.user_sessions

    def test_add_failed_card_success(self, batch_manager):
        """測試添加失敗處理的名片"""
        user_id = "fail_user"

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)

        # 添加失敗記錄
        batch_manager.add_failed_card(user_id, "模糊圖片.jpg", "圖片質量過低，無法識別")

        # 驗證失敗記錄被添加
        session = batch_manager.user_sessions[user_id]
        assert len(session["failed_cards"]) == 1

        fail_record = session["failed_cards"][0]
        assert fail_record["description"] == "模糊圖片.jpg"
        assert fail_record["error"] == "圖片質量過低，無法識別"
        assert "failed_time" in fail_record

    def test_get_batch_status_active_session(self, batch_manager, sample_card_info):
        """測試獲取活躍會話的狀態"""
        user_id = "status_user"

        # 啟動批次模式並添加一些記錄
        batch_manager.start_batch_mode(user_id)
        batch_manager.add_processed_card(user_id, sample_card_info)
        batch_manager.add_failed_card(user_id, "失敗圖片", "錯誤原因")

        status = batch_manager.get_batch_status(user_id)

        assert status["is_active"] is True
        assert status["processed_count"] == 1
        assert status["failed_count"] == 1
        assert "start_time" in status
        assert "duration_minutes" in status

    def test_get_batch_status_no_session(self, batch_manager):
        """測試獲取不存在會話的狀態"""
        user_id = "no_status_user"

        status = batch_manager.get_batch_status(user_id)

        assert status["is_active"] is False
        assert status["processed_count"] == 0
        assert status["failed_count"] == 0

    # ==========================================
    # 4. 並發處理和線程安全測試
    # ==========================================

    def test_concurrent_batch_operations(self, batch_manager):
        """測試並發批次操作的線程安全性"""
        num_users = 10
        operations_per_user = 5
        results = []

        def user_operations(user_id):
            try:
                # 啟動批次模式
                start_result = batch_manager.start_batch_mode(f"user_{user_id}")
                results.append(("start", user_id, start_result["success"]))

                # 添加一些記錄
                for i in range(operations_per_user):
                    card_info = {
                        "name": f"用戶{user_id}名片{i}",
                        "company": f"公司{i}",
                        "notion_url": f"https://notion.so/page-{user_id}-{i}",
                    }
                    batch_manager.add_processed_card(f"user_{user_id}", card_info)

                # 檢查狀態
                is_active = batch_manager.is_in_batch_mode(f"user_{user_id}")
                results.append(("status", user_id, is_active))

                # 結束批次模式
                end_result = batch_manager.end_batch_mode(f"user_{user_id}")
                results.append(("end", user_id, end_result["success"]))

            except Exception as e:
                results.append(("error", user_id, str(e)))

        # 創建並啟動多個線程
        threads = []
        for i in range(num_users):
            thread = threading.Thread(target=user_operations, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        # 驗證結果
        start_successes = [r for r in results if r[0] == "start" and r[2] is True]
        end_successes = [r for r in results if r[0] == "end" and r[2] is True]
        errors = [r for r in results if r[0] == "error"]

        assert len(start_successes) == num_users
        assert len(end_successes) == num_users
        assert len(errors) == 0

        # 驗證所有會話都被清除
        assert len(batch_manager.user_sessions) == 0

    def test_high_frequency_operations(self, batch_manager):
        """測試高頻操作的性能和穩定性"""
        user_id = "high_freq_user"
        num_operations = 1000

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)

        # 高頻添加記錄
        start_time = time.time()

        for i in range(num_operations):
            if i % 2 == 0:
                card_info = {
                    "name": f"名片{i}",
                    "company": f"公司{i}",
                    "notion_url": f"https://notion.so/page-{i}",
                }
                batch_manager.add_processed_card(user_id, card_info)
            else:
                batch_manager.add_failed_card(user_id, f"失敗圖片{i}", f"錯誤{i}")

        end_time = time.time()
        operation_time = end_time - start_time

        # 驗證所有操作都完成
        session = batch_manager.user_sessions[user_id]
        assert len(session["processed_cards"]) == num_operations // 2
        assert len(session["failed_cards"]) == num_operations - (num_operations // 2)

        # 性能檢查（應該在合理時間內完成）
        assert operation_time < 5.0, f"高頻操作耗時過長: {operation_time:.2f}秒"

        # 清理
        batch_manager.end_batch_mode(user_id)

    # ==========================================
    # 5. 記憶體管理和資源清理測試
    # ==========================================

    def test_memory_usage_under_load(self, batch_manager):
        """測試負載下的記憶體使用"""
        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # 創建大量會話和記錄
            num_users = 100
            records_per_user = 50

            for user_i in range(num_users):
                user_id = f"memory_test_user_{user_i}"
                batch_manager.start_batch_mode(user_id)

                for record_i in range(records_per_user):
                    card_info = {
                        "name": f"名片{record_i}" * 10,  # 較長的文本
                        "company": f"公司{record_i}" * 10,
                        "notes": f"備註{record_i}" * 20,
                        "notion_url": f"https://notion.so/page-{user_i}-{record_i}",
                    }
                    batch_manager.add_processed_card(user_id, card_info)

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # 清理所有會話
            for user_i in range(num_users):
                user_id = f"memory_test_user_{user_i}"
                batch_manager.end_batch_mode(user_id)

            # 記憶體增長不應該過大
            max_allowed_increase = 200 * 1024 * 1024  # 200MB
            assert (
                memory_increase < max_allowed_increase
            ), f"記憶體增長過多: {memory_increase / 1024 / 1024:.2f}MB"

        except ImportError:
            pytest.skip("psutil 不可用，跳過記憶體測試")

    def test_session_cleanup_on_expiry(self, batch_manager):
        """測試過期會話的自動清理"""
        # 創建多個會話
        user_ids = ["cleanup_user_1", "cleanup_user_2", "cleanup_user_3"]

        for user_id in user_ids:
            batch_manager.start_batch_mode(user_id)

        assert len(batch_manager.user_sessions) == 3

        # 手動設置部分會話為過期
        batch_manager.user_sessions["cleanup_user_1"][
            "last_activity"
        ] = datetime.now() - timedelta(minutes=15)
        batch_manager.user_sessions["cleanup_user_2"][
            "last_activity"
        ] = datetime.now() - timedelta(minutes=20)

        # 檢查會話狀態（應該觸發清理）
        active_users = []
        for user_id in user_ids:
            if batch_manager.is_in_batch_mode(user_id):
                active_users.append(user_id)

        # 只有 cleanup_user_3 應該還活躍
        assert len(active_users) == 1
        assert "cleanup_user_3" in active_users
        assert len(batch_manager.user_sessions) == 1

    # ==========================================
    # 6. 統計和報告測試
    # ==========================================

    def test_comprehensive_statistics_report(self, batch_manager, sample_card_info):
        """測試全面的統計報告生成"""
        user_id = "stats_user"

        # 啟動批次模式
        batch_manager.start_batch_mode(user_id)

        # 添加多種類型的記錄
        for i in range(5):
            card_info = dict(sample_card_info)
            card_info["name"] = f"成功名片{i}"
            batch_manager.add_processed_card(user_id, card_info)

        for i in range(3):
            batch_manager.add_failed_card(user_id, f"失敗圖片{i}", f"錯誤原因{i}")

        # 等待一些時間
        time.sleep(0.2)

        # 獲取統計報告
        result = batch_manager.end_batch_mode(user_id)

        assert result["success"] is True
        stats = result["statistics"]

        # 驗證統計數據的完整性
        assert stats["total_processed"] == 5
        assert stats["total_failed"] == 3
        assert stats["total_time_minutes"] > 0
        assert len(stats["processed_cards"]) == 5
        assert len(stats["failed_cards"]) == 3

        # 驗證每條記錄的完整性
        for card in stats["processed_cards"]:
            assert "name" in card
            assert "company" in card
            assert "processed_time" in card

        for fail in stats["failed_cards"]:
            assert "description" in fail
            assert "error" in fail
            assert "failed_time" in fail

    def test_empty_session_statistics(self, batch_manager):
        """測試空會話的統計報告"""
        user_id = "empty_stats_user"

        # 啟動批次模式但不添加任何記錄
        batch_manager.start_batch_mode(user_id)

        # 立即結束
        result = batch_manager.end_batch_mode(user_id)

        assert result["success"] is True
        stats = result["statistics"]

        assert stats["total_processed"] == 0
        assert stats["total_failed"] == 0
        assert stats["total_time_minutes"] >= 0
        assert len(stats["processed_cards"]) == 0
        assert len(stats["failed_cards"]) == 0

    # ==========================================
    # 7. 邊緣案例和錯誤處理測試
    # ==========================================

    def test_invalid_user_id_handling(self, batch_manager):
        """測試無效用戶 ID 的處理"""
        invalid_user_ids = [None, "", "   ", 123, [], {}]

        for invalid_id in invalid_user_ids:
            try:
                # 這些操作不應該拋出異常
                batch_manager.start_batch_mode(str(invalid_id))
                batch_manager.is_in_batch_mode(str(invalid_id))
                batch_manager.end_batch_mode(str(invalid_id))
                # 如果到達這裡，說明處理了無效 ID
            except Exception as e:
                # 如果拋出異常，應該是合理的異常
                assert isinstance(e, (TypeError, ValueError))

    def test_corrupted_session_data_handling(self, batch_manager):
        """測試損壞會話數據的處理"""
        user_id = "corrupted_user"

        # 啟動正常會話
        batch_manager.start_batch_mode(user_id)

        # 人為損壞會話數據
        batch_manager.user_sessions[user_id]["processed_cards"] = "invalid_data"
        batch_manager.user_sessions[user_id]["start_time"] = "not_a_datetime"

        # 嘗試操作損壞的會話
        try:
            result = batch_manager.end_batch_mode(user_id)
            # 應該能夠處理損壞的數據或者拋出合理的異常
        except Exception as e:
            assert isinstance(e, (TypeError, AttributeError, ValueError))

    # ==========================================
    # 8. 整合測試
    # ==========================================

    def test_complete_batch_workflow(self, batch_manager, sample_card_info):
        """完整的批次工作流程測試"""
        user_id = "complete_workflow_user"

        # 1. 啟動批次模式
        start_result = batch_manager.start_batch_mode(user_id)
        assert start_result["success"] is True
        assert batch_manager.is_in_batch_mode(user_id) is True

        # 2. 處理多張名片
        card_results = []
        for i in range(10):
            card_info = dict(sample_card_info)
            card_info["name"] = f"測試名片{i}"
            card_info["company"] = f"測試公司{i}"

            if i % 3 == 0:  # 每3張中有1張失敗
                batch_manager.add_failed_card(user_id, f"名片{i}.jpg", "處理失敗")
            else:
                batch_manager.add_processed_card(user_id, card_info)
                card_results.append(card_info)

        # 3. 檢查中間狀態
        status = batch_manager.get_batch_status(user_id)
        assert status["is_active"] is True
        assert status["processed_count"] > 0
        assert status["failed_count"] > 0

        # 4. 結束批次模式
        end_result = batch_manager.end_batch_mode(user_id)
        assert end_result["success"] is True

        # 5. 驗證最終統計
        stats = end_result["statistics"]
        assert stats["total_processed"] == len(card_results)
        assert stats["total_failed"] == 10 - len(card_results)
        assert stats["total_time_minutes"] > 0

        # 6. 驗證會話清理
        assert user_id not in batch_manager.user_sessions
        assert batch_manager.is_in_batch_mode(user_id) is False


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
