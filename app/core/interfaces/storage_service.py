"""儲存服務接口定義

定義了資料儲存相關的抽象接口，支援多種儲存後端。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.business_card import BusinessCard


class StorageServiceInterface(ABC):
    """儲存服務抽象接口"""

    @abstractmethod
    async def create_card_record(
        self, card: BusinessCard, image_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        建立名片記錄

        Args:
            card: 名片業務模型
            image_data: 可選的圖片數據

        Returns:
            建立結果，包含記錄 ID 和狀態

        Raises:
            StorageError: 儲存操作失敗時拋出
        """
        pass

    @abstractmethod
    async def batch_create_records(self, cards: List[BusinessCard]) -> Dict[str, Any]:
        """
        批次建立記錄

        Args:
            cards: 名片列表

        Returns:
            批次操作結果
        """
        pass

    @abstractmethod
    async def update_card_record(
        self, record_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新名片記錄

        Args:
            record_id: 記錄 ID
            updates: 更新資料

        Returns:
            更新結果
        """
        pass

    @abstractmethod
    async def get_card_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取名片記錄

        Args:
            record_id: 記錄 ID

        Returns:
            名片記錄數據或 None
        """
        pass

    @abstractmethod
    async def search_cards(
        self, query: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜尋名片記錄

        Args:
            query: 搜尋條件
            limit: 結果限制

        Returns:
            符合條件的記錄列表
        """
        pass

    @abstractmethod
    async def delete_card_record(self, record_id: str) -> bool:
        """
        刪除名片記錄

        Args:
            record_id: 記錄 ID

        Returns:
            刪除是否成功
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            服務狀態資訊
        """
        pass


class NotionStorageInterface(StorageServiceInterface):
    """Notion 儲存服務專用接口"""

    @abstractmethod
    async def validate_database_schema(self) -> Dict[str, Any]:
        """
        驗證 Notion 資料庫結構

        Returns:
            驗證結果和結構資訊
        """
        pass

    @abstractmethod
    async def create_page_with_blocks(
        self, card: BusinessCard, additional_blocks: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        建立帶有額外區塊的 Notion 頁面

        Args:
            card: 名片數據
            additional_blocks: 額外的 Notion 區塊

        Returns:
            建立結果
        """
        pass


class CacheInterface(ABC):
    """快取服務接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """設置快取值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """刪除快取值"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        pass

    @abstractmethod
    async def flush(self) -> bool:
        """清空快取"""
        pass
