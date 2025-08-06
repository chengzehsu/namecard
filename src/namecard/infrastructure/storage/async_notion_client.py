"""
異步 Notion 客戶端 - 支援高並發批次寫入
"""

import asyncio
import os
import time
import weakref
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from notion_client import AsyncClient


# 簡化配置
class SimpleConfig:
    NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


Config = SimpleConfig


class AsyncNotionManager:
    """異步 Notion 管理器，支援高並發批次操作"""

    def __init__(self, max_concurrent: int = 10):
        """
        初始化異步 Notion 管理器

        Args:
            max_concurrent: 最大並發寫入數量
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        try:
            self.notion = AsyncClient(auth=Config.NOTION_API_KEY)
            self.database_id = Config.NOTION_DATABASE_ID
        except Exception as e:
            raise Exception(f"初始化 Notion 客戶端失敗: {e}")

        # 效能監控
        self.stats = {
            "total_created": 0,
            "total_errors": 0,
            "avg_creation_time": 0.0,
            "concurrent_peak": 0,
        }

        self.active_tasks = weakref.WeakSet()

    async def create_name_card_record_async(
        self,
        card_data: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        異步創建名片記錄

        Args:
            card_data: 名片數據
            image_bytes: 圖片二進制數據
            timeout: 超時時間（秒）

        Returns:
            創建結果
        """
        start_time = time.time()

        async with self.semaphore:
            try:
                # 更新並發統計
                current_concurrent = len(self.active_tasks) + 1
                if current_concurrent > self.stats["concurrent_peak"]:
                    self.stats["concurrent_peak"] = current_concurrent

                # 創建任務
                task = asyncio.create_task(
                    self._create_record_with_timeout(card_data, image_bytes, timeout)
                )
                self.active_tasks.add(task)

                result = await task

                # 更新統計
                processing_time = time.time() - start_time
                self._update_stats(processing_time, success=True)

                return result

            except asyncio.TimeoutError:
                self._update_stats(time.time() - start_time, success=False)
                return {"success": False, "error": f"Notion 操作超時（{timeout}秒）"}
            except Exception as e:
                self._update_stats(time.time() - start_time, success=False)
                return {"success": False, "error": f"創建 Notion 記錄失敗: {str(e)}"}

    async def _create_record_with_timeout(
        self, card_data: Dict[str, Any], image_bytes: Optional[bytes], timeout: float
    ) -> Dict[str, Any]:
        """帶超時的記錄創建"""
        return await asyncio.wait_for(
            self._create_record_core(card_data, image_bytes), timeout=timeout
        )

    async def _create_record_core(
        self, card_data: Dict[str, Any], image_bytes: Optional[bytes]
    ) -> Dict[str, Any]:
        """核心記錄創建邏輯"""
        try:
            # 建構 Notion 頁面屬性
            properties = await self._build_properties_async(card_data)

            # 創建頁面
            response = await self.notion.pages.create(
                parent={"database_id": self.database_id}, properties=properties
            )

            page_id = response["id"]
            page_url = response["url"]

            # 異步添加額外內容
            tasks = []

            # 添加圖片處理資訊
            if image_bytes:
                tasks.append(self._add_image_info_async(page_id, image_bytes))

            # 添加地址處理資訊
            if card_data.get("_address_confidence") is not None:
                tasks.append(
                    self._add_address_processing_info_async(page_id, card_data)
                )

            # 並行執行所有附加任務
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 檢查是否有錯誤
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"⚠️ 附加任務 {i} 失敗: {result}")

            return {"success": True, "notion_page_id": page_id, "url": page_url}

        except Exception as e:
            raise e

    async def _build_properties_async(
        self, card_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """異步建構 Notion 頁面屬性"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._build_properties_sync, card_data)

    def _build_properties_sync(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """同步建構 Notion 頁面屬性（在執行器中運行）"""
        properties = {}

        # Name (標題欄位)
        if card_data.get("name"):
            properties["Name"] = {"title": [{"text": {"content": card_data["name"]}}]}

        # 公司名稱
        if card_data.get("company"):
            properties["公司名稱"] = {
                "rich_text": [{"text": {"content": card_data["company"]}}]
            }

        # 職稱
        if card_data.get("title"):
            properties["職稱"] = {"select": {"name": card_data["title"]}}

        # 部門
        if card_data.get("department"):
            properties["部門"] = {
                "rich_text": [{"text": {"content": card_data["department"]}}]
            }

        # 決策影響力
        if card_data.get("decision_influence"):
            properties["決策影響力"] = {
                "select": {"name": card_data["decision_influence"]}
            }

        # Email（帶格式驗證）
        if card_data.get("email"):
            email = card_data["email"].strip()
            if self._is_valid_email(email):
                properties["Email"] = {"email": email}
            else:
                properties["Email備註"] = {
                    "rich_text": [{"text": {"content": f"格式待確認: {email}"}}]
                }

        # 電話
        if card_data.get("phone"):
            phone_text = card_data["phone"]
            try:
                properties["電話"] = {"phone_number": phone_text}
            except:
                properties["電話備註"] = {
                    "rich_text": [{"text": {"content": f"格式待確認: {phone_text}"}}]
                }

        # 地址
        if card_data.get("address"):
            properties["地址"] = {
                "rich_text": [{"text": {"content": card_data["address"]}}]
            }

        # 取得聯繫來源
        if card_data.get("contact_source"):
            properties["取得聯繫來源"] = {
                "rich_text": [{"text": {"content": card_data["contact_source"]}}]
            }

        # 聯繫注意事項
        if card_data.get("notes"):
            properties["聯繫注意事項"] = {
                "rich_text": [{"text": {"content": card_data["notes"]}}]
            }

        return properties

    def _is_valid_email(self, email: str) -> bool:
        """簡單的 email 格式驗證"""
        import re

        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

    async def _add_image_info_async(self, page_id: str, image_bytes: bytes):
        """異步添加圖片處理資訊"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_size_kb = len(image_bytes) / 1024

            blocks_to_add = [
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "📷 圖片處理資訊"}}
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"處理時間: {current_time}"},
                            }
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"圖片大小: {image_size_kb:.1f} KB"
                                },
                            }
                        ]
                    },
                },
            ]

            await self.notion.blocks.children.append(
                block_id=page_id, children=blocks_to_add
            )

        except Exception as e:
            print(f"添加圖片資訊失敗: {e}")

    async def _add_address_processing_info_async(
        self, page_id: str, card_data: Dict[str, Any]
    ):
        """異步添加地址處理資訊"""
        try:
            original_address = card_data.get("_original_address", "")
            address_confidence = card_data.get("_address_confidence", 0.0)

            blocks_to_add = [
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "🗺️ 地址處理資訊"}}
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"原始地址: {original_address}"},
                            }
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"處理信心度: {address_confidence:.1%}"
                                },
                            }
                        ]
                    },
                },
            ]

            await self.notion.blocks.children.append(
                block_id=page_id, children=blocks_to_add
            )

        except Exception as e:
            print(f"添加地址處理資訊失敗: {e}")

    async def create_batch_records(
        self,
        cards_data: List[Dict[str, Any]],
        image_bytes_list: Optional[List[bytes]] = None,
        max_concurrent: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        批次創建名片記錄

        Args:
            cards_data: 名片數據列表
            image_bytes_list: 圖片數據列表
            max_concurrent: 批次並發數限制

        Returns:
            創建結果列表
        """
        concurrent_limit = max_concurrent or self.max_concurrent
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def create_single_record(
            index: int, card_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            async with semaphore:
                image_bytes = (
                    image_bytes_list[index]
                    if image_bytes_list and index < len(image_bytes_list)
                    else None
                )
                return await self.create_name_card_record_async(card_data, image_bytes)

        # 創建所有任務
        tasks = [
            create_single_record(i, card_data) for i, card_data in enumerate(cards_data)
        ]

        # 並發執行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理異常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {"success": False, "error": f"批次項目 {i} 失敗: {str(result)}"}
                )
            else:
                processed_results.append(result)

        return processed_results

    def _update_stats(self, processing_time: float, success: bool):
        """更新統計資訊"""
        if success:
            self.stats["total_created"] += 1

            # 更新平均處理時間
            total_operations = self.stats["total_created"]
            current_avg = self.stats["avg_creation_time"]
            new_avg = (
                current_avg * (total_operations - 1) + processing_time
            ) / total_operations
            self.stats["avg_creation_time"] = new_avg
        else:
            self.stats["total_errors"] += 1

    async def get_performance_stats(self) -> Dict[str, Any]:
        """獲取效能統計"""
        success_rate = (
            self.stats["total_created"]
            / (self.stats["total_created"] + self.stats["total_errors"])
            if (self.stats["total_created"] + self.stats["total_errors"]) > 0
            else 0.0
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "active_tasks": len(self.active_tasks),
            "semaphore_available": self.semaphore._value,
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            # 測試基本連接
            start_time = time.time()
            await self.notion.databases.retrieve(database_id=self.database_id)
            response_time = time.time() - start_time

            # 檢查負載
            current_load = len(self.active_tasks) / self.max_concurrent

            status = "healthy"
            if response_time > 5.0:
                status = "warning"
            elif current_load > 0.8:
                status = "warning"

            return {
                "status": status,
                "response_time": response_time,
                "current_load": current_load,
                "max_concurrent": self.max_concurrent,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}
