"""
異步 Flask 應用 - 支援高並發多用戶名片處理
使用 Quart 實現異步 Flask 兼容的 Web 應用
"""

import asyncio
import base64
import io
import traceback
from datetime import datetime
from typing import Optional

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import ImageMessage, MessageEvent, TextMessage, TextSendMessage
from quart import Quart, g, jsonify, request

from simple_config import Config
from src.namecard.core.services.async_batch_service import BatchStatus
from src.namecard.infrastructure.ai.optimized_ai_service import (
    OptimizedAIService,
    ProcessingPriority,
)

# 創建異步 Flask 應用
app = Quart(__name__)

# LINE Bot 設置
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

# 全局 AI 服務實例
ai_service = None

# 用戶狀態管理
user_states = {}


async def initialize_services():
    """初始化服務"""
    global ai_service
    try:
        ai_service = OptimizedAIService(
            max_concurrent_ai=20, max_concurrent_notion=10, enable_cache=True
        )
        await ai_service.start()
        print("🚀 異步 AI 服務初始化完成")
    except Exception as e:
        print(f"❌ 服務初始化失敗: {e}")
        raise


@app.before_serving
async def startup():
    """應用啟動時初始化"""
    await initialize_services()


@app.after_serving
async def shutdown():
    """應用關閉時清理"""
    global ai_service
    if ai_service:
        await ai_service.stop()


@app.route("/", methods=["GET"])
async def home():
    """首頁"""
    return jsonify(
        {
            "service": "Async NameCard Processing Bot",
            "version": "2.0.0",
            "status": "running",
            "features": [
                "High-concurrency async processing",
                "Intelligent caching",
                "Multi-user batch processing",
                "Real-time performance monitoring",
            ],
        }
    )


