#!/usr/bin/env python3
"""
Telegram Bot 連接池修復驗證測試

測試修復後的連接池配置是否能解決超時問題
"""

import asyncio
import logging
import sys
import time
from typing import List

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_telegram_client_import():
    """測試 Telegram 客戶端導入"""
    try:
        from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
        logger.info("✅ TelegramBotHandler 導入成功")
        return TelegramBotHandler
    except ImportError as e:
        logger.error(f"❌ 導入失敗: {e}")
        return None

async def test_connection_pool_configuration():
    """測試連接池配置"""
    try:
        TelegramBotHandler = test_telegram_client_import()
        if not TelegramBotHandler:
            return False
            
        # 創建客戶端實例（測試模式）
        client = TelegramBotHandler.__new__(TelegramBotHandler)  # 避免調用 __init__
        client.logger = logging.getLogger(__name__)
        client._test_mode = True  # 啟用測試模式
        client.error_stats = {"pool_timeouts": 0}
        client._connection_pool_stats = {
            "active_connections": 0,
            "pool_timeouts": 0,
            "connection_errors": 0,
            "last_cleanup": time.time()
        }
        client._pool_cleanup_interval = 300
        client._setup_http_client_only()  # 只設置 HTTP 客戶端
        
        # 檢查連接池配置
        if hasattr(client, '_http_client') and client._http_client:
            limits = client._http_client._limits
            timeout = client._http_client._timeout
            
            logger.info("🔧 HTTP 客戶端配置檢查:")
            logger.info(f"  - 最大連接數: {limits.max_connections}")
            logger.info(f"  - 保持連接數: {limits.max_keepalive_connections}")
            logger.info(f"  - 連接保持時間: {limits.keepalive_expiry}s")
            logger.info(f"  - 連接池超時: {timeout.pool}s")
            logger.info(f"  - 讀取超時: {timeout.read}s")
            
            # 驗證修復後的配置
            expected_config = {
                "max_connections": 150,
                "max_keepalive_connections": 60,
                "keepalive_expiry": 60.0,
                "pool_timeout": 300.0,
                "read_timeout": 60.0
            }
            
            actual_config = {
                "max_connections": limits.max_connections,
                "max_keepalive_connections": limits.max_keepalive_connections,
                "keepalive_expiry": limits.keepalive_expiry,
                "pool_timeout": timeout.pool,
                "read_timeout": timeout.read
            }
            
            config_ok = True
            for key, expected in expected_config.items():
                actual = actual_config[key]
                if actual != expected:
                    logger.warning(f"⚠️ 配置不匹配 {key}: 期望 {expected}, 實際 {actual}")
                    config_ok = False
                else:
                    logger.info(f"✅ {key}: {actual}")
            
            if config_ok:
                logger.info("🎉 連接池配置驗證通過！")
                return True
            else:
                logger.error("❌ 連接池配置不符合預期")
                return False
                
        else:
            logger.warning("⚠️ 無法找到 HTTP 客戶端配置")
            return False
            
    except Exception as e:
        logger.error(f"❌ 連接池配置測試失敗: {e}")
        return False

