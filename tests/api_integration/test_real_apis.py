"""
真實 API 整合測試套件 - Test Engineer 實作
定期驗證與外部服務的整合狀況
"""

import pytest
import os
import time
from unittest.mock import patch
import requests
import sys

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from name_card_processor import NameCardProcessor
from notion_manager import NotionManager
from config import Config


@pytest.mark.api
@pytest.mark.slow
class TestRealAPIIntegration:
    """真實 API 整合測試類別"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_keys(self):
        """如果沒有 API 金鑰則跳過測試"""
        required_keys = [
            'GOOGLE_API_KEY',
            'NOTION_API_KEY', 
            'NOTION_DATABASE_ID'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not os.getenv(key) and not hasattr(Config, key):
                missing_keys.append(key)
        
        if missing_keys:
            pytest.skip(f"跳過真實 API 測試，缺少環境變數: {', '.join(missing_keys)}")
    
    @pytest.fixture
    def name_card_processor(self, skip_if_no_api_keys):
        """提供真實的名片處理器"""
        return NameCardProcessor()
    
    @pytest.fixture  
    def notion_manager(self, skip_if_no_api_keys):
        """提供真實的 Notion 管理器"""
        return NotionManager()
    
    def test_google_gemini_api_connectivity(self, name_card_processor):
        """測試 Google Gemini API 連接性"""
        print("🔗 測試 Google Gemini API 連接...")
        
        # 創建測試圖片數據（小型測試圖片）
        test_image_data = self._create_test_image_bytes()
        
        try:
            # 測試 API 調用
            start_time = time.time()
            result = name_card_processor.process_business_card(
                test_image_data, 
                user_id="api_test_user"
            )
            response_time = time.time() - start_time
            
            # 驗證響應
            assert result is not None, "Gemini API 無響應"
            print(f"✅ Gemini API 響應時間: {response_time:.2f}s")
            
            # 檢查 API 配額狀態
            if 'error' in result:
                if 'quota' in result['error'].lower() or 'limit' in result['error'].lower():
                    pytest.skip("API 配額已達上限，跳過此測試")
                else:
                    pytest.fail(f"Gemini API 錯誤: {result['error']}")
            
            # 性能基準檢查
            assert response_time < 30.0, f"API 響應時間過長: {response_time:.2f}s"
            
        except Exception as e:
            pytest.fail(f"Gemini API 連接失敗: {str(e)}")
    
    def test_notion_api_connectivity(self, notion_manager):
        """測試 Notion API 連接性"""
        print("🔗 測試 Notion API 連接...")
        
        # 測試數據
        test_card_data = {
            "name": "API測試用戶",
            "company": "測試公司",
            "email": "apitest@example.com",
            "phone": "+886-912-345-678",
            "department": "測試部門",
            "title": "測試工程師",
            "decision_influence": "中",
            "address": "台北市信義區測試路123號",
            "contact_source": "API整合測試",
            "notes": "這是API測試創建的記錄"
        }
        
        try:
            start_time = time.time()
            result = notion_manager.create_business_card_record(
                test_card_data,
                user_id="api_test_user",
                image_info={"message": "API測試圖片"}
            )
            response_time = time.time() - start_time
            
            # 驗證結果
            assert result.get("success") == True, f"Notion 記錄創建失敗: {result.get('error')}"
            assert "page_url" in result, "Notion 頁面 URL 缺失"
            
            print(f"✅ Notion API 響應時間: {response_time:.2f}s")
            print(f"✅ 創建的頁面: {result['page_url']}")
            
            # 性能基準檢查
            assert response_time < 15.0, f"Notion API 響應時間過長: {response_time:.2f}s"
            
        except Exception as e:
            pytest.fail(f"Notion API 連接失敗: {str(e)}")
    
    def test_api_rate_limiting_behavior(self, name_card_processor):
        """測試 API 速率限制行為"""
        print("⏱️ 測試 API 速率限制...")
        
        test_image_data = self._create_test_image_bytes()
        request_times = []
        errors = []
        
        # 快速連續請求測試
        for i in range(5):
            try:
                start_time = time.time()
                result = name_card_processor.process_business_card(
                    test_image_data,
                    user_id=f"rate_limit_test_user_{i}"
                )
                end_time = time.time()
                
                request_times.append(end_time - start_time)
                
                if 'error' in result:
                    errors.append(result['error'])
                
                # 避免過度請求
                time.sleep(1)
                
            except Exception as e:
                errors.append(str(e))
        
        # 分析結果
        avg_response_time = sum(request_times) / len(request_times) if request_times else 0
        rate_limit_errors = [e for e in errors if 'rate' in e.lower() or 'quota' in e.lower()]
        
        print(f"📊 速率限制測試結果:")
        print(f"   - 平均響應時間: {avg_response_time:.2f}s")
        print(f"   - 總錯誤數: {len(errors)}")
        print(f"   - 速率限制錯誤: {len(rate_limit_errors)}")
        
        # 記錄但不失敗（速率限制是預期行為）
        if rate_limit_errors:
            print(f"⚠️ 檢測到速率限制: {rate_limit_errors[0]}")
    
    def test_api_error_recovery(self, name_card_processor):
        """測試 API 錯誤恢復機制"""
        print("🔄 測試 API 錯誤恢復...")
        
        # 測試無效圖片數據
        invalid_image_data = b"invalid_image_data"
        
        try:
            result = name_card_processor.process_business_card(
                invalid_image_data,
                user_id="error_recovery_test_user"
            )
            
            # 應該優雅地處理錯誤
            assert result is not None, "應該返回錯誤訊息而不是 None"
            assert 'error' in result, "應該包含錯誤訊息"
            
            print(f"✅ 錯誤恢復測試通過: {result.get('error', '未知錯誤')}")
            
        except Exception as e:
            # 檢查是否是預期的錯誤類型
            expected_errors = ['image', 'format', 'invalid', 'decode']
            if any(keyword in str(e).lower() for keyword in expected_errors):
                print(f"✅ 預期錯誤處理正確: {str(e)}")
            else:
                pytest.fail(f"未預期的錯誤類型: {str(e)}")
    
    def test_end_to_end_api_workflow(self, name_card_processor, notion_manager):
        """測試端到端 API 工作流程"""
        print("🔄 測試端到端 API 工作流程...")
        
        # 創建測試圖片
        test_image_data = self._create_test_image_bytes()
        
        try:
            # 步驟 1: 名片識別
            print("   1️⃣ 執行名片識別...")
            start_time = time.time()
            
            process_result = name_card_processor.process_business_card(
                test_image_data,
                user_id="e2e_test_user"
            )
            
            process_time = time.time() - start_time
            
            # 檢查識別結果
            if 'error' in process_result:
                if 'quota' in process_result['error'].lower():
                    pytest.skip(f"API 配額限制: {process_result['error']}")
                else:
                    pytest.fail(f"名片識別失敗: {process_result['error']}")
            
            print(f"   ✅ 識別完成 ({process_time:.2f}s)")
            
            # 步驟 2: 存入 Notion
            print("   2️⃣ 存入 Notion 資料庫...")
            start_time = time.time()
            
            notion_result = notion_manager.create_business_card_record(
                process_result,
                user_id="e2e_test_user",
                image_info={"message": "端到端測試"}
            )
            
            notion_time = time.time() - start_time
            
            # 檢查 Notion 結果
            assert notion_result.get("success") == True, f"Notion 存儲失敗: {notion_result.get('error')}"
            
            print(f"   ✅ Notion 存儲完成 ({notion_time:.2f}s)")
            print(f"   📄 頁面 URL: {notion_result.get('page_url', 'N/A')}")
            
            # 總體性能檢查
            total_time = process_time + notion_time
            print(f"⏱️ 總處理時間: {total_time:.2f}s")
            
            assert total_time < 45.0, f"端到端處理時間過長: {total_time:.2f}s"
            
        except Exception as e:
            pytest.fail(f"端到端工作流程失敗: {str(e)}")
    
    def _create_test_image_bytes(self) -> bytes:
        """創建測試用圖片數據"""
        # 創建一個簡單的測試圖片（1x1 像素 PNG）
        # PNG 格式的最小有效圖片
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13'
            b'\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```'
            b'\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return png_data


@pytest.mark.health_check
class TestAPIHealthChecks:
    """API 健康檢查測試"""
    
    def test_external_service_availability(self):
        """測試外部服務可用性"""
        services = {
            "Google Gemini": "https://generativelanguage.googleapis.com",
            "Notion API": "https://api.notion.com/v1"
        }
        
        results = {}
        
        for service_name, base_url in services.items():
            try:
                response = requests.get(f"{base_url}/", timeout=10)
                results[service_name] = {
                    "available": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
                print(f"✅ {service_name}: 可用 ({response.status_code})")
            except requests.RequestException as e:
                results[service_name] = {
                    "available": False,
                    "error": str(e),
                    "response_time": None
                }
                print(f"❌ {service_name}: 不可用 - {str(e)}")
        
        # 至少一個服務應該可用
        available_services = [name for name, info in results.items() if info["available"]]
        assert len(available_services) > 0, "所有外部服務都不可用"


if __name__ == "__main__":
    # 運行真實 API 測試
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "api"])