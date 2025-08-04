import io
import json
import time
import random

import google.generativeai as genai
from PIL import Image

from src.namecard.core.services.address_service import AddressNormalizer
from simple_config import Config


class NameCardProcessor:
    def __init__(self):
        """初始化 Gemini AI 模型和地址正規化器"""
        self.current_api_key = Config.GOOGLE_API_KEY
        self.fallback_api_key = Config.GOOGLE_API_KEY_FALLBACK
        self.using_fallback = False

        try:
            genai.configure(api_key=self.current_api_key)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
            self.address_normalizer = AddressNormalizer()
        except Exception as e:
            raise Exception(f"初始化 Gemini 模型失敗: {e}")

    def _switch_to_fallback_api(self):
        """切換到備用 API Key"""
        if not self.fallback_api_key:
            raise Exception("沒有設定備用 API Key (GOOGLE_API_KEY_FALLBACK)")

        if self.using_fallback:
            raise Exception("已經在使用備用 API Key，無法再次切換")

        try:
            print(f"⚠️ 主要 API Key 額度不足，正在切換到備用 API Key...")
            genai.configure(api_key=self.fallback_api_key)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
            self.current_api_key = self.fallback_api_key
            self.using_fallback = True
            print(f"✅ 已成功切換到備用 API Key")
            return True
        except Exception as e:
            raise Exception(f"切換到備用 API Key 失敗: {e}")

    def _is_quota_exceeded_error(self, error_message):
        """檢查是否為 API 額度超限錯誤"""
        quota_error_keywords = [
            "quota exceeded",
            "resource exhausted",
            "429",
            "rate limit",
            "usage limit",
            "billing",
            "quota",
            "exceeded",
        ]

        error_str = str(error_message).lower()
        return any(keyword in error_str for keyword in quota_error_keywords)

    def _is_transient_error(self, error_message):
        """檢查是否為暫時性錯誤（可重試）"""
        transient_error_keywords = [
            "500",
            "502",
            "503",
            "504",
            "internal error",
            "service unavailable",
            "timeout",
            "temporary",
            "try again",
            "retry",
            "network",
            "connection",
        ]

        error_str = str(error_message).lower()
        return any(keyword in error_str for keyword in transient_error_keywords)

    def _generate_content_with_fallback(self, content, max_retries=3):
        """使用主要 API Key 生成內容，支援重試和備用 API Key 切換"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 嘗試生成內容
                response = self.model.generate_content(content)
                return response.text.strip()

            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # 檢查是否為額度超限錯誤
                if (
                    self._is_quota_exceeded_error(error_str)
                    and not self.using_fallback
                    and self.fallback_api_key
                ):
                    try:
                        print(f"🔄 API 額度超限，切換到備用 API Key...")
                        self._switch_to_fallback_api()
                        
                        # 用備用 API Key 重試
                        response = self.model.generate_content(content)
                        return response.text.strip()
                        
                    except Exception as fallback_error:
                        raise Exception(
                            f"主要和備用 API Key 都失敗: 主要錯誤={error_str}, 備用錯誤={str(fallback_error)}"
                        )
                
                # 檢查是否為暫時性錯誤（可重試）
                elif self._is_transient_error(error_str):
                    if attempt < max_retries - 1:  # 不是最後一次嘗試
                        # 指數退避策略：1秒、2秒、4秒
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️ 暫時性錯誤（{error_str[:100]}...），{wait_time:.1f}秒後重試 (第{attempt + 1}/{max_retries}次)")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 最後一次嘗試失敗
                        raise Exception(f"經過{max_retries}次重試後仍然失敗: {error_str}")
                
                else:
                    # 其他類型錯誤，不重試
                    raise e
        
        # 如果到這裡，表示所有重試都失敗了
        raise Exception(f"經過{max_retries}次重試後仍然失敗: {str(last_error)}")

    def extract_info_from_image(self, image_bytes):
        """從名片圖片中提取結構化資訊（支援多名片檢測）"""
        if not image_bytes:
            return {"error": "沒有圖像數據"}

        # 使用新的多名片檢測方法
        return self.extract_multi_card_info(image_bytes)

    def extract_multi_card_info(self, image_bytes):
        """從圖片中提取多張名片的資訊，包含品質評估"""
        if not image_bytes:
            return {"error": "沒有圖像數據"}

        # 多名片檢測的增強 prompt
        prompt = """
        請你扮演一位專業的名片信息提取助手。仔細分析這張圖像，執行以下任務：

        **第一步：名片檢測**
        - 檢查圖像中有幾張名片
        - 如果有多張名片，請分別標記為 card_1, card_2 等

        **第二步：信息提取與品質評估**
        對每張名片提取以下欄位，並評估提取信心度：

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

        **品質評估規則:**
        - `confidence_score`: 0.0-1.0，表示整張名片識別的信心度
        - `field_confidence`: 各欄位的信心度評估
        - `clarity_issues`: 列出不清楚或可能錯誤的欄位
        - `suggestions`: 改善建議（如需要重拍特定區域）

        **決策影響力判斷:**
        - 總經理、CEO、董事長 → "高"
        - 經理、主管、部長 → "中"
        - 一般職員、專員、工程師 → "低"

        **輸出格式 (JSON):**
        {
          "card_count": 檢測到的名片數量,
          "cards": [
            {
              "card_index": 1,
              "confidence_score": 0.85,
              "name": "張三",
              "company": "ABC公司",
              "department": "業務部",
              "title": "經理",
              "decision_influence": "中",
              "email": "example@abc.com",
              "phone": "+886912345678",
              "address": "台北市信義區...",
              "contact_source": "名片交換",
              "notes": null,
              "field_confidence": {
                "name": 0.9,
                "company": 0.8,
                "email": 0.7
              },
              "clarity_issues": ["電話號碼部分模糊"],
              "suggestions": []
            }
          ],
          "overall_quality": "good|partial|poor",
          "processing_suggestions": ["建議重新拍攝第2張名片的右下角"]
        }

        **注意事項:**
        1. 如果欄位無法識別，使用 null
        2. confidence_score 基於文字清晰度、完整性評估
        3. 如果只有一張名片，card_count = 1
        4. 輸出必須是有效的 JSON

        JSON 輸出:
        """

        try:
            # 轉換為 PIL Image
            img_pil = Image.open(io.BytesIO(image_bytes))

            # 發送請求到 Gemini，支援 API Key 切換
            raw_response = self._generate_content_with_fallback([prompt, img_pil])

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

            # 驗證回應格式
            if not isinstance(extracted_data, dict):
                return {
                    "error": "Gemini 返回的不是有效的 JSON 對象",
                    "raw_response": raw_response,
                }

            # 檢查是否為新的多名片格式
            if "card_count" in extracted_data and "cards" in extracted_data:
                # 新格式：多名片檢測結果
                return self._process_multi_card_response(extracted_data)
            else:
                # 舊格式：單一名片 - 轉換為新格式以保持一致性
                return self._convert_single_card_to_multi_format(extracted_data)

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

    def _process_multi_card_response(self, extracted_data):
        """處理多名片格式的回應，包含地址正規化"""
        try:
            # 對每張名片進行地址正規化處理
            for card in extracted_data.get("cards", []):
                if card.get("address"):
                    # 地址正規化
                    address_result = self.address_normalizer.normalize_address(
                        card["address"]
                    )
                    card["address"] = address_result["normalized"]

                    # 添加地址處理資訊
                    if address_result["warnings"]:
                        address_warnings = (
                            f"地址處理警告: {', '.join(address_result['warnings'])}"
                        )
                        current_notes = card.get("notes", "")
                        if current_notes:
                            card["notes"] = f"{current_notes}; {address_warnings}"
                        else:
                            card["notes"] = address_warnings

                    # 添加地址信心度資訊
                    card["_address_confidence"] = address_result["confidence"]
                    card["_original_address"] = address_result["original"]

            # 添加整體品質評估
            extracted_data = self._assess_overall_quality(extracted_data)

            return extracted_data

        except Exception as e:
            return {"error": f"處理多名片回應時發生錯誤: {str(e)}"}

    def _convert_single_card_to_multi_format(self, single_card_data):
        """將單一名片格式轉換為多名片格式，保持向後兼容性"""
        try:
            # 先進行地址正規化（原有邏輯）
            if single_card_data.get("address"):
                address_result = self.address_normalizer.normalize_address(
                    single_card_data["address"]
                )
                single_card_data["address"] = address_result["normalized"]

                if address_result["warnings"]:
                    address_warnings = (
                        f"地址處理警告: {', '.join(address_result['warnings'])}"
                    )
                    current_notes = single_card_data.get("notes", "")
                    if current_notes:
                        single_card_data["notes"] = (
                            f"{current_notes}; {address_warnings}"
                        )
                    else:
                        single_card_data["notes"] = address_warnings

                single_card_data["_address_confidence"] = address_result["confidence"]
                single_card_data["_original_address"] = address_result["original"]

            # 轉換為多名片格式
            multi_card_format = {
                "card_count": 1,
                "cards": [
                    {
                        **single_card_data,
                        "card_index": 1,
                        "confidence_score": self._calculate_single_card_confidence(
                            single_card_data
                        ),
                        "field_confidence": self._calculate_field_confidence(
                            single_card_data
                        ),
                        "clarity_issues": [],
                        "suggestions": [],
                    }
                ],
                "overall_quality": self._assess_single_card_quality(single_card_data),
                "processing_suggestions": [],
            }

            return multi_card_format

        except Exception as e:
            return {"error": f"轉換單一名片格式時發生錯誤: {str(e)}"}

    def _assess_overall_quality(self, multi_card_data):
        """評估多名片的整體品質"""
        try:
            cards = multi_card_data.get("cards", [])
            if not cards:
                multi_card_data["overall_quality"] = "poor"
                return multi_card_data

            # 計算平均信心度
            total_confidence = sum(card.get("confidence_score", 0.5) for card in cards)
            avg_confidence = total_confidence / len(cards)

            # 檢查關鍵欄位完整性
            complete_cards = 0
            for card in cards:
                required_fields = ["name", "company"]
                if all(card.get(field) for field in required_fields):
                    complete_cards += 1

            completeness_ratio = complete_cards / len(cards)

            # 綜合評估
            if avg_confidence >= 0.8 and completeness_ratio >= 0.8:
                multi_card_data["overall_quality"] = "good"
            elif avg_confidence >= 0.6 and completeness_ratio >= 0.5:
                multi_card_data["overall_quality"] = "partial"
            else:
                multi_card_data["overall_quality"] = "poor"

            # 生成處理建議
            suggestions = []
            for i, card in enumerate(cards, 1):
                if card.get("confidence_score", 0.5) < 0.6:
                    suggestions.append(f"第{i}張名片識別品質較差，建議重新拍攝")
                if card.get("clarity_issues"):
                    suggestions.append(
                        f"第{i}張名片存在清晰度問題: {', '.join(card['clarity_issues'])}"
                    )

            multi_card_data["processing_suggestions"] = suggestions

            return multi_card_data

        except Exception as e:
            multi_card_data["overall_quality"] = "error"
            multi_card_data["processing_suggestions"] = [f"品質評估錯誤: {str(e)}"]
            return multi_card_data

    def _calculate_single_card_confidence(self, card_data):
        """計算單一名片的信心度"""
        score = 0.5  # 基礎分數

        # 關鍵欄位存在性檢查
        if card_data.get("name"):
            score += 0.2
        if card_data.get("company"):
            score += 0.2
        if card_data.get("email"):
            score += 0.1
        if card_data.get("phone"):
            score += 0.1

        return min(score, 1.0)

    def _calculate_field_confidence(self, card_data):
        """計算各欄位的信心度"""
        field_confidence = {}

        # 簡單的欄位信心度計算邏輯
        for field in ["name", "company", "email", "phone", "title"]:
            if card_data.get(field):
                # 基於欄位值的簡單評估
                value = str(card_data[field])
                if len(value) > 2 and not any(
                    char in value for char in ["?", "unclear", "模糊"]
                ):
                    field_confidence[field] = 0.8
                else:
                    field_confidence[field] = 0.4
            else:
                field_confidence[field] = 0.0

        return field_confidence

    def _assess_single_card_quality(self, card_data):
        """評估單一名片的品質"""
        required_fields = ["name", "company"]
        has_all_required = all(card_data.get(field) for field in required_fields)

        optional_fields = ["email", "phone", "title"]
        optional_count = sum(1 for field in optional_fields if card_data.get(field))

        if has_all_required and optional_count >= 2:
            return "good"
        elif has_all_required:
            return "partial"
        else:
            return "poor"
