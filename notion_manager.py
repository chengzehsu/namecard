from notion_client import Client
from config import Config
from datetime import datetime
import tempfile
import os
import base64
import re

class NotionManager:
    def __init__(self):
        """初始化 Notion 客戶端"""
        try:
            self.notion = Client(auth=Config.NOTION_API_KEY)
            self.database_id = Config.NOTION_DATABASE_ID
        except Exception as e:
            raise Exception(f"初始化 Notion 客戶端失敗: {e}")
    
    def create_name_card_record(self, card_data, image_bytes=None):
        """在 Notion 資料庫中建立名片記錄並添加圖片處理資訊"""
        try:
            # 建構 Notion 頁面屬性
            properties = self._build_properties(card_data)
            
            # 建立頁面
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            page_url = response["url"]
            
            # 如果有圖片，添加圖片處理資訊到頁面內容中
            if image_bytes:
                try:
                    self._add_image_info_to_page(page_id, image_bytes)
                    print("✅ 名片圖片處理資訊已成功添加到 Notion 頁面")
                except Exception as img_error:
                    print(f"⚠️ 添加圖片資訊失敗，但頁面建立成功: {img_error}")
            
            return {
                "success": True,
                "notion_page_id": page_id,
                "url": page_url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"建立 Notion 記錄失敗: {str(e)}"
            }
    
    def _build_properties(self, card_data):
        """建構 Notion 頁面屬性"""
        properties = {}
        
        # Name (標題欄位)
        if card_data.get("name"):
            properties["Name"] = {
                "title": [
                    {
                        "text": {
                            "content": card_data["name"]
                        }
                    }
                ]
            }
        
        # 公司名稱 (使用 rich_text 欄位)
        if card_data.get("company"):
            properties["公司名稱"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": card_data["company"]
                        }
                    }
                ]
            }
        
        # 職稱 (select 類型)
        if card_data.get("title"):
            properties["職稱"] = {
                "select": {
                    "name": card_data["title"]
                }
            }
        
        # 部門 (rich_text 類型)
        if card_data.get("department"):
            properties["部門"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": card_data["department"]
                        }
                    }
                ]
            }
        
        # 決策影響力 (選項欄位)
        if card_data.get("decision_influence"):
            properties["決策影響力"] = {
                "select": {
                    "name": card_data["decision_influence"]
                }
            }
        
        # Email (email 類型) - 需要驗證格式
        if card_data.get("email"):
            email = card_data["email"].strip()
            # 簡單的 email 格式驗證
            if re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                properties["Email"] = {
                    "email": email
                }
            else:
                # 如果格式不正確，改用 rich_text
                properties["Email備註"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"格式待確認: {email}"
                            }
                        }
                    ]
                }
        
        # 電話 (phone_number 類型) - 需要非空驗證
        if card_data.get("phone"):
            phone_text = card_data["phone"]
            if isinstance(phone_text, list):
                phone_text = phone_text[0] if phone_text else ""  # 取第一個電話號碼
            
            # 確保電話號碼不為空且格式合理
            if phone_text and phone_text.strip():
                phone_text = phone_text.strip()
                properties["電話"] = {
                    "phone_number": phone_text
                }
            else:
                # 如果電話為空，創建一個占位符
                properties["電話備註"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": "待補充電話資訊"
                            }
                        }
                    ]
                }
        
        # 地址 (rich_text 類型)
        if card_data.get("address"):
            properties["地址"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": card_data["address"]
                        }
                    }
                ]
            }
        
        # 取得聯繫來源
        if card_data.get("contact_source"):
            properties["取得聯繫來源"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": card_data["contact_source"]
                        }
                    }
                ]
            }
        
        # 聯繫注意事項
        if card_data.get("notes"):
            properties["聯繫注意事項"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": card_data["notes"]
                        }
                    }
                ]
            }
        
        # 窗口的困擾或 KPI (暫時留空，可後續手動填寫)
        properties["窗口的困擾或 KPI"] = {
            "rich_text": [
                {
                    "text": {
                        "content": "待後續補充"
                    }
                }
            ]
        }
        
        return properties
    
    def _add_image_info_to_page(self, page_id, image_bytes):
        """將圖片和處理資訊添加到 Notion 頁面內容中"""
        try:
            # 計算圖片大小
            image_size_kb = len(image_bytes) / 1024
            
            # 嘗試方法1：先創建圖片檔案並嘗試直接上傳
            success = self._try_upload_image_directly(page_id, image_bytes)
            
            if not success:
                # 方法2：創建空的圖片區塊供手動上傳
                self._create_image_placeholder_block(page_id, image_bytes, image_size_kb)
                
        except Exception as e:
            print(f"❌ 添加圖片資訊時發生錯誤: {e}")
            # 使用簡化的替代方案
            self._add_simple_image_note(page_id)
    
    def _try_upload_image_directly(self, page_id, image_bytes):
        """嘗試直接上傳圖片到 Notion"""
        try:
            # 將圖片保存到臨時檔案
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_bytes)
                temp_file_path = temp_file.name
            
            try:
                # 嘗試使用外部 URL 方式 (需要可訪問的 URL)
                # 由於這不太可行，我們改用佔位符方式
                return False
            finally:
                # 清理臨時檔案
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            print(f"直接上傳失敗: {e}")
            return False
    
    def _create_image_placeholder_block(self, page_id, image_bytes, image_size_kb):
        """創建包含圖片佔位符的區塊"""
        try:
            # 將圖片轉為 base64 (截取前部分避免過長)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            base64_preview = image_base64[:200] + "..." if len(image_base64) > 200 else image_base64
            
            self.notion.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "📸 名片圖片"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"📊 圖片大小: {image_size_kb:.1f} KB\n📅 處理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🤖 已使用 Gemini AI 識別完成"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "icon": {
                                "type": "emoji",
                                "emoji": "📋"
                            },
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "請在下方空白區域手動貼上名片圖片："
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "👆 點此區域並貼上名片圖片 (Ctrl+V / Cmd+V)"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "🔍 展開查看圖片技術資訊"
                                    }
                                }
                            ],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "code",
                                    "code": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": f"圖片 Base64 預覽:\ndata:image/jpeg;base64,{base64_preview}\n\n完整圖片已透過 LINE Bot 處理並識別"
                                                }
                                            }
                                        ],
                                        "language": "plain text"
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
            print("✅ 圖片佔位符已成功添加到 Notion 頁面")
            
        except Exception as e:
            print(f"❌ 創建圖片佔位符失敗: {e}")
            self._add_simple_image_note(page_id)
    
    def _add_simple_image_note(self, page_id):
        """添加簡單的圖片處理說明"""
        try:
            self.notion.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "📸 名片圖片已處理並識別完成"
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
        except Exception as e:
            print(f"❌ 添加簡單圖片說明失敗: {e}")
    
    def test_connection(self):
        """測試 Notion 連接和資料庫存取權限"""
        try:
            # 嘗試讀取資料庫資訊
            database = self.notion.databases.retrieve(database_id=self.database_id)
            return {
                "success": True,
                "database_title": database.get("title", [{}])[0].get("text", {}).get("content", "Unknown"),
                "properties": list(database.get("properties", {}).keys())
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Notion 連接測試失敗: {str(e)}"
            }