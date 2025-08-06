#!/usr/bin/env python3
"""
Telegram Bot 初始化診斷工具
用於診斷為什麼增強處理器和媒體群組處理失敗
"""

import asyncio
import logging
import os
import sys

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, root_dir)

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_config():
    """測試配置"""
    print("=== 1. 配置測試 ===")
    try:
        from simple_config import Config

        print(f"✅ Config 導入成功")
        print(f"Telegram Token: {'已設置' if Config.TELEGRAM_BOT_TOKEN else '未設置'}")
        print(f"Google API Key: {'已設置' if Config.GOOGLE_API_KEY else '未設置'}")
        print(f"Notion API Key: {'已設置' if Config.NOTION_API_KEY else '未設置'}")

        valid = Config.validate()
        print(f"配置驗證: {'✅ 通過' if valid else '❌ 失敗'}")
        return valid
    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        return False


def test_basic_imports():
    """測試基本導入"""
    print("\n=== 2. 基本導入測試 ===")
    try:
        from src.namecard.infrastructure.messaging.telegram_client import (
            TelegramBotHandler,
        )

        print("✅ TelegramBotHandler 導入成功")

        from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
            EnhancedTelegramBotHandler,
            create_enhanced_telegram_handler,
        )

        print("✅ EnhancedTelegramBotHandler 導入成功")

        from src.namecard.infrastructure.ai.ultra_fast_processor import (
            UltraFastProcessor,
        )

        print("✅ UltraFastProcessor 導入成功")

        from src.namecard.core.services.batch_image_collector import (
            BatchImageCollector,
            get_batch_collector,
        )

        print("✅ BatchImageCollector 導入成功")

        return True
    except Exception as e:
        print(f"❌ 導入測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_handler_creation():
    """測試處理器創建"""
    print("\n=== 3. 處理器創建測試 ===")

    # 測試基本處理器
    try:
        from src.namecard.infrastructure.messaging.telegram_client import (
            TelegramBotHandler,
        )

        basic_handler = TelegramBotHandler()
        print("✅ TelegramBotHandler 創建成功")
    except Exception as e:
        print(f"❌ TelegramBotHandler 創建失敗: {e}")
        return False

    # 測試增強處理器
    try:
        from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
            create_enhanced_telegram_handler,
        )

        enhanced_handler = create_enhanced_telegram_handler(
            enable_queue=True, queue_workers=2, batch_size=1, batch_timeout=1.0  # 減少測試
        )
        print("✅ EnhancedTelegramBotHandler 創建成功")

        # 測試啟動
        if enhanced_handler:
            await enhanced_handler.start_queue_system()
            print("✅ 增強處理器佇列系統啟動成功")

            # 清理
            await enhanced_handler.cleanup()

    except Exception as e:
        print(f"❌ EnhancedTelegramBotHandler 創建失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 測試超高速處理器
    try:
        from src.namecard.infrastructure.ai.ultra_fast_processor import (
            UltraFastProcessor,
        )

        ultra_fast = UltraFastProcessor()
        print("✅ UltraFastProcessor 創建成功")
    except Exception as e:
        print(f"❌ UltraFastProcessor 創建失敗: {e}")
        return False

    # 測試批次收集器
    try:
        from src.namecard.core.services.batch_image_collector import get_batch_collector

        batch_collector = get_batch_collector()
        print("✅ BatchImageCollector 創建成功")
    except Exception as e:
        print(f"❌ BatchImageCollector 創建失敗: {e}")
        return False

    return True


async def test_telegram_api():
    """測試 Telegram API 連接"""
    print("\n=== 4. Telegram API 測試 ===")
    try:
        from telegram import Bot

        from simple_config import Config

        bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ Telegram Bot API 連接成功")
        print(f"Bot 名稱: {me.first_name}")
        print(f"Bot 用戶名: @{me.username}")
        return True

    except Exception as e:
        print(f"❌ Telegram API 測試失敗: {e}")
        return False


async def main():
    """主測試流程"""
    print("🔍 Telegram Bot 初始化診斷開始...\n")

    # 1. 配置測試
    if not test_config():
        print("\n❌ 配置驗證失敗，請檢查環境變數")
        return

    # 2. 導入測試
    if not test_basic_imports():
        print("\n❌ 模組導入失敗，請檢查依賴")
        return

    # 3. 處理器創建測試
    if not await test_handler_creation():
        print("\n❌ 處理器創建失敗")
        return

    # 4. API 連接測試
    if not await test_telegram_api():
        print("\n❌ Telegram API 連接失敗")
        return

    print("\n✅ 所有測試通過！Telegram Bot 應該可以正常運行。")
    print("\n💡 建議檢查：")
    print("1. 部署環境的環境變數設置")
    print("2. Zeabur 服務的日誌輸出")
    print("3. 網路連接和防火牆設置")


if __name__ == "__main__":
    asyncio.run(main())