async def test_semaphore_configuration():
    """測試信號量配置"""
    try:
        TelegramBotHandler = test_telegram_client_import()
        if not TelegramBotHandler:
            return False
            
        client = TelegramBotHandler()
        client._test_mode = True  # 啟用測試模式
        client._setup_optimized_bot()  # 重新初始化
        
        # 測試信號量創建
        semaphore = await client._get_semaphore()
        
        if semaphore:
            # 檢查信號量容量 (間接測試)
            logger.info("🔧 信號量配置檢查:")
            logger.info(f"  - 信號量類型: {type(semaphore).__name__}")
            
            # 測試併發控制
            start_time = time.time()
            tasks = []
            
            async def dummy_task(task_id):
                """模擬任務"""
                async with semaphore:
                    await asyncio.sleep(0.1)  # 模擬處理時間
                    return f"task_{task_id}_completed"
            
            # 創建 20 個並發任務測試信號量
            for i in range(20):
                task = asyncio.create_task(dummy_task(i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_tasks = sum(1 for r in results if isinstance(r, str))
            failed_tasks = sum(1 for r in results if isinstance(r, Exception))
            
            logger.info(f"📊 併發測試結果:")
            logger.info(f"  - 總任務數: {len(tasks)}")
            logger.info(f"  - 成功任務: {successful_tasks}")
            logger.info(f"  - 失敗任務: {failed_tasks}")
            logger.info(f"  - 執行時間: {end_time - start_time:.2f}s")
            
            if successful_tasks == 20 and failed_tasks == 0:
                logger.info("✅ 信號量併發控制測試通過！")
                return True
            else:
                logger.error("❌ 信號量併發控制測試失敗")
                return False
                
        else:
            logger.error("❌ 無法創建信號量")
            return False
            
    except Exception as e:
        logger.error(f"❌ 信號量配置測試失敗: {e}")
        return False

async def test_connection_pool_monitoring():
    """測試連接池監控功能"""
    try:
        TelegramBotHandler = test_telegram_client_import()
        if not TelegramBotHandler:
            return False
            
        client = TelegramBotHandler()
        client._test_mode = True  # 啟用測試模式
        client._setup_optimized_bot()  # 重新初始化
        
        # 檢查監控統計
        if hasattr(client, '_connection_pool_stats'):
            stats = client._connection_pool_stats
            logger.info("📊 連接池監控統計:")
            for key, value in stats.items():
                logger.info(f"  - {key}: {value}")
            
            # 測試狀態報告
            status_report = client.get_status_report()
            logger.info("📋 狀態報告:")
            for key, value in status_report.items():
                if key == "recommendations":
                    logger.info(f"  - {key}: {', '.join(value)}")
                else:
                    logger.info(f"  - {key}: {value}")
            
            logger.info("✅ 連接池監控功能測試通過！")
            return True
            
        else:
            logger.error("❌ 連接池監控統計不存在")
            return False
            
    except Exception as e:
        logger.error(f"❌ 連接池監控測試失敗: {e}")
        return False

async def test_error_handling_enhancement():
    """測試增強的錯誤處理"""
    try:
        TelegramBotHandler = test_telegram_client_import()
        if not TelegramBotHandler:
            return False
            
        client = TelegramBotHandler()
        client._test_mode = True  # 啟用測試模式
        client._setup_optimized_bot()  # 重新初始化
        
        # 模擬網路錯誤
        from telegram.error import NetworkError
        
        # 測試連接池超時錯誤處理
        pool_timeout_error = NetworkError("Pool timeout: All connections in the connection pool are occupied")
        result = client._handle_telegram_error(pool_timeout_error, "test_context")
        
        logger.info("🔧 連接池超時錯誤處理測試:")
        logger.info(f"  - 錯誤類型: {result.get('error_type')}")
        logger.info(f"  - 可重試: {result.get('can_retry')}")
        logger.info(f"  - 重試等待: {result.get('retry_after')}s")
        
        if (result.get('error_type') == 'connection_pool_timeout' and 
            result.get('can_retry') == True and
            result.get('retry_after') == 60):
            logger.info("✅ 連接池超時錯誤處理測試通過！")
            return True
        else:
            logger.error("❌ 連接池超時錯誤處理測試失敗")
            return False
            
    except Exception as e:
        logger.error(f"❌ 錯誤處理增強測試失敗: {e}")
        return False

async def run_all_tests():
    """運行所有測試"""
    logger.info("🚀 開始連接池修復驗證測試")
    
    tests = [
        ("連接池配置", test_connection_pool_configuration),
        ("信號量配置", test_semaphore_configuration), 
        ("連接池監控", test_connection_pool_monitoring),
        ("錯誤處理增強", test_error_handling_enhancement)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 執行測試: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} 測試通過")
            else:
                logger.error(f"❌ {test_name} 測試失敗")
        except Exception as e:
            logger.error(f"❌ {test_name} 測試異常: {e}")
            results.append((test_name, False))
    
    # 總結報告
    logger.info("\n" + "="*60)
    logger.info("📊 連接池修復驗證測試總結")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        logger.info("🎉 所有測試通過！連接池修復驗證成功")
        return True
    else:
        logger.error("❌ 部分測試失敗，需要進一步檢查")
        return False

def main():
    """主函數"""
    try:
        # 檢查 Python 版本
        if sys.version_info < (3, 7):
            logger.error("❌ 需要 Python 3.7 或更高版本")
            return False
            
        # 運行異步測試
        result = asyncio.run(run_all_tests())
        return result
        
    except KeyboardInterrupt:
        logger.info("🛑 測試被使用者中斷")
        return False
    except Exception as e:
        logger.error(f"❌ 測試執行失敗: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)