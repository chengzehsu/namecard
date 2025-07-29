from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

class BatchManager:
    def __init__(self):
        """初始化批次管理器"""
        self.user_sessions: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.session_timeout = timedelta(minutes=10)  # 10分鐘無操作自動結束批次模式
    
    def start_batch_mode(self, user_id: str) -> Dict:
        """啟動用戶的批次模式"""
        with self.lock:
            self.user_sessions[user_id] = {
                'is_batch_mode': True,
                'start_time': datetime.now(),
                'last_activity': datetime.now(),
                'processed_cards': [],
                'failed_cards': [],
                'total_count': 0
            }
            return {
                'success': True,
                'message': '✅ 批次模式已啟動！現在可以連續發送多張名片圖片。'
            }
    
    def end_batch_mode(self, user_id: str) -> Dict:
        """結束用戶的批次模式並返回統計結果"""
        with self.lock:
            if user_id not in self.user_sessions:
                return {
                    'success': False,
                    'message': '❌ 您目前不在批次模式中。'
                }
            
            session = self.user_sessions[user_id]
            
            # 計算統計資訊
            total_processed = len(session['processed_cards'])
            total_failed = len(session['failed_cards'])
            total_time = datetime.now() - session['start_time']
            
            # 清除會話
            del self.user_sessions[user_id]
            
            return {
                'success': True,
                'statistics': {
                    'total_processed': total_processed,
                    'total_failed': total_failed,
                    'total_time_minutes': total_time.total_seconds() / 60,
                    'processed_cards': session['processed_cards'],
                    'failed_cards': session['failed_cards']
                }
            }
    
    def is_in_batch_mode(self, user_id: str) -> bool:
        """檢查用戶是否在批次模式中"""
        with self.lock:
            if user_id not in self.user_sessions:
                return False
            
            session = self.user_sessions[user_id]
            
            # 檢查會話是否過期
            if datetime.now() - session['last_activity'] > self.session_timeout:
                del self.user_sessions[user_id]
                return False
            
            return session['is_batch_mode']
    
    def add_processed_card(self, user_id: str, card_info: Dict) -> None:
        """添加已處理的名片記錄"""
        with self.lock:
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['processed_cards'].append({
                    'name': card_info.get('name', 'Unknown'),
                    'company': card_info.get('company', 'Unknown'),
                    'notion_url': card_info.get('notion_url', ''),
                    'processed_time': datetime.now().isoformat()
                })
                self.user_sessions[user_id]['last_activity'] = datetime.now()
                self.user_sessions[user_id]['total_count'] += 1
    
    def add_failed_card(self, user_id: str, error_message: str) -> None:
        """添加處理失敗的名片記錄"""
        with self.lock:
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['failed_cards'].append({
                    'error': error_message,
                    'failed_time': datetime.now().isoformat()
                })
                self.user_sessions[user_id]['last_activity'] = datetime.now()
                self.user_sessions[user_id]['total_count'] += 1
    
    def get_session_info(self, user_id: str) -> Optional[Dict]:
        """獲取用戶會話資訊"""
        with self.lock:
            if user_id not in self.user_sessions:
                return None
            
            session = self.user_sessions[user_id]
            return {
                'is_batch_mode': session['is_batch_mode'],
                'start_time': session['start_time'],
                'processed_count': len(session['processed_cards']),
                'failed_count': len(session['failed_cards']),
                'total_count': session['total_count']
            }
    
    def update_activity(self, user_id: str) -> None:
        """更新用戶活動時間"""
        with self.lock:
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['last_activity'] = datetime.now()
    
    def cleanup_expired_sessions(self) -> None:
        """清理過期的會話"""
        with self.lock:
            expired_users = []
            for user_id, session in self.user_sessions.items():
                if datetime.now() - session['last_activity'] > self.session_timeout:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.user_sessions[user_id]
    
    def get_batch_progress_message(self, user_id: str) -> str:
        """獲取批次進度訊息"""
        session_info = self.get_session_info(user_id)
        if not session_info:
            return ""
        
        return f"""🔄 **批次模式進行中**
📊 已處理: {session_info['processed_count']} 張
❌ 失敗: {session_info['failed_count']} 張
📝 總計: {session_info['total_count']} 張

💡 繼續發送名片圖片，或發送「結束批次」完成處理"""