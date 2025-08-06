#!/usr/bin/env python3
"""
Telegram Bot 本地啟動測試工具
用於診斷 Zeabur 部署問題
"""

import os
import sys
import traceback
from datetime import datetime


def test_imports():
    """測試所有必要的導入"""
    print("=== 測試導入 ===")
    try:
        import flask

        print("✅ Flask 導入成功")

        import telegram

        print("✅ python-telegram-bot 導入成功")

        import google.generativeai as genai

        print("✅ Google Generative AI 導入成功")

        from notion_client import Client

        print("✅ Notion Client 導入成功")

        import requests

        print("✅ requests 導入成功")

        import aiofiles

        print("✅ aiofiles 導入成功")

        # 測試本地模組
        from config import Config

        print("✅ Config 模組導入成功")

        from telegram_app import flask_app

        print("✅ telegram_app 導入成功")

        from telegram_bot_handler import TelegramBotHandler

        print("✅ TelegramBotHandler 導入成功")

        return True
    except Exception as e:
        print(f"❌ 導入失敗: {e}")
        traceback.print_exc()
        return False


def test_environment():
    """測試環境變數"""
    print("\n=== 測試環境變數 ===")
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "GOOGLE_API_KEY",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
    ]

    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * 8}{value[-4:] if len(value) > 4 else '****'}")
        else:
            print(f"❌ {var}: 未設置")
            missing_vars.append(var)

    return len(missing_vars) == 0, missing_vars


def test_config():
    """測試配置初始化"""
    print("\n=== 測試配置初始化 ===")
    try:
        from config import Config

        print(f"✅ 配置類載入成功")
        print(
            f"   Telegram Bot Token: {'已設置' if Config.TELEGRAM_BOT_TOKEN else '未設置'}"
        )
        print(f"   Google API Key: {'已設置' if Config.GOOGLE_API_KEY else '未設置'}")
        print(f"   Notion API Key: {'已設置' if Config.NOTION_API_KEY else '未設置'}")
        print(
            f"   Notion Database ID: {'已設置' if Config.NOTION_DATABASE_ID else '未設置'}"
        )

        # 驗證配置
        try:
            Config.validate_config("telegram")
            print("✅ Telegram Bot 配置驗證通過")
        except Exception as ve:
            print(f"⚠️ 配置驗證警告: {ve}")

        return True
    except Exception as e:
        print(f"❌ 配置初始化失敗: {e}")
        traceback.print_exc()
        return False


def test_flask_app():
    """測試 Flask 應用初始化"""
    print("\n=== 測試 Flask 應用 ===")
    try:
        from telegram_app import flask_app, setup_telegram_handlers

        # 設置處理器
        setup_telegram_handlers()
        print("✅ Telegram 處理器設置成功")

        # 測試路由
        with flask_app.test_client() as client:
            # 測試健康檢查
            response = client.get("/health")
            print(f"✅ /health 端點: {response.status_code}")

            # 測試服務狀態
            response = client.get("/test")
            print(f"✅ /test 端點: {response.status_code}")

        return True
    except Exception as e:
        print(f"❌ Flask 應用測試失敗: {e}")
        traceback.print_exc()
        return False


def main():
    """主測試函數"""
    print(f"🔍 Telegram Bot 本地診斷工具")
    print(f"⏰ 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python 版本: {sys.version}")
    print(f"📁 工作目錄: {os.getcwd()}")

    # 載入環境變數
    try:
        from dotenv import load_dotenv

        if os.path.exists(".env.telegram"):
            load_dotenv(".env.telegram")
            print("✅ 載入 .env.telegram")
        else:
            print("⚠️ .env.telegram 不存在")
    except Exception as e:
        print(f"⚠️ 環境變數載入失敗: {e}")

    all_passed = True

    # 執行測試
    tests = [
        ("導入測試", test_imports),
        ("環境變數測試", lambda: test_environment()[0]),
        ("配置測試", test_config),
        ("Flask 應用測試", test_flask_app),
    ]

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} 通過")
            else:
                print(f"❌ {test_name} 失敗")
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} 異常: {e}")
            all_passed = False

    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 所有測試通過！本地應用應該可以正常啟動")
        print("\n🚀 嘗試啟動應用...")
        try:
            os.system("python main.py")
        except KeyboardInterrupt:
            print("\n⏹️ 應用已停止")
    else:
        print("❌ 存在問題，需要修復後才能正常部署")

        # 提供診斷建議
        print("\n🔧 修復建議:")
        print("1. 檢查是否安裝了所有依賴: pip install -r requirements-telegram.txt")
        print("2. 檢查 .env.telegram 文件是否包含所有必要的環境變數")
        print("3. 檢查 API Keys 是否有效")
        print("4. 檢查網路連接是否正常")


if __name__ == "__main__":
    main()
