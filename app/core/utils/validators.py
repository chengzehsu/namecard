"""數據驗證工具

提供各種數據驗證和清理功能。
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from email_validator import EmailNotValidError
from email_validator import validate_email as _validate_email

from .exceptions import ValidationError, raise_validation_error


class EmailValidator:
    """電子郵件驗證器"""

    @staticmethod
    def validate(email: str, check_deliverability: bool = False) -> str:
        """
        驗證電子郵件格式

        Args:
            email: 電子郵件地址
            check_deliverability: 是否檢查可投遞性

        Returns:
            標準化的電子郵件地址

        Raises:
            ValidationError: 電子郵件格式無效
        """
        if not email:
            raise_validation_error("電子郵件不能為空", field="email")

        try:
            # 使用 email-validator 庫進行驗證
            validated_email = _validate_email(
                email, check_deliverability=check_deliverability
            )
            return validated_email.email
        except EmailNotValidError as e:
            raise_validation_error(
                f"電子郵件格式無效: {str(e)}", field="email", value=email
            )

    @staticmethod
    def is_valid(email: str) -> bool:
        """檢查電子郵件是否有效（不拋出異常）"""
        try:
            EmailValidator.validate(email)
            return True
        except ValidationError:
            return False


class PhoneValidator:
    """電話號碼驗證器"""

    # 台灣電話號碼格式正則表達式
    TAIWAN_MOBILE_PATTERN = re.compile(r"^09\d{8}$")
    TAIWAN_LANDLINE_PATTERN = re.compile(r"^0[2-8]\d{7,8}$")
    INTERNATIONAL_PATTERN = re.compile(r"^\+\d{1,3}\d{6,14}$")

    @staticmethod
    def clean_phone(phone: str) -> str:
        """
        清理電話號碼格式

        Args:
            phone: 原始電話號碼

        Returns:
            清理後的電話號碼
        """
        if not phone:
            return ""

        # 移除空格、連字符、括號等
        cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)

        # 保留數字、加號
        cleaned = re.sub(r"[^\d\+]", "", cleaned)

        return cleaned

    @staticmethod
    def validate(phone: str, country_code: str = "TW") -> str:
        """
        驗證電話號碼格式

        Args:
            phone: 電話號碼
            country_code: 國家代碼

        Returns:
            標準化的電話號碼

        Raises:
            ValidationError: 電話號碼格式無效
        """
        if not phone:
            raise_validation_error("電話號碼不能為空", field="phone")

        cleaned = PhoneValidator.clean_phone(phone)

        if country_code == "TW":
            # 台灣電話號碼驗證
            if PhoneValidator.TAIWAN_MOBILE_PATTERN.match(cleaned):
                return cleaned
            elif PhoneValidator.TAIWAN_LANDLINE_PATTERN.match(cleaned):
                return cleaned
            else:
                raise_validation_error(
                    "台灣電話號碼格式無效（應為 09xxxxxxxx 或 0x-xxxxxxxx）",
                    field="phone",
                    value=phone,
                )
        else:
            # 國際電話號碼驗證
            if not cleaned.startswith("+"):
                cleaned = "+" + cleaned

            if PhoneValidator.INTERNATIONAL_PATTERN.match(cleaned):
                return cleaned
            else:
                raise_validation_error(
                    "國際電話號碼格式無效", field="phone", value=phone
                )

    @staticmethod
    def is_valid(phone: str, country_code: str = "TW") -> bool:
        """檢查電話號碼是否有效（不拋出異常）"""
        try:
            PhoneValidator.validate(phone, country_code)
            return True
        except ValidationError:
            return False

    @staticmethod
    def format_display(phone: str, country_code: str = "TW") -> str:
        """
        格式化電話號碼用於顯示

        Args:
            phone: 電話號碼
            country_code: 國家代碼

        Returns:
            格式化的電話號碼
        """
        try:
            validated = PhoneValidator.validate(phone, country_code)

            if country_code == "TW":
                if validated.startswith("09"):
                    # 手機號碼: 0912-345-678
                    return f"{validated[:4]}-{validated[4:7]}-{validated[7:]}"
                elif validated.startswith("0"):
                    # 市話: (02)1234-5678
                    if len(validated) == 9:  # 台北市話
                        return f"({validated[:3]}){validated[3:7]}-{validated[7:]}"
                    else:  # 其他市話
                        return f"({validated[:3]}){validated[3:6]}-{validated[6:]}"

            return validated
        except ValidationError:
            return phone  # 返回原始格式


class AddressValidator:
    """地址驗證器"""

    # 台灣縣市列表
    TAIWAN_CITIES = {
        "台北市",
        "新北市",
        "桃園市",
        "台中市",
        "台南市",
        "高雄市",
        "基隆市",
        "新竹市",
        "嘉義市",
        "新竹縣",
        "苗栗縣",
        "彰化縣",
        "南投縣",
        "雲林縣",
        "嘉義縣",
        "屏東縣",
        "宜蘭縣",
        "花蓮縣",
        "台東縣",
        "澎湖縣",
        "金門縣",
        "連江縣",
    }

    @staticmethod
    def validate_taiwan_address(address: str) -> Dict[str, Any]:
        """
        驗證台灣地址格式

        Args:
            address: 地址字符串

        Returns:
            驗證結果字典
        """
        if not address:
            raise_validation_error("地址不能為空", field="address")

        result = {
            "is_valid": False,
            "normalized_address": address,
            "components": {},
            "issues": [],
        }

        # 檢查是否包含台灣縣市
        found_city = None
        for city in AddressValidator.TAIWAN_CITIES:
            if city in address or city.replace("台", "臺") in address:
                found_city = city
                break

        if found_city:
            result["components"]["city"] = found_city
            result["is_valid"] = True
        else:
            result["issues"].append("未找到有效的台灣縣市")

        # 檢查郵遞區號
        zipcode_pattern = re.compile(r"\b\d{3,5}\b")
        zipcode_match = zipcode_pattern.search(address)
        if zipcode_match:
            result["components"]["zipcode"] = zipcode_match.group()

        # 檢查路名
        road_pattern = re.compile(r"[一-龯\w]+(?:路|街|巷|弄|號|樓)")
        road_match = road_pattern.search(address)
        if road_match:
            result["components"]["road_info"] = road_match.group()

        return result

    @staticmethod
    def is_taiwan_address(address: str) -> bool:
        """檢查是否為台灣地址"""
        try:
            result = AddressValidator.validate_taiwan_address(address)
            return result["is_valid"]
        except ValidationError:
            return False


class BusinessCardValidator:
    """名片數據驗證器"""

    REQUIRED_FIELDS = ["name"]  # 必要欄位
    OPTIONAL_FIELDS = ["company", "department", "title", "email", "phone", "address"]

    @staticmethod
    def validate_card_data(card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        驗證名片數據

        Args:
            card_data: 名片數據字典

        Returns:
            驗證和清理後的數據

        Raises:
            ValidationError: 數據驗證失敗
        """
        if not isinstance(card_data, dict):
            raise_validation_error("名片數據必須是字典格式", field="card_data")

        validated_data = {}
        validation_issues = []

        # 檢查必要欄位
        for field in BusinessCardValidator.REQUIRED_FIELDS:
            if field not in card_data or not card_data[field]:
                validation_issues.append(f"必要欄位 '{field}' 缺失或為空")
            else:
                validated_data[field] = str(card_data[field]).strip()

        # 驗證可選欄位
        for field in BusinessCardValidator.OPTIONAL_FIELDS:
            if field in card_data and card_data[field]:
                value = str(card_data[field]).strip()

                if field == "email":
                    try:
                        validated_data[field] = EmailValidator.validate(value)
                    except ValidationError as e:
                        validation_issues.append(f"電子郵件格式錯誤: {e.message}")

                elif field == "phone":
                    try:
                        validated_data[field] = PhoneValidator.validate(value)
                    except ValidationError as e:
                        validation_issues.append(f"電話號碼格式錯誤: {e.message}")

                elif field == "address":
                    validated_data[field] = value
                    # 地址驗證（非強制性）
                    try:
                        addr_result = AddressValidator.validate_taiwan_address(value)
                        if not addr_result["is_valid"]:
                            validation_issues.append("地址格式可能不正確")
                    except ValidationError:
                        pass  # 地址驗證失敗不阻止整體驗證

                else:
                    validated_data[field] = value

        # 驗證信心度
        if "confidence_score" in card_data:
            confidence = card_data["confidence_score"]
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                validation_issues.append("信心度必須在 0 到 1 之間")
            else:
                validated_data["confidence_score"] = float(confidence)

        # 如果有嚴重的驗證問題，拋出異常
        critical_issues = [issue for issue in validation_issues if "必要欄位" in issue]
        if critical_issues:
            raise_validation_error(
                "名片數據驗證失敗", details={"issues": critical_issues}
            )

        # 添加驗證元數據
        validated_data["validation_metadata"] = {
            "validated_at": datetime.now().isoformat(),
            "issues": validation_issues,
            "is_valid": len(critical_issues) == 0,
        }

        return validated_data


