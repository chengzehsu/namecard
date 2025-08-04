#!/usr/bin/env python3
"""
診斷 Telegram 處理器問題
"""

import os
import sys
import asyncio
import logging

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)

# 設置日誌
logging.basicConfig(level=logging.DEBUG)

def test_config():
    """測試配置"""
    print("🔍 Step 1: 測試配置載入...")
    
    try:
        from simple_config import Config
        print(f"✅ Config 載入成功")
        print(f"📋 TELEGRAM_BOT_TOKEN: {'已設置' if Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_BOT_TOKEN != 'YOUR_TELEGRAM_BOT_TOKEN_HERE' else '未設置'}")
        print(f"📋 GOOGLE_API_KEY: {'已設置' if Config.GOOGLE_API_KEY and Config.GOOGLE_API_KEY != 'YOUR_GOOGLE_API_KEY_HERE' else '未設置'}")
        print(f"📋 NOTION_API_KEY: {'已設置' if Config.NOTION_API_KEY and Config.NOTION_API_KEY != 'YOUR_NOTION_API_KEY_HERE' else '未設置'}")
        
        # 在生產環境中，這些應該都是已設置的
        if not Config.validate():
            print("⚠️  本地配置未設置 - 這是正常的，生產環境應該有配置")
        return Config
    except Exception as e:
        print(f"❌ Config 載入失敗: {e}")
        return None

def test_processors_init():
    """測試處理器初始化"""
    print("\n🔍 Step 2: 測試處理器初始化...")
    
    try:
        # 這些導入應該會失敗，因為沒有環境變數
        from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
        from src.namecard.infrastructure.storage.notion_client import NotionManager
        from src.namecard.core.services.batch_service import BatchManager
        from src.namecard.core.services.multi_card_service import MultiCardProcessor
        from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
        
        print("📦 嘗試初始化 NameCardProcessor...")
        try:
            card_processor = NameCardProcessor()
            print("✅ NameCardProcessor 初始化成功")
        except Exception as e:
            print(f"❌ NameCardProcessor 初始化失敗: {e}")
            
        print("📦 嘗試初始化 NotionManager...")
        try:
            notion_manager = NotionManager()
            print("✅ NotionManager 初始化成功")
        except Exception as e:
            print(f"❌ NotionManager 初始化失敗: {e}")
            
        print("📦 嘗試初始化 TelegramBotHandler...")
        try:
            telegram_handler = TelegramBotHandler()
            print("✅ TelegramBotHandler 初始化成功")
        except Exception as e:
            print(f"❌ TelegramBotHandler 初始化失敗: {e}")
            
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
    except Exception as e:
        print(f"❌ 處理器測試失敗: {e}")

async def test_telegram_send():
    """測試 Telegram 發送功能"""
    print("\n🔍 Step 3: 測試 Telegram 發送功能...")
    
    try:
        from simple_config import Config
        from telegram import Bot
        
        if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            print("⚠️  沒有 TELEGRAM_BOT_TOKEN，跳過發送測試")
            return
            
        bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        
        # 測試 getMe
        print("📤 測試 bot.get_me()...")
        me = await bot.get_me()
        print(f"✅ Bot 信息: {me.first_name} (@{me.username})")
        
    except Exception as e:
        print(f"❌ Telegram 發送測試失敗: {e}")

def analyze_webhook_flow():
    """分析 webhook 處理流程"""
    print("\n🔍 Step 4: 分析 webhook 處理流程...")
    
    print("📋 根據日誌分析:")
    print("  1. ✅ webhook 接收到 photo message")
    print("  2. ✅ 異步處理初始化完成")
    print("  3. ❌ 沒有看到 '📸 收到名片圖片' 訊息")
    print("  4. ✅ 異步處理完成")
    
    print("\n💡 可能的問題:")
    print("  A. handle_photo_message 中的某個步驟失敗")
    print("  B. telegram_bot_handler.safe_send_message 失敗")
    print("  C. 處理器初始化失敗但被捕獲")
    print("  D. 異步事件循環問題")

def main():
    """主診斷函數"""
    print("🔍 Telegram Bot 處理器診斷")
    print("=" * 50)
    
    # 測試步驟
    config = test_config()
    test_processors_init()
    
    # 異步測試
    try:
        asyncio.run(test_telegram_send())
    except Exception as e:
        print(f"❌ 異步測試失敗: {e}")
    
    analyze_webhook_flow()
    
    print("\n" + "=" * 50)
    print("💡 診斷建議:")
    print("1. 檢查生產環境的環境變數設置")
    print("2. 查看完整的錯誤日誌 (包含 traceback)")
    print("3. 測試單個處理器的初始化")
    print("4. 確認 Telegram Bot Token 有效性")

if __name__ == "__main__":
    main()