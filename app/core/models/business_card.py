"""名片業務模型定義

定義了名片相關的資料模型和驗證邏輯。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class DecisionInfluence(Enum):
    """決策影響力枚舉"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class CardQuality(Enum):
    """名片品質等級"""

    EXCELLENT = "excellent"  # 信心度 > 0.9
    GOOD = "good"  # 信心度 > 0.7
    FAIR = "fair"  # 信心度 > 0.5
    POOR = "poor"  # 信心度 <= 0.5


class ProcessingStatus(Enum):
    """處理狀態"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_USER_INPUT = "requires_user_input"


class ContactSource(Enum):
    """聯繫來源"""

    BUSINESS_CARD = "名片交換"
    NETWORKING_EVENT = "社交活動"
    INTRODUCTION = "他人介紹"
    ONLINE = "線上聯繫"
    COLD_CONTACT = "主動聯繫"
    OTHER = "其他"


class BusinessCard(BaseModel):
    """名片資料模型"""

    # 基本資訊
    name: Optional[str] = Field(None, max_length=100, description="姓名")
    company: Optional[str] = Field(None, max_length=200, description="公司名稱")
    department: Optional[str] = Field(None, max_length=100, description="部門")
    title: Optional[str] = Field(None, max_length=100, description="職稱")

    # 聯絡資訊
    email: Optional[str] = Field(None, description="電子郵件")
    phone: Optional[str] = Field(None, description="電話號碼")
    address: Optional[str] = Field(None, max_length=500, description="地址")

    # 業務資訊
    decision_influence: Optional[DecisionInfluence] = Field(
        None, description="決策影響力"
    )
    contact_source: ContactSource = Field(
        default=ContactSource.BUSINESS_CARD, description="聯繫來源"
    )
    notes: Optional[str] = Field(None, description="備註")

    # 處理元資訊
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="識別信心度"
    )
    quality: CardQuality = Field(default=CardQuality.FAIR, description="品質等級")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, description="處理狀態"
    )

    # 時間戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 額外資料
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="原始 AI 數據")
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="處理元數據"
    )

    class Config:
        use_enum_values = True
        str_strip_whitespace = True
        validate_assignment = True

    @validator("email")
    def validate_email(cls, v):
        """驗證電子郵件格式"""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @validator("phone")
    def clean_phone(cls, v):
        """清理電話號碼格式"""
        if v:
            # 保留數字、+、-、()、空格
            import re

            cleaned = re.sub(r"[^\d+\-\(\)\s]", "", v)
            if len(re.sub(r"[^\d]", "", cleaned)) < 8:
                raise ValueError("Phone number too short")
            return cleaned.strip()
        return v

    @validator("confidence_score")
    def validate_confidence_score(cls, v):
        """驗證信心度範圍"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v

    @validator("quality", pre=True, always=True)
    def determine_quality_from_confidence(cls, v, values):
        """根據信心度自動判斷品質等級"""
        if "confidence_score" in values:
            confidence = values["confidence_score"]
            if confidence > 0.9:
                return CardQuality.EXCELLENT
            elif confidence > 0.7:
                return CardQuality.GOOD
            elif confidence > 0.5:
                return CardQuality.FAIR
            else:
                return CardQuality.POOR
        return v or CardQuality.FAIR

    @classmethod
    def from_ai_response(cls, data: Dict[str, Any]) -> "BusinessCard":
        """
        從 AI 響應數據創建 BusinessCard 實例

        Args:
            data: AI 識別結果字典

        Returns:
            BusinessCard 實例
        """
        # 提取標準欄位
        card_data = {
            "name": data.get("name"),
            "company": data.get("company"),
            "department": data.get("department"),
            "title": data.get("title"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "address": data.get("address"),
            "notes": data.get("notes"),
            "confidence_score": data.get("confidence_score", 0.0),
            "raw_data": data,
        }

        # 處理決策影響力
        if "decision_influence" in data:
            influence_value = data["decision_influence"]
            if influence_value in ["高", "high"]:
                card_data["decision_influence"] = DecisionInfluence.HIGH
            elif influence_value in ["中", "medium"]:
                card_data["decision_influence"] = DecisionInfluence.MEDIUM
            elif influence_value in ["低", "low"]:
                card_data["decision_influence"] = DecisionInfluence.LOW

        # 處理聯繫來源
        if "contact_source" in data:
            source_mapping = {
                "名片交換": ContactSource.BUSINESS_CARD,
                "社交活動": ContactSource.NETWORKING_EVENT,
                "他人介紹": ContactSource.INTRODUCTION,
                "線上聯繫": ContactSource.ONLINE,
                "主動聯繫": ContactSource.COLD_CONTACT,
            }
            card_data["contact_source"] = source_mapping.get(
                data["contact_source"], ContactSource.OTHER
            )

        return cls(**card_data)

    def to_notion_properties(self) -> Dict[str, Any]:
        """
        轉換為 Notion 資料庫屬性格式

        Returns:
            Notion 屬性字典
        """
        properties = {}

        # 文本屬性
        if self.name:
            properties["Name"] = {"title": [{"text": {"content": self.name}}]}

        if self.company:
            properties["公司名稱"] = {
                "rich_text": [{"text": {"content": self.company}}]
            }

        if self.department:
            properties["部門"] = {"rich_text": [{"text": {"content": self.department}}]}

        if self.title:
            properties["職稱"] = {"select": {"name": self.title}}

        # 聯絡資訊
        if self.email:
            properties["Email"] = {"email": self.email}

        if self.phone:
            properties["電話"] = {"phone_number": self.phone}

        if self.address:
            properties["地址"] = {"rich_text": [{"text": {"content": self.address}}]}

        # 選擇屬性
        if self.decision_influence:
            properties["決策影響力"] = {
                "select": {"name": self.decision_influence.value}
            }

        # 其他屬性
        properties["取得聯繫來源"] = {
            "rich_text": [{"text": {"content": self.contact_source.value}}]
        }

        if self.notes:
            properties["聯繫注意事項"] = {
                "rich_text": [{"text": {"content": self.notes}}]
            }

        return properties

    def get_completeness_score(self) -> float:
        """
        計算名片資訊完整度分數

        Returns:
            完整度分數 (0.0-1.0)
        """
        fields = ["name", "company", "title", "email", "phone", "address"]
        filled_fields = sum(1 for field in fields if getattr(self, field))
        return filled_fields / len(fields)

    def is_high_quality(self) -> bool:
        """判斷是否為高品質名片"""
        return (
            self.quality in [CardQuality.EXCELLENT, CardQuality.GOOD]
            and self.confidence_score > 0.7
            and self.get_completeness_score() > 0.6
        )


class CardQualityAssessment(BaseModel):
    """名片品質評估結果"""

    overall_quality: CardQuality
    confidence_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)

    # 品質指標
    has_essential_fields: bool = Field(description="是否有基本必要欄位")
    text_clarity: float = Field(ge=0.0, le=1.0, description="文字清晰度")
    field_accuracy: float = Field(ge=0.0, le=1.0, description="欄位準確度")

    # 決策建議
    requires_user_choice: bool = Field(description="是否需要用戶選擇")
    auto_process_recommended: bool = Field(description="建議自動處理")

    # 改善建議
    improvement_suggestions: List[str] = Field(default_factory=list)
    quality_issues: List[str] = Field(default_factory=list)

    @classmethod
    def create_from_card(cls, card: BusinessCard) -> "CardQualityAssessment":
        """從名片創建品質評估"""
        completeness = card.get_completeness_score()
        confidence = card.confidence_score

        # 基本欄位檢查
        essential_fields = ["name", "company"]
        has_essential = all(getattr(card, field) for field in essential_fields)

        # 決策邏輯
        auto_process = (
            card.quality in [CardQuality.EXCELLENT, CardQuality.GOOD]
            and confidence > 0.8
            and has_essential
        )

        requires_choice = not auto_process and confidence > 0.5

        # 改善建議
        suggestions = []
        issues = []

        if not has_essential:
            issues.append("缺少基本資訊（姓名或公司）")
            suggestions.append("請確保名片上的姓名和公司名稱清晰可見")

        if completeness < 0.5:
            issues.append("資訊不完整")
            suggestions.append("請檢查名片是否完整拍攝")

        if confidence < 0.7:
            issues.append("識別信心度偏低")
            suggestions.append("請確保光線充足，名片清晰不模糊")

        return cls(
            overall_quality=card.quality,
            confidence_score=confidence,
            completeness_score=completeness,
            has_essential_fields=has_essential,
            text_clarity=confidence,  # 簡化處理
            field_accuracy=confidence,
            requires_user_choice=requires_choice,
            auto_process_recommended=auto_process,
            improvement_suggestions=suggestions,
            quality_issues=issues,
        )
