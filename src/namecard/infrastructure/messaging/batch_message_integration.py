"""
批次處理與異步訊息排程系統的整合範例
展示如何在現有的批次處理流程中使用訊息排程
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .enhanced_telegram_client import EnhancedTelegramBotHandler, with_batch_context


class BatchProcessingIntegration:
    """
    批次處理整合器
    
    將現有的批次處理邏輯與新的異步訊息排程系統整合
    """
    
    def __init__(self, telegram_handler: EnhancedTelegramBotHandler):
        """
        初始化批次處理整合器
        
        Args:
            telegram_handler: 增強版 Telegram 處理器
        """
        self.telegram_handler = telegram_handler
        self.logger = logging.getLogger(__name__)
        
    @with_batch_context()
    async def process_batch_cards(self, user_id: str, card_images: List[bytes], 
                                batch_session: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理批次名片 - 使用異步訊息排程
        
        Args:
            user_id: 用戶ID  
            card_images: 名片圖片數據列表
            batch_session: 批次會話信息
            
        Returns:
            批次處理結果統計
        """
        self.logger.info(f"🔄 開始批次處理 {len(card_images)} 張名片 (用戶: {user_id})")
        
        # 1. 發送批次開始通知
        await self.telegram_handler.send_batch_message(
            chat_id=user_id,
            text=f"🚀 **批次處理開始**\n📊 總共 {len(card_images)} 張名片\n⏱️ 預計處理時間: {len(card_images) * 10} 秒",
            parse_mode="Markdown"
        )
        
        # 2. 並發處理所有名片
        processing_tasks = []
        for i, image_data in enumerate(card_images):
            task = asyncio.create_task(
                self._process_single_card_with_feedback(
                    user_id, image_data, i + 1, len(card_images)
                )
            )
            processing_tasks.append(task)
            
        # 3. 等待所有處理完成
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # 4. 統計結果
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "index": i + 1,
                    "error": str(result)
                })
                self.logger.error(f"❌ 名片 {i + 1} 處理失敗: {result}")
            else:
                successful_results.append(result)
                
        # 5. 發送批次完成統計 - 使用高優先級
        await self._send_batch_completion_summary(
            user_id, successful_results, failed_results, batch_session
        )
        
        return {
            "total_processed": len(card_images),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "success_rate": len(successful_results) / len(card_images) if card_images else 0,
            "results": successful_results,
            "errors": failed_results
        }
        
    async def _process_single_card_with_feedback(self, user_id: str, image_data: bytes,
                                               card_index: int, total_cards: int) -> Dict[str, Any]:
        """
        處理單張名片並提供進度反饋
        
        Args:
            user_id: 用戶ID
            image_data: 名片圖片數據
            card_index: 當前名片索引 (1-based)
            total_cards: 總名片數量
            
        Returns:
            處理結果
        """
        try:
            # 1. 發送處理開始通知（批次訊息，可合併）
            await self.telegram_handler.send_batch_message(
                chat_id=user_id,
                text=f"🔄 正在處理第 {card_index}/{total_cards} 張名片..."
            )
            
            # 2. 模擬名片處理（這裡應該調用實際的處理邏輯）
            # 例如：調用 NameCardProcessor, MultiCardProcessor 等
            processing_result = await self._simulate_card_processing(image_data)
            
            # 3. 發送處理完成通知（高優先級）
            if processing_result.get("success"):
                card_info = processing_result["card_info"]
                await self.telegram_handler.send_completion_message(
                    chat_id=user_id,
                    text=f"✅ **名片 {card_index}/{total_cards} 處理完成**\n"
                         f"👤 姓名: {card_info.get('name', 'N/A')}\n"
                         f"🏢 公司: {card_info.get('company', 'N/A')}\n"
                         f"📄 [查看詳情]({processing_result.get('notion_url', '#')})",
                    parse_mode="Markdown"
                )
            else:
                await self.telegram_handler.send_urgent_message(
                    chat_id=user_id,
                    text=f"❌ **名片 {card_index}/{total_cards} 處理失敗**\n"
                         f"📝 錯誤: {processing_result.get('error', '未知錯誤')}",
                    parse_mode="Markdown"
                )
                
            return {
                "index": card_index,
                "success": processing_result.get("success", False),
                "card_info": processing_result.get("card_info", {}),
                "notion_url": processing_result.get("notion_url", ""),
                "processing_time": processing_result.get("processing_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 處理名片 {card_index} 時發生錯誤: {e}")
            
            # 發送錯誤通知
            await self.telegram_handler.send_urgent_message(
                chat_id=user_id,
                text=f"💥 **名片 {card_index}/{total_cards} 處理發生異常**\n"
                     f"📝 錯誤: {str(e)}",
                parse_mode="Markdown"
            )
            
            raise e
            
    async def _simulate_card_processing(self, image_data: bytes) -> Dict[str, Any]:
        """
        模擬名片處理邏輯
        
        實際使用時應該替換為真實的處理邏輯：
        - 調用 NameCardProcessor 進行 AI 識別
        - 調用 NotionManager 存儲數據
        - 調用 MultiCardProcessor 處理多名片場景
        """
        # 模擬處理時間
        await asyncio.sleep(2)  # 模擬 2 秒處理時間
        
        # 模擬 90% 成功率
        import random
        if random.random() > 0.1:
            return {
                "success": True,
                "card_info": {
                    "name": f"測試用戶 {random.randint(1, 100)}",
                    "company": f"測試公司 {random.randint(1, 50)}",
                    "title": "測試職位",
                    "email": "test@example.com",
                    "phone": "0912345678"
                },
                "notion_url": "https://notion.so/test-page",
                "processing_time": 2.0
            }
        else:
            return {
                "success": False,
                "error": "AI 識別失敗：圖片模糊或格式不支援",
                "processing_time": 2.0
            }
            
    async def _send_batch_completion_summary(self, user_id: str, 
                                           successful_results: List[Dict],
                                           failed_results: List[Dict],
                                           batch_session: Dict[str, Any]):
        """發送批次完成統計摘要"""
        total_count = len(successful_results) + len(failed_results)
        success_rate = len(successful_results) / total_count if total_count > 0 else 0
        
        # 建立摘要訊息
        summary_text = f"""🎉 **批次處理完成**

📊 **處理統計**
✅ 成功: {len(successful_results)} 張
❌ 失敗: {len(failed_results)} 張  
📈 成功率: {success_rate:.1%}
⏱️ 總處理時間: {self._calculate_batch_duration(batch_session)}

"""
        
        # 添加成功名片的簡要列表
        if successful_results:
            summary_text += "📋 **成功處理的名片**:\n"
            for result in successful_results[:5]:  # 只顯示前5個
                card_info = result.get("card_info", {})
                name = card_info.get("name", "未知")
                company = card_info.get("company", "未知")
                summary_text += f"• {name} ({company})\n"
                
            if len(successful_results) > 5:
                summary_text += f"• ... 及其他 {len(successful_results) - 5} 張名片\n"
                
        # 添加失敗統計
        if failed_results:
            summary_text += f"\n⚠️ **失敗統計**:\n"
            summary_text += f"共 {len(failed_results)} 張名片處理失敗\n"
            summary_text += "請檢查圖片品質後重新上傳\n"
            
        # 發送完成統計（高優先級，不合併）
        await self.telegram_handler.send_completion_message(
            chat_id=user_id,
            text=summary_text,
            parse_mode="Markdown"
        )
        
        # 如果有失敗的名片，發送詳細錯誤報告
        if failed_results:
            await self._send_failure_details(user_id, failed_results)
            
    async def _send_failure_details(self, user_id: str, failed_results: List[Dict]):
        """發送詳細的失敗報告"""
        if not failed_results:
            return
            
        failure_text = "❌ **詳細錯誤報告**\n\n"
        
        for failure in failed_results[:10]:  # 最多顯示10個錯誤
            failure_text += f"📄 名片 {failure['index']}: {failure['error']}\n"
            
        if len(failed_results) > 10:
            failure_text += f"\n... 及其他 {len(failed_results) - 10} 個錯誤"
            
        failure_text += "\n💡 **建議**:\n"
        failure_text += "• 確保圖片清晰且光線充足\n"
        failure_text += "• 名片內容完整可見\n"
        failure_text += "• 支援 JPG, PNG 格式\n"
        failure_text += "• 可重新上傳失敗的名片"
        
        await self.telegram_handler.send_urgent_message(
            chat_id=user_id,
            text=failure_text,
            parse_mode="Markdown"
        )
        
    def _calculate_batch_duration(self, batch_session: Dict[str, Any]) -> str:
        """計算批次處理持續時間"""
        try:
            start_time = batch_session.get("start_time")
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            elif not isinstance(start_time, datetime):
                return "未知"
                
            duration = datetime.now() - start_time
            total_seconds = int(duration.total_seconds())
            
            if total_seconds < 60:
                return f"{total_seconds} 秒"
            else:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes} 分 {seconds} 秒"
                
        except Exception:
            return "未知"


