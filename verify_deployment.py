#!/usr/bin/env python3
"""
Telegram Bot 部署驗證腳本
確保所有修復都正確完成
"""

import os
import sys
import ast

def check_linebot_dependencies():
    """檢查是否還有 linebot 依賴"""
    print("🔍 檢查 LINE Bot 依賴...")
    
    # 核心 Telegram Bot 文件
    telegram_files = [
        'main.py',
        'telegram_main.py', 
        'telegram_app.py',
        'telegram_bot_handler.py'
    ]
    
    # 核心共享模組
    shared_modules = [
        'config.py',
        'batch_manager.py',
        'name_card_processor.py',
        'notion_manager.py',
        'multi_card_processor.py',
        'user_interaction_handler.py',
        'address_normalizer.py'
    ]
    
    all_files = telegram_files + shared_modules
    has_linebot_deps = False
    
    for filepath in all_files:
        if not os.path.exists(filepath):
            print(f"⚠️  {filepath} 不存在")
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            linebot_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if 'linebot' in name.name.lower():
                            linebot_imports.append(f'import {name.name}')
                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'linebot' in node.module.lower():
                        linebot_imports.append(f'from {node.module} import ...')
            
            if linebot_imports:
                print(f"❌ {filepath} 包含 LINE Bot 依賴:")
                for imp in linebot_imports:
                    print(f"    {imp}")
                has_linebot_deps = True
            else:
                print(f"✅ {filepath} - 無 LINE Bot 依賴")
                
        except Exception as e:
            print(f"⚠️  {filepath} 檢查失敗: {e}")
    
    return not has_linebot_deps

def check_file_structure():
    """檢查文件結構"""
    print("\n📁 檢查文件結構...")
    
    required_files = [
        'main.py',
        'telegram_main.py',
        'telegram_app.py', 
        'telegram_bot_handler.py',
        'requirements-telegram.txt',
        'config.py',
        'name_card_processor.py',
        'notion_manager.py',
        'batch_manager.py',
        'multi_card_processor.py',
        'user_interaction_handler.py',
        'address_normalizer.py'
    ]
    
    missing_files = []
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"✅ {filepath}")
        else:
            print(f"❌ {filepath} 缺失")
            missing_files.append(filepath)
    
    return len(missing_files) == 0

def check_deployment_config():
    """檢查部署配置"""
    print("\n⚙️ 檢查部署配置...")
    
    deploy_file = '.github/workflows/deploy-telegram-bot.yml'
    if not os.path.exists(deploy_file):
        print(f"❌ {deploy_file} 不存在")
        return False
    
    with open(deploy_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('主入口配置', 'python main.py'),
        ('文件觸發', 'main.py'),
        ('文件觸發', 'telegram_main.py'), 
        ('必要文件檢查', 'telegram_main.py'),
        ('語法檢查', 'telegram_main.py')
    ]
    
    all_passed = True
    for check_name, expected_content in checks:
        if expected_content in content:
            print(f"✅ {check_name} - 配置正確")
        else:
            print(f"❌ {check_name} - 缺少: {expected_content}")
            all_passed = False
    
    return all_passed

def simulate_import_test():
    """模擬導入測試"""
    print("\n🧪 模擬導入測試...")
    
    # 添加當前目錄到 Python 路徑
    sys.path.insert(0, os.getcwd())
    
    test_modules = [
        ('config', 'Config'),
        ('batch_manager', 'BatchManager'),
        ('name_card_processor', 'NameCardProcessor'),
        ('notion_manager', 'NotionManager'),
        ('multi_card_processor', 'MultiCardProcessor'),
        ('user_interaction_handler', 'UserInteractionHandler'),
        ('address_normalizer', 'AddressNormalizer')
    ]
    
    failed_imports = []
    
    for module_name, class_name in test_modules:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name}")
            else:
                print(f"⚠️  {module_name}.{class_name} - 類別不存在")
        except ImportError as e:
            if 'linebot' in str(e).lower():
                print(f"❌ {module_name} - LINE Bot 依賴錯誤: {e}")
                failed_imports.append(module_name)
            else:
                print(f"⚠️  {module_name} - 依賴缺失 (正常): {e}")
        except Exception as e:
            print(f"⚠️  {module_name} - 其他錯誤: {e}")
    
    # 測試主入口
    try:
        import telegram_main
        print("✅ telegram_main - 獨立入口可導入")
    except ImportError as e:
        if 'linebot' in str(e).lower():
            print(f"❌ telegram_main - LINE Bot 依賴錯誤: {e}")
            failed_imports.append('telegram_main')
        else:
            print(f"⚠️  telegram_main - 依賴缺失 (正常): {e}")
    except Exception as e:
        print(f"⚠️  telegram_main - 其他錯誤: {e}")
    
    return len(failed_imports) == 0

def main():
    """主驗證流程"""
    print("🚀 Telegram Bot 部署驗證開始")
    print("=" * 60)
    
    tests = [
        ("LINE Bot 依賴檢查", check_linebot_dependencies),
        ("文件結構檢查", check_file_structure), 
        ("部署配置檢查", check_deployment_config),
        ("導入測試", simulate_import_test)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 執行失敗: {e}")
            results.append((test_name, False))
    
    # 總結
    print("\n" + "=" * 60)
    print("📊 驗證結果總結:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有驗證通過！Telegram Bot 可以安全部署")
        print("\n📋 部署步驟:")
        print("1. 提交代碼到 GitHub")
        print("2. GitHub Actions 會自動觸發部署")
        print("3. 或手動觸發: gh workflow run '部署 Telegram Bot 到 Zeabur'")
        print("4. 部署完成後更新 Telegram webhook URL")
        return 0
    else:
        print("❌ 驗證失敗！請修復上述問題後重新驗證")
        return 1

if __name__ == "__main__":
    sys.exit(main())