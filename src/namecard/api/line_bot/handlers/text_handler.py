"""文字訊息處理器"""

import logging
import sys
from datetime import datetime


class TextMessageHandler:
    """處理 LINE Bot 文字訊息"""

    def __init__(
        self, batch_manager, safe_line_bot, user_interaction_handler, pr_creator
    ):
        self.batch_manager = batch_manager
        self.safe_line_bot = safe_line_bot
        self.user_interaction_handler = user_interaction_handler
        self.pr_creator = pr_creator
        self.logger = logging.getLogger(__name__)

    def log_message(self, message, level="INFO"):
        """統一日誌輸出函數"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {level}: {message}"
        print(log_line, flush=True)
        sys.stdout.flush()
        return log_line

    def handle_text_message(self, event, _process_multiple_cards_async):
        """處理文字訊息"""
        user_message = event.message.text.strip()
        user_id = event.source.user_id

        # 批次模式指令處理
        if user_message.lower() in ["批次", "batch", "批次模式", "開始批次"]:
            return self._handle_start_batch(event, user_id)

        elif user_message.lower() in ["結束批次", "end batch", "完成批次", "批次結束"]:
            return self._handle_end_batch(event, user_id)

        elif user_message.lower() in ["狀態", "status", "批次狀態"]:
            return self._handle_batch_status(event, user_id)

        elif user_message.lower() in ["help", "幫助", "說明"]:
            return self._handle_help(event)

        elif user_message.lower().startswith(("create pr:", "pr:")):
            return self._handle_pr_creation(event, user_message, user_id)

        else:
            return self._handle_other_text(
                event, user_id, user_message, _process_multiple_cards_async
            )

    def _handle_start_batch(self, event, user_id):
        """處理開始批次模式"""
        result = self.batch_manager.start_batch_mode(user_id)
        reply_result = self.safe_line_bot.safe_reply_message(
            event.reply_token, result["message"]
        )

        if (
            not reply_result["success"]
            and reply_result.get("error_type") == "quota_exceeded"
        ):
            # 記錄離線訊息
            self.log_message(f"📝 離線訊息記錄 - 用戶 {user_id}: 開始批次", "INFO")

    def _handle_end_batch(self, event, user_id):
        """處理結束批次模式"""
        result = self.batch_manager.end_batch_mode(user_id)
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

            self.safe_line_bot.safe_reply_message(event.reply_token, summary_text)
        else:
            self.safe_line_bot.safe_reply_message(event.reply_token, result["message"])

    def _handle_batch_status(self, event, user_id):
        """處理批次狀態查詢"""
        if self.batch_manager.is_in_batch_mode(user_id):
            progress_msg = self.batch_manager.get_batch_progress_message(user_id)
            self.safe_line_bot.safe_reply_message(event.reply_token, progress_msg)
        else:
            self.safe_line_bot.safe_reply_message(
                event.reply_token, "您目前不在批次模式中。發送「批次」開始批次處理。"
            )

    def _handle_help(self, event):
        """處理幫助訊息"""
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

        self.safe_line_bot.safe_reply_message(event.reply_token, help_text)

    def _handle_pr_creation(self, event, user_message, user_id):
        """處理 PR 創建請求"""
        pr_description = user_message[user_message.find(":") + 1 :].strip()

        if not pr_description:
            reply_text = "請提供 PR 描述，例如：create pr: 添加用戶登入功能"
            self.safe_line_bot.safe_reply_message(event.reply_token, reply_text)
        else:
            # Send processing message
            self.safe_line_bot.safe_reply_message(
                event.reply_token, "🚀 正在創建 PR，請稍候..."
            )

            # Create PR
            result = self.pr_creator.create_instant_pr(pr_description)

            if result["success"]:
                success_msg = f"""✅ PR 創建成功！

🔗 **PR URL:** {result['pr_url']}
🌿 **分支:** {result['branch_name']}
📝 **變更數量:** {result['changes_applied']}

💡 請檢查 GitHub 查看完整的 PR 內容"""

                self.safe_line_bot.safe_push_message(event.source.user_id, success_msg)
            else:
                error_msg = f"❌ PR 創建失敗: {result['error']}"
                self.safe_line_bot.safe_push_message(event.source.user_id, error_msg)

    def _handle_other_text(
        self, event, user_id, user_message, _process_multiple_cards_async
    ):
        """處理其他文字訊息"""
        # 檢查是否有待處理的多名片會話
        if self.user_interaction_handler.has_pending_session(user_id):
            # 處理多名片選擇
            choice_result = self.user_interaction_handler.handle_user_choice(
                user_id, user_message
            )

            if choice_result["action"] == "retake_photo":
                self.safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

            elif choice_result["action"] in [
                "process_all_cards",
                "process_selected_cards",
            ]:
                # 處理選擇的名片
                cards_to_process = choice_result.get("cards_to_process", [])
                self.safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

                # 異步處理多張名片（檢查批次模式狀態）
                user_is_batch_mode = self.batch_manager.is_in_batch_mode(user_id)
                _process_multiple_cards_async(
                    user_id, cards_to_process, user_is_batch_mode
                )

            else:
                # 其他狀況（無效選擇、會話過期等）
                self.safe_line_bot.safe_reply_message(
                    event.reply_token, choice_result["message"]
                )

        # 檢查是否在批次模式中
        elif self.batch_manager.is_in_batch_mode(user_id):
            progress_msg = self.batch_manager.get_batch_progress_message(user_id)
            reply_text = f"您目前在批次模式中，請發送名片圖片。\n\n{progress_msg}"
            self.safe_line_bot.safe_reply_message(event.reply_token, reply_text)
        else:
            reply_text = "請上傳名片圖片，我會幫您識別並存入 Notion 📸\n\n💡 提示：發送「批次」可開啟批次處理模式"
            self.safe_line_bot.safe_reply_message(event.reply_token, reply_text)
