"""
用戶交互處理器 - 專門處理多名片識別過程中的用戶交互界面
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class UserInteractionHandler:
    """用戶交互處理器，管理多名片處理的用戶選擇和會話狀態"""

    def __init__(self):
        """初始化用戶交互處理器"""
        # 存儲待處理的多名片會話 {user_id: session_data}
        self.pending_sessions = {}

        # 會話過期時間（5分鐘）
        self.session_timeout = timedelta(minutes=5)

    def create_multi_card_session(
        self, user_id: str, analysis_result: Dict[str, Any]
    ) -> str:
        """
        創建多名片處理會話

        Args:
            user_id: 用戶ID
            analysis_result: 多名片分析結果

        Returns:
            用戶友好的交互訊息
        """
        try:
            # 清理過期會話
            self._cleanup_expired_sessions()

            # 創建會話資料
            session_data = {
                "created_at": datetime.now(),
                "analysis_result": analysis_result,
                "status": "waiting_for_choice",
                "retries": 0,
            }

            self.pending_sessions[user_id] = session_data

            # 生成用戶交互訊息
            return self._generate_choice_message(analysis_result)

        except Exception as e:
            return f"❌ 創建多名片會話時出錯: {str(e)}"

    def handle_user_choice(self, user_id: str, user_input: str) -> Dict[str, Any]:
        """
        處理用戶的選擇回應

        Args:
            user_id: 用戶ID
            user_input: 用戶輸入的選擇

        Returns:
            處理結果包含 action 和相關資料
        """
        try:
            # 檢查是否有待處理的會話
            if user_id not in self.pending_sessions:
                return {
                    "action": "no_session",
                    "message": "沒有找到待處理的名片會話。請重新上傳名片圖片。",
                }

            session = self.pending_sessions[user_id]

            # 檢查會話是否過期
            if datetime.now() - session["created_at"] > self.session_timeout:
                del self.pending_sessions[user_id]
                return {
                    "action": "session_expired",
                    "message": "會話已過期，請重新上傳名片圖片。",
                }

            # 解析用戶選擇
            choice_result = self._parse_user_choice(
                user_input, session["analysis_result"]
            )

            if choice_result["action"] == "invalid_choice":
                # 無效選擇，增加重試次數
                session["retries"] += 1
                if session["retries"] >= 3:
                    del self.pending_sessions[user_id]
                    return {
                        "action": "max_retries",
                        "message": "選擇次數過多，會話已結束。請重新上傳名片圖片。",
                    }

                return {
                    "action": "invalid_choice",
                    "message": choice_result["message"]
                    + "\n\n"
                    + self._generate_choice_message(session["analysis_result"]),
                }

            # 有效選擇，處理並清理會話
            del self.pending_sessions[user_id]
            return choice_result

        except Exception as e:
            # 清理會話
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            return {"action": "error", "message": f"❌ 處理用戶選擇時出錯: {str(e)}"}

    def _generate_choice_message(self, analysis_result: Dict[str, Any]) -> str:
        """生成用戶選擇界面訊息"""
        try:
            card_count = analysis_result.get("card_count", 0)
            recommendation = analysis_result.get("recommendation", "")
            user_options = analysis_result.get("user_options", [])
            good_cards = analysis_result.get("good_cards", [])
            poor_cards = analysis_result.get("poor_cards", [])

            # 基礎訊息
            message = "🏷️ **多名片處理選擇**\n\n"
            message += f"📸 檢測到 **{card_count}** 張名片\n"
            message += f"🤖 AI 建議：{recommendation}\n\n"

            # 品質資訊
            if good_cards and poor_cards:
                message += "📊 **品質分析**\n"
                message += f"✅ 品質良好：第 {', '.join(map(str, good_cards))} 張名片\n"
                message += (
                    f"⚠️ 需要改善：第 {', '.join(map(str, poor_cards))} 張名片\n\n"
                )

            # 選項列表
            if user_options:
                message += "🎯 **請選擇操作方式**\n"
                for i, option in enumerate(user_options, 1):
                    emoji = self._get_option_emoji(option)
                    message += f"{emoji} {i}. {option}\n"

                message += "\n💬 **請回覆選項編號 (1-{}) 或直接回覆選項內容**".format(
                    len(user_options)
                )

            # 添加拍攝提示
            if analysis_result.get("suggest_single_shot"):
                message += "\n\n💡 **拍攝小提示**\n"
                message += "• 建議一次只拍一張名片\n"
                message += "• 確保名片平整且光線充足\n"
                message += "• 避免陰影和反光"

            return message

        except Exception as e:
            return f"❌ 生成選擇訊息時出錯: {str(e)}"

    def _get_option_emoji(self, option: str) -> str:
        """根據選項內容返回合適的表情符號"""
        option_lower = option.lower()

        if "重新拍攝" in option or "retake" in option_lower:
            return "📷"
        elif "分別處理" in option or "process" in option_lower:
            return "✅"
        elif "繼續處理" in option or "continue" in option_lower:
            return "▶️"
        elif "只處理" in option or "good" in option_lower:
            return "⭐"
        else:
            return "🔹"

    def _parse_user_choice(
        self, user_input: str, analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析用戶的選擇輸入"""
        try:
            user_options = analysis_result.get("user_options", [])
            user_input_clean = user_input.strip()

            # 嘗試解析為數字選擇
            try:
                choice_num = int(user_input_clean)
                if 1 <= choice_num <= len(user_options):
                    selected_option = user_options[choice_num - 1]
                    return self._process_selected_option(
                        selected_option, analysis_result
                    )
            except ValueError:
                pass

            # 嘗試模糊匹配選項內容
            user_input_lower = user_input_clean.lower()

            for option in user_options:
                if self._is_option_match(user_input_lower, option.lower()):
                    return self._process_selected_option(option, analysis_result)

            # 檢查常見的同義詞
            if any(
                keyword in user_input_lower
                for keyword in ["重拍", "重新", "再拍", "retake"]
            ):
                retake_options = [opt for opt in user_options if "重新拍攝" in opt]
                if retake_options:
                    return self._process_selected_option(
                        retake_options[0], analysis_result
                    )

            if any(
                keyword in user_input_lower
                for keyword in ["繼續", "處理", "確定", "ok", "continue"]
            ):
                continue_options = [
                    opt
                    for opt in user_options
                    if "繼續處理" in opt or "分別處理" in opt
                ]
                if continue_options:
                    return self._process_selected_option(
                        continue_options[0], analysis_result
                    )

            # 無效選擇
            return {
                "action": "invalid_choice",
                "message": f"❌ 無法識別您的選擇：「{user_input_clean}」\n請選擇有效的選項編號或選項內容。",
            }

        except Exception as e:
            return {
                "action": "invalid_choice",
                "message": f"❌ 解析選擇時出錯: {str(e)}",
            }

    def _is_option_match(self, user_input: str, option: str) -> bool:
        """檢查用戶輸入是否匹配某個選項"""
        # 簡單的關鍵字匹配
        option_keywords = option.split()
        return any(
            keyword in user_input for keyword in option_keywords if len(keyword) > 1
        )

    def _process_selected_option(
        self, selected_option: str, analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理用戶選擇的選項"""
        try:
            if "重新拍攝" in selected_option:
                return {
                    "action": "retake_photo",
                    "message": "📷 請重新拍攝名片。\n\n💡 建議：\n• 一次只拍一張名片\n• 確保光線充足\n• 保持名片平整",
                    "selected_option": selected_option,
                }

            elif "分別處理所有名片" in selected_option:
                return {
                    "action": "process_all_cards",
                    "message": "✅ 將分別處理所有名片並存入 Notion",
                    "cards_to_process": analysis_result.get("cards", []),
                    "selected_option": selected_option,
                }

            elif "只處理品質良好" in selected_option:
                good_cards = analysis_result.get("good_cards", [])
                all_cards = analysis_result.get("cards", [])
                good_card_data = [
                    all_cards[i - 1] for i in good_cards if i <= len(all_cards)
                ]

                return {
                    "action": "process_selected_cards",
                    "message": f"⭐ 將處理品質良好的 {len(good_card_data)} 張名片",
                    "cards_to_process": good_card_data,
                    "selected_option": selected_option,
                }

            elif "繼續處理" in selected_option:
                return {
                    "action": "process_all_cards",
                    "message": "▶️ 將繼續處理識別到的名片",
                    "cards_to_process": analysis_result.get("cards", []),
                    "selected_option": selected_option,
                }

            else:
                # 處理其他特殊選項
                return {
                    "action": "custom_option",
                    "message": f"🔹 執行選擇：{selected_option}",
                    "selected_option": selected_option,
                    "cards_to_process": analysis_result.get("cards", []),
                }

        except Exception as e:
            return {"action": "error", "message": f"❌ 處理選項時出錯: {str(e)}"}

    def has_pending_session(self, user_id: str) -> bool:
        """檢查用戶是否有待處理的會話"""
        self._cleanup_expired_sessions()
        return user_id in self.pending_sessions

    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """獲取會話資訊"""
        return self.pending_sessions.get(user_id)

    def clear_user_session(self, user_id: str) -> bool:
        """清理用戶會話"""
        if user_id in self.pending_sessions:
            del self.pending_sessions[user_id]
            return True
        return False

    def _cleanup_expired_sessions(self):
        """清理過期的會話"""
        try:
            current_time = datetime.now()
            expired_users = []

            for user_id, session in self.pending_sessions.items():
                if current_time - session["created_at"] > self.session_timeout:
                    expired_users.append(user_id)

            for user_id in expired_users:
                del self.pending_sessions[user_id]

        except Exception as e:
            print(f"清理過期會話時出錯: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """獲取會話統計資訊"""
        self._cleanup_expired_sessions()
        return {
            "active_sessions": len(self.pending_sessions),
            "session_users": list(self.pending_sessions.keys()),
        }