# 🎯 進度追蹤器
class BatchProgressTracker:
    """批次處理進度追蹤器"""
    
    def __init__(self, telegram_handler: EnhancedTelegramBotHandler):
        self.telegram_handler = telegram_handler
        self.progress_cache = {}
        
    async def update_progress(self, user_id: str, batch_id: str, 
                            current: int, total: int, 
                            details: Optional[str] = None):
        """更新進度並智能發送通知"""
        progress_key = f"{user_id}_{batch_id}"
        
        # 計算進度百分比
        progress_percent = (current / total) * 100 if total > 0 else 0
        
        # 檢查是否需要發送進度更新
        last_percent = self.progress_cache.get(progress_key, -1)
        
        # 每20%進度或最後一個發送更新
        should_update = (
            progress_percent - last_percent >= 20 or
            current == total or
            current == 1  # 第一個
        )
        
        if should_update:
            progress_text = f"📊 **批次進度更新**\n"
            progress_text += f"🔄 進度: {current}/{total} ({progress_percent:.0f}%)\n"
            
            # 進度條
            bar_length = 10
            filled_length = int(bar_length * progress_percent / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            progress_text += f"📈 {bar} {progress_percent:.0f}%\n"
            
            if details:
                progress_text += f"📝 {details}"
                
            # 使用批次訊息發送進度更新
            await self.telegram_handler.send_batch_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode="Markdown"
            )
            
            self.progress_cache[progress_key] = progress_percent
            
    def clear_progress(self, user_id: str, batch_id: str):
        """清理進度快取"""
        progress_key = f"{user_id}_{batch_id}"
        self.progress_cache.pop(progress_key, None)


# 🔧 工廠函數
async def create_batch_processing_system(telegram_handler: Optional[EnhancedTelegramBotHandler] = None,
                                       enable_queue: bool = True) -> BatchProcessingIntegration:
    """
    創建完整的批次處理系統
    
    Args:
        telegram_handler: 可選的現有處理器
        enable_queue: 是否啟用訊息排程
        
    Returns:
        配置好的批次處理整合器
    """
    if not telegram_handler:
        from .enhanced_telegram_client import create_enhanced_telegram_handler
        telegram_handler = await create_enhanced_telegram_handler(enable_queue=enable_queue)
        
    return BatchProcessingIntegration(telegram_handler)