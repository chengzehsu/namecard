#!/usr/bin/env python3
"""
用於 Railway 部署的 LINE Bot 應用
"""
import os

from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import ImageMessage, MessageEvent, TextMessage, TextSendMessage

from batch_manager import BatchManager
from name_card_processor import NameCardProcessor
from notion_manager import NotionManager
from pr_creator import PRCreator

# 環境變數設定（用於 Railway）
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化處理器
try:
    card_processor = NameCardProcessor()
    notion_manager = NotionManager()
    batch_manager = BatchManager()
    pr_creator = PRCreator()
    print("✅ 處理器初始化成功")
except Exception as e:
    print(f"❌ 處理器初始化失敗: {e}")


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Bot webhook 回調函數"""
    signature = request.headers.get("X-Line-Signature")

    if not signature:
        return "Missing X-Line-Signature header", 400

    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@app.route("/health", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "LINE Bot is running on Railway"}


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息"""
    user_message = event.message.text

    if user_message.lower() in ["help", "幫助", "說明"]:
        help_text = """🤖 名片管理 LINE Bot 使用說明

📸 **上傳名片圖片**
- 直接傳送名片照片給我
- 我會自動識別名片資訊並存入 Notion

💡 **功能特色:**
- 使用 Google Gemini AI 識別文字
- 自動整理聯絡資訊
- 直接存入 Notion 資料庫
- 支援中英文名片

❓ 需要幫助請輸入 "help" """

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請上傳名片圖片，我會幫您識別並存入 Notion 📸"),
        )


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理圖片訊息 - 名片識別"""
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="📸 收到名片圖片！正在使用 AI 識別中，請稍候..."),
        )

        # 下載圖片
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b""
        for chunk in message_content.iter_content():
            image_bytes += chunk

        # 使用 Gemini 識別名片
        extracted_info = card_processor.extract_info_from_image(image_bytes)

        if "error" in extracted_info:
            error_message = f"❌ 名片識別失敗: {extracted_info['error']}"
            line_bot_api.push_message(
                event.source.user_id, TextSendMessage(text=error_message)
            )
            return

        # 存入 Notion
        notion_result = notion_manager.create_name_card_record(extracted_info)

        if notion_result["success"]:
            success_message = f"""✅ 名片資訊已成功存入 Notion！

👤 **姓名:** {extracted_info.get('name', 'N/A')}
🏢 **公司:** {extracted_info.get('company', 'N/A')}
🏬 **部門:** {extracted_info.get('department', 'N/A')}
💼 **職稱:** {extracted_info.get('title', 'N/A')}
📧 **Email:** {extracted_info.get('email', 'N/A')}
📞 **電話:** {extracted_info.get('phone', 'N/A')}
📍 **地址:** {extracted_info.get('address', 'N/A')}

🔗 **Notion 頁面:** {notion_result['url']}"""

            line_bot_api.push_message(
                event.source.user_id, TextSendMessage(text=success_message)
            )
        else:
            error_message = f"❌ Notion 存入失敗: {notion_result['error']}"
            line_bot_api.push_message(
                event.source.user_id, TextSendMessage(text=error_message)
            )

    except Exception as e:
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"❌ 處理過程中發生錯誤: {str(e)}"),
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
