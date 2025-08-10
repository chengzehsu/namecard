#!/usr/bin/env python3
"""
LINE Bot 名片管理系統測試腳本
驗證各項功能是否正常運作
"""

import os
import sys
from datetime import datetime

import requests

# 添加 src 目錄到 Python 路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


class LineBotTester:
    def __init__(self, base_url="http://localhost:5002"):
        self.base_url = base_url
        self.test_results = []

    def log_test(self, test_name, success, message=""):
        """記錄測試結果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}: {message}")

    def test_health_check(self):
        """測試健康檢查端點"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("健康檢查", True, "服務運行正常")
                else:
                    self.log_test("健康檢查", False, f"狀態異常: {data}")
            else:
                self.log_test("健康檢查", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("健康檢查", False, f"連接失敗: {e}")

    def test_service_connections(self):
        """測試服務連接狀態"""
        try:
            response = requests.get(f"{self.base_url}/test", timeout=15)
            if response.status_code == 200:
                data = response.json()

                # 測試 Notion 連接
                notion_test = data.get("notion", {})
                if notion_test.get("success"):
                    self.log_test(
                        "Notion 連接",
                        True,
                        f"資料庫: {notion_test.get('database_title', 'Unknown')}",
                    )
                else:
                    self.log_test(
                        "Notion 連接", False, notion_test.get("error", "未知錯誤")
                    )

                # 測試 Gemini 連接
                gemini_test = data.get("gemini", {})
                if gemini_test.get("success"):
                    self.log_test("Gemini AI", True, "AI 服務可用")
                else:
                    self.log_test(
                        "Gemini AI", False, gemini_test.get("error", "未知錯誤")
                    )
            else:
                self.log_test("服務連接測試", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("服務連接測試", False, f"測試失敗: {e}")

    def test_webhook_endpoint(self):
        """測試 Webhook 端點"""
        try:
            # GET 請求應該返回資訊
            response = requests.get(f"{self.base_url}/callback", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "LINE Bot webhook" in data.get("message", ""):
                    self.log_test("Webhook GET", True, "端點可訪問")
                else:
                    self.log_test("Webhook GET", False, "回應格式異常")
            else:
                self.log_test("Webhook GET", False, f"HTTP {response.status_code}")

            # POST 請求應該返回 400 (缺少簽名)
            response = requests.post(
                f"{self.base_url}/callback", json={"test": "data"}, timeout=10
            )
            if response.status_code == 400:
                self.log_test("Webhook POST", True, "正確拒絕無效請求")
            else:
                self.log_test(
                    "Webhook POST", False, f"HTTP {response.status_code} (預期 400)"
                )
        except Exception as e:
            self.log_test("Webhook 測試", False, f"測試失敗: {e}")

    def test_configuration(self):
        """測試配置驗證"""
        try:
            from simple_config import Config

            # 檢查關鍵配置是否存在
            required_configs = [
                ("LINE_CHANNEL_ACCESS_TOKEN", Config.LINE_CHANNEL_ACCESS_TOKEN),
                ("LINE_CHANNEL_SECRET", Config.LINE_CHANNEL_SECRET),
                ("GOOGLE_API_KEY", Config.GOOGLE_API_KEY),
                ("NOTION_API_KEY", Config.NOTION_API_KEY),
                ("NOTION_DATABASE_ID", Config.NOTION_DATABASE_ID),
            ]

            missing_configs = []
            for name, value in required_configs:
                if not value:
                    missing_configs.append(name)

            if not missing_configs:
                self.log_test("環境變數配置", True, "所有必要配置已設置")
            else:
                self.log_test(
                    "環境變數配置", False, f"缺少: {', '.join(missing_configs)}"
                )

            # 測試配置驗證方法
            if Config.validate():
                self.log_test("配置驗證", True, "通過驗證")
            else:
                self.log_test("配置驗證", False, "驗證失敗")

        except Exception as e:
            self.log_test("配置測試", False, f"測試失敗: {e}")

    def test_imports(self):
        """測試關鍵模組導入"""
        import_tests = [
            ("LINE Bot SDK", "linebot"),
            ("Flask", "flask"),
            ("Pillow", "PIL"),
            ("Google Generative AI", "google.generativeai"),
            ("Notion Client", "notion_client"),
            ("Requests", "requests"),
        ]

        for name, module_name in import_tests:
            try:
                __import__(module_name)
                self.log_test(f"導入 {name}", True, f"{module_name} 可用")
            except ImportError as e:
                self.log_test(f"導入 {name}", False, f"導入失敗: {e}")

    def test_core_components(self):
        """測試核心組件初始化"""
        try:
            from src.namecard.infrastructure.ai.card_processor import NameCardProcessor

            NameCardProcessor()
            self.log_test("名片處理器初始化", True, "Gemini AI 處理器正常")
        except Exception as e:
            self.log_test("名片處理器初始化", False, f"初始化失敗: {e}")

        try:
            from src.namecard.infrastructure.storage.notion_client import NotionManager

            NotionManager()
            self.log_test("Notion 管理器初始化", True, "Notion 客戶端正常")
        except Exception as e:
            self.log_test("Notion 管理器初始化", False, f"初始化失敗: {e}")

    def generate_report(self):
        """生成測試報告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["success"])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 60)
        print("📊 LINE Bot 測試報告")
        print("=" * 60)
        print(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 總測試數: {total_tests}")
        print(f"✅ 通過: {passed_tests}")
        print(f"❌ 失敗: {failed_tests}")
        print(f"📈 成功率: {(passed_tests/total_tests)*100:.1f}%")

        if failed_tests > 0:
            print("\n❌ 失敗的測試:")
            for test in self.test_results:
                if not test["success"]:
                    print(f"   • {test['test']}: {test['message']}")

        print("\n💡 建議:")
        if failed_tests == 0:
            print("   🎉 所有測試通過！LINE Bot 系統就緒")
            print("   🚀 可以開始部署到生產環境")
        else:
            print("   🔧 請修復失敗的測試項目")
            print("   📝 檢查環境變數和依賴包安裝")
            if any(
                "連接" in test["test"]
                for test in self.test_results
                if not test["success"]
            ):
                print("   🌐 確認網路連接和 API Keys 正確性")

        print("=" * 60)
        return failed_tests == 0

    def run_all_tests(self):
        """執行所有測試"""
        print("🧪 開始執行 LINE Bot 系統測試...")
        print()

        # 按優先級執行測試
        self.test_imports()
        self.test_configuration()
        self.test_core_components()
        self.test_health_check()
        self.test_service_connections()
        self.test_webhook_endpoint()

        # 生成報告
        return self.generate_report()


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="LINE Bot 名片管理系統測試")
    parser.add_argument(
        "--url",
        default="http://localhost:5002",
        help="LINE Bot 服務 URL (預設: http://localhost:5002)",
    )
    parser.add_argument(
        "--skip-network", action="store_true", help="跳過網路相關測試 (僅測試本地組件)"
    )

    args = parser.parse_args()

    tester = LineBotTester(args.url)

    if args.skip_network:
        print("⚠️ 跳過網路測試模式")
        tester.test_imports()
        tester.test_configuration()
        tester.test_core_components()
    else:
        success = tester.run_all_tests()

    # 返回適當的退出碼
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
