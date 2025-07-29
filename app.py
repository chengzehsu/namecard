from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage, FollowEvent
)
import requests
from config import Config
from name_card_processor import NameCardProcessor
from notion_manager import NotionManager
from batch_manager import BatchManager
from pr_creator import PRCreator

# 初始化 Flask 應用
app = Flask(__name__)

# 驗證配置
try:
    Config.validate_config()
    print("✅ 配置驗證成功")
except ValueError as e:
    print(f"❌ 配置錯誤: {e}")
    exit(1)

# 初始化 LINE Bot
if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_CHANNEL_SECRET:
    print("❌ LINE Bot 配置不完整")
    exit(1)

line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

# 初始化處理器
try:
    card_processor = NameCardProcessor()
    notion_manager = NotionManager()
    batch_manager = BatchManager()
    pr_creator = PRCreator()
    print("✅ 處理器初始化成功")
except Exception as e:
    print(f"❌ 處理器初始化失敗: {e}")
    exit(1)

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Bot webhook 回調函數 - 嚴格按照 LINE API 規範"""
    
    # 記錄請求資訊
    print(f"📥 收到 POST 請求到 /callback")
    print(f"📋 Request headers: {dict(request.headers)}")
    print(f"🌍 Remote addr: {request.environ.get('REMOTE_ADDR', 'unknown')}")
    print(f"🔍 User agent: {request.headers.get('User-Agent', 'unknown')}")
    
    # 1. 檢查 Content-Type（LINE 要求 application/json）
    content_type = request.headers.get('Content-Type', '')
    if not content_type.startswith('application/json'):
        print(f"❌ 錯誤的 Content-Type: {content_type}")
        return 'Content-Type must be application/json', 400
    
    # 2. 獲取 X-Line-Signature header（必須）
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        print("❌ 缺少必要的 X-Line-Signature header")
        return 'Missing X-Line-Signature header', 400
    
    # 3. 獲取請求體
    body = request.get_data(as_text=True)
    if not body:
        print("❌ 空的請求體")
        return 'Empty request body', 400
        
    print(f"📄 Request body length: {len(body)}")
    print(f"📄 Request body preview: {body[:200]}...")
    
    # 4. 驗證簽名並處理 webhook
    try:
        handler.handle(body, signature)
        print("✅ Webhook 處理成功")
        
        # LINE API 要求返回 200 狀態碼
        return 'OK', 200
        
    except InvalidSignatureError as e:
        print(f"❌ 簽名驗證失敗: {e}")
        print(f"🔑 使用的 Channel Secret: {Config.LINE_CHANNEL_SECRET[:10]}...")
        abort(400)
        
    except Exception as e:
        print(f"❌ Webhook 處理過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        abort(500)

# 為了解決 ngrok 免費版的問題，添加一個簡單的 GET 端點
@app.route("/callback", methods=['GET'])
def callback_info():
    """顯示 callback 端點資訊"""
    return {
        "message": "LINE Bot webhook endpoint", 
        "method": "POST only",
        "status": "ready"
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    
    # 批次模式指令處理
    if user_message.lower() in ['批次', 'batch', '批次模式', '開始批次']:
        result = batch_manager.start_batch_mode(user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result['message'])
        )
        return
    
    elif user_message.lower() in ['結束批次', 'end batch', '完成批次', '批次結束']:
        result = batch_manager.end_batch_mode(user_id)
        if result['success']:
            stats = result['statistics']
            summary_text = f"""📊 **批次處理完成**

✅ **處理成功:** {stats['total_processed']} 張
❌ **處理失敗:** {stats['total_failed']} 張
⏱️ **總耗時:** {stats['total_time_minutes']:.1f} 分鐘

📋 **成功處理的名片:**"""
            
            for card in stats['processed_cards']:
                summary_text += f"\n• {card['name']} ({card['company']})"
            
            if stats['failed_cards']:
                summary_text += f"\n\n❌ **失敗記錄:**"
                for i, failed in enumerate(stats['failed_cards'], 1):
                    summary_text += f"\n{i}. {failed['error'][:50]}..."
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=summary_text)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result['message'])
            )
        return
    
    elif user_message.lower() in ['狀態', 'status', '批次狀態']:
        if batch_manager.is_in_batch_mode(user_id):
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=progress_msg)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您目前不在批次模式中。發送「批次」開始批次處理。")
            )
        return
        
    elif user_message.lower() in ['help', '幫助', '說明']:
        help_text = """🤖 名片管理 LINE Bot - 完整使用指南

