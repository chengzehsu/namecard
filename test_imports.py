#!/usr/bin/env python3
"""
測試 import 路徑是否正確
"""

import sys
import os

# 添加專案根目錄到 Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """測試各種 import"""
    print("🔍 測試 import 路徑...")
    
    # 測試基本模組
    try:
        print("  ✅ 測試基本 Python 模組...")
        import asyncio
        import time
        print("    ✅ asyncio, time - OK")
    except ImportError as e:
        print(f"    ❌ 基本模組失敗: {e}")
        return False
    
    # 測試配置
    try:
        print("  ✅ 測試配置模組...")
        from simple_config import Config
        print("    ✅ Config - OK")
    except ImportError as e:
        print(f"    ❌ Config 失敗: {e}")
        # 嘗試複雜配置
        try:
            from config.settings import get_config
            config = get_config()
            print("    ✅ Complex Config - OK")
        except ImportError as e2:
            print(f"    ❌ 複雜配置也失敗: {e2}")
            return False
    
    # 測試地址服務
    try:
        print("  ✅ 測試地址服務...")
        from src.namecard.core.services.address_service import AddressNormalizer
        normalizer = AddressNormalizer()
        print("    ✅ AddressNormalizer - OK")
    except ImportError as e:
        print(f"    ❌ AddressNormalizer 失敗: {e}")
        return False
    
    # 測試 AI 相關
    try:
        print("  ✅ 測試 AI 相關模組...")
        import google.generativeai as genai
        from PIL import Image
        print("    ✅ Gemini AI, PIL - OK")
    except ImportError as e:
        print(f"    ❌ AI 模組失敗: {e}")
        return False
    
    # 測試異步框架
    try:
        print("  ✅ 測試異步框架...")
        from quart import Quart
        import hypercorn
        print("    ✅ Quart, Hypercorn - OK")
    except ImportError as e:
        print(f"    ❌ 異步框架失敗: {e}")
        return False
    
    print("🎉 所有 import 測試通過！")
    return True

def test_async_components():
    """測試異步組件能否正確載入"""
    print("\n🧪 測試異步組件載入...")
    
    try:
        # 測試異步卡片處理器
        print("  ✅ 載入 AsyncCardProcessor...")
        sys.path.append(os.path.join(project_root, 'src'))
        from src.namecard.infrastructure.ai.async_card_processor import AsyncCardProcessor, ProcessingPriority
        print("    ✅ AsyncCardProcessor - OK")
        
        # 測試批次服務
        print("  ✅ 載入 AsyncBatchService...")
        from src.namecard.core.services.async_batch_service import AsyncBatchService
        print("    ✅ AsyncBatchService - OK")
        
        # 測試統一服務
        print("  ✅ 載入 OptimizedAIService...")
        from src.namecard.infrastructure.ai.optimized_ai_service import OptimizedAIService
        print("    ✅ OptimizedAIService - OK")
        
        print("🎉 所有異步組件載入成功！")
        return True
        
    except Exception as e:
        print(f"❌ 異步組件載入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 開始 import 路徑測試...")
    
    success = True
    success &= test_imports()
    success &= test_async_components()
    
    if success:
        print("\n✅ 所有測試通過！系統準備就緒。")
        sys.exit(0)
    else:
        print("\n❌ 部分測試失敗，需要修復。")
        sys.exit(1)