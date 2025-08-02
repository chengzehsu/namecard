import logging
import os
import sys
from datetime import datetime

from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import ImageMessage, MessageEvent, TextMessage, TextSendMessage

from batch_manager import BatchManager

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config
from line_bot_handler import LineBotApiHandler
from multi_card_processor import MultiCardProcessor
from name_card_processor import NameCardProcessor
from notion_manager import NotionManager
from pr_creator import PRCreator
from user_interaction_handler import UserInteractionHandler

# 初始化 Flask 應用
app = Flask(__name__)

# 配置日誌輸出（確保 Zeabur 可以捕獲日誌）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.StreamHandler(sys.stderr)],
)

# 設置 Flask 應用日誌
app.logger.setLevel(logging.INFO)
app.logger.addHandler(logging.StreamHandler(sys.stdout))


# 強制輸出到 stdout（Zeabur 日誌捕獲）
def log_message(message, level="INFO"):
    """統一日誌輸出函數"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {level}: {message}"
    print(log_line, flush=True)  # 強制刷新輸出
    sys.stdout.flush()
    return log_line


# 驗證配置（使用新的日誌函數）
try:
    Config.validate_config()
    log_message("✅ 配置驗證成功")
except ValueError as e:
    log_message(f"❌ 配置錯誤: {e}", "ERROR")
    exit(1)

# 初始化 LINE Bot
if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_CHANNEL_SECRET:
    log_message("❌ LINE Bot 配置不完整", "ERROR")
    exit(1)

line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

# 初始化安全的 LINE Bot API 處理器
safe_line_bot = LineBotApiHandler(Config.LINE_CHANNEL_ACCESS_TOKEN)

# 初始化處理器
try:
    card_processor = NameCardProcessor()
    notion_manager = NotionManager()
    batch_manager = BatchManager()
    pr_creator = PRCreator()
    multi_card_processor = MultiCardProcessor()
    user_interaction_handler = UserInteractionHandler()
    print("✅ 處理器初始化成功")
except Exception as e:
    print(f"❌ 處理器初始化失敗: {e}")
    exit(1)


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Bot webhook 回調函數 - 嚴格按照 LINE API 規範"""

    # 記錄請求資訊（使用統一日誌函數）
    log_message(f"📥 收到 POST 請求到 /callback")
    log_message(f"📋 Request headers: {dict(request.headers)}")
    log_message(f"🌍 Remote addr: {request.environ.get('REMOTE_ADDR', 'unknown')}")
    log_message(f"🔍 User agent: {request.headers.get('User-Agent', 'unknown')}")

    # 1. 檢查 Content-Type（LINE 要求 application/json）
    content_type = request.headers.get("Content-Type", "")
    if not content_type.startswith("application/json"):
        log_message(f"❌ 錯誤的 Content-Type: {content_type}", "ERROR")
        return "Content-Type must be application/json", 400

    # 2. 獲取 X-Line-Signature header（必須）
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        log_message("❌ 缺少必要的 X-Line-Signature header", "ERROR")
        return "Missing X-Line-Signature header", 400

    # 3. 獲取請求體
    body = request.get_data(as_text=True)
    if not body:
        log_message("❌ 空的請求體", "ERROR")
        return "Empty request body", 400

    log_message(f"📄 Request body length: {len(body)}")
    log_message(f"📄 Request body preview: {body[:200]}...")

    # 4. 驗證簽名並處理 webhook
    try:
        handler.handle(body, signature)
        log_message("✅ Webhook 處理成功")

        # LINE API 要求返回 200 狀態碼
        return "OK", 200

    except InvalidSignatureError as e:
        log_message(f"❌ 簽名驗證失敗: {e}", "ERROR")
        log_message(
            f"🔑 使用的 Channel Secret: {Config.LINE_CHANNEL_SECRET[:10]}...", "ERROR"
        )
        abort(400)

    except Exception as e:
        log_message(f"❌ Webhook 處理過程中發生錯誤: {e}", "ERROR")
        import traceback

        traceback.print_exc()
        abort(500)