📸 **單張名片處理**
• 直接傳送名片照片給我
• 我會自動識別名片資訊並存入 Notion
• 支援中文、英文名片

🔄 **批次處理模式（推薦！）**
• 發送「批次」進入批次模式
• 連續發送多張名片圖片，省時高效
• 發送「結束批次」查看統計結果
• 發送「狀態」查看當前進度
• 非常適合展會、會議後大量名片處理

🚀 **即時 PR 創建**
• 發送「create pr: 您的需求描述」
• 例如：create pr: 添加用戶登入功能
• 系統會自動生成完整 PR

⚡ **智能特色:**
• Google Gemini AI 精準識別
• 自動整理完整聯絡資訊
• 直接存入 Notion 資料庫
• 支援多種圖片格式
• 批次處理統計報告
• 自動化 PR 創建

💡 **使用技巧:**
• 確保名片照片清晰可見
• 批次模式可大幅提升處理效率
• 處理完成後會自動生成 Notion 頁面連結

❓ **需要協助隨時輸入「help」**"""
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_text)
        )
        
    elif user_message.lower().startswith('create pr:') or user_message.lower().startswith('pr:'):
        # Extract PR description
        pr_description = user_message[user_message.find(':')+1:].strip()
        
        if not pr_description:
            reply_text = "請提供 PR 描述，例如：create pr: 添加用戶登入功能"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        else:
            # Send processing message
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚀 正在創建 PR，請稍候...")
            )
            
            # Create PR
            result = pr_creator.create_instant_pr(pr_description)
            
            if result['success']:
                success_msg = f"""✅ PR 創建成功！
                
🔗 **PR URL:** {result['pr_url']}
🌿 **分支:** {result['branch_name']} 
📝 **變更數量:** {result['changes_applied']}

💡 請檢查 GitHub 查看完整的 PR 內容"""
                
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=success_msg)
                )
            else:
                error_msg = f"❌ PR 創建失敗: {result['error']}"
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=error_msg)
                )
        return
        
    else:
        # 檢查是否在批次模式中
        if batch_manager.is_in_batch_mode(user_id):
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            reply_text = f"您目前在批次模式中，請發送名片圖片。\n\n{progress_msg}"
        else:
            reply_text = """📸 請上傳您的名片照片，我來幫您智能識別！

💡 **小提示：**
• 單張處理：直接傳送圖片即可
• 批次處理：先發送「批次」再連續上傳多張
• 需要幫助：發送「help」查看完整指南

🚀 準備好了嗎？上傳您的名片吧！"""
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

@handler.add(FollowEvent)
def handle_follow_event(event):
    """處理用戶關注/加入事件 - 歡迎新用戶並提供指引"""
    user_id = event.source.user_id
    
    # 歡迎訊息
    welcome_message = """🎉 歡迎使用名片管理 LINE Bot！

📱 **快速開始指南：**

📸 **上傳單張名片**
• 直接傳送名片照片給我
• 我會自動識別並存入 Notion 資料庫

🔄 **批次處理多張名片**
• 發送「批次」進入批次模式
• 連續上傳多張名片照片
• 發送「結束批次」查看統計結果

✨ **智能特色：**
• 使用 Google Gemini AI 精準識別
• 支援中文、英文名片
• 自動整理聯絡資訊
• 直接存入 Notion 資料庫
• 支援批次處理省時高效

💡 **小提示：**
• 請確保名片照片清晰可見
• 可以上傳多種格式的圖片
• 發送「help」查看詳細說明

