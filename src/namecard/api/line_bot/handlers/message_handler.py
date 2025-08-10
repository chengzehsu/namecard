"""主要訊息處理器"""

import logging

from linebot.models import ImageMessage, MessageEvent, TextMessage


class MessageHandler:
    """統一的訊息處理器"""

    def __init__(self, text_handler, image_handler):
        self.text_handler = text_handler
        self.image_handler = image_handler
        self.logger = logging.getLogger(__name__)

    def handle_message(self, event):
        """根據訊息類型分發處理"""
        if isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessage):
                return self.text_handler.handle_text_message(
                    event, self._process_multiple_cards_async
                )
            elif isinstance(event.message, ImageMessage):
                return self.image_handler.handle_image_message(
                    event, self._process_single_card_from_multi_format
                )

        self.logger.warning(f"未處理的訊息類型: {type(event)}")

    def _process_single_card_from_multi_format(
        self, user_id: str, card_data: dict, is_batch_mode: bool
    ):
        """處理單張名片（從多名片格式適配到原有邏輯）"""
        try:
            from ..utils import get_batch_manager, get_notion_manager, get_safe_line_bot

            notion_manager = get_notion_manager()
            batch_manager = get_batch_manager()
            safe_line_bot = get_safe_line_bot()

            # 存入 Notion
            print("💾 存入 Notion 資料庫...")
            notion_result = notion_manager.create_name_card_record(card_data, None)

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
            from ..utils import get_safe_line_bot

            safe_line_bot = get_safe_line_bot()
            safe_line_bot.safe_push_message(user_id, error_msg)

    def _process_multiple_cards_async(
        self, user_id: str, cards_to_process: list, is_batch_mode: bool
    ):
        """異步處理多張名片"""
        try:
            from ..utils import get_batch_manager, get_notion_manager, get_safe_line_bot

            notion_manager = get_notion_manager()
            batch_manager = get_batch_manager()
            safe_line_bot = get_safe_line_bot()

            success_count = 0
            failed_count = 0
            results = []

            for i, card_data in enumerate(cards_to_process, 1):
                try:
                    # 處理單張名片
                    notion_result = notion_manager.create_name_card_record(
                        card_data, None
                    )

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
                                "error": notion_result["error"],
                            }
                        )

                        # 記錄失敗（如果在批次模式中）
                        if is_batch_mode:
                            batch_manager.add_failed_card(
                                user_id, notion_result["error"]
                            )

                except Exception as e:
                    failed_count += 1
                    results.append(
                        {
                            "success": False,
                            "name": card_data.get("name", f"名片{i}"),
                            "error": str(e),
                        }
                    )

                    if is_batch_mode:
                        batch_manager.add_failed_card(user_id, str(e))

            # 創建摘要訊息
            if is_batch_mode:
                # 批次模式：簡化摘要
                progress_msg = batch_manager.get_batch_progress_message(user_id)
                summary = f"📊 多名片處理完成\n✅ 成功: {success_count} 張  ❌ 失敗: {failed_count} 張\n\n{progress_msg}"
            else:
                # 一般模式：詳細摘要
                summary = f"📊 **多名片處理完成**\n\n✅ **成功處理:** {success_count} 張\n❌ **處理失敗:** {failed_count} 張\n\n"

                if results:
                    summary += "**處理結果:**\n"
                    for result in results:
                        if result["success"]:
                            summary += f"✅ {result['name']} - 已存入 Notion\n"
                        else:
                            summary += (
                                f"❌ {result['name']} - {result['error'][:50]}...\n"
                            )

            safe_line_bot.safe_push_message(user_id, summary)

        except Exception as e:
            error_msg = f"❌ 批次處理時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            from ..utils import get_safe_line_bot

            safe_line_bot = get_safe_line_bot()
            safe_line_bot.safe_push_message(user_id, error_msg)
