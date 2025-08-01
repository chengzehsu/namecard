"""訊息處理接口定義

定義了 LINE Bot 訊息處理相關的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from linebot.models import ImageMessage, MessageEvent, TextMessage


class MessageHandlerInterface(ABC):
    """訊息處理器抽象接口"""

    @abstractmethod
    async def handle_text_message(
        self, message: TextMessage, user_id: str, reply_token: str
    ) -> Dict[str, Any]:
        """
        處理文字訊息

        Args:
            message: LINE 文字訊息物件
            user_id: 使用者 ID
            reply_token: 回覆權杖

        Returns:
            處理結果
        """
        pass

    @abstractmethod
    async def handle_image_message(
        self, message: ImageMessage, user_id: str, reply_token: str
    ) -> Dict[str, Any]:
        """
        處理圖片訊息

        Args:
            message: LINE 圖片訊息物件
            user_id: 使用者 ID
            reply_token: 回覆權杖

        Returns:
            處理結果
        """
        pass

    @abstractmethod
    async def handle_follow_event(
        self, user_id: str, reply_token: str
    ) -> Dict[str, Any]:
        """
        處理用戶關注事件

        Args:
            user_id: 使用者 ID
            reply_token: 回覆權杖

        Returns:
            處理結果
        """
        pass


class BatchManagerInterface(ABC):
    """批次處理管理器接口"""

    @abstractmethod
    async def start_batch_mode(self, user_id: str) -> Dict[str, Any]:
        """啟動批次模式"""
        pass

    @abstractmethod
    async def end_batch_mode(self, user_id: str) -> Dict[str, Any]:
        """結束批次模式"""
        pass

    @abstractmethod
    async def is_batch_active(self, user_id: str) -> bool:
        """檢查批次模式是否啟動"""
        pass

    @abstractmethod
    async def add_card_to_batch(
        self, user_id: str, card_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """添加名片到批次"""
        pass

    @abstractmethod
    async def get_batch_status(self, user_id: str) -> Dict[str, Any]:
        """獲取批次狀態"""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """清理過期會話"""
        pass


class UserInteractionInterface(ABC):
    """用戶互動管理接口"""

    @abstractmethod
    async def create_choice_session(
        self, user_id: str, options: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """建立選擇會話"""
        pass

    @abstractmethod
    async def handle_user_choice(self, user_id: str, choice: str) -> Dict[str, Any]:
        """處理用戶選擇"""
        pass

    @abstractmethod
    async def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """獲取活躍會話"""
        pass

    @abstractmethod
    async def close_session(self, user_id: str) -> bool:
        """關閉會話"""
        pass


class LineBotClientInterface(ABC):
    """LINE Bot 客戶端接口"""

    @abstractmethod
    async def reply_message(
        self, reply_token: str, messages: Union[List[Any], Any]
    ) -> Dict[str, Any]:
        """回覆訊息"""
        pass

    @abstractmethod
    async def push_message(
        self, user_id: str, messages: Union[List[Any], Any]
    ) -> Dict[str, Any]:
        """推送訊息"""
        pass

    @abstractmethod
    async def get_message_content(self, message_id: str) -> bytes:
        """獲取訊息內容"""
        pass

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶資料"""
        pass

    @abstractmethod
    async def validate_signature(self, body: str, signature: str) -> bool:
        """驗證請求簽名"""
        pass
