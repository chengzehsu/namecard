"""批次會話模型定義

定義了批次處理相關的資料模型。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .business_card import BusinessCard, ProcessingStatus


class BatchStatus(Enum):
    """批次狀態"""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class BatchSessionConfig(BaseModel):
    """批次會話配置"""

    timeout_minutes: int = Field(default=10, description="會話超時時間（分鐘）")
    max_cards_per_session: int = Field(default=50, description="每個會話最大名片數")
    auto_save_interval: int = Field(default=5, description="自動保存間隔（分鐘）")
    enable_progress_notifications: bool = Field(
        default=True, description="啟用進度通知"
    )


class BatchSession(BaseModel):
    """批次處理會話"""

    # 基本資訊
    session_id: str = Field(description="會話 ID")
    user_id: str = Field(description="使用者 ID")
    status: BatchStatus = Field(default=BatchStatus.ACTIVE)

    # 時間管理
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(description="過期時間")

    # 會話配置
    config: BatchSessionConfig = Field(default_factory=BatchSessionConfig)

    # 處理結果
    processed_cards: List[BusinessCard] = Field(default_factory=list)
    failed_cards: List[Dict[str, Any]] = Field(default_factory=list)
    pending_cards: List[Dict[str, Any]] = Field(default_factory=list)

    # 統計資訊
    total_images_processed: int = Field(default=0)
    successful_recognitions: int = Field(default=0)
    failed_recognitions: int = Field(default=0)

    # 處理元數據
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        validate_assignment = True

    def __init__(self, **data):
        # 自動設置過期時間
        if "expires_at" not in data and "config" in data:
            timeout_minutes = data["config"].timeout_minutes
        else:
            timeout_minutes = 10

        data["expires_at"] = datetime.now() + timedelta(minutes=timeout_minutes)

        super().__init__(**data)

    @property
    def is_expired(self) -> bool:
        """檢查會話是否過期"""
        return datetime.now() > self.expires_at

    @property
    def is_active(self) -> bool:
        """檢查會話是否活躍"""
        return self.status == BatchStatus.ACTIVE and not self.is_expired

    @property
    def total_cards_count(self) -> int:
        """總名片數量"""
        return (
            len(self.processed_cards) + len(self.failed_cards) + len(self.pending_cards)
        )

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.total_images_processed
        if total == 0:
            return 0.0
        return self.successful_recognitions / total

    @property
    def duration_minutes(self) -> float:
        """會話持續時間（分鐘）"""
        return (datetime.now() - self.created_at).total_seconds() / 60

    @property
    def time_remaining_minutes(self) -> float:
        """剩餘時間（分鐘）"""
        if self.is_expired:
            return 0.0
        return (self.expires_at - datetime.now()).total_seconds() / 60

    def update_activity(self) -> None:
        """更新最後活動時間"""
        self.last_activity = datetime.now()

    def add_processed_card(self, card: BusinessCard) -> None:
        """添加處理成功的名片"""
        self.processed_cards.append(card)
        self.successful_recognitions += 1
        self.update_activity()

    def add_failed_card(self, error_info: Dict[str, Any]) -> None:
        """添加處理失敗的名片"""
        self.failed_cards.append(
            {
                "timestamp": datetime.now().isoformat(),
                "error": error_info,
                "attempt_count": error_info.get("attempt_count", 1),
            }
        )
        self.failed_recognitions += 1
        self.update_activity()

    def add_pending_card(self, card_info: Dict[str, Any]) -> None:
        """添加等待處理的名片"""
        self.pending_cards.append(
            {"timestamp": datetime.now().isoformat(), "data": card_info}
        )
        self.update_activity()

    def extend_session(self, minutes: int = 10) -> None:
        """延長會話時間"""
        self.expires_at = max(
            self.expires_at + timedelta(minutes=minutes),
            datetime.now() + timedelta(minutes=minutes),
        )
        self.update_activity()

    def pause_session(self) -> None:
        """暫停會話"""
        self.status = BatchStatus.PAUSED
        self.update_activity()

    def resume_session(self) -> None:
        """恢復會話"""
        if not self.is_expired:
            self.status = BatchStatus.ACTIVE
            self.update_activity()

    def complete_session(self) -> "BatchSessionSummary":
        """完成會話並生成總結"""
        self.status = BatchStatus.COMPLETED
        self.update_activity()

        return BatchSessionSummary.from_session(self)

    def cancel_session(self, reason: Optional[str] = None) -> None:
        """取消會話"""
        self.status = BatchStatus.CANCELLED
        if reason:
            self.processing_metadata["cancellation_reason"] = reason
        self.update_activity()

    def get_progress_info(self) -> Dict[str, Any]:
        """獲取進度資訊"""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "total_cards": self.total_cards_count,
            "processed": len(self.processed_cards),
            "failed": len(self.failed_cards),
            "pending": len(self.pending_cards),
            "success_rate": self.success_rate,
            "duration_minutes": self.duration_minutes,
            "time_remaining_minutes": self.time_remaining_minutes,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
        }


class BatchSessionSummary(BaseModel):
    """批次會話總結"""

    session_id: str
    user_id: str

    # 時間資訊
    created_at: datetime
    completed_at: datetime
    duration_minutes: float

    # 處理統計
    total_images_processed: int
    total_cards_recognized: int
    successful_cards: int
    failed_cards: int
    success_rate: float

    # 品質統計
    high_quality_cards: int
    medium_quality_cards: int
    low_quality_cards: int

    # 詳細結果
    processed_cards: List[BusinessCard]
    failed_items: List[Dict[str, Any]]

    # 建議和改進
    performance_notes: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)

    @classmethod
    def from_session(cls, session: BatchSession) -> "BatchSessionSummary":
        """從批次會話創建總結"""

        # 品質統計
        quality_counts = {"high": 0, "medium": 0, "low": 0}
        for card in session.processed_cards:
            if card.is_high_quality():
                quality_counts["high"] += 1
            elif card.confidence_score > 0.5:
                quality_counts["medium"] += 1
            else:
                quality_counts["low"] += 1

        # 生成建議
        suggestions = []
        notes = []

        if session.success_rate < 0.7:
            suggestions.append("建議確保拍攝環境光線充足，名片平整清晰")
            notes.append(f"識別成功率較低：{session.success_rate:.1%}")

        if quality_counts["low"] > quality_counts["high"]:
            suggestions.append("建議重新拍攝品質較差的名片以提高識別準確度")

        if session.duration_minutes > 30:
            notes.append("批次處理時間較長，建議分批處理以提高效率")

        return cls(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            completed_at=datetime.now(),
            duration_minutes=session.duration_minutes,
            total_images_processed=session.total_images_processed,
            total_cards_recognized=len(session.processed_cards),
            successful_cards=session.successful_recognitions,
            failed_cards=session.failed_recognitions,
            success_rate=session.success_rate,
            high_quality_cards=quality_counts["high"],
            medium_quality_cards=quality_counts["medium"],
            low_quality_cards=quality_counts["low"],
            processed_cards=session.processed_cards,
            failed_items=session.failed_cards,
            performance_notes=notes,
            improvement_suggestions=suggestions,
        )

    def generate_report_text(self) -> str:
        """生成可讀的報告文字"""
        report_lines = [
            f"📊 批次處理報告",
            f"⏱️ 處理時間：{self.duration_minutes:.1f} 分鐘",
            f"📸 處理圖片：{self.total_images_processed} 張",
            f"📋 識別名片：{self.total_cards_recognized} 張",
            f"✅ 成功率：{self.success_rate:.1%}",
            "",
            "📈 品質分布：",
            f"  🟢 高品質：{self.high_quality_cards} 張",
            f"  🟡 中品質：{self.medium_quality_cards} 張",
            f"  🔴 低品質：{self.low_quality_cards} 張",
        ]

        if self.failed_cards > 0:
            report_lines.extend(["", f"❌ 失敗項目：{self.failed_cards} 個"])

        if self.improvement_suggestions:
            report_lines.extend(
                [
                    "",
                    "💡 改進建議：",
                    *[
                        f"  • {suggestion}"
                        for suggestion in self.improvement_suggestions
                    ],
                ]
            )

        return "\n".join(report_lines)
