#!/usr/bin/env python3
"""
Zeabur 環境變數問題診斷和修復工具
專門用於解決環境變數已設置但程式讀取不到的問題
"""
import os
import sys
from pathlib import Path


def fix_python_path():
    """修復 Python 路徑，模擬 main.py 的路徑設置"""
    # 模擬 src/namecard/api/telegram_bot/main.py 的路徑設置
    current_file = Path(__file__)
    root_dir = current_file.parent  # 已經在根目錄了

    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    print(f"✅ Python 路徑已設置: {root_dir}")
    return root_dir


def check_raw_environment():
    """檢查原始環境變數"""
    print("🔍 === 原始環境變數檢查 ===")
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Telegram Bot Token",
        "GOOGLE_API_KEY": "Google Gemini API Key",
        "NOTION_API_KEY": "Notion API Key",
        "NOTION_DATABASE_ID": "Notion Database ID",
    }

    env_status = {}
    for var, desc in required_vars.items():
        value = os.environ.get(var, "")
        env_status[var] = bool(value.strip() if value else False)

        if env_status[var]:
            # 顯示部分值以確認
            if len(value) > 20:
                display = f"{value[:10]}...{value[-6:]}"
            elif len(value) > 10:
                display = f"{value[:6]}...{value[-4:]}"
            else:
                display = "***"
            print(f"✅ {var}: {display}")
        else:
            print(f"❌ {var}: 未設置或為空")

    return env_status


def test_config_loading():
    """測試 simple_config 載入"""
    print(f"\n⚙️ === Config 載入測試 ===")

    try:
        # 清除緩存並重新導入
        if "simple_config" in sys.modules:
            del sys.modules["simple_config"]

        from simple_config import Config

        print("✅ simple_config 模組載入成功")

        # 顯示 Config 中的實際值
        print(f"\n📊 Config 類中的值:")
        config_status = {
            "TELEGRAM_BOT_TOKEN": bool(Config.TELEGRAM_BOT_TOKEN.strip())
            if Config.TELEGRAM_BOT_TOKEN
            else False,
            "GOOGLE_API_KEY": bool(Config.GOOGLE_API_KEY.strip())
            if Config.GOOGLE_API_KEY
            else False,
            "NOTION_API_KEY": bool(Config.NOTION_API_KEY.strip())
            if Config.NOTION_API_KEY
            else False,
            "NOTION_DATABASE_ID": bool(Config.NOTION_DATABASE_ID.strip())
            if Config.NOTION_DATABASE_ID
            else False,
        }

        for var, has_value in config_status.items():
            status = "✅ 有值" if has_value else "❌ 空值"
            print(f"  {var}: {status}")

        # 執行配置驗證
        print(f"\n🔍 執行 Config.validate():")
        try:
            valid = Config.validate()
            print(f"驗證結果: {'✅ 通過' if valid else '❌ 失敗'}")
            return valid, config_status
        except Exception as validate_error:
            print(f"❌ 驗證過程出錯: {validate_error}")
            return False, config_status

    except ImportError as e:
        print(f"❌ 無法導入 simple_config: {e}")
        return False, {}
    except Exception as e:
        print(f"❌ Config 測試失敗: {e}")
        return False, {}


def diagnose_and_fix():
    """診斷問題並提供修復建議"""
    print("🚀 === Zeabur 環境變數診斷開始 ===\n")

    # 1. 設置 Python 路徑
    root_dir = fix_python_path()

    # 2. 檢查原始環境變數
    env_status = check_raw_environment()

    # 3. 測試 Config 載入
    config_valid, config_status = test_config_loading()

    # 4. 分析問題
    print(f"\n🎯 === 問題診斷 ===")

    env_all_set = all(env_status.values())
    config_all_set = all(config_status.values()) if config_status else False

    if env_all_set and config_all_set and config_valid:
        print("✅ 所有檢查通過！問題可能在其他地方。")
        print("建議檢查:")
        print("1. Telegram Bot Token 是否有效")
        print("2. Google API Key 是否有 Gemini 權限")
        print("3. Notion API Key 和 Database ID 是否正確")

    elif env_all_set and not config_all_set:
        print("❌ 環境變數已設置，但 Config 類讀取失敗")
        print("可能原因:")
        print("1. 環境變數包含特殊字符或空格")
        print("2. Python 模組緩存問題")
        print("3. 路徑設置問題")

        print(f"\n🔧 建議的修復方式:")
        print("1. 重新部署 Zeabur 服務")
        print("2. 檢查環境變數值是否包含換行符或特殊字符")
        print("3. 在 Zeabur Dashboard 中重新設置環境變數")

    elif not env_all_set:
        print("❌ 環境變數未正確設置")
        missing = [var for var, status in env_status.items() if not status]
        print(f"缺失的變數: {', '.join(missing)}")

        print(f"\n🔧 修復步驟:")
        print("1. 前往 Zeabur Dashboard")
        print("2. 選擇你的專案和服務")
        print("3. 找到 'Environment Variables' 或 'Variables' 標籤")
        print("4. 設置以下變數:")
        for var in missing:
            print(f"   - {var}")
        print("5. 點擊 'Save' 然後 'Redeploy'")

    else:
        print("❌ 配置驗證失敗，但環境變數看起來正確")
        print("可能的問題:")
        print("1. API Keys 格式不正確")
        print("2. Token 已過期")
        print("3. 權限不足")


if __name__ == "__main__":
    diagnose_and_fix()
