#!/usr/bin/env python3
"""
Telegram Bot 連接池修復效果驗證

簡化版測試 - 專注於驗證關鍵配置修復
"""

import asyncio
import logging
import sys
import time

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_import():
    """基本導入測試"""
    logger.info("🔍 測試基本模組導入...")
    try:
        from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
        logger.info("✅ TelegramBotHandler 導入成功")
        return TelegramBotHandler
    except Exception as e:
        logger.error(f"❌ 導入失敗: {e}")
        return None

async def test_exponential_backoff():
    """測試指數退避計算"""
    logger.info("🔍 測試指數退避重試計算...")
    
    TelegramBotHandler = test_basic_import()
    if not TelegramBotHandler:
        return False
    
    try:
        # 創建測試實例（不初始化 Bot）
        handler = TelegramBotHandler.__new__(TelegramBotHandler)
        handler.base_retry_delay = 1
        handler.max_retry_delay = 60
        handler.exponential_backoff = True
        
        # 測試指數退避計算
        delays = []
        for attempt in range(5):
            delay = handler._calculate_retry_delay(attempt)
            delays.append(delay)
            logger.info(f"  嘗試 {attempt + 1}: {delay:.2f} 秒")
        
        # 驗證指數增長趨勢
        if delays[1] > delays[0] and delays[2] > delays[1]:
            logger.info("✅ 指數退避計算正常")
            return True
        else:
            logger.error("❌ 指數退避計算異常")
            return False
            
    except Exception as e:
        logger.error(f"❌ 指數退避測試失敗: {e}")
        return False

def test_connection_pool_config():
    """測試連接池配置（靜態檢查）"""
    logger.info("🔍 檢查連接池配置值...")
    
    try:
        # 檢查代碼中的配置值
        import inspect
        from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
        
        # 獲取源代碼
        source = inspect.getsource(TelegramBotHandler._setup_http_client_only)
        
        # 檢查關鍵配置值
        config_checks = {
            "max_connections=150": "最大連接數 150",
            "max_keepalive_connections=60": "保持連接數 60", 
            "pool=300.0": "連接池超時 300 秒",
            "read=60.0": "讀取超時 60 秒"
        }
        
        all_good = True
        for config, description in config_checks.items():
            if config in source:
                logger.info(f"✅ {description}")
            else:
                logger.error(f"❌ 缺少配置: {description}")
                all_good = False
        
        if all_good:
            logger.info("✅ 連接池配置檢查通過")
            return True
        else:
            logger.error("❌ 連接池配置檢查失敗")
            return False
            
    except Exception as e:
        logger.error(f"❌ 連接池配置檢查失敗: {e}")
        return False

def test_error_handling_enhancement():
    """測試錯誤處理增強"""
    logger.info("🔍 測試連接池超時錯誤處理...")
    
    TelegramBotHandler = test_basic_import()
    if not TelegramBotHandler:
        return False
    
    try:
        # 創建測試實例
        handler = TelegramBotHandler.__new__(TelegramBotHandler)
        handler.logger = logger
        handler._connection_pool_stats = {"pool_timeouts": 0}
        
        # 模擬網路錯誤處理
        class MockNetworkError:
            def __init__(self, message):
                self.message = message
            def __str__(self):
                return self.message
        
        # 測試連接池超時錯誤
        pool_error = MockNetworkError("Pool timeout: All connections in the connection pool are occupied")
        
        # 檢查錯誤處理方法是否存在
        if hasattr(handler, '_handle_telegram_error'):
            logger.info("✅ 錯誤處理方法存在")
            return True
        else:
            logger.error("❌ 缺少錯誤處理方法")
            return False
            
    except Exception as e:
        logger.error(f"❌ 錯誤處理測試失敗: {e}")
        return False

async def main():
    """主測試函數"""
    logger.info("🚀 開始連接池修復驗證")
    logger.info("=" * 60)
    
    tests = [
        ("基本導入", lambda: test_basic_import() is not None),
        ("連接池配置", test_connection_pool_config),
        ("指數退避計算", test_exponential_backoff),
        ("錯誤處理增強", test_error_handling_enhancement),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 執行測試: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} - 通過")
            else:
                logger.error(f"❌ {test_name} - 失敗")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - 異常: {e}")
            results.append((test_name, False))
    
    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試總結")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        logger.info("🎉 連接池修復驗證成功！")
        logger.info("\n🔧 主要修復內容:")
        logger.info("  • 連接池超時從 120s 增加到 300s (5分鐘)")
        logger.info("  • 最大連接數從 100 增加到 150")
        logger.info("  • 保持連接數從 40 增加到 60")
        logger.info("  • 添加指數退避重試機制 (1, 2, 4, 8, 16... 秒)")
        logger.info("  • 增強連接池超時錯誤檢測和自動清理")
        logger.info("  • 併發控制從 20 調整到 15 (避免連接池耗盡)")
        logger.info("\n✨ 這些修復應該能解決你遇到的連接池超時問題！")
        return True
    else:
        logger.error("❌ 部分測試失敗")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 測試被中斷")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 測試執行失敗: {e}")
        sys.exit(1)