🚀 **現在就開始吧！請上傳您的第一張名片～**"""

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )
        print(f"✅ 歡迎新用戶: {user_id}")
    except Exception as e:
        print(f"❌ 發送歡迎訊息失敗: {e}")

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
            current_count = session_info['total_count'] + 1 if session_info else 1
            processing_message = f"📸 批次模式 - 正在處理第 {current_count} 張名片，請稍候..."
        else:
            processing_message = "📸 收到名片圖片！正在使用 AI 識別中，請稍候..."
            
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=processing_message)
        )
        
        # 下載圖片
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b''
        for chunk in message_content.iter_content():
            image_bytes += chunk
        
        # 使用 Gemini 識別名片
        print("🔍 開始 Gemini AI 識別...")
        extracted_info = card_processor.extract_info_from_image(image_bytes)
        
        if 'error' in extracted_info:
            error_message = f"❌ 名片識別失敗: {extracted_info['error']}"
            
            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, extracted_info['error'])
                # 添加批次進度資訊
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"
            
            line_bot_api.push_message(
                event.source.user_id,
                TextSendMessage(text=error_message)
            )
            return
        
        # 存入 Notion (包含圖片)
        print("💾 存入 Notion 資料庫...")
        notion_result = notion_manager.create_name_card_record(extracted_info, image_bytes)
        
        if notion_result['success']:
            # 記錄成功處理（如果在批次模式中）
            if is_batch_mode:
                card_info = {
                    'name': extracted_info.get('name', 'Unknown'),
                    'company': extracted_info.get('company', 'Unknown'),
                    'notion_url': notion_result['url']
                }
                batch_manager.add_processed_card(user_id, card_info)
                
                # 批次模式簡化回應
                session_info = batch_manager.get_session_info(user_id)
                batch_message = f"""✅ 第 {session_info['total_count']} 張名片處理完成
                
👤 {extracted_info.get('name', 'N/A')} ({extracted_info.get('company', 'N/A')})

{batch_manager.get_batch_progress_message(user_id)}"""
                
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=batch_message)
                )
            else:
                # 單張模式詳細回應
                success_message = f"""✅ 名片資訊已成功存入 Notion！

👤 **姓名:** {extracted_info.get('name', 'N/A')}
🏢 **公司:** {extracted_info.get('company', 'N/A')}
🏬 **部門:** {extracted_info.get('department', 'N/A')}
💼 **職稱:** {extracted_info.get('title', 'N/A')}
📧 **Email:** {extracted_info.get('email', 'N/A')}
📞 **電話:** {extracted_info.get('phone', 'N/A')}
📍 **地址:** {extracted_info.get('address', 'N/A')}

🔗 **Notion 頁面:** {notion_result['url']}

💡 提示：發送「批次」可開啟批次處理模式"""
                
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=success_message)
                )
        else:
            error_message = f"❌ Notion 存入失敗: {notion_result['error']}"
            
            # 記錄失敗（如果在批次模式中）
            if is_batch_mode:
                batch_manager.add_failed_card(user_id, notion_result['error'])
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                error_message += f"\n\n{progress_msg}"
            
            line_bot_api.push_message(
                event.source.user_id,
                TextSendMessage(text=error_message)
            )
            
    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {e}")
        error_msg = f"❌ 處理過程中發生錯誤: {str(e)}"
        
        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            batch_manager.add_failed_card(user_id, str(e))
            progress_msg = batch_manager.get_batch_progress_message(user_id)
            error_msg += f"\n\n{progress_msg}"
        
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=error_msg)
        )

@app.route("/health", methods=['GET'])
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "LINE Bot is running"}

@app.route("/test", methods=['GET'])
def test_services():
    """測試各服務連接狀態"""
    results = {}
    
    # 測試 Notion 連接
    notion_test = notion_manager.test_connection()
    results['notion'] = notion_test
    
    # 測試 Gemini (簡單檢查)
    try:
        # 檢查是否能創建處理器實例
        test_processor = NameCardProcessor()
        results['gemini'] = {"success": True, "message": "Gemini 連接正常"}
    except Exception as e:
        results['gemini'] = {"success": False, "error": str(e)}
    
    return results

# 添加一個調試用的通用路由
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """捕獲所有請求以便調試"""
    print(f"🔍 收到請求: method={request.method}, path=/{path}")
    print(f"📋 Headers: {dict(request.headers)}")
    
    if path == 'callback' and request.method == 'POST':
        # 重定向到正確的 callback 處理
        return callback()
    
    return {
        "message": "Debug endpoint", 
        "path": f"/{path}",
        "method": request.method,
        "available_endpoints": ["/health", "/test", "/callback"]
    }

if __name__ == "__main__":
    print("🚀 啟動 LINE Bot 名片管理系統...")
    print("📋 使用 Notion 作為資料庫")
    print("🤖 使用 Google Gemini AI 識別名片")
    print("⚡ 服務已就緒！")
    
    # 在開發環境中運行
    app.run(host='0.0.0.0', port=5002, debug=True)