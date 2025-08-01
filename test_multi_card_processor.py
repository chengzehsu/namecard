#!/usr/bin/env python3
"""
多名片處理系統測試套件
測試場景：單張名片、多張名片、品質評估、用戶交互
"""

import json
import sys
import os
from datetime import datetime

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from multi_card_processor import MultiCardProcessor
    from user_interaction_handler import UserInteractionHandler
    from name_card_processor import NameCardProcessor
except ImportError as e:
    print(f"❌ 導入模組失敗: {e}")
    print("請確保所有相關檔案都在正確位置")
    sys.exit(1)


class MultiCardTestSuite:
    """多名片處理系統測試套件"""

    def __init__(self):
        """初始化測試套件"""
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def run_all_tests(self):
        """執行所有測試"""
        print("🧪 開始多名片處理系統測試")
        print("=" * 50)

        # 單元測試
        self.test_name_card_processor()
        self.test_multi_card_processor()
        self.test_user_interaction_handler()

        # 整合測試
        self.test_single_card_workflow()
        self.test_multi_card_workflow()
        self.test_quality_assessment()
        self.test_user_choice_handling()

        # 顯示測試結果
        self.show_test_summary()

    def test_name_card_processor(self):
        """測試名片處理器的多名片檢測功能"""
        print("\n📋 測試: NameCardProcessor 多名片檢測")

        try:
            processor = NameCardProcessor()

            # 測試空圖片處理
            result = processor.extract_multi_card_info(b"")
            self.assert_true("error" in result, "空圖片應該返回錯誤")

            # 測試新格式兼容性（模擬單一名片回應）
            single_card_data = {
                "name": "測試用戶",
                "company": "測試公司",
                "email": "test@example.com",
            }

            multi_format = processor._convert_single_card_to_multi_format(
                single_card_data
            )
            self.assert_true(
                multi_format.get("card_count") == 1, "單一名片應該轉換為 card_count = 1"
            )
            self.assert_true(
                len(multi_format.get("cards", [])) == 1, "應該包含一張名片資料"
            )

            print("✅ NameCardProcessor 測試通過")

        except Exception as e:
            self.record_failure("NameCardProcessor", str(e))

    def test_multi_card_processor(self):
        """測試多名片處理器"""
        print("\n📋 測試: MultiCardProcessor")

        try:
            processor = MultiCardProcessor()

            # 測試空圖片
            result = processor.process_image_with_quality_check(b"")
            self.assert_true("error" in result, "空圖片應該返回錯誤")

            print("✅ MultiCardProcessor 基本測試通過")

        except Exception as e:
            self.record_failure("MultiCardProcessor", str(e))

    def test_user_interaction_handler(self):
        """測試用戶交互處理器"""
        print("\n📋 測試: UserInteractionHandler")

        try:
            handler = UserInteractionHandler()

            # 測試會話管理
            user_id = "test_user_123"

            # 測試無會話狀態
            self.assert_false(
                handler.has_pending_session(user_id), "新用戶不應該有待處理會話"
            )

            # 創建模擬的分析結果
            mock_analysis = {
                "card_count": 2,
                "cards": [
                    {"name": "張三", "company": "ABC公司", "confidence_score": 0.9},
                    {"name": "李四", "company": "DEF公司", "confidence_score": 0.6},
                ],
                "overall_quality": "partial",
                "user_options": ["分別處理所有名片", "重新拍攝"],
                "good_cards": [1],
                "poor_cards": [2],
            }

            # 創建會話
            message = handler.create_multi_card_session(user_id, mock_analysis)
            self.assert_true(
                "檢測到 **2** 張名片" in message or "檢測到 2 張名片" in message,
                "會話訊息應該包含名片數量",
            )

            # 檢查會話是否創建
            self.assert_true(handler.has_pending_session(user_id), "應該有待處理會話")

            # 測試用戶選擇處理
            choice_result = handler.handle_user_choice(user_id, "1")
            self.assert_true(
                choice_result.get("action") in ["process_all_cards", "retake_photo"],
                "應該返回有效的處理動作",
            )

            # 會話應該被清理
            self.assert_false(
                handler.has_pending_session(user_id), "處理後會話應該被清理"
            )

            print("✅ UserInteractionHandler 測試通過")

        except Exception as e:
            self.record_failure("UserInteractionHandler", str(e))

    def test_single_card_workflow(self):
        """測試單張名片工作流程"""
        print("\n📋 測試: 單張名片工作流程")

        try:
            # 模擬高品質單張名片
            mock_single_card = {
                "card_count": 1,
                "cards": [
                    {
                        "card_index": 1,
                        "name": "高品質用戶",
                        "company": "優質公司",
                        "confidence_score": 0.95,
                        "clarity_issues": [],
                    }
                ],
                "overall_quality": "good",
            }

            processor = MultiCardProcessor()
            result = processor._analyze_and_recommend_action(mock_single_card)

            # 高品質單張名片應該自動處理
            self.assert_true(
                result.get("auto_process") == True, "高品質單張名片應該標記為自動處理"
            )

            print("✅ 單張名片工作流程測試通過")

        except Exception as e:
            self.record_failure("單張名片工作流程", str(e))

    def test_multi_card_workflow(self):
        """測試多張名片工作流程"""
        print("\n📋 測試: 多張名片工作流程")

        try:
            # 模擬多張名片場景
            mock_multi_card = {
                "card_count": 3,
                "cards": [
                    {"name": "用戶1", "company": "公司1", "confidence_score": 0.9},
                    {"name": "用戶2", "company": "公司2", "confidence_score": 0.7},
                    {"name": None, "company": "公司3", "confidence_score": 0.4},
                ],
                "overall_quality": "partial",
            }

            processor = MultiCardProcessor()
            result = processor._analyze_and_recommend_action(mock_multi_card)

            # 多張名片應該需要用戶選擇
            self.assert_true(
                result.get("action_required") == True, "多張名片應該需要用戶選擇"
            )

            self.assert_true(
                len(result.get("user_options", [])) > 0, "應該提供用戶選項"
            )

            print("✅ 多張名片工作流程測試通過")

        except Exception as e:
            self.record_failure("多張名片工作流程", str(e))

    def test_quality_assessment(self):
        """測試品質評估功能"""
        print("\n📋 測試: 品質評估功能")

        try:
            processor = MultiCardProcessor()

            # 測試高品質評估
            high_quality_card = {
                "name": "完整用戶",
                "company": "完整公司",
                "email": "complete@example.com",
                "phone": "+886912345678",
                "title": "經理",
            }

            # 使用 NameCardProcessor 來測試信心度計算
            card_processor = NameCardProcessor()
            confidence = card_processor._calculate_single_card_confidence(
                high_quality_card
            )
            self.assert_true(
                confidence >= 0.8, f"高品質名片信心度應該 >= 0.8，實際: {confidence}"
            )

            # 測試低品質評估
            low_quality_card = {"name": None, "company": "部分公司"}

            confidence = card_processor._calculate_single_card_confidence(
                low_quality_card
            )
            self.assert_true(
                confidence < 0.8, f"低品質名片信心度應該 < 0.8，實際: {confidence}"
            )

            print("✅ 品質評估測試通過")

        except Exception as e:
            self.record_failure("品質評估", str(e))

    def test_user_choice_handling(self):
        """測試用戶選擇處理"""
        print("\n📋 測試: 用戶選擇處理")

        try:
            handler = UserInteractionHandler()

            # 測試數字選擇解析
            mock_analysis = {
                "user_options": ["分別處理所有名片", "重新拍攝"],
                "cards": [{"name": "測試"}],
            }

            # 測試數字選擇
            result = handler._parse_user_choice("1", mock_analysis)
            self.assert_true(
                result.get("action") == "process_all_cards", "數字1應該對應第一個選項"
            )

            # 測試文字選擇
            result = handler._parse_user_choice("重新拍攝", mock_analysis)
            self.assert_true(
                result.get("action") == "retake_photo", "重新拍攝應該觸發重拍動作"
            )

            # 測試無效選擇
            result = handler._parse_user_choice("無效選擇", mock_analysis)
            self.assert_true(
                result.get("action") == "invalid_choice", "無效選擇應該返回錯誤"
            )

            print("✅ 用戶選擇處理測試通過")

        except Exception as e:
            self.record_failure("用戶選擇處理", str(e))

    def assert_true(self, condition, message):
        """斷言為真"""
        if condition:
            self.passed += 1
            self.test_results.append({"status": "PASS", "message": message})
        else:
            self.failed += 1
            self.test_results.append({"status": "FAIL", "message": message})
            print(f"❌ 斷言失敗: {message}")

    def assert_false(self, condition, message):
        """斷言為假"""
        self.assert_true(not condition, message)

    def record_failure(self, test_name, error):
        """記錄測試失敗"""
        self.failed += 1
        message = f"{test_name} 測試失敗: {error}"
        self.test_results.append({"status": "ERROR", "message": message})
        print(f"❌ {message}")

    def show_test_summary(self):
        """顯示測試摘要"""
        print("\n" + "=" * 50)
        print("📊 測試結果摘要")
        print("=" * 50)

        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0

        print(f"✅ 通過: {self.passed}")
        print(f"❌ 失敗: {self.failed}")
        print(f"📈 成功率: {success_rate:.1f}%")

        if self.failed > 0:
            print("\n❌ 失敗的測試:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"  • {result['message']}")

        print("\n🎯 測試完成")

        # 返回是否全部通過
        all_passed = self.failed == 0
        if all_passed:
            print("✅ 單元測試全部通過")
        return all_passed


def run_integration_test():
    """執行整合測試"""
    print("\n🔗 整合測試: 完整工作流程")

    try:
        # 模擬完整的多名片處理流程
        multi_processor = MultiCardProcessor()
        interaction_handler = UserInteractionHandler()

        # 模擬多名片分析結果
        mock_analysis = {
            "card_count": 2,
            "cards": [
                {
                    "name": "張三",
                    "company": "ABC公司",
                    "confidence_score": 0.9,
                    "card_index": 1,
                },
                {
                    "name": "李四",
                    "company": "DEF公司",
                    "confidence_score": 0.6,
                    "card_index": 2,
                },
            ],
            "overall_quality": "partial",
            "action_required": True,
            "user_options": ["分別處理所有名片", "只處理品質良好的名片", "重新拍攝"],
            "good_cards": [1],
            "poor_cards": [2],
        }

        user_id = "integration_test_user"

        # 1. 創建多名片會話
        choice_message = interaction_handler.create_multi_card_session(
            user_id, mock_analysis
        )
        print(f"✅ 會話創建成功，訊息長度: {len(choice_message)}")

        # 2. 模擬用戶選擇
        choice_result = interaction_handler.handle_user_choice(
            user_id, "2"
        )  # 選擇第二個選項
        print(f"✅ 用戶選擇處理成功: {choice_result.get('action', 'unknown')}")

        # 3. 獲取要處理的名片
        if choice_result.get("cards_to_process"):
            cards = choice_result["cards_to_process"]
            print(f"✅ 獲取到 {len(cards)} 張名片待處理")

        print("✅ 整合測試通過")
        return True

    except Exception as e:
        print(f"❌ 整合測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🚀 多名片處理系統測試開始")
    print(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 執行單元測試
    test_suite = MultiCardTestSuite()
    unit_test_passed = test_suite.run_all_tests()

    # 執行整合測試
    integration_test_passed = run_integration_test()

    # 整體結果
    print("\n" + "=" * 60)
    if unit_test_passed and integration_test_passed:
        print("🎉 所有測試通過！多名片處理系統準備就緒")
        print("✅ 系統可以正常處理:")
        print("  • 單張名片自動識別")
        print("  • 多張名片檢測和用戶選擇")
        print("  • 品質評估和建議")
        print("  • 用戶交互會話管理")
        return 0
    else:
        print("⚠️ 部分測試失敗，請檢查上述錯誤訊息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
