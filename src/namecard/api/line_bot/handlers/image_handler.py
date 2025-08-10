"""圖片訊息處理器"""

import logging


class ImageMessageHandler:
    """處理 LINE Bot 圖片訊息"""

    def __init__(
        self,
        batch_manager,
        safe_line_bot,
        multi_card_processor,
        user_interaction_handler,
    ):
        self.batch_manager = batch_manager
        self.safe_line_bot = safe_line_bot
        self.multi_card_processor = multi_card_processor
        self.user_interaction_handler = user_interaction_handler
        self.logger = logging.getLogger(__name__)

    def handle_image_message(self, event, _process_single_card_from_multi_format):
        """處理圖片訊息 - 名片識別（支援批次模式）"""
        user_id = event.source.user_id
        is_batch_mode = self.batch_manager.is_in_batch_mode(user_id)

        try:
            # 更新用戶活動時間
            if is_batch_mode:
                self.batch_manager.update_activity(user_id)

            # 發送處理中訊息
            processing_message = self._get_processing_message(user_id, is_batch_mode)
            self.safe_line_bot.safe_reply_message(event.reply_token, processing_message)

            # 下載圖片
            content_result = self.safe_line_bot.safe_get_message_content(
                event.message.id
            )
            if not content_result["success"]:
                self._handle_download_error(
                    event, content_result, is_batch_mode, user_id
                )
                return

            # 提取圖片位元組資料
            image_bytes = self._extract_image_bytes(content_result["content"])

            # 使用多名片處理器進行品質檢查
            print("🔍 開始多名片 AI 識別和品質評估...")
            analysis_result = (
                self.multi_card_processor.process_image_with_quality_check(image_bytes)
            )

            # 處理分析結果
            self._handle_analysis_result(
                analysis_result,
                event,
                user_id,
                is_batch_mode,
                _process_single_card_from_multi_format,
            )

        except Exception as e:
            self._handle_processing_error(e, event, user_id, is_batch_mode)

    def _get_processing_message(self, user_id, is_batch_mode):
        """獲取處理中訊息"""
        if is_batch_mode:
            session_info = self.batch_manager.get_session_info(user_id)
            current_count = session_info["total_count"] + 1 if session_info else 1
            return f"📸 批次模式 - 正在處理第 {current_count} 張名片，請稍候..."
        else:
            return "📸 收到名片圖片！正在使用 AI 識別中，請稍候..."

    def _handle_download_error(self, event, content_result, is_batch_mode, user_id):
        """處理圖片下載錯誤"""
        error_msg = f"❗ 無法下載圖片: {content_result['message']}"

        if content_result.get("error_type") == "quota_exceeded":
            fallback_msg = self.safe_line_bot.create_fallback_message(
                "名片圖片識別", "quota_exceeded"
            )
            self.safe_line_bot.safe_push_message(event.source.user_id, fallback_msg)
        else:
            self.safe_line_bot.safe_push_message(event.source.user_id, error_msg)

        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            self.batch_manager.add_failed_card(user_id, content_result["message"])

    def _extract_image_bytes(self, message_content):
        """提取圖片位元組資料"""
        image_bytes = b""
        for chunk in message_content.iter_content():
            image_bytes += chunk
        return image_bytes

    def _handle_analysis_result(
        self,
        analysis_result,
        event,
        user_id,
        is_batch_mode,
        _process_single_card_from_multi_format,
    ):
        """處理分析結果"""
        if "error" in analysis_result:
            self._handle_analysis_error(analysis_result, event, user_id, is_batch_mode)
            return

        # 根據分析結果決定處理方式
        if analysis_result.get("action_required", False):
            # 需要用戶選擇，創建交互會話
            choice_message = self.user_interaction_handler.create_multi_card_session(
                user_id, analysis_result
            )
            self.safe_line_bot.safe_push_message(event.source.user_id, choice_message)

        elif analysis_result.get("auto_process", False):
            # 自動處理（單張高品質名片）
            cards_to_process = analysis_result.get("cards", [])
            if cards_to_process:
                self.safe_line_bot.safe_push_message(
                    event.source.user_id, "✅ 名片品質良好，正在自動處理..."
                )
                _process_single_card_from_multi_format(
                    user_id, cards_to_process[0], is_batch_mode
                )

        else:
            # 如果到這裡，說明沒有匹配到其他情況，直接處理（向後兼容）
            cards = analysis_result.get("cards", [])
            if cards:
                _process_single_card_from_multi_format(user_id, cards[0], is_batch_mode)

    def _handle_analysis_error(self, analysis_result, event, user_id, is_batch_mode):
        """處理分析錯誤"""
        error_message = f"❌ 名片識別失敗: {analysis_result['error']}"

        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            self.batch_manager.add_failed_card(user_id, analysis_result["error"])
            # 添加批次進度資訊
            progress_msg = self.batch_manager.get_batch_progress_message(user_id)
            error_message += f"\n\n{progress_msg}"

        self.safe_line_bot.safe_push_message(event.source.user_id, error_message)

    def _handle_processing_error(self, error, event, user_id, is_batch_mode):
        """處理一般處理錯誤"""
        print(f"❌ 處理圖片時發生錯誤: {error}")
        error_msg = f"❌ 處理過程中發生錯誤: {str(error)}"

        # 記錄失敗（如果在批次模式中）
        if is_batch_mode:
            self.batch_manager.add_failed_card(user_id, str(error))
            progress_msg = self.batch_manager.get_batch_progress_message(user_id)
            error_msg += f"\n\n{progress_msg}"

        self.safe_line_bot.safe_push_message(event.source.user_id, error_msg)
