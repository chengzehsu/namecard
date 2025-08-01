import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os


class EnhancedSessionManager:
    """
    改進的會話管理系統 - 支援持久化和更好的錯誤恢復
    Backend Engineer 實作 - 解決記憶體儲存和擴展性問題
    """

    def __init__(self, session_file_path: str = "sessions.json"):
        """初始化增強版會話管理器"""
        self.session_file_path = session_file_path
        self.user_sessions: Dict[str, Dict] = {}
        self.lock = threading.RLock()  # 使用可重入鎖避免死鎖
        self.session_timeout = timedelta(minutes=10)
        self.auto_save_interval = 30  # 每30秒自動保存
        self.last_save_time = time.time()

        # 啟動時載入持久化會話
        self._load_sessions()

        # 清理過期會話
        self._cleanup_expired_sessions()

    def _load_sessions(self):
        """從檔案載入會話數據"""
        try:
            if os.path.exists(self.session_file_path):
                with open(self.session_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 轉換時間字串回 datetime 物件
                    for user_id, session in data.items():
                        if "start_time" in session:
                            session["start_time"] = datetime.fromisoformat(
                                session["start_time"]
                            )
                        if "last_activity" in session:
                            session["last_activity"] = datetime.fromisoformat(
                                session["last_activity"]
                            )
                    self.user_sessions = data
                    print(f"✅ 載入 {len(self.user_sessions)} 個持久化會話")
        except Exception as e:
            print(f"⚠️ 載入會話失敗，使用空會話: {e}")
            self.user_sessions = {}

    def _save_sessions(self):
        """保存會話數據到檔案"""
        try:
            with self.lock:
                # 轉換 datetime 物件為字串以便 JSON 序列化
                serializable_sessions = {}
                for user_id, session in self.user_sessions.items():
                    session_copy = session.copy()
                    if "start_time" in session_copy:
                        session_copy["start_time"] = session_copy[
                            "start_time"
                        ].isoformat()
                    if "last_activity" in session_copy:
                        session_copy["last_activity"] = session_copy[
                            "last_activity"
                        ].isoformat()
                    serializable_sessions[user_id] = session_copy

                with open(self.session_file_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_sessions, f, ensure_ascii=False, indent=2)

                self.last_save_time = time.time()
                print(f"💾 會話已保存 ({len(self.user_sessions)} 個活躍會話)")
        except Exception as e:
            print(f"❌ 保存會話失敗: {e}")

    def _auto_save_if_needed(self):
        """如果需要則自動保存"""
        if time.time() - self.last_save_time > self.auto_save_interval:
            self._save_sessions()

    def _cleanup_expired_sessions(self):
        """清理過期的會話"""
        with self.lock:
            current_time = datetime.now()
            expired_users = []

            for user_id, session in self.user_sessions.items():
                if "last_activity" in session:
                    if current_time - session["last_activity"] > self.session_timeout:
                        expired_users.append(user_id)

            for user_id in expired_users:
                del self.user_sessions[user_id]
                print(f"🧹 清理過期會話: {user_id}")

            if expired_users:
                self._save_sessions()

    def start_batch_mode(self, user_id: str) -> Dict:
        """啟動用戶的批次模式（支援會話恢復）"""
        with self.lock:
            current_time = datetime.now()

            # 檢查是否有現有可恢復的會話
            if user_id in self.user_sessions:
                existing_session = self.user_sessions[user_id]
                if (
                    current_time - existing_session.get("last_activity", current_time)
                    < self.session_timeout
                ):
                    # 恢復現有會話
                    existing_session["last_activity"] = current_time
                    self._auto_save_if_needed()
                    return {
                        "success": True,
                        "message": "🔄 批次模式已恢復！繼續您的名片處理。",
                        "recovered": True,
                        "stats": {
                            "processed": len(
                                existing_session.get("processed_cards", [])
                            ),
                            "failed": len(existing_session.get("failed_cards", [])),
                        },
                    }

            # 創建新會話
            self.user_sessions[user_id] = {
                "is_batch_mode": True,
                "start_time": current_time,
                "last_activity": current_time,
                "processed_cards": [],
                "failed_cards": [],
                "total_count": 0,
                "session_id": f"{user_id}_{int(current_time.timestamp())}",
            }

            self._auto_save_if_needed()

            return {
                "success": True,
                "message": "✅ 批次模式已啟動！現在可以連續發送多張名片圖片。",
                "recovered": False,
            }

    def add_processed_card(self, user_id: str, card_data: Dict) -> bool:
        """添加已處理的名片（增強錯誤處理）"""
        with self.lock:
            try:
                if user_id not in self.user_sessions:
                    return False

                session = self.user_sessions[user_id]
                session["processed_cards"].append(
                    {
                        "data": card_data,
                        "processed_at": datetime.now().isoformat(),
                        "success": True,
                    }
                )
                session["total_count"] += 1
                session["last_activity"] = datetime.now()

                self._auto_save_if_needed()
                return True

            except Exception as e:
                print(f"❌ 添加處理卡片失敗: {e}")
                return False

    def add_failed_card(self, user_id: str, error_info: Dict) -> bool:
        """添加處理失敗的名片（增強錯誤追蹤）"""
        with self.lock:
            try:
                if user_id not in self.user_sessions:
                    return False

                session = self.user_sessions[user_id]
                session["failed_cards"].append(
                    {
                        "error": error_info,
                        "failed_at": datetime.now().isoformat(),
                        "retry_count": error_info.get("retry_count", 0),
                    }
                )
                session["total_count"] += 1
                session["last_activity"] = datetime.now()

                self._auto_save_if_needed()
                return True

            except Exception as e:
                print(f"❌ 添加失敗卡片失敗: {e}")
                return False

    def get_session_health(self, user_id: str) -> Dict:
        """獲取會話健康狀態"""
        with self.lock:
            if user_id not in self.user_sessions:
                return {"healthy": False, "reason": "session_not_found"}

            session = self.user_sessions[user_id]
            current_time = datetime.now()

            # 檢查會話是否過期
            if (
                current_time - session.get("last_activity", current_time)
                > self.session_timeout
            ):
                return {"healthy": False, "reason": "session_expired"}

            # 檢查會話活躍度
            processing_time = current_time - session.get("start_time", current_time)
            success_rate = 0
            if session["total_count"] > 0:
                success_rate = len(session["processed_cards"]) / session["total_count"]

            return {
                "healthy": True,
                "session_duration_minutes": processing_time.total_seconds() / 60,
                "success_rate": success_rate,
                "total_processed": len(session["processed_cards"]),
                "total_failed": len(session["failed_cards"]),
            }

    def force_cleanup(self):
        """強制清理所有會話並保存"""
        with self.lock:
            self._cleanup_expired_sessions()
            self._save_sessions()

    def get_system_stats(self) -> Dict:
        """獲取系統統計資訊"""
        with self.lock:
            active_sessions = len(self.user_sessions)
            total_processed = sum(
                len(s.get("processed_cards", [])) for s in self.user_sessions.values()
            )
            total_failed = sum(
                len(s.get("failed_cards", [])) for s in self.user_sessions.values()
            )

            return {
                "active_sessions": active_sessions,
                "total_processed_cards": total_processed,
                "total_failed_cards": total_failed,
                "session_file_exists": os.path.exists(self.session_file_path),
                "last_save_time": self.last_save_time,
            }
