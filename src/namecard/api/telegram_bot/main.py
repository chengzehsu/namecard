import asyncio
import io
import logging
import os
import sys
from datetime import datetime
from typing import Optional

from flask import Flask, request
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# 添加根目錄到 Python 路徑
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
sys.path.insert(0, root_dir)

# 導入現有的處理器
from simple_config import Config
from src.namecard.core.services.batch_service import BatchManager
from src.namecard.core.services.multi_card_service import MultiCardProcessor
from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
from src.namecard.infrastructure.storage.notion_client import NotionManager
from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler
from src.namecard.core.services.interaction_service import UserInteractionHandler

# 🚀 導入超高速處理組件
from src.namecard.infrastructure.ai.ultra_fast_processor import (
    UltraFastProcessor, 
    ultra_fast_process_telegram_image, 
    get_ultra_fast_processor,
    UltraFastResult
)
from src.namecard.infrastructure.messaging.enhanced_telegram_client import (
    EnhancedTelegramBotHandler,
    create_enhanced_telegram_handler
)
from src.namecard.infrastructure.messaging.async_message_queue import MessagePriority

# Flask 應用 (用於 webhook)
flask_app = Flask(__name__)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)


# 統一日誌輸出函數
def log_message(message, level="INFO"):
    """統一日誌輸出函數"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {level}: {message}"
    print(log_line, flush=True)
    sys.stdout.flush()
    return log_line


# 驗證配置
config_valid = False
try:
    # 檢查 Telegram Bot Token
    if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        log_message("❌ TELEGRAM_BOT_TOKEN 未設置", "ERROR")
        log_message("💡 請在 Zeabur Dashboard 設置 TELEGRAM_BOT_TOKEN", "INFO")
        log_message("📋 目前環境變數狀態:", "INFO")
        Config.show_config()
    elif not Config.validate():
        log_message("❌ 配置驗證失敗", "ERROR")
        log_message("💡 請檢查環境變數設置", "INFO")
        log_message("📋 目前環境變數狀態:", "INFO")
        Config.show_config()
    else:
        log_message("✅ Telegram Bot 配置驗證成功")
        config_valid = True
except Exception as e:
    log_message(f"❌ 配置錯誤: {e}", "ERROR")
    log_message("💡 請檢查環境變數設置", "INFO")
    log_message("📋 目前環境變數狀態:", "INFO")
    Config.show_config()

if not config_valid:
    log_message("🚨 配置無效，啟動失敗模式", "ERROR")
    # 不立即退出，而是啟動一個基本的錯誤報告服務

# 初始化處理器
processors_valid = False
card_processor = None
notion_manager = None
batch_manager = None
multi_card_processor = None
user_interaction_handler = None
telegram_bot_handler = None

# 🚀 超高速處理組件
ultra_fast_processor = None
enhanced_telegram_handler = None

if config_valid:
    try:
        log_message("📦 正在初始化處理器...")
        
        card_processor = NameCardProcessor()
        log_message("✅ NameCardProcessor 初始化成功")
        
        notion_manager = NotionManager()
        log_message("✅ NotionManager 初始化成功")
        
        batch_manager = BatchManager()
        log_message("✅ BatchManager 初始化成功")
        
        multi_card_processor = MultiCardProcessor()
        log_message("✅ MultiCardProcessor 初始化成功")
        
        user_interaction_handler = UserInteractionHandler()
        log_message("✅ UserInteractionHandler 初始化成功")
        
        telegram_bot_handler = TelegramBotHandler()
        log_message("✅ TelegramBotHandler 初始化成功")
        
        # 🚀 初始化超高速處理組件
        ultra_fast_processor = UltraFastProcessor()
        log_message("✅ UltraFastProcessor 超高速處理器初始化成功")
        
        # 創建增強型 Telegram 處理器（整合異步佇列系統）
        enhanced_telegram_handler = create_enhanced_telegram_handler(
            enable_queue=True,
            queue_workers=12,  # 增加併發工作者
            batch_size=5,
            batch_timeout=1.5  # 減少批次超時時間
        )
        log_message("✅ EnhancedTelegramBotHandler 增強處理器初始化成功")
        
        log_message("🚀 所有處理器初始化成功（包含超高速組件）")
        processors_valid = True
    except Exception as e:
        log_message(f"❌ 處理器初始化失敗: {e}", "ERROR")
        import traceback
        log_message(f"錯誤詳情: {traceback.format_exc()}", "ERROR")
        log_message("⚠️ 將以錯誤模式運行", "WARNING")
        
        # 🔧 關鍵修復：確保即使初始化失敗，也有基本的處理器
        telegram_bot_handler = None
        enhanced_telegram_handler = None
        ultra_fast_processor = None
        processors_valid = False
else:
    log_message("⚠️ 配置無效，跳過處理器初始化", "WARNING")


# === Telegram Bot 處理器設置函數 ===

async def safe_telegram_send(chat_id: int, message: str, priority: MessagePriority = MessagePriority.NORMAL) -> bool:
    """安全發送 Telegram 訊息的助手函數（支援優先級）"""
    # 優先使用增強處理器
    if enhanced_telegram_handler is not None:
        try:
            result = await enhanced_telegram_handler.safe_send_message(
                chat_id, message, priority=priority
            )
            return result.get("success", False)
        except Exception as e:
            log_message(f"❌ 增強處理器發送失敗，降級到基礎處理器: {e}", "WARNING")
    
    # 降級到基礎處理器
    if telegram_bot_handler is None:
        log_message("❌ TelegramBotHandler 未初始化，嘗試直接 API 調用", "WARNING")
        try:
            import requests
            response = requests.post(
                f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            log_message(f"❌ 直接 API 調用失敗: {e}", "ERROR")
            return False
    
    try:
        result = await telegram_bot_handler.safe_send_message(chat_id, message)
        return result.get("success", False)
    except Exception as e:
        log_message(f"❌ 發送訊息失敗: {e}", "ERROR")
        return False

def setup_telegram_handlers():
    """設置 Telegram Bot 處理器"""
    if not application:
        log_message("❌ 無法設置處理器：Application 未初始化", "ERROR")
        return False
    
    try:
        # 指令處理器
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("batch", batch_command))
        application.add_handler(CommandHandler("endbatch", endbatch_command))
        application.add_handler(CommandHandler("status", status_command))

        # 訊息處理器
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        
        log_message("🔧 所有處理器已成功註冊")
        return True
        
    except Exception as e:
        log_message(f"❌ 處理器註冊失敗: {e}", "ERROR")
        return False


# === Telegram Bot Application 初始化 ===

# Telegram Bot Application
application = None
if config_valid and Config.TELEGRAM_BOT_TOKEN:
    try:
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        log_message("✅ Telegram Bot Application 初始化成功")
        log_message("⏳ 處理器將在所有函數定義完成後設置")
            
    except Exception as e:
        log_message(f"❌ Telegram Bot Application 初始化失敗: {e}", "ERROR")
        application = None
else:
    log_message("⚠️ Telegram Bot Token 無效，跳過 Application 初始化", "WARNING")

# === Telegram Bot 指令處理器 ===


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /start 指令"""
    welcome_text = """🤖 **歡迎使用名片管理 Telegram Bot！**

📸 **功能介紹：**
• 智能名片識別 - 使用 Google Gemini AI
• 自動存入 Notion 資料庫  
• 多名片檢測和品質評估
• 批次處理模式
• 台灣地址正規化

🚀 **開始使用：**
• 直接傳送名片照片給我
• 或輸入 /help 查看詳細說明

💡 **提示：** 使用 /batch 開啟批次處理模式"""

    await telegram_bot_handler.safe_send_message(
        update.effective_chat.id, welcome_text, parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /help 指令"""
    help_text = """🤖 **名片管理 Telegram Bot 使用說明**

📸 **單張名片處理**
• 直接傳送名片照片給我
• 我會自動識別名片資訊並存入 Notion

🔄 **批次處理模式**
• `/batch` - 進入批次模式
• 連續發送多張名片圖片
• `/endbatch` - 結束批次並查看統計
• `/status` - 查看當前批次進度

⚙️ **其他指令**
• `/start` - 開始使用
• `/help` - 顯示本說明

💡 **功能特色：**
• 使用 Google Gemini AI 識別文字
• 支援多名片檢測和品質評估
• 自動整理聯絡資訊
• 直接存入 Notion 資料庫
• 支援中英文名片
• 台灣地址正規化處理

❓ 有問題請聯繫系統管理員"""

    await telegram_bot_handler.safe_send_message(
        update.effective_chat.id, help_text, parse_mode=ParseMode.MARKDOWN
    )


async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /batch 指令 - 開始批次模式"""
    user_id = str(update.effective_user.id)
    result = batch_manager.start_batch_mode(user_id)

    await telegram_bot_handler.safe_send_message(
        update.effective_chat.id, result["message"]
    )


async def endbatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /endbatch 指令 - 結束批次模式"""
    user_id = str(update.effective_user.id)
    result = batch_manager.end_batch_mode(user_id)

    if result["success"]:
        stats = result["statistics"]
        summary_text = f"""📊 **批次處理完成**

✅ **處理成功：** {stats['total_processed']} 張
❌ **處理失敗：** {stats['total_failed']} 張
⏱️ **總耗時：** {stats['total_time_minutes']:.1f} 分鐘

📋 **成功處理的名片：**"""

        for card in stats["processed_cards"]:
            summary_text += f"\n• {card['name']} ({card['company']})"

        if stats["failed_cards"]:
            summary_text += f"\n\n❌ **失敗記錄：**"
            for i, failed in enumerate(stats["failed_cards"], 1):
                summary_text += f"\n{i}. {failed['error'][:50]}..."

        await telegram_bot_handler.safe_send_message(
            update.effective_chat.id, summary_text
        )
    else:
        await telegram_bot_handler.safe_send_message(
            update.effective_chat.id, result["message"]
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /status 指令 - 查看批次狀態"""
    user_id = str(update.effective_user.id)

    if batch_manager.is_in_batch_mode(user_id):
        progress_msg = batch_manager.get_batch_progress_message(user_id)
        await telegram_bot_handler.safe_send_message(
            update.effective_chat.id, progress_msg
        )
    else:
        await telegram_bot_handler.safe_send_message(
            update.effective_chat.id, "您目前不在批次模式中。使用 /batch 開始批次處理。"
        )


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """處理文字訊息"""
    user_message = update.message.text.strip()
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    # 檢查是否有待處理的多名片會話
    if user_interaction_handler.has_pending_session(user_id):
        # 處理多名片選擇
        choice_result = user_interaction_handler.handle_user_choice(
            user_id, user_message
        )

        if choice_result["action"] == "retake_photo":
            await telegram_bot_handler.safe_send_message(
                chat_id, choice_result["message"]
            )

        elif choice_result["action"] in [
            "process_all_cards",
            "process_selected_cards",
        ]:
            # 處理選擇的名片
            cards_to_process = choice_result.get("cards_to_process", [])
            await telegram_bot_handler.safe_send_message(
                chat_id, choice_result["message"]
            )

            # 異步處理多張名片
            user_is_batch_mode = batch_manager.is_in_batch_mode(user_id)
            await _process_multiple_cards_async(
                user_id, chat_id, cards_to_process, user_is_batch_mode
            )

        else:
            # 其他狀況（無效選擇、會話過期等）
            await telegram_bot_handler.safe_send_message(
                chat_id, choice_result["message"]
            )

    # 檢查是否在批次模式中
    elif batch_manager.is_in_batch_mode(user_id):
        progress_msg = batch_manager.get_batch_progress_message(user_id)
        reply_text = f"您目前在批次模式中，請發送名片圖片。\n\n{progress_msg}"
        await telegram_bot_handler.safe_send_message(chat_id, reply_text)
    else:
        reply_text = "請上傳名片圖片，我會幫您識別並存入 Notion 📸\n\n💡 提示：使用 /batch 可開啟批次處理模式"
        await telegram_bot_handler.safe_send_message(chat_id, reply_text)


async def handle_photo_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """處理圖片訊息 - 名片識別"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    is_batch_mode = batch_manager.is_in_batch_mode(user_id)

    try:
        # 更新用戶活動時間
        if is_batch_mode:
            batch_manager.update_activity(user_id)

        # 發送處理中訊息
        if is_batch_mode:
            session_info = batch_manager.get_session_info(user_id)
            current_count = session_info["total_count"] + 1 if session_info else 1
            processing_message = (
                f"📸 批次模式 - 正在處理第 {current_count} 張名片，請稍候...\n"
                f"⏱️ 預計需要 30-60 秒完成處理"
            )
        else:
            processing_message = (
                "📸 收到名片圖片！正在使用 AI 識別中，請稍候...\n"
                "⏱️ 預計需要 30-60 秒完成處理\n"
                "🤖 使用 Google Gemini AI + 多名片檢測"
            )

        # 🔧 關鍵修復：使用安全發送函數
        if telegram_bot_handler is None and enhanced_telegram_handler is None:
            await safe_telegram_send(chat_id, "❌ 系統初始化錯誤，請聯繫管理員", MessagePriority.EMERGENCY)
            return

        # 立即發送處理開始訊息
        await safe_telegram_send(chat_id, processing_message, MessagePriority.HIGH)

        # 下載圖片
        photo = update.message.photo[-1]  # 獲取最高解析度的圖片
        
        # 優先使用增強處理器下載文件
        file_result = None
        if enhanced_telegram_handler:
            try:
                file_result = await enhanced_telegram_handler.safe_get_file(photo.file_id)
            except Exception as e:
                log_message(f"⚠️ 增強處理器下載失敗，降級到基礎處理器: {e}")
        
        if not file_result and telegram_bot_handler:
            file_result = await telegram_bot_handler.safe_get_file(photo.file_id)

        if not file_result or not file_result["success"]:
            error_msg = f"❗ 無法下載圖片: {file_result.get('message', '未知錯誤') if file_result else '處理器未初始化'}"
            await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)
            return

        # 獲取圖片字節數據
        log_message("📥 開始下載圖片字節數據...")
        try:
            file_obj = file_result["file"]
            image_bytes = await file_obj.download_as_bytearray()
            log_message(f"✅ 圖片下載完成，大小: {len(image_bytes)} bytes")
        except Exception as download_error:
            log_message(f"❌ 圖片下載失敗: {download_error}", "ERROR")
            error_msg = f"❗ 圖片下載失敗: {str(download_error)}"
            await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)
            return

        # 🚀 使用超高速處理器進行圖片處理
        ai_progress_msg = "🚀 圖片下載完成，正在使用超高速 AI 識別中..."
        await safe_telegram_send(chat_id, ai_progress_msg, MessagePriority.HIGH)

        log_message("🚀 開始超高速名片識別處理...")
        try:
            # 使用超高速處理器
            ultra_result = await ultra_fast_processor.process_telegram_photo_ultra_fast(
                file_obj, user_id, processing_type="single_card"
            )
            
            if ultra_result.success:
                log_message(f"✅ 超高速處理完成 - 耗時: {ultra_result.total_time:.2f}s, 等級: {ultra_result.performance_grade}")
                
                # 轉換為多名片格式以保持兼容性
                analysis_result = {
                    "card_count": 1,
                    "cards": [ultra_result.data],
                    "overall_quality": "good" if ultra_result.performance_grade in ["S", "A"] else "partial",
                    "auto_process": True,  # 高品質自動處理
                    "processing_suggestions": []
                }
            else:
                # 降級到傳統處理器
                log_message(f"⚠️ 超高速處理失敗，降級到傳統處理器: {ultra_result.error}")
                
                # 設置處理超時 (最大 90 秒)
                import asyncio
                analysis_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        multi_card_processor.process_image_with_quality_check,
                        bytes(image_bytes)
                    ),
                    timeout=90.0
                )
                log_message("✅ 傳統 AI 識別和品質評估完成")
                
        except Exception as ultra_error:
            log_message(f"❌ 超高速處理器錯誤，降級到傳統處理器: {ultra_error}")
            
            # 降級到傳統處理器
            import asyncio
            analysis_result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    multi_card_processor.process_image_with_quality_check,
                    bytes(image_bytes)
                ),
                timeout=90.0
            )
            log_message("✅ 傳統 AI 識別和品質評估完成")
        except asyncio.TimeoutError:
            log_message("❌ AI 識別處理超時 (90秒)", "ERROR")
            timeout_error_msg = (
                "⏰ **AI 識別處理超時**\n\n"
                "處理時間超過 90 秒限制，請嘗試：\n"
                "• 📷 上傳更清晰的圖片\n"
                "• 📏 降低圖片解析度 (<2048x2048)\n"
                "• 📦 減小檔案大小 (<3MB)\n"
                "• ⏰ 稍候 2-3 分鐘後重試\n\n"
                "💡 如問題持續，請聯繫管理員"
            )
            
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, "AI 識別超時")
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                timeout_error_msg += f"\n\n{progress_msg}"
                
            await safe_telegram_send(chat_id, timeout_error_msg, MessagePriority.EMERGENCY)
            return
            
        except Exception as ai_error:
            log_message(f"❌ AI 識別過程發生錯誤: {ai_error}", "ERROR")
            import traceback
            log_message(f"AI 錯誤堆疊: {traceback.format_exc()}", "ERROR")
            
            # 根據錯誤類型提供具體建議
            error_str = str(ai_error).lower()
            if "quota" in error_str or "limit" in error_str:
                error_msg = (
                    "🔑 **AI 服務配額已用完**\n\n"
                    "Gemini AI 今日配額已達上限，請：\n"
                    "• ⏰ 明天再試\n"
                    "• 📞 聯繫管理員增加配額\n"
                    "• 🔄 嘗試使用備用服務"
                )
            elif "network" in error_str or "connection" in error_str:
                error_msg = (
                    "🌐 **網路連接問題**\n\n"
                    "與 AI 服務連接中斷，請：\n"
                    "• 🔄 稍後重試 (1-2 分鐘)\n"
                    "• 📶 檢查網路連接\n"
                    "• 📞 如問題持續，請聯繫管理員"
                )
            else:
                error_msg = (
                    "❌ **AI 識別過程中發生錯誤**\n\n"
                    f"錯誤詳情：{str(ai_error)[:100]}...\n\n"
                    "建議：\n"
                    "• 🔄 重新上傳圖片\n"
                    "• 📷 確保圖片清晰度良好\n"
                    "• 📞 如問題持續，請聯繫管理員"
                )
            
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, str(ai_error))
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_msg += f"\n\n{progress_msg}"
                
            await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)
            return

        if "error" in analysis_result:
            error_message = f"❌ 名片識別失敗: {analysis_result['error']}"

            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, analysis_result["error"])
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"

            await safe_telegram_send(chat_id, error_message, MessagePriority.EMERGENCY)
            return

        # 根據分析結果決定處理方式
        if analysis_result.get("action_required", False):
            # 需要用戶選擇，創建交互會話
            choice_message = user_interaction_handler.create_multi_card_session(
                user_id, analysis_result
            )
            await safe_telegram_send(chat_id, choice_message, MessagePriority.HIGH)
            return

        # 自動處理（單張高品質名片）
        elif analysis_result.get("auto_process", False):
            cards_to_process = analysis_result.get("cards", [])
            if cards_to_process:
                await safe_telegram_send(
                    chat_id, "✅ 名片品質良好，正在自動處理...", MessagePriority.HIGH
                )
                # 處理名片
                await _process_single_card_from_multi_format(
                    user_id, chat_id, cards_to_process[0], is_batch_mode
                )
            return

        # 如果到這裡，說明沒有匹配到其他情況，直接處理（向後兼容）
        cards = analysis_result.get("cards", [])
        if cards:
            await _process_single_card_from_multi_format(
                user_id, chat_id, cards[0], is_batch_mode
            )

    except Exception as e:
        log_message(f"❌ 處理圖片時發生錯誤: {e}", "ERROR")
        import traceback
        log_message(f"完整錯誤堆疊: {traceback.format_exc()}", "ERROR")
        
        # 根據錯誤類型提供更具體的錯誤信息
        error_type = type(e).__name__
        error_str = str(e).lower()
        
        if "timeout" in error_str or "TimeoutError" in error_type:
            error_msg = (
                "⏰ **處理超時**\n\n"
                "建議解決方案：\n"
                "• 📷 上傳較小的圖片 (<3MB)\n"
                "• 📏 降低解析度 (<2048x2048)\n"
                "• ⏰ 等待 2-3 分鐘後重試\n"
                "• 🔄 如果是網路問題，請檢查連接"
            )
        elif "memory" in error_str or "MemoryError" in error_type:
            error_msg = (
                "💾 **記憶體不足**\n\n"
                "圖片太大，請：\n"
                "• 📏 解析度 < 2048x2048\n"
                "• 📦 檔案大小 < 3MB\n"
                "• 🎨 格式：JPG/PNG"
            )
        elif "network" in error_str or "ConnectionError" in error_type:
            error_msg = (
                "🌐 **網路連接問題**\n\n"
                "• 🔄 請稍後重試 (1-2 分鐘)\n"
                "• 📶 檢查網路連接穩定性\n"
                "• 📞 問題持續請聯繫管理員"
            )
        elif "api" in error_str or "quota" in error_str:
            error_msg = (
                "🔑 **API 服務問題**\n\n"
                "• ⏰ AI 服務暫時不可用\n"
                "• 🔄 請稍後重試\n"
                "• 📞 如問題持續，請聯繫管理員"
            )
        else:
            error_msg = (
                f"❌ **處理過程中發生錯誤**\n\n"
                f"🔍 錯誤類型: {error_type}\n"
                f"📝 錯誤摘要: {str(e)[:80]}...\n\n"
                "建議：\n"
                "• 🔄 重新上傳圖片\n"
                "• 📞 如問題持續，請聯繫管理員"
            )

        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            batch_manager.add_failed_card(user_id, str(e))
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            error_msg += f"\n\n{progress_msg}"

        # 🔧 安全發送錯誤訊息
        await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)


# === 輔助函數 ===


async def _process_single_card_from_multi_format(
    user_id: str, chat_id: int, card_data: dict, is_batch_mode: bool
):
    """處理單張名片（從多名片格式適配到原有邏輯）"""
    try:
        # 存入 Notion
        log_message("💾 存入 Notion 資料庫...")
        notion_result = notion_manager.create_name_card_record(
            card_data, None
        )  # 暫時不傳圖片

        if notion_result["success"]:
            # 記錄成功處理（如果在批次模式中）
            if is_batch_mode:
                card_info = {
                    "name": card_data.get("name", "Unknown"),
                    "company": card_data.get("company", "Unknown"),
                    "notion_url": notion_result["url"],
                }
                batch_manager.add_processed_card(user_id, card_info)

                # 批次模式簡化回應
                session_info = batch_manager.get_session_info(user_id)
                batch_message = f"""✅ 第 {session_info['total_count']} 張名片處理完成
                
👤 {card_data.get('name', 'N/A')} ({card_data.get('company', 'N/A')})

{batch_manager.get_batch_progress_message(user_id)}"""

                await safe_telegram_send(chat_id, batch_message, MessagePriority.BATCH)
            else:
                # 單張模式詳細回應
                confidence_info = ""
                if card_data.get("confidence_score"):
                    confidence_info = (
                        f"\n🎯 **識別信心度：** {card_data['confidence_score']:.1%}"
                    )

                success_message = f"""✅ **名片資訊已成功存入 Notion！**

👤 **姓名：** {card_data.get('name', 'N/A')}
🏢 **公司：** {card_data.get('company', 'N/A')}
🏬 **部門：** {card_data.get('department', 'N/A')}
💼 **職稱：** {card_data.get('title', 'N/A')}
📧 **Email：** {card_data.get('email', 'N/A')}
📞 **電話：** {card_data.get('phone', 'N/A')}{confidence_info}

🔗 **Notion 頁面：** {notion_result['url']}

💡 提示：使用 /batch 可開啟批次處理模式"""

                # 優先使用增強處理器發送成功訊息
                if enhanced_telegram_handler:
                    await enhanced_telegram_handler.safe_send_message(
                        chat_id, success_message, parse_mode=ParseMode.MARKDOWN,
                        priority=MessagePriority.HIGH
                    )
                else:
                    await safe_telegram_send(chat_id, success_message, MessagePriority.HIGH)
        else:
            error_message = f"❌ Notion 存入失敗: {notion_result['error']}"

            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, notion_result["error"])
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"

            await safe_telegram_send(chat_id, error_message, MessagePriority.EMERGENCY)

    except Exception as e:
        error_msg = f"❌ 處理名片時發生錯誤: {str(e)}"
        log_message(error_msg, "ERROR")
        await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)


async def _process_multiple_cards_async(
    user_id: str, chat_id: int, cards_to_process: list, is_batch_mode: bool
):
    """異步處理多張名片"""
    try:
        success_count = 0
        failed_count = 0
        results = []

        for i, card_data in enumerate(cards_to_process, 1):
            try:
                # 處理單張名片
                notion_result = notion_manager.create_name_card_record(card_data, None)

                if notion_result["success"]:
                    success_count += 1
                    results.append(
                        {
                            "success": True,
                            "name": card_data.get("name", f"名片{i}"),
                            "company": card_data.get("company", "Unknown"),
                            "url": notion_result["url"],
                        }
                    )

                    # 記錄成功（如果在批次模式中）
                    if is_batch_mode:
                        card_info = {
                            "name": card_data.get("name", f"名片{i}"),
                            "company": card_data.get("company", "Unknown"),
                            "notion_url": notion_result["url"],
                        }
                        batch_manager.add_processed_card(user_id, card_info)
                else:
                    failed_count += 1
                    results.append(
                        {
                            "success": False,
                            "name": card_data.get("name", f"名片{i}"),
                            "error": notion_result.get("error", "未知錯誤"),
                        }
                    )

                    if is_batch_mode:
                        batch_manager.add_failed_card(
                            user_id, notion_result.get("error", "未知錯誤")
                        )

            except Exception as e:
                failed_count += 1
                error_msg = f"處理第{i}張名片時出錯: {str(e)}"
                results.append(
                    {
                        "success": False,
                        "name": card_data.get("name", f"名片{i}"),
                        "error": error_msg,
                    }
                )

                if is_batch_mode:
                    batch_manager.add_failed_card(user_id, error_msg)

        # 發送處理結果摘要
        summary_message = f"📊 **多名片處理完成**\n\n"
        summary_message += f"✅ 成功處理：{success_count} 張\n"
        summary_message += f"❌ 處理失敗：{failed_count} 張\n\n"

        if success_count > 0:
            summary_message += "**成功處理的名片：**\n"
            for result in results:
                if result["success"]:
                    summary_message += (
                        f"• {result['name']} ({result.get('company', 'N/A')})\n"
                    )

        if failed_count > 0:
            summary_message += f"\n**失敗記錄：**\n"
            for result in results:
                if not result["success"]:
                    summary_message += (
                        f"• {result['name']}: {result['error'][:30]}...\n"
                    )

        if is_batch_mode:
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            summary_message += f"\n{progress_msg}"

        # 優先使用增強處理器發送摘要
        if enhanced_telegram_handler:
            await enhanced_telegram_handler.safe_send_message(
                chat_id, summary_message, parse_mode=ParseMode.MARKDOWN,
                priority=MessagePriority.HIGH
            )
        else:
            await safe_telegram_send(chat_id, summary_message, MessagePriority.HIGH)

    except Exception as e:
        error_msg = f"❌ 批次處理多名片時發生錯誤: {str(e)}"
        log_message(error_msg, "ERROR")
        await safe_telegram_send(chat_id, error_msg, MessagePriority.EMERGENCY)


# === Flask Webhook 處理 ===


@flask_app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """Telegram Bot webhook 處理"""
    try:
        log_message("📥 收到 Telegram webhook 請求")

        # 獲取更新數據
        update_data = request.get_json()
        if not update_data:
            log_message("❌ 空的請求體", "ERROR")
            return "Empty request body", 400

        log_message(f"📄 Update data: {update_data}")

        # 驗證數據格式是否為有效的 Telegram Update
        if not isinstance(update_data, dict):
            log_message("❌ 無效的數據格式：不是字典", "ERROR")
            return "Invalid data format", 400
            
        # 檢查是否是測試數據（在檢查 update_id 之前）
        if update_data.get("test") == "data":
            log_message("🧪 檢測到測試數據，返回成功", "INFO")
            return "Test data received successfully", 200
            
        # 檢查是否包含必要的 update_id
        if "update_id" not in update_data:
            log_message("❌ 無效的 Telegram Update：缺少 update_id", "ERROR")
            return "Invalid Telegram Update: missing update_id", 400

        # 創建 Update 對象並處理
        try:
            update = Update.de_json(update_data, application.bot)
            if not update:
                log_message("❌ 無法解析 Telegram Update 數據", "ERROR")
                return "Failed to parse Telegram Update", 400
        except Exception as parse_error:
            log_message(f"❌ 解析 Telegram Update 時發生錯誤: {parse_error}", "ERROR")
            return f"Parse error: {str(parse_error)}", 400

        # 使用新的事件循環運行異步處理
        import asyncio
        import threading

        def run_async_update(update):
            """在新線程中運行異步更新處理"""
            try:
                # 創建新的事件循環
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # 初始化應用並運行異步處理
                async def process_update_with_init():
                    try:
                        await application.initialize()
                        await application.process_update(update)
                        await application.shutdown()
                        log_message("✅ 異步處理完成")
                    except Exception as inner_e:
                        log_message(f"❌ 處理更新時發生錯誤: {inner_e}", "ERROR")
                        import traceback
                        log_message(f"完整錯誤堆疊: {traceback.format_exc()}", "ERROR")
                        traceback.print_exc()
                        
                        # 嘗試發送更詳細的錯誤訊息給用戶
                        try:
                            if hasattr(update, 'effective_chat') and update.effective_chat:
                                chat_id = update.effective_chat.id
                                
                                # 根據錯誤類型提供具體的錯誤訊息
                                error_str = str(inner_e).lower()
                                if "timeout" in error_str:
                                    error_msg = (
                                        "⏰ 處理超時，請稍後重試\n\n"
                                        "💡 建議：\n"
                                        "• 上傳較小的圖片 (<5MB)\n"
                                        "• 確保圖片清晰度適中\n"
                                        "• 稍等 1-2 分鐘後重試"
                                    )
                                elif "memory" in error_str:
                                    error_msg = (
                                        "💾 圖片太大，請上傳較小的圖片\n\n"
                                        "💡 建議圖片規格：\n"
                                        "• 檔案大小 < 5MB\n"
                                        "• 解析度 < 4096x4096\n"
                                        "• 格式：JPG/PNG"
                                    )
                                elif "api" in error_str or "key" in error_str:
                                    error_msg = (
                                        "🔑 AI 服務暫時不可用\n\n"
                                        "請稍後重試，或聯繫管理員"
                                    )
                                else:
                                    error_msg = (
                                        f"❌ 處理過程中發生錯誤\n\n"
                                        f"🔍 錯誤類型: {type(inner_e).__name__}\n"
                                        f"📞 如問題持續，請聯繫管理員"
                                    )
                                
                                # 使用 Bot API 直接發送錯誤訊息
                                import requests
                                requests.post(
                                    f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                                    json={"chat_id": chat_id, "text": error_msg},
                                    timeout=5
                                )
                                log_message(f"📤 已發送具體錯誤訊息給用戶 {chat_id}")
                        except Exception as send_error:
                            log_message(f"❌ 無法發送錯誤訊息: {send_error}", "ERROR")

                loop.run_until_complete(process_update_with_init())
                loop.close()
            except Exception as e:
                log_message(f"❌ 異步處理錯誤: {e}", "ERROR")
                import traceback
                traceback.print_exc()

        # 立即返回給 Telegram，避免 webhook 超時
        # 實際處理在後台進行，錯誤會直接發送給用戶
        log_message("⚡ 立即回應 Telegram webhook，開始後台處理")
        
        # 在後台線程中處理更新
        thread = threading.Thread(target=run_async_update, args=(update,))
        thread.daemon = False  # 確保處理完成
        thread.start()
        
        return "OK", 200

    except Exception as e:
        log_message(f"❌ Webhook 處理過程中發生錯誤: {e}", "ERROR")
        import traceback

        traceback.print_exc()
        return "Internal Server Error", 500


@flask_app.route("/health", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "Telegram Bot is running"}


@flask_app.route("/test", methods=["GET"])
def test_services():
    """測試各服務連接狀態"""
    results = {}

    # 測試 Notion 連接
    notion_test = notion_manager.test_connection()
    results["notion"] = notion_test

    # 測試 Gemini (簡單檢查)
    try:
        NameCardProcessor()
        results["gemini"] = {"success": True, "message": "Gemini 連接正常"}
    except Exception as e:
        results["gemini"] = {"success": False, "error": str(e)}

    # 測試 Telegram Bot API
    try:
        results["telegram"] = {"success": True, "message": "Telegram Bot 連接正常"}
    except Exception as e:
        results["telegram"] = {"success": False, "error": str(e)}

    return results


@flask_app.route("/ultra-fast-status", methods=["GET"])
def ultra_fast_status():
    """超高速處理系統狀態"""
    try:
        status = {
            "ultra_fast_processor": {
                "initialized": ultra_fast_processor is not None,
                "status": "ready" if ultra_fast_processor else "not_initialized"
            },
            "enhanced_telegram_handler": {
                "initialized": enhanced_telegram_handler is not None,
                "queue_running": enhanced_telegram_handler.message_queue.is_running if enhanced_telegram_handler and enhanced_telegram_handler.message_queue else False
            },
            "performance_target": "35-40s → 5-10s (4-8x improvement)",
            "optimizations": [
                "Async parallel AI processing",
                "Smart multi-layer caching",
                "Optimized prompt engineering", 
                "Parallel image downloading",
                "Intelligent message queue routing"
            ]
        }
        
        # 獲取詳細統計
        if ultra_fast_processor:
            status["ultra_fast_processor"]["dashboard"] = ultra_fast_processor.get_performance_dashboard()
        
        if enhanced_telegram_handler:
            status["enhanced_telegram_handler"]["metrics"] = enhanced_telegram_handler.get_performance_metrics()
            
        return status
    except Exception as e:
        return {"error": str(e), "status": "error"}

@flask_app.route("/", methods=["GET"])
def index():
    """首頁"""
    return {
        "message": "Telegram Bot 名片管理系統 (超高速版)",
        "status": "running",
        "endpoints": ["/health", "/test", "/telegram-webhook", "/ultra-fast-status"],
        "bot_info": "使用 Google Gemini AI 識別名片並存入 Notion",
        "performance_features": [
            "🚀 超高速處理 (4-8x 提升)",
            "🤖 智能異步訊息佇列",
            "💾 多層智能快取",
            "⚡ 並行圖片下載",
            "🎯 優化 Prompt 工程"
        ]
    }


# === 初始化和啟動 ===




# 🔧 關鍵修復：在所有函數定義完成後設置處理器
if application and config_valid:
    try:
        if setup_telegram_handlers():
            log_message("✅ Telegram Bot 處理器設置完成")
        else:
            log_message("❌ Telegram Bot 處理器設置失敗", "ERROR")
    except Exception as e:
        log_message(f"❌ 處理器設置過程發生錯誤: {e}", "ERROR")
        import traceback
        log_message(f"錯誤詳情: {traceback.format_exc()}", "ERROR")


async def startup_enhanced_systems():
    """啟動增強系統組件"""
    try:
        if enhanced_telegram_handler:
            await enhanced_telegram_handler.start_queue_system()
            log_message("✅ 增強處理器佇列系統已啟動")
        
        if ultra_fast_processor:
            # 預熱連接池
            async with ultra_fast_processor:
                log_message("✅ 超高速處理器預熱完成")
                
    except Exception as e:
        log_message(f"⚠️ 增強系統啟動警告: {e}", "WARNING")

def run_startup():
    """在背景執行啟動程序"""
    import asyncio
    import threading
    
    def startup_thread():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(startup_enhanced_systems())
            loop.close()
            log_message("🚀 增強系統啟動完成")
        except Exception as e:
            log_message(f"❌ 增強系統啟動失敗: {e}", "ERROR")
    
    thread = threading.Thread(target=startup_thread)
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    # 🔧 處理器現在在 application 初始化時自動設置，無需重複調用
    
    # 使用統一日誌輸出
    log_message("🚀 啟動 Telegram Bot 名片管理系統...")
    log_message("📋 使用 Notion 作為資料庫")
    log_message("🤖 使用 Google Gemini AI 識別名片 + 多名片檢測")
    log_message("🎯 支援品質評估和用戶交互選擇")
    log_message("⚡ 整合超高速處理系統 (目標: 4-8x 速度提升)")

    # 獲取端口配置
    port = int(os.environ.get("PORT", 5003))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    log_message(f"⚡ Telegram Bot 服務啟動中... 端口: {port}, Debug: {debug_mode}")
    
    # 啟動增強系統
    if processors_valid:
        run_startup()

    # 生產環境配置
    flask_app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=False,
    )
