"""基礎服務類和接口定義"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseService(ABC):
    """所有服務的基礎類"""

    def __init__(self, name: Optional[str] = None):
        self.logger = logging.getLogger(name or self.__class__.__name__)
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """初始化服務"""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        pass

    def is_initialized(self) -> bool:
        """檢查服務是否已初始化"""
        return self._initialized


class CardProcessorInterface(ABC):
    """名片處理器接口"""

    @abstractmethod
    def process_card(self, image_data: bytes) -> Dict[str, Any]:
        """處理名片"""
        pass

    @abstractmethod
    def process_multiple_cards(self, image_data: bytes) -> Dict[str, Any]:
        """處理多張名片"""
        pass


class StorageInterface(ABC):
    """存儲服務接口"""

    @abstractmethod
    def save_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """保存名片數據"""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """測試存儲連接"""
        pass


class BatchManagerInterface(ABC):
    """批次管理器接口"""

    @abstractmethod
    def start_batch_mode(self, user_id: str) -> Dict[str, Any]:
        """開始批次模式"""
        pass

    @abstractmethod
    def end_batch_mode(self, user_id: str) -> Dict[str, Any]:
        """結束批次模式"""
        pass

    @abstractmethod
    def is_in_batch_mode(self, user_id: str) -> bool:
        """檢查是否在批次模式中"""
        pass


class MessageClientInterface(ABC):
    """消息客戶端接口"""

    @abstractmethod
    def send_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """發送消息"""
        pass

    @abstractmethod
    def reply_message(self, reply_token: str, message: str) -> Dict[str, Any]:
        """回覆消息"""
        pass