# 為了解決 ngrok 免費版的問題，添加一個簡單的 GET 端點
@app.route("/callback", methods=["GET"])
def callback_info():
    """顯示 callback 端點資訊"""
    return {
        "message": "LINE Bot webhook endpoint",
        "method": "POST only",
        "status": "ready",
    }


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 批次模式指令處理
    if user_message.lower() in ["批次", "batch", "批次模式", "開始批次"]:
        result = batch_manager.start_batch_mode(user_id)
        reply_result = safe_line_bot.safe_reply_message(
            event.reply_token, result["message"]
        )

        if (
            not reply_result["success"]
            and reply_result.get("error_type") == "quota_exceeded"
        ):
            # 記錄離線訊息
            log_message(f"📝 離線訊息記錄 - 用戶 {user_id}: {user_message}", "INFO")
        return

    elif user_message.lower() in ["結束批次", "end batch", "完成批次", "批次結束"]:
        result = batch_manager.end_batch_mode(user_id)
        if result["success"]:
            stats = result["statistics"]
            summary_text = f"""📊 **批次處理完成**

✅ **處理成功:** {stats['total_processed']} 張
❌ **處理失敗:** {stats['total_failed']} 張
⏱️ **總耗時:** {stats['total_time_minutes']:.1f} 分鐘

📋 **成功處理的名片:**"""

            for card in stats["processed_cards"]:
                summary_text += f"\n• {card['name']} ({card['company']})"

            if stats["failed_cards"]:
                summary_text += f"\n\n❌ **失敗記錄:**"
                for i, failed in enumerate(stats["failed_cards"], 1):
                    summary_text += f"\n{i}. {failed['error'][:50]}..."

            safe_line_bot.safe_reply_message(event.reply_token, summary_text)
        else:
            safe_line_bot.safe_reply_message(event.reply_token, result["message"])
        return

    elif user_message.lower() in ["狀態", "status", "批次狀態"]:
        if batch_manager.is_in_batch_mode(user_id):
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            safe_line_bot.safe_reply_message(event.reply_token, progress_msg)
        else:
            safe_line_bot.safe_reply_message(
                event.reply_token, "您目前不在批次模式中。發送「批次」開始批次處理。"
            )
        return

    elif user_message.lower() in ["help", "幫助", "說明"]:
        help_text = """🤖 名片管理 LINE Bot 使用說明

📸 **單張名片處理**
- 直接傳送名片照片給我
- 我會自動識別名片資訊並存入 Notion

🔄 **批次處理模式**
- 發送「批次」進入批次模式
- 連續發送多張名片圖片
- 發送「結束批次」查看處理結果
- 發送「狀態」查看當前進度

💡 **功能特色:**
- 使用 Google Gemini AI 識別文字
- 自動整理聯絡資訊
- 直接存入 Notion 資料庫
- 支援中英文名片
- 支援批次處理多張名片

❓ 需要幫助請輸入 "help" """

        safe_line_bot.safe_reply_message(event.reply_token, help_text)

    elif user_message.lower().startswith(
        "create pr:"
    ) or user_message.lower().startswith("pr:"):
        # Extract PR description
        pr_description = user_message[user_message.find(":") + 1 :].strip()

        if not pr_description:
            reply_text = "請提供 PR 描述，例如：create pr: 添加用戶登入功能"
            safe_line_bot.safe_reply_message(event.reply_token, reply_text)
        else:
            # Send processing message
            safe_line_bot.safe_reply_message(
                event.reply_token, "🚀 正在創建 PR，請稍候..."
            )

            # Create PR
            result = pr_creator.create_instant_pr(pr_description)

            if result["success"]:
                success_msg = f"""✅ PR 創建成功！
                
🔗 **PR URL:** {result['pr_url']}
🌿 **分支:** {result['branch_name']} 
📝 **變更數量:** {result['changes_applied']}

💡 請檢查 GitHub 查看完整的 PR 內容"""

                safe_line_bot.safe_push_message(event.source.user_id, success_msg)
            else:
                error_msg = f"❌ PR 創建失敗: {result['error']}"
                safe_line_bot.safe_push_message(event.source.user_id, error_msg)
        return

    else:
        # 檢查是否有待處理的多名片會話
        if user_interaction_handler.has_pending_session(user_id):
            # 處理多名片選擇
            choice_result = user_interaction_handler.handle_user_choice(
                user_id, user_message
            )

            if choice_result["action"] == "retake_photo":
                safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

            elif choice_result["action"] in [
                "process_all_cards",
                "process_selected_cards",
            ]:
                # 處理選擇的名片
                cards_to_process = choice_result.get("cards_to_process", [])
                safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

                # 異步處理多張名片（檢查批次模式狀態）
                user_is_batch_mode = batch_manager.is_in_batch_mode(user_id)
                _process_multiple_cards_async(
                    user_id, cards_to_process, user_is_batch_mode
                )

            else:
                # 其他狀況（無效選擇、會話過期等）
                safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

        # 檢查是否在批次模式中
        elif batch_manager.is_in_batch_mode(user_id):
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            reply_text = f"您目前在批次模式中，請發送名片圖片。\n\n{progress_msg}"
            safe_line_bot.safe_reply_message(event.reply_token, reply_text)
        else:
            reply_text = "請上傳名片圖片，我會幫您識別並存入 Notion 📸\n\n💡 提示：發送「批次」可開啟批次處理模式"
            safe_line_bot.safe_reply_message(event.reply_token, reply_text)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理圖片訊息 - 名片識別（支援批次模式）"""
    user_id = event.source.user_id
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
                f"📸 批次模式 - 正在處理第 {current_count} 張名片，請稍候..."
            )
        else:
            processing_message = "📸 收到名片圖片！正在使用 AI 識別中，請稍候..."

        safe_line_bot.safe_reply_message(event.reply_token, processing_message)

        # 下載圖片
        content_result = safe_line_bot.safe_get_message_content(event.message.id)
        if not content_result["success"]:
            error_msg = f"❗ 無法下載圖片: {content_result['message']}"
            if content_result.get("error_type") == "quota_exceeded":
                fallback_msg = safe_line_bot.create_fallback_message(
                    "名片圖片識別", "quota_exceeded"
                )
                safe_line_bot.safe_push_message(event.source.user_id, fallback_msg)
            else:
                safe_line_bot.safe_push_message(event.source.user_id, error_msg)
            return

        message_content = content_result["content"]
        image_bytes = b""
        for chunk in message_content.iter_content():
            image_bytes += chunk

        # 使用多名片處理器進行品質檢查
        print("🔍 開始多名片 AI 識別和品質評估...")
        analysis_result = multi_card_processor.process_image_with_quality_check(
            image_bytes
        )

        if "error" in analysis_result:
            error_message = f"❌ 名片識別失敗: {analysis_result['error']}"

            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, analysis_result["error"])
                # 添加批次進度資訊
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"

            safe_line_bot.safe_push_message(event.source.user_id, error_message)
            return

        # 根據分析結果決定處理方式
        if analysis_result.get("action_required", False):
            # 需要用戶選擇，創建交互會話
            choice_message = user_interaction_handler.create_multi_card_session(
                user_id, analysis_result
            )
            safe_line_bot.safe_push_message(event.source.user_id, choice_message)
            return

        # 自動處理（單張高品質名片）
        elif analysis_result.get("auto_process", False):
            cards_to_process = analysis_result.get("cards", [])
            if cards_to_process:
                safe_line_bot.safe_push_message(
                    event.source.user_id, "✅ 名片品質良好，正在自動處理..."
                )
                # 處理名片（使用原有邏輯，但適配新格式）
                _process_single_card_from_multi_format(
                    user_id, cards_to_process[0], is_batch_mode
                )
            return

        # 如果到這裡，說明沒有匹配到其他情況，直接處理（向後兼容）
        cards = analysis_result.get("cards", [])
        if cards:
            _process_single_card_from_multi_format(user_id, cards[0], is_batch_mode)

    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {e}")
        error_msg = f"❌ 處理過程中發生錯誤: {str(e)}"

        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            batch_manager.add_failed_card(user_id, str(e))
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            error_msg += f"\n\n{progress_msg}"

        safe_line_bot.safe_push_message(event.source.user_id, error_msg)


@app.route("/health", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "LINE Bot is running"}


@app.route("/test", methods=["GET"])
def test_services():
    """測試各服務連接狀態"""
    results = {}

    # 測試 Notion 連接
    notion_test = notion_manager.test_connection()
    results["notion"] = notion_test

    # 測試 Gemini (簡單檢查)
    try:
        # 檢查是否能創建處理器實例
        NameCardProcessor()
        results["gemini"] = {"success": True, "message": "Gemini 連接正常"}
    except Exception as e:
        results["gemini"] = {"success": False, "error": str(e)}

    return results


@app.route("/api-status", methods=["GET"])
def api_status():
    """LINE Bot API 狀態監控端點"""
    status_report = safe_line_bot.get_status_report()

    # 添加詳細的狀態信息
    detailed_status = {
        "timestamp": datetime.now().isoformat(),
        "line_bot_api": {
            "operational": status_report["is_operational"],
            "quota_exceeded": status_report["quota_exceeded"],
            "quota_reset_time": status_report["quota_reset_time"],
            "error_statistics": status_report["error_statistics"],
        },
        "service_status": {
            "healthy": not status_report["quota_exceeded"],
            "degraded_service": status_report["quota_exceeded"],
            "fallback_mode": status_report["quota_exceeded"],
        },
        "recommendations": [],
    }

    # 基於狀態提供建議
    if status_report["quota_exceeded"]:
        detailed_status["recommendations"].extend(
            [
                "LINE Bot API 配額已達上限",
                "考慮升級到付費方案",
                "或等待下個月配額重置",
                "目前系統運行在降級模式",
            ]
        )
    elif sum(status_report["error_statistics"].values()) > 10:
        detailed_status["recommendations"].extend(
            [
                "檢測到較多 API 錯誤",
                "建議檢查網路連接狀況",
                "或聯繫 LINE 客服確認服務狀態",
            ]
        )
    else:
        detailed_status["recommendations"].append("系統運行正常")

    return detailed_status


# 添加一個調試用的通用路由
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    """捕獲所有請求以便調試"""
    print(f"🔍 收到請求: method={request.method}, path=/{path}")
    print(f"📋 Headers: {dict(request.headers)}")

    if path == "callback" and request.method == "POST":
        # 重定向到正確的 callback 處理
        return callback()

    return {
        "message": "Debug endpoint",
        "path": f"/{path}",
        "method": request.method,
        "available_endpoints": ["/health", "/test", "/callback"],
    }


def _process_single_card_from_multi_format(
    user_id: str, card_data: dict, is_batch_mode: bool
):
    """處理單張名片（從多名片格式適配到原有邏輯）"""
    try:
        # 存入 Notion
        print("💾 存入 Notion 資料庫...")
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

                safe_line_bot.safe_push_message(user_id, batch_message)
            else:
                # 單張模式詳細回應
                confidence_info = ""
                if card_data.get("confidence_score"):
                    confidence_info = (
                        f"\n🎯 **識別信心度:** {card_data['confidence_score']:.1%}"
                    )

                success_message = f"""✅ 名片資訊已成功存入 Notion！

