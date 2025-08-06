#!/usr/bin/env python3
"""
統一批次結果格式化器 - UnifiedResultFormatter

將多張圖片的處理結果合併成一條友好的訊息，減少用戶接收的訊息數量。
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ProcessingStatus(Enum):
    """處理狀態枚舉"""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class SingleCardResult:
    """單張名片處理結果"""

    status: ProcessingStatus
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    # 錯誤和質量信息
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    confidence_score: Optional[float] = None
    quality_grade: Optional[str] = None

    # 處理信息
    processing_time: Optional[float] = None
    image_index: Optional[int] = None
    notion_url: Optional[str] = None


@dataclass
class BatchProcessingResult:
    """批次處理結果"""

    user_id: str
    total_images: int
    successful_results: List[SingleCardResult]
    failed_results: List[SingleCardResult]
    skipped_results: List[SingleCardResult]

    total_processing_time: float
    success_rate: float
    notion_pages_created: int

    # 統計信息
    started_at: float
    completed_at: float


class UnifiedResultFormatter:
    """統一批次結果格式化器"""

    def __init__(self):
        self.templates = {
            "success_header": "✅ 批次處理完成！",
            "partial_success_header": "⚠️ 批次處理完成 (部分成功)",
            "all_failed_header": "❌ 批次處理失敗",
            "separator": "━" * 20,
        }

    def format_batch_result(self, result: BatchProcessingResult) -> str:
        """
        格式化批次處理結果為用戶友好的訊息

        Args:
            result: 批次處理結果對象

        Returns:
            格式化的訊息字符串
        """
        success_count = len(result.successful_results)
        total_count = result.total_images

        # 選擇合適的標題
        if success_count == total_count and total_count > 0:
            header = self.templates["success_header"]
        elif success_count > 0:
            header = self.templates["partial_success_header"]
        else:
            header = self.templates["all_failed_header"]

        # 構建訊息
        message_parts = [header]

        # 添加處理統計
        stats_line = f"\n📊 處理結果 ({success_count}/{total_count} 成功)"
        message_parts.append(stats_line)
        message_parts.append(self.templates["separator"])

        # 添加成功結果
        if result.successful_results:
            message_parts.extend(
                self._format_successful_results(result.successful_results)
            )

        # 添加失敗結果
        if result.failed_results:
            message_parts.extend(self._format_failed_results(result.failed_results))

        # 添加跳過結果
        if result.skipped_results:
            message_parts.extend(self._format_skipped_results(result.skipped_results))

        # 添加footer統計
        footer = self._format_footer_stats(result)
        message_parts.append(footer)

        # 添加建議（如果有失敗）
        if result.failed_results or result.skipped_results:
            suggestions = self._generate_suggestions(result)
            if suggestions:
                message_parts.append(f"\n💡 建議：\n{suggestions}")

        return "\n".join(message_parts)

    def _format_successful_results(self, results: List[SingleCardResult]) -> List[str]:
        """格式化成功結果"""
        lines = []
        for result in results:
            name = result.name or "未知"
            company = result.company or "未知公司"
            title = result.title or ""

            if title:
                line = f"✅ {name} - {company} ({title})"
            else:
                line = f"✅ {name} - {company}"

            # 添加信心度信息（如果可用）
            if result.confidence_score:
                confidence_emoji = self._get_confidence_emoji(result.confidence_score)
                line += f" {confidence_emoji}"

            lines.append(line)

        return lines

    def _format_failed_results(self, results: List[SingleCardResult]) -> List[str]:
        """格式化失敗結果"""
        lines = []
        for i, result in enumerate(results, 1):
            error_summary = self._get_error_summary(
                result.error_message, result.error_type
            )

            if result.image_index:
                line = f"⚠️ 第{result.image_index}張 - {error_summary}"
            else:
                line = f"⚠️ 第{i}張 - {error_summary}"

            lines.append(line)

        return lines

    def _format_skipped_results(self, results: List[SingleCardResult]) -> List[str]:
        """格式化跳過結果"""
        lines = []
        for i, result in enumerate(results, 1):
            reason = result.error_message or "品質不佳"

            if result.image_index:
                line = f"⏭️ 第{result.image_index}張 - 已跳過 ({reason})"
            else:
                line = f"⏭️ 第{i}張 - 已跳過 ({reason})"

            lines.append(line)

        return lines

    def _format_footer_stats(self, result: BatchProcessingResult) -> str:
        """格式化footer統計信息"""
        lines = []

        # Notion 存儲信息
        if result.notion_pages_created > 0:
            lines.append(f"💾 {result.notion_pages_created}筆資料已存入 Notion 資料庫")

        # 處理時間
        if result.total_processing_time > 0:
            lines.append(f"⏱️ 總處理時間: {result.total_processing_time:.1f}秒")

        # 成功率
        if result.total_images > 0:
            lines.append(f"🎯 成功率: {result.success_rate:.0f}%")

        return "\n" + "\n".join(lines)

    def _get_error_summary(
        self, error_message: Optional[str], error_type: Optional[str]
    ) -> str:
        """將技術錯誤訊息轉換為用戶友好的摘要"""
        if not error_message:
            return "處理失敗"

        error_lower = error_message.lower()

        # API 相關錯誤
        if "quota" in error_lower or "limit" in error_lower:
            return "AI 配額已用完"
        elif "timeout" in error_lower:
            return "處理超時"
        elif "network" in error_lower or "connection" in error_lower:
            return "網路連接問題"

        # 圖片相關錯誤
        elif "blur" in error_lower or "模糊" in error_lower:
            return "圖片太模糊"
        elif "dark" in error_lower or "暗" in error_lower:
            return "圖片太暗"
        elif "size" in error_lower or "large" in error_lower:
            return "檔案太大"
        elif "format" in error_lower:
            return "格式不支援"

        # 識別相關錯誤
        elif "no card" in error_lower or "非名片" in error_lower:
            return "非名片圖片"
        elif "low confidence" in error_lower:
            return "識別信心度太低"

        # 通用錯誤
        else:
            # 截取錯誤訊息的前30個字符
            if len(error_message) > 30:
                return error_message[:30] + "..."
            return error_message

    def _get_confidence_emoji(self, confidence: float) -> str:
        """根據信心度返回對應的emoji"""
        if confidence >= 0.9:
            return "🎯"  # 極高信心度
        elif confidence >= 0.8:
            return "✨"  # 高信心度
        elif confidence >= 0.7:
            return "⭐"  # 中等信心度
        else:
            return "❓"  # 低信心度

    def _generate_suggestions(self, result: BatchProcessingResult) -> str:
        """根據失敗原因生成建議"""
        suggestions = []

        # 分析失敗原因
        blur_count = sum(
            1
            for r in result.failed_results
            if r.error_message and "模糊" in r.error_message.lower()
        )
        dark_count = sum(
            1
            for r in result.failed_results
            if r.error_message and "暗" in r.error_message.lower()
        )
        network_count = sum(
            1
            for r in result.failed_results
            if r.error_message
            and (
                "network" in r.error_message.lower()
                or "connection" in r.error_message.lower()
            )
        )
        quota_count = sum(
            1
            for r in result.failed_results
            if r.error_message
            and (
                "quota" in r.error_message.lower() or "limit" in r.error_message.lower()
            )
        )

        # 根據錯誤類型生成建議
        if blur_count > 0:
            suggestions.append("• 📷 重新拍攝模糊的名片，確保對焦清晰")

        if dark_count > 0:
            suggestions.append("• 💡 在光線充足的環境下重新拍攝")

        if network_count > 0:
            suggestions.append("• 📶 檢查網路連接，稍後重試")

        if quota_count > 0:
            suggestions.append("• ⏰ AI 配額已用完，請明天再試")

        # 通用建議
        if result.success_rate < 0.5:  # 成功率低於50%
            suggestions.append("• 🎯 確保圖片為名片且清晰可見")
            suggestions.append("• 📏 圖片大小 < 5MB，解析度適中")

        if not suggestions:
            suggestions.append("• 🔄 如問題持續，請聯繫客服")

        return "\n".join(suggestions)

    def format_single_image_result(
        self, result: SingleCardResult, is_batch: bool = False
    ) -> str:
        """
        格式化單張圖片結果（兼容現有邏輯）

        Args:
            result: 單張名片結果
            is_batch: 是否為批次模式

        Returns:
            格式化的訊息字符串
        """
        if result.status == ProcessingStatus.SUCCESS:
            name = result.name or "未知"
            company = result.company or "未知公司"
            title = result.title or ""

            message = f"✅ 名片識別成功！\n\n"
            message += f"👤 **姓名**: {name}\n"
            message += f"🏢 **公司**: {company}\n"

            if title:
                message += f"💼 **職稱**: {title}\n"

            if result.email:
                message += f"📧 **Email**: {result.email}\n"

            if result.phone:
                message += f"📞 **電話**: {result.phone}\n"

            if result.address:
                message += f"📍 **地址**: {result.address}\n"

            if result.confidence_score:
                confidence_emoji = self._get_confidence_emoji(result.confidence_score)
                message += f"\n🎯 **識別信心度**: {result.confidence_score:.1%} {confidence_emoji}"

            if result.processing_time:
                message += f"\n⏱️ **處理時間**: {result.processing_time:.1f}秒"

            message += f"\n\n💾 資料已存入 Notion 資料庫"

            if result.notion_url:
                message += f"\n🔗 [查看詳細資料]({result.notion_url})"

        else:
            error_summary = self._get_error_summary(
                result.error_message, result.error_type
            )
            message = f"❌ 名片識別失敗\n\n"
            message += f"📋 **錯誤原因**: {error_summary}\n\n"

            # 添加具體建議
            suggestions = self._generate_single_error_suggestions(result.error_message)
            if suggestions:
                message += f"💡 **建議解決方案**:\n{suggestions}"

        return message

    def _generate_single_error_suggestions(self, error_message: Optional[str]) -> str:
        """為單張圖片錯誤生成建議"""
        if not error_message:
            return "• 🔄 重新上傳圖片\n• 📞 如問題持續，請聯繫客服"

        error_lower = error_message.lower()
        suggestions = []

        if "quota" in error_lower or "limit" in error_lower:
            suggestions.extend(
                [
                    "• ⏰ AI 配額已用完，請明天上午9點後重試",
                    "• 📞 如有緊急需求，請聯繫客服",
                ]
            )
        elif "timeout" in error_lower:
            suggestions.extend(
                [
                    "• ⏰ 稍等2-3分鐘後重試",
                    "• 📏 嘗試上傳較小的圖片 (<3MB)",
                    "• 📶 檢查網路連接穩定性",
                ]
            )
        elif "network" in error_lower or "connection" in error_lower:
            suggestions.extend(
                [
                    "• 📶 檢查網路連接",
                    "• 🔄 稍後重試 (1-2分鐘)",
                    "• 📱 嘗試切換到其他網路",
                ]
            )
        elif "blur" in error_lower or "模糊" in error_lower:
            suggestions.extend(
                [
                    "• 📷 重新拍攝，確保對焦清晰",
                    "• 💡 在光線充足的環境下拍攝",
                    "• 📐 將名片平放，避免陰影",
                ]
            )
        else:
            suggestions.extend(
                [
                    "• 📷 確保圖片為名片且清晰可見",
                    "• 📏 檢查圖片大小和格式 (JPG/PNG, <5MB)",
                    "• 🔄 重新上傳圖片",
                ]
            )

        return "\n".join(suggestions)


# 工具函數
def create_single_card_result(
    status: ProcessingStatus,
    card_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    processing_time: Optional[float] = None,
    **kwargs,
) -> SingleCardResult:
    """創建單張名片結果的便利函數"""
    result = SingleCardResult(status=status)

    if card_data:
        result.name = card_data.get("name")
        result.company = card_data.get("company")
        result.title = card_data.get("title")
        result.email = card_data.get("email")
        result.phone = card_data.get("phone")
        result.address = card_data.get("address")

    if error_message:
        result.error_message = error_message

    if processing_time:
        result.processing_time = processing_time

    # 設置其他屬性
    for key, value in kwargs.items():
        if hasattr(result, key):
            setattr(result, key, value)

    return result


def create_batch_result(
    user_id: str,
    results: List[SingleCardResult],
    total_processing_time: float,
    started_at: float,
) -> BatchProcessingResult:
    """創建批次結果的便利函數"""
    successful = [r for r in results if r.status == ProcessingStatus.SUCCESS]
    failed = [r for r in results if r.status == ProcessingStatus.FAILED]
    skipped = [r for r in results if r.status == ProcessingStatus.SKIPPED]

    total_images = len(results)
    success_rate = (len(successful) / total_images * 100) if total_images > 0 else 0
    notion_pages = len(successful)  # 假設每個成功結果創建一個Notion頁面

    return BatchProcessingResult(
        user_id=user_id,
        total_images=total_images,
        successful_results=successful,
        failed_results=failed,
        skipped_results=skipped,
        total_processing_time=total_processing_time,
        success_rate=success_rate,
        notion_pages_created=notion_pages,
        started_at=started_at,
        completed_at=time.time(),
    )
