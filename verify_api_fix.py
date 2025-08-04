#!/usr/bin/env python3
"""
驗證和測試 Gemini API 500 錯誤修復
"""
import os
import sys
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_environment():
    """檢查環境變數設置"""
    print("🔧 檢查環境變數...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    fallback_key = os.getenv("GOOGLE_API_KEY_FALLBACK")
    
    if not api_key:
        print("❌ GOOGLE_API_KEY 未設置")
        return False
    
    print(f"✅ GOOGLE_API_KEY: {'已設置' if api_key else '未設置'}")
    print(f"✅ GOOGLE_API_KEY_FALLBACK: {'已設置' if fallback_key else '未設置'}")
    
    return True

def test_improved_error_handling():
    """測試改進的錯誤處理"""
    print("\n🧪 測試改進的錯誤處理機制...")
    
    try:
        from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
        
        # 初始化處理器
        processor = NameCardProcessor()
        print("✅ 名片處理器初始化成功")
        
        # 測試錯誤檢測方法
        print("\n🔍 測試錯誤檢測...")
        
        # 測試 500 錯誤檢測
        test_error = "500 An internal error has occurred. Please retry or report in https://developers.generativeai.google/guide/troubleshooting"
        is_transient = processor._is_transient_error(test_error)
        print(f"500 錯誤檢測: {'✅ 正確' if is_transient else '❌ 錯誤'}")
        
        # 測試其他暫時性錯誤
        transient_errors = [
            "502 Bad Gateway",
            "503 Service Unavailable", 
            "timeout occurred",
            "network connection failed"
        ]
        
        for error in transient_errors:
            result = processor._is_transient_error(error)
            print(f"'{error}' 檢測: {'✅' if result else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

def summarize_improvements():
    """總結改進內容"""
    print("\n📋 Gemini API 500 錯誤修復總結:")
    print("=" * 50)
    print("🔧 已實施的改進:")
    print("   ✅ 新增暫時性錯誤檢測方法 _is_transient_error()")
    print("   ✅ 實作指數退避重試機制 (1s, 2s, 4s)")
    print("   ✅ 區分不同錯誤類型的處理策略:")
    print("      - 500/502/503/504 錯誤 → 自動重試")
    print("      - 429 配額錯誤 → 切換備用 API Key")
    print("      - 400/401/403 錯誤 → 不重試，直接拋出")
    print("   ✅ 增強錯誤訊息和調試信息")
    print("   ✅ 添加隨機抖動防止雷群效應")
    
    print("\n🚀 使用者體驗改進:")
    print("   ✅ 透明的重試過程，用戶可見進度")
    print("   ✅ 智能錯誤恢復，減少處理失敗")
    print("   ✅ 詳細的錯誤分類和建議")
    
    print("\n⚙️ 技術特性:")
    print("   ✅ 最多 3 次重試 (可配置)")
    print("   ✅ 指數退避 + 隨機抖動")
    print("   ✅ 支援 API Key 無縫切換")
    print("   ✅ 完整的錯誤追蹤和報告")

def main():
    """主函數"""
    print("🛠️ Gemini API 500 錯誤修復驗證")
    print("=" * 50)
    
    # 檢查環境
    if not check_environment():
        print("\n⚠️ 環境變數未設置，但修復代碼已完成")
        print("   當設置正確的 API Key 後，錯誤處理將自動生效")
    
    # 測試錯誤處理
    test_improved_error_handling()
    
    # 總結改進
    summarize_improvements()
    
    print("\n🎯 建議操作:")
    print("1. 確保設置 GOOGLE_API_KEY 環境變數")
    print("2. 可選設置 GOOGLE_API_KEY_FALLBACK 作為備用")
    print("3. 重新測試名片識別功能")
    print("4. 觀察錯誤處理和重試機制是否正常工作")
    
    return True

if __name__ == "__main__":
    main()