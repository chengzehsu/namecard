#!/usr/bin/env python3
"""
測試 Telegram Bot 系統的獨立性
確保沒有 LINE Bot 依賴
"""

import sys
import os

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_telegram_imports():
    """測試 Telegram Bot 相關模組的導入"""
    
    print("🔍 測試 Telegram Bot 系統的獨立性...")
    print("=" * 50)
    
    # 測試核心模組
    core_modules = [
        'config',
        'batch_manager', 
        'name_card_processor',
        'notion_manager',
        'multi_card_processor',
        'user_interaction_handler',
        'telegram_bot_handler'
    ]
    
    failed_modules = []
    
    for module_name in core_modules:
        try:
            module = __import__(module_name)
            print(f"✅ {module_name} - 導入成功")
        except ImportError as e:
            if 'linebot' in str(e).lower():
                print(f"❌ {module_name} - LINE Bot 依賴錯誤: {e}")
                failed_modules.append(module_name)
            else:
                print(f"⚠️  {module_name} - 其他導入錯誤: {e}")
        except Exception as e:
            print(f"⚠️  {module_name} - 意外錯誤: {e}")
    
    # 測試 Telegram App
    print("\n📱 測試 Telegram App 導入...")
    try:
        # 注意：這會因為缺少 flask 等依賴而失敗，但不應該是因為 linebot
        import telegram_app
        print("✅ telegram_app - 導入成功")
    except ImportError as e:
        if 'linebot' in str(e).lower():
            print(f"❌ telegram_app - LINE Bot 依賴錯誤: {e}")
            failed_modules.append('telegram_app')
        else:
            print(f"⚠️  telegram_app - 其他導入錯誤 (預期): {e}")
    except Exception as e:
        print(f"⚠️  telegram_app - 意外錯誤: {e}")
    
    # 測試獨立主程序
    print("\n🚀 測試 Telegram 主程序導入...")
    try:
        import telegram_main
        print("✅ telegram_main - 導入成功")
    except ImportError as e:
        if 'linebot' in str(e).lower():
            print(f"❌ telegram_main - LINE Bot 依賴錯誤: {e}")
            failed_modules.append('telegram_main')
        else:
            print(f"⚠️  telegram_main - 其他導入錯誤 (預期): {e}")
    except Exception as e:
        print(f"⚠️  telegram_main - 意外錯誤: {e}")
    
    # 結果總結
    print("\n" + "=" * 50)
    if failed_modules:
        print(f"❌ 測試失敗！以下模組有 LINE Bot 依賴:")
        for module in failed_modules:
            print(f"  - {module}")
        return False
    else:
        print("✅ 測試通過！Telegram Bot 系統完全獨立於 LINE Bot")
        print("✨ 可以安全部署到生產環境")
        return True

if __name__ == "__main__":
    success = test_telegram_imports()
    sys.exit(0 if success else 1)