class ConfigValidator:
    """配置驗證器"""

    @staticmethod
    def validate_url(url: str, schemes: List[str] = None) -> str:
        """驗證 URL 格式"""
        if not url:
            raise_validation_error("URL 不能為空", field="url")

        schemes = schemes or ["http", "https"]
        url_pattern = re.compile(
            r"^(?:" + "|".join(schemes) + r")://"
            r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            raise_validation_error(
                f"URL 格式無效，必須以 {'/'.join(schemes)} 開頭", field="url", value=url
            )

        return url

    @staticmethod
    def validate_port(
        port: Union[int, str], min_port: int = 1024, max_port: int = 65535
    ) -> int:
        """驗證端口號"""
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            raise_validation_error("端口號必須是數字", field="port", value=port)

        if not min_port <= port_int <= max_port:
            raise_validation_error(
                f"端口號必須在 {min_port} 到 {max_port} 之間", field="port", value=port
            )

        return port_int

    @staticmethod
    def validate_timeout(
        timeout: Union[int, float], min_timeout: float = 0.1, max_timeout: float = 300
    ) -> float:
        """驗證超時時間"""
        try:
            timeout_float = float(timeout)
        except (ValueError, TypeError):
            raise_validation_error("超時時間必須是數字", field="timeout", value=timeout)

        if not min_timeout <= timeout_float <= max_timeout:
            raise_validation_error(
                f"超時時間必須在 {min_timeout} 到 {max_timeout} 秒之間",
                field="timeout",
                value=timeout,
            )

        return timeout_float


class DataSanitizer:
    """數據清理工具"""

    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """清理文本數據"""
        if not text:
            return ""

        # 移除前後空格
        sanitized = text.strip()

        # 移除控制字符
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

        # 標準化空白字符
        sanitized = re.sub(r"\s+", " ", sanitized)

        # 限制長度
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()

        return sanitized

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        if not filename:
            return "untitled"

        # 移除危險字符
        sanitized = re.sub(r'[<>:"/\\|?*]', "", filename)

        # 移除控制字符
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

        # 限制長度
        if len(sanitized) > 255:
            name, ext = (
                sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
            )
            max_name_length = 255 - len(ext) - 1 if ext else 255
            sanitized = name[:max_name_length] + ("." + ext if ext else "")

        return sanitized or "untitled"

    @staticmethod
    def sanitize_dict(
        data: Dict[str, Any], allowed_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """清理字典數據"""
        if not isinstance(data, dict):
            return {}

        sanitized = {}

        for key, value in data.items():
            # 檢查允許的鍵
            if allowed_keys and key not in allowed_keys:
                continue

            # 清理鍵名
            clean_key = DataSanitizer.sanitize_text(str(key))
            if not clean_key:
                continue

            # 清理值
            if isinstance(value, str):
                sanitized[clean_key] = DataSanitizer.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = DataSanitizer.sanitize_dict(value, allowed_keys)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    (
                        DataSanitizer.sanitize_text(str(item))
                        if isinstance(item, str)
                        else item
                    )
                    for item in value
                ]
            else:
                sanitized[clean_key] = value

        return sanitized


# 使用範例
"""
# 電子郵件驗證
try:
    valid_email = EmailValidator.validate("user@example.com")
    print(f"Valid email: {valid_email}")
except ValidationError as e:
    print(f"Invalid email: {e.message}")

# 電話號碼驗證
try:
    valid_phone = PhoneValidator.validate("0912345678")
    formatted_phone = PhoneValidator.format_display(valid_phone)
    print(f"Valid phone: {valid_phone} -> {formatted_phone}")
except ValidationError as e:
    print(f"Invalid phone: {e.message}")

# 名片數據驗證
card_data = {
    'name': '張三',
    'company': 'ABC公司',
    'email': 'zhang@abc.com',
    'phone': '0912345678'
}

try:
    validated_card = BusinessCardValidator.validate_card_data(card_data)
    print(f"Validated card: {validated_card}")
except ValidationError as e:
    print(f"Invalid card data: {e.message}")

# 數據清理
raw_text = "  Hello\t\nWorld  \x00"
clean_text = DataSanitizer.sanitize_text(raw_text)
print(f"Clean text: '{clean_text}'")
"""
