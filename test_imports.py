#!/usr/bin/env python3
"""
測試所有重要模組的導入是否正常
"""
import sys
import os

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)

def test_config_import():
    """测试配置導入"""
    try:
        from simple_config import Config
        print("✅ simple_config.Config 導入成功")
        
        # 測試配置方法
        config_valid = Config.validate()
        print(f"✅ Config.validate() 運行成功: {config_valid}")
        
        return True
    except Exception as e:
        print(f"❌ Config 導入失敗: {e}")
        return False

def test_main_app_imports():
    """測試主應用導入"""
    try:
        from src.namecard.api.telegram_bot.main import flask_app
        print("✅ Telegram Bot Flask app 導入成功")
        
        from src.namecard.api.line_bot.main import app
        print("✅ LINE Bot Flask app 導入成功")
        
        return True
    except Exception as e:
        print(f"❌ 主應用導入失敗: {e}")
        return False

def test_core_services():
    """測試核心服務導入"""
    try:
        from src.namecard.core.services.batch_service import BatchManager
        print("✅ BatchManager 導入成功")
        
        from src.namecard.core.services.multi_card_service import MultiCardProcessor
        print("✅ MultiCardProcessor 導入成功")
        
        from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
        print("✅ NameCardProcessor 導入成功")
        
        from src.namecard.infrastructure.storage.notion_client import NotionManager
        print("✅ NotionManager 導入成功")
        
        return True
    except Exception as e:
        print(f"❌ 核心服務導入失敗: {e}")
        return False

def test_infrastructure():
    """測試基礎設施導入"""
    try:
        from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
        print("✅ TelegramBotHandler 導入成功")
        
        from src.namecard.core.services.interaction_service import UserInteractionHandler
        print("✅ UserInteractionHandler 導入成功")
        
        return True
    except Exception as e:
        print(f"❌ 基礎設施導入失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🧪 開始測試所有模組導入...")
    print(f"📂 工作目錄: {os.getcwd()}")
    print(f"🐍 Python 路徑: {sys.path[:3]}...")
    print()
    
    all_tests_passed = True
    
    # 運行所有測試
    tests = [
        ("配置模組", test_config_import),
        ("主應用", test_main_app_imports),
        ("核心服務", test_core_services),
        ("基礎設施", test_infrastructure),
    ]
    
    for test_name, test_func in tests:
        print(f"🔍 測試 {test_name}...")
        try:
            if test_func():
                print(f"✅ {test_name} 測試通過\n")
            else:
                print(f"❌ {test_name} 測試失敗\n")
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}\n")
            all_tests_passed = False
    
    print("=" * 50)
    if all_tests_passed:
        print("🎉 所有導入測試通過！可以安全部署。")
        return 0
    else:
        print("❌ 部分導入測試失敗，請修復後再部署。")
        return 1

if __name__ == "__main__":
    exit(main())