👤 **姓名:** {card_data.get('name', 'N/A')}
🏢 **公司:** {card_data.get('company', 'N/A')}
🏬 **部門:** {card_data.get('department', 'N/A')}
💼 **職稱:** {card_data.get('title', 'N/A')}
📧 **Email:** {card_data.get('email', 'N/A')}
📞 **電話:** {card_data.get('phone', 'N/A')}{confidence_info}

🔗 **Notion 頁面:** {notion_result['url']}

💡 提示：發送「批次」可開啟批次處理模式"""

                safe_line_bot.safe_push_message(user_id, success_message)
        else:
            error_message = f"❌ Notion 存入失敗: {notion_result['error']}"

            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, notion_result["error"])
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"

            safe_line_bot.safe_push_message(user_id, error_message)

    except Exception as e:
        error_msg = f"❌ 處理名片時發生錯誤: {str(e)}"
        print(error_msg)
        safe_line_bot.safe_push_message(user_id, error_msg)


def _process_multiple_cards_async(
    user_id: str, cards_to_process: list, is_batch_mode: bool
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

        safe_line_bot.safe_push_message(user_id, summary_message)

    except Exception as e:
        error_msg = f"❌ 批次處理多名片時發生錯誤: {str(e)}"
        print(error_msg)
        safe_line_bot.safe_push_message(user_id, error_msg)


if __name__ == "__main__":
    # 使用統一日誌輸出
    log_message("🚀 啟動 LINE Bot 名片管理系統...")
    log_message("📋 使用 Notion 作為資料庫")
    log_message("🤖 使用 Google Gemini AI 識別名片 + 多名片檢測")
    log_message("🎯 支援品質評估和用戶交互選擇")

    # 獲取端口配置（支援 Zeabur/Heroku 等雲端平台）
    port = int(os.environ.get("PORT", 5002))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    log_message(f"⚡ 服務啟動中... 端口: {port}, Debug: {debug_mode}")

    # 生產環境配置
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=False,  # 在生產環境中關閉重載器
    )
