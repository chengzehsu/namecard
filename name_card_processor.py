import io
import json

import google.generativeai as genai
from PIL import Image

from config import Config


class NameCardProcessor:
    def __init__(self):
        """初始化 Gemini AI 模型"""
        try:
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        except Exception as e:
            raise Exception(f"初始化 Gemini 模型失敗: {e}")

    def extract_info_from_image(self, image_bytes):
        """從名片圖片中提取結構化資訊"""
        if not image_bytes:
            return {"error": "沒有圖像數據"}

        # 準備 Gemini prompt，專門針對 Notion 欄位優化
        prompt = """
        請你扮演一位專業的名片信息提取助手。仔細分析這張名片圖像，提取以下欄位的資訊：

        請將資訊結構化為有效的 JSON 格式：
        
        **欄位定義:**
        - `name` (姓名): 人名
        - `company` (客戶/SI 名稱): 公司名稱
        - `department` (部門): 部門名稱或單位
        - `title` (職稱): 職位名稱
        - `decision_influence` (決策影響力): 根據職稱推斷 (高/中/低)
        - `email` (Email): 電子郵件地址
        - `phone` (電話): 電話號碼，轉換為 E.164 格式 (+886...)
        - `address` (地址): 公司地址或聯絡地址
        - `contact_source` (取得聯繫來源): 設為 "名片交換"
        - `notes` (聯繫注意事項): 任何特殊備註或補充資訊
        
        **提取規則:**
        1. 如果欄位未找到，使用 null
        2. 電話號碼轉換為國際格式 (+886...)
        3. 決策影響力根據職稱判斷：
           - 總經理、CEO、董事長 → "高"
           - 經理、主管、部長 → "中" 
           - 一般職員、專員、工程師 → "低"
        4. 輸出必須是有效的 JSON，不要包含註釋

        JSON 輸出:
        """

        try:
            # 轉換為 PIL Image
            img_pil = Image.open(io.BytesIO(image_bytes))

            # 發送請求到 Gemini
            response = self.model.generate_content([prompt, img_pil])
            raw_response = response.text.strip()

            # 清理回應文字
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:]
            if raw_response.startswith("```"):
                raw_response = raw_response[3:]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3]

            raw_response = raw_response.strip()

            # 解析 JSON
            extracted_data = json.loads(raw_response)

            # 驗證回應是否為字典
            if not isinstance(extracted_data, dict):
                return {
                    "error": "Gemini 返回的不是有效的 JSON 對象",
                    "raw_response": raw_response,
                }

            return extracted_data

        except json.JSONDecodeError:
            return {
                "error": "無法解析 Gemini 的 JSON 響應",
                "raw_response": raw_response,
            }
        except Exception as e:
            return {"error": f"處理圖像時發生錯誤: {str(e)}"}

    def format_phone_number(self, phone):
        """格式化電話號碼為 E.164 格式"""
        if not phone:
            return None

        # 移除所有非數字字符
        clean_phone = "".join(filter(str.isdigit, phone))

        # 台灣手機號碼處理
        if clean_phone.startswith("09") and len(clean_phone) == 10:
            return f"+886{clean_phone[1:]}"

        # 台灣市話處理
        if clean_phone.startswith("0") and len(clean_phone) >= 9:
            return f"+886{clean_phone[1:]}"

        # 已經是國際格式
        if clean_phone.startswith("886"):
            return f"+{clean_phone}"

        return phone  # 無法識別格式，返回原始號碼
