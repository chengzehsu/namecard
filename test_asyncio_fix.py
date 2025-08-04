#!/usr/bin/env python3
"""
測試 Telegram Bot asyncio 事件循環修復
"""
import asyncio
import sys
import os
import threading
from unittest.mock import Mock, patch

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler

def test_semaphore_in_different_event_loops():
    """測試在不同事件循環中使用 Semaphore"""
    print("🧪 測試 Semaphore 在不同事件循環中的行為...")
    
    results = []
    
    def run_in_new_loop(loop_name):
        """在新的事件循環中運行測試"""
        async def test_handler():
            try:
                # 模擬 Bot token (測試用)
                with patch('simple_config.Config.TELEGRAM_BOT_TOKEN', 'dummy_token'):
                    handler = TelegramBotHandler()
                    
                    # 測試獲取 Semaphore
                    semaphore1 = await handler._get_semaphore()
                    semaphore2 = await handler._get_semaphore()
                    
                    # 驗證在同一事件循環中返回相同的 Semaphore
                    same_semaphore = semaphore1 is semaphore2
                    current_loop = asyncio.get_running_loop()
                    
                    results.append({
                        'loop_name': loop_name,
                        'same_semaphore': same_semaphore,
                        'loop_id': id(current_loop),
                        'semaphore_id': id(semaphore1)
                    })
                    
                    print(f"   {loop_name}: 同一 Semaphore: {'✅' if same_semaphore else '❌'}")
                    print(f"   {loop_name}: 事件循環 ID: {id(current_loop)}")
                    print(f"   {loop_name}: Semaphore ID: {id(semaphore1)}")
                    
            except Exception as e:
                print(f"   ❌ {loop_name} 測試失敗: {e}")
                results.append({
                    'loop_name': loop_name,
                    'error': str(e)
                })
        
        # 創建新的事件循環
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(test_handler())
        finally:
            loop.close()
    
    # 在多個線程中創建不同的事件循環
    threads = []
    for i in range(3):
        thread = threading.Thread(target=run_in_new_loop, args=(f"Loop-{i+1}",))
        threads.append(thread)
        thread.start()
    
    # 等待所有線程完成
    for thread in threads:
        thread.join()
    
    # 分析結果
    print(f"\n📊 測試結果分析:")
    success_count = 0
    error_count = 0
    
    for result in results:
        if 'error' in result:
            error_count += 1
            print(f"   ❌ {result['loop_name']}: {result['error']}")
        else:
            if result['same_semaphore']:
                success_count += 1
                print(f"   ✅ {result['loop_name']}: Semaphore 管理正常")
            else:
                print(f"   ⚠️ {result['loop_name']}: Semaphore 不一致")
    
    return success_count, error_count, len(results)

def test_event_loop_error_simulation():
    """模擬原始的事件循環錯誤"""
    print("\n🔍 模擬原始錯誤情況...")
    
    async def simulate_original_error():
        """模擬原始的事件循環綁定錯誤"""
        try:
            # 在第一個事件循環中創建 Semaphore
            semaphore = asyncio.Semaphore(5)
            print(f"   原始 Semaphore 創建在事件循環: {id(asyncio.get_running_loop())}")
            
            # 在新線程中嘗試使用（模擬問題場景）
            def use_in_new_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def use_semaphore():
                    try:
                        print(f"   嘗試在新事件循環中使用: {id(asyncio.get_running_loop())}")
                        # 這應該會引發錯誤（如果沒有修復）
                        async with semaphore:
                            print("   ✅ 成功使用 Semaphore")
                    except RuntimeError as e:
                        if "different event loop" in str(e):
                            print(f"   🎯 捕獲到預期錯誤: {e}")
                            return "expected_error"
                        else:
                            raise
                    return "success"
                
                try:
                    result = loop.run_until_complete(use_semaphore())
                    return result
                finally:
                    loop.close()
            
            # 在新線程中執行
            import threading
            result_container = []
            
            def thread_target():
                result_container.append(use_in_new_loop())
            
            thread = threading.Thread(target=thread_target)
            thread.start()
            thread.join()
            
            return result_container[0] if result_container else "no_result"
            
        except Exception as e:
            print(f"   ❌ 模擬錯誤失敗: {e}")
            return "simulation_failed"
    
    # 在主事件循環中運行模擬
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(simulate_original_error())
        print(f"   模擬結果: {result}")
        return result
    finally:
        loop.close()

def main():
    """主測試函數"""
    print("🔧 Telegram Bot AsyncIO 事件循環修復測試")
    print("=" * 50)
    
    # 測試 1: Semaphore 在不同事件循環中的行為
    success_count, error_count, total_count = test_semaphore_in_different_event_loops()
    
    # 測試 2: 模擬原始錯誤情況
    simulation_result = test_event_loop_error_simulation()
    
    # 總結結果
    print("\n" + "=" * 50)
    print("🎯 測試總結:")
    print(f"   成功測試: {success_count}/{total_count}")
    print(f"   錯誤測試: {error_count}/{total_count}")
    print(f"   錯誤模擬: {simulation_result}")
    
    if success_count == total_count and error_count == 0:
        print("\n🎉 所有測試通過！事件循環修復成功")
        return True
    else:
        print("\n⚠️ 部分測試失敗，需要進一步檢查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)