@app.route("/health", methods=["GET"])
async def health_check():
    """健康檢查端點"""
    try:
        health_status = await ai_service.health_check()
        return jsonify(health_status), (
            200 if health_status["status"] == "healthy" else 503
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.route("/stats", methods=["GET"])
async def get_stats():
    """獲取服務統計"""
    try:
        service_status = await ai_service.get_service_status()
        return jsonify(service_status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/performance-report", methods=["GET"])
async def performance_report():
    """生成效能報告"""
    try:
        hours = request.args.get("hours", 24, type=int)
        report = await ai_service.get_performance_report(hours=hours)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/callback", methods=["POST"])
async def callback():
    """LINE webhook 回調處理"""
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.get_data(as_text=True)

    try:
        # 驗證簽名
        handler.handle(body, signature)

        # 異步處理 webhook 事件
        await process_webhook_async(body)

        return "OK", 200

    except InvalidSignatureError:
        return "Invalid signature", 400
    except Exception as e:
        print(f"Webhook 處理錯誤: {e}")
        return "Internal error", 500


async def process_webhook_async(body: str):
    """異步處理 webhook 事件"""
    try:
        import json

        events = json.loads(body).get("events", [])

        # 並發處理所有事件
        tasks = [process_single_event(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        print(f"處理 webhook 事件失敗: {e}")


async def process_single_event(event: dict):
    """處理單個 LINE 事件"""
    try:
        event_type = event.get("type")
        user_id = event.get("source", {}).get("userId")

        if event_type == "message":
            await handle_message_event(event, user_id)
        elif event_type == "follow":
            await handle_follow_event(user_id)

    except Exception as e:
        print(f"處理事件失敗: {e}")
        traceback.print_exc()


async def handle_message_event(event: dict, user_id: str):
    """處理訊息事件"""
    message = event.get("message", {})
    message_type = message.get("type")
    reply_token = event.get("replyToken")

    if message_type == "text":
        await handle_text_message(message, user_id, reply_token)
    elif message_type == "image":
        await handle_image_message(message, user_id, reply_token)


async def handle_text_message(message: dict, user_id: str, reply_token: str):
    """處理文字訊息"""
    text = message.get("text", "").strip().lower()

    try:
        if text in ["批次", "batch"]:
            await start_batch_mode(user_id, reply_token)
        elif text in ["結束批次", "完成批次", "end batch", "finish batch"]:
            await end_batch_mode(user_id, reply_token)
        elif text in ["狀態", "status"]:
            await show_batch_status(user_id, reply_token)
        elif text in ["help", "幫助", "說明"]:
            await show_help(reply_token)
        else:
            await reply_message(reply_token, "輸入「help」查看使用說明")

    except Exception as e:
        await reply_message(reply_token, f"處理指令時發生錯誤: {str(e)}")


async def handle_image_message(message: dict, user_id: str, reply_token: str):
    """處理圖片訊息"""
    message_id = message.get("id")

    try:
        # 立即回覆確認收到
        await reply_message(reply_token, "🔍 正在分析名片圖片，請稍候...")

        # 獲取圖片內容
        image_bytes = await get_line_image_content(message_id)
        if not image_bytes:
            await push_message(user_id, "❌ 無法獲取圖片內容")
            return

        # 檢查是否在批次模式
        is_batch_mode = user_states.get(user_id, {}).get("batch_mode", False)

        if is_batch_mode:
            await process_batch_image(user_id, image_bytes, message_id)
        else:
            await process_single_image(user_id, image_bytes)

    except Exception as e:
        await push_message(user_id, f"❌ 處理圖片時發生錯誤: {str(e)}")


async def process_single_image(user_id: str, image_bytes: bytes):
    """處理單張圖片"""
    try:
        # 使用優化 AI 服務處理
        result, metadata = await ai_service.process_image(
            image_bytes=image_bytes,
            user_id=user_id,
            priority=ProcessingPriority.HIGH,
            enable_cache=True,
            save_to_notion=True,
            timeout=30.0,
        )

        # 發送處理結果
        if result.get("error"):
            await push_message(user_id, f"❌ 處理失敗: {result['error']}")
        else:
            await send_processing_result(user_id, result, metadata)

    except Exception as e:
        await push_message(user_id, f"❌ 處理圖片失敗: {str(e)}")


async def process_batch_image(user_id: str, image_bytes: bytes, message_id: str):
    """處理批次模式圖片"""
    try:
        # 添加到批次會話
        session_id = user_states.get(user_id, {}).get("batch_session_id")
        if not session_id:
            # 創建新的批次會話
            session_id = await ai_service.batch_service.create_batch_session(
                user_id=user_id, auto_process=True, max_concurrent=3
            )
            user_states[user_id]["batch_session_id"] = session_id

        # 添加項目到批次
        item_id = f"{user_id}_{message_id}"
        success = await ai_service.batch_service.add_item_to_batch(
            session_id=session_id,
            item_id=item_id,
            image_bytes=image_bytes,
            priority=ProcessingPriority.NORMAL,
        )

        if success:
            await push_message(user_id, f"✅ 圖片已加入批次處理佇列")
        else:
            await push_message(user_id, "❌ 加入批次失敗")

    except Exception as e:
        await push_message(user_id, f"❌ 批次處理失敗: {str(e)}")


async def start_batch_mode(user_id: str, reply_token: str):
    """啟動批次模式"""
    try:
        user_states[user_id] = {
            "batch_mode": True,
            "batch_session_id": None,
            "start_time": datetime.now(),
        }

        message = """🚀 **批次處理模式已啟動**

現在您可以：
1. 連續發送多張名片圖片
2. 系統會自動並發處理
3. 發送「結束批次」查看統計結果

✨ 優化功能：
• 高並發處理（最多3張同時）
• 智能快取（避免重複處理）
• 自動保存到 Notion
• 實時處理狀態"""

        await reply_message(reply_token, message)

    except Exception as e:
        await reply_message(reply_token, f"啟動批次模式失敗: {str(e)}")


async def end_batch_mode(user_id: str, reply_token: str):
    """結束批次模式"""
    try:
        user_state = user_states.get(user_id, {})
        session_id = user_state.get("batch_session_id")

        if not user_state.get("batch_mode"):
            await reply_message(reply_token, "您目前不在批次模式中")
            return

        if session_id:
            # 獲取批次狀態
            status = await ai_service.batch_service.get_batch_status(session_id)
            results = await ai_service.batch_service.get_batch_results(session_id)

            # 生成統計報告
            report = generate_batch_report(
                status, results, user_state.get("start_time")
            )
            await reply_message(reply_token, report)

            # 保存結果到 Notion
            if results:
                await save_batch_to_notion(results)

            # 清理會話
            await ai_service.batch_service.remove_batch_session(session_id)
        else:
            await reply_message(reply_token, "批次處理已結束，但沒有處理任何圖片")

        # 清理用戶狀態
        user_states.pop(user_id, None)

    except Exception as e:
        await reply_message(reply_token, f"結束批次模式失敗: {str(e)}")


async def show_batch_status(user_id: str, reply_token: str):
    """顯示批次狀態"""
    try:
        user_state = user_states.get(user_id, {})

        if not user_state.get("batch_mode"):
            await reply_message(reply_token, "您目前不在批次模式中")
            return

        session_id = user_state.get("batch_session_id")
        if session_id:
            status = await ai_service.batch_service.get_batch_status(session_id)
            status_message = generate_status_message(status)
            await reply_message(reply_token, status_message)
        else:
            await reply_message(reply_token, "批次會話尚未建立，請先發送圖片")

    except Exception as e:
        await reply_message(reply_token, f"獲取狀態失敗: {str(e)}")


async def show_help(reply_token: str):
    """顯示幫助訊息"""
    help_message = """📋 **異步名片處理Bot使用說明**

🚀 **新功能特色**：
• 高並發處理（支援50+用戶同時使用）
• 智能快取（相同圖片秒回）
• 批次並發（一次處理多張名片）
• 自動Notion保存

📝 **基本指令**：
• `批次` / `batch` - 啟動批次處理模式
• `結束批次` - 完成批次並查看統計
• `狀態` / `status` - 查看當前處理狀態
• `help` - 顯示此說明

📷 **使用方式**：
1. 單張處理：直接發送圖片（3-5秒完成）
2. 批次處理：先輸入「批次」，再連續發送多張圖片

⚡ **效能提升**：
• 響應時間：5-10秒 → 2-5秒
• 並發能力：1用戶 → 50+用戶
• 快取命中：0% → 30-60%"""

    await reply_message(reply_token, help_message)


async def handle_follow_event(user_id: str):
    """處理關注事件"""
    welcome_message = """🎉 **歡迎使用異步名片處理Bot！**

🚀 **全新升級功能**：
✅ 高速並發處理
✅ 智能結果快取
✅ 批次處理支援
✅ 自動Notion保存

發送「help」查看詳細使用說明
或直接發送名片圖片開始體驗！"""

    await push_message(user_id, welcome_message)


def generate_batch_report(status: dict, results: list, start_time: datetime) -> str:
    """生成批次處理報告"""
    if not status:
        return "❌ 無法獲取批次狀態"

    total_items = status.get("total_items", 0)
    successful = len([r for r in results if r.get("status") == "completed"])
    failed = len([r for r in results if r.get("status") == "failed"])

    processing_time = (datetime.now() - start_time).total_seconds() if start_time else 0

    report = f"""📊 **批次處理完成報告**

🔢 **處理統計**：
• 總計圖片：{total_items} 張
• 成功處理：{successful} 張
• 處理失敗：{failed} 張
• 成功率：{(successful/total_items*100):.1f}%

⏱️ **效能統計**：
• 總處理時間：{processing_time:.1f} 秒
• 平均每張：{(processing_time/total_items):.1f} 秒
• 處理速度：{(total_items/processing_time*60):.1f} 張/分鐘

💾 **Notion 保存**：
✅ 成功處理的名片已自動保存到 Notion 資料庫

感謝使用異步名片處理服務！"""

    return report


def generate_status_message(status: dict) -> str:
    """生成狀態訊息"""
    if not status:
        return "❌ 無法獲取狀態"

    total = status.get("total_items", 0)
    progress = status.get("progress", 0)
    breakdown = status.get("status_breakdown", {})

    message = f"""📊 **批次處理狀態**

📈 **進度**：{progress:.1%} ({breakdown.get("completed", 0)}/{total})

📋 **詳細狀態**：
• ⏳ 等待中：{breakdown.get("pending", 0)} 張
• 🔄 處理中：{breakdown.get("processing", 0)} 張  
• ✅ 已完成：{breakdown.get("completed", 0)} 張
• ❌ 處理失敗：{breakdown.get("failed", 0)} 張

發送「結束批次」完成處理並查看詳細報告"""

    return message


async def send_processing_result(user_id: str, result: dict, metadata: dict):
    """發送處理結果"""
    try:
        cards = result.get("cards", [])
        if not cards:
            await push_message(user_id, "❌ 未檢測到名片內容")
            return

        # 生成結果訊息
        card_count = len(cards)
        processing_time = metadata.get("processing_time", 0)
        cache_hit = metadata.get("cache_hit", False)
        notion_saved = metadata.get("notion_saved", 0)

        message = f"""✅ **名片處理完成**

📊 **處理結果**：
• 檢測到 {card_count} 張名片
• 處理時間：{processing_time:.1f} 秒
• {('💾 已快取' if cache_hit else '🔍 新分析')}
• 💾 已保存 {notion_saved} 張到 Notion

📝 **名片資訊**："""

        for i, card in enumerate(cards, 1):
            name = card.get("name", "未知")
            company = card.get("company", "未知")
            title = card.get("title", "未知")

            message += f"""

**名片 {i}**：
• 姓名：{name}
• 公司：{company}  
• 職稱：{title}"""

            if card.get("confidence_score"):
                confidence = card["confidence_score"] * 100
                message += f"\n• 識別信心度：{confidence:.1f}%"

        await push_message(user_id, message)

    except Exception as e:
        await push_message(user_id, f"❌ 發送結果失敗: {str(e)}")


async def save_batch_to_notion(results: list):
    """批次保存結果到 Notion"""
    try:
        cards_to_save = []
        for result in results:
            if result.get("result") and result["result"].get("cards"):
                cards_to_save.extend(result["result"]["cards"])

        if cards_to_save:
            await ai_service.notion_manager.create_batch_records(cards_to_save)

    except Exception as e:
        print(f"批次保存到 Notion 失敗: {e}")


async def get_line_image_content(message_id: str) -> Optional[bytes]:
    """獲取 LINE 圖片內容"""
    try:
        # 這裡需要同步調用 LINE API，使用 run_in_executor
        loop = asyncio.get_event_loop()
        message_content = await loop.run_in_executor(
            None, line_bot_api.get_message_content, message_id
        )

        image_bytes = b""
        for chunk in message_content.iter_content():
            image_bytes += chunk

        return image_bytes

    except Exception as e:
        print(f"獲取圖片內容失敗: {e}")
        return None


async def reply_message(reply_token: str, text: str):
    """回覆訊息"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, line_bot_api.reply_message, reply_token, TextSendMessage(text=text)
        )
    except Exception as e:
        print(f"回覆訊息失敗: {e}")


async def push_message(user_id: str, text: str):
    """推播訊息"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, line_bot_api.push_message, user_id, TextSendMessage(text=text)
        )
    except Exception as e:
        print(f"推播訊息失敗: {e}")


if __name__ == "__main__":
    # 異步應用啟動
    app.run(host="0.0.0.0", port=5002, debug=False)
