"""AI 處理器接口定義

定義了所有 AI 相關處理的抽象接口，支援依賴注入和測試 mock。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..models.business_card import BusinessCard, CardQualityAssessment


class AIProcessorInterface(ABC):
    """AI 處理器抽象接口"""

    @abstractmethod
    async def process_single_card(self, image_data: bytes) -> Dict[str, Any]:
        """
        處理單張名片

        Args:
            image_data: 圖片二進制數據

        Returns:
            包含名片資訊的字典

        Raises:
            AIProcessingError: AI 處理失敗時拋出
        """
        pass

    @abstractmethod
    async def process_multiple_cards(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        處理多張名片

        Args:
            image_data: 包含多張名片的圖片二進制數據

        Returns:
            名片資訊列表

        Raises:
            AIProcessingError: AI 處理失敗時拋出
        """
        pass

    @abstractmethod
    async def assess_card_quality(
        self, card_data: Dict[str, Any]
    ) -> CardQualityAssessment:
        """
        評估名片識別品質

        Args:
            card_data: 名片數據字典

        Returns:
            品質評估結果
        """
        pass

    @abstractmethod
    async def normalize_address(self, address: str) -> Tuple[str, Dict[str, Any]]:
        """
        正規化地址格式

        Args:
            address: 原始地址字符串

        Returns:
            正規化後的地址和處理資訊
        """
        pass


class AddressNormalizerInterface(ABC):
    """地址正規化處理器接口"""

    @abstractmethod
    def normalize_taiwan_address(self, address: str) -> Dict[str, Any]:
        """
        正規化台灣地址

        Args:
            address: 原始地址

        Returns:
            正規化結果，包含處理後地址和信心度
        """
        pass

    @abstractmethod
    def validate_address_format(self, address: str) -> bool:
        """
        驗證地址格式

        Args:
            address: 地址字符串

        Returns:
            是否為有效格式
        """
        pass


class PromptEngineering:
    """提示工程常量和模板"""

    # 單張名片處理提示
    SINGLE_CARD_PROMPT = """
    請分析這張名片圖片，提取以下資訊並以 JSON 格式回傳：
    
    {
        "name": "姓名",
        "company": "公司名稱", 
        "department": "部門",
        "title": "職稱",
        "email": "電子郵件",
        "phone": "電話號碼",
        "address": "地址",
        "decision_influence": "決策影響力(高/中/低)",
        "confidence_score": 0.95,
        "notes": "其他備註"
    }
    
    注意事項：
    1. 如果某個欄位無法識別，請設為 null
    2. confidence_score 為整體識別信心度 (0-1)
    3. 電話號碼請保持原始格式
    4. 地址請盡量完整
    """

    # 多張名片處理提示
    MULTI_CARD_PROMPT = """
    請分析這張圖片中的所有名片，每張名片提取相同的資訊。
    
    回傳格式：
    {
        "cards": [
            {
                "card_index": 1,
                "name": "姓名",
                "company": "公司名稱",
                // ... 其他欄位
                "confidence_score": 0.95,
                "clarity_assessment": "清晰度評估"
            }
        ],
        "total_cards_detected": 2,
        "overall_quality": "整體品質評估"
    }
    """

    # 品質評估標準
    QUALITY_THRESHOLDS = {"excellent": 0.9, "good": 0.7, "fair": 0.5, "poor": 0.0}
