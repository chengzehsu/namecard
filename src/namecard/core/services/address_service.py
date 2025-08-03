"""
地址正規化模組 - Address Normalizer (簡化版)

此模組提供台灣地址基本標準化功能，包括：
- 縣市名稱統一化
- 區域名稱標準化
- 道路段數中文化
- 樓層表示法統一
- 基本格式驗證

設計理念：簡單、實用、可靠
"""

import re
from typing import Any, Dict, Optional


class AddressNormalizer:
    """地址正規化處理器 (簡化版)"""

    def __init__(self):
        # 台灣縣市對照表
        self.city_mapping = {
            "台北": "台北市",
            "新北": "新北市",
            "桃園": "桃園市",
            "台中": "台中市",
            "台南": "台南市",
            "高雄": "高雄市",
            # 完整縣市名稱（保持不變）
            "台北市": "台北市",
            "新北市": "新北市",
            "桃園市": "桃園市",
            "台中市": "台中市",
            "台南市": "台南市",
            "高雄市": "高雄市",
            "基隆市": "基隆市",
            "新竹市": "新竹市",
            "嘉義市": "嘉義市",
            "新竹縣": "新竹縣",
            "苗栗縣": "苗栗縣",
            "彰化縣": "彰化縣",
            "南投縣": "南投縣",
            "雲林縣": "雲林縣",
            "嘉義縣": "嘉義縣",
            "屏東縣": "屏東縣",
            "宜蘭縣": "宜蘭縣",
            "花蓮縣": "花蓮縣",
            "台東縣": "台東縣",
            "澎湖縣": "澎湖縣",
            "金門縣": "金門縣",
            "連江縣": "連江縣",
        }

        # 數字轉中文對照表
        self.number_mapping = {
            "1": "一",
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
            "7": "七",
            "8": "八",
            "9": "九",
            "10": "十",
        }

    def normalize_address(self, address: str) -> Dict[str, Any]:
        """
        正規化地址 (簡化版)

        Args:
            address: 原始地址字串

        Returns:
            Dict包含：
            - normalized: 正規化後的地址
            - original: 原始地址
            - confidence: 信心度 (0-1)
            - warnings: 警告訊息列表
            - is_taiwan_address: 是否為台灣地址
        """
        if not address or not isinstance(address, str):
            return self._create_result("", address, 0.0, ["地址為空或格式錯誤"], False)

        # 清理地址
        cleaned = self._clean_address(address)

        # 正規化處理
        normalized = self._normalize_simple(cleaned)

        # 計算信心度和生成警告
        confidence = self._calculate_simple_confidence(normalized)
        warnings = self._generate_simple_warnings(normalized)
        is_taiwan = self._is_taiwan_address(normalized)

        return self._create_result(normalized, address, confidence, warnings, is_taiwan)

    def _clean_address(self, address: str) -> str:
        """清理地址字串"""
        # 移除多餘空白
        address = re.sub(r"\s+", "", address)

        # 處理郵遞區號 - 移除縣市後接數字+區的情況（如：桃園市333龜山區）
        # 匹配模式：縣市名 + 3位數字 + 區名
        address = re.sub(
            r"(台北市|新北市|桃園市|台中市|台南市|高雄市)(\d{3})([^市]+區)",
            r"\1\3",
            address,
        )
        address = re.sub(
            r"(台北縣|桃園縣|台中縣|台南縣|高雄縣|新竹縣|苗栗縣|彰化縣|南投縣|雲林縣|嘉義縣|屏東縣|宜蘭縣|花蓮縣|台東縣|澎湖縣|基隆市|新竹市|嘉義市)(\d{3})([^縣市]+[鄉鎮市區])",
            r"\1\3",
            address,
        )

        # 移除特殊符號（保留中文、數字、常見符號）
        address = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z\-()（）]", "", address)
        return address.strip()

    def _normalize_simple(self, address: str) -> str:
        """簡單正規化處理"""
        result = address

        # 1. 縣市名稱標準化 - 按長度排序避免重複匹配
        city_keys = sorted(self.city_mapping.keys(), key=len, reverse=True)
        for city_key in city_keys:
            if result.startswith(city_key):
                if city_key != self.city_mapping[city_key]:
                    result = self.city_mapping[city_key] + result[len(city_key) :]
                break

        # 2. 區域名稱標準化 - 簡單版本，只處理明確沒有區字的情況
        common_districts = [
            "信義",
            "大安",
            "中正",
            "松山",
            "萬華",
            "中山",
            "大同",
            "內湖",
            "南港",
            "士林",
            "北投",
            "文山",
            "板橋",
            "新莊",
            "中和",
            "永和",
            "土城",
            "樹林",
            "三重",
            "蘆洲",
            "五股",
            "泰山",
            "林口",
            "淡水",
            "中壢",
            "平鎮",
            "八德",
            "楊梅",
            "蘆竹",
            "龜山",
            "龍潭",
            "大溪",
            "大園",
            "觀音",
            "新屋",
            "西屯",
            "北屯",
            "南屯",
            "北區",
            "西區",
            "南區",
            "東區",
            "中區",
            "太平",
            "大里",
            "霧峰",
            "烏日",
            "前金",
            "新興",
            "左營",
            "鼓山",
            "三民",
            "苓雅",
            "前鎮",
            "小港",
            "旗津",
            "鳳山",
            "大寮",
            "林園",
        ]

        # 排序避免短名稱誤匹配長名稱
        common_districts.sort(key=len, reverse=True)

        for district in common_districts:
            # 更精確的模式：縣市後面直接跟區域名稱，且不是以區鎮鄉市結尾，後面跟著路街等
            pattern = f"([市縣])({district})(?![區鎮鄉市])(?=[路街大道巷弄])"
            if re.search(pattern, result):
                result = re.sub(pattern, f"\\1{district}區", result, 1)
                break

        # 3. 道路段數中文化
        for num, chinese in self.number_mapping.items():
            result = re.sub(f"{num}段", f"{chinese}段", result)

        # 4. 樓層格式統一
        # F格式轉樓：1F -> 1樓
        result = re.sub(r"(\d+)F", r"\1樓", result)
        # B格式轉地下樓：B1 -> 地下1樓
        result = re.sub(r"B(\d+)", r"地下\1樓", result)

        return result

    def _calculate_simple_confidence(self, address: str) -> float:
        """簡單信心度計算"""
        score = 0.0

        # 檢查是否有台灣縣市
        has_taiwan_city = any(city in address for city in self.city_mapping.values())
        if has_taiwan_city:
            score += 0.5

        # 檢查是否有區域標識
        if re.search(r"[區鎮鄉市]", address):
            score += 0.3

        # 檢查是否有道路標識
        if re.search(r"[路街大道巷弄]", address):
            score += 0.2

        return min(score, 1.0)

    def _generate_simple_warnings(self, address: str) -> list:
        """生成簡單警告"""
        warnings = []

        has_taiwan_city = any(city in address for city in self.city_mapping.values())
        if not has_taiwan_city:
            warnings.append("無法識別台灣縣市")

        if not re.search(r"[區鎮鄉市]", address):
            warnings.append("無法識別區域資訊")

        if not re.search(r"[路街大道巷弄]", address):
            warnings.append("無法識別道路資訊")

        return warnings

    def _is_taiwan_address(self, address: str) -> bool:
        """檢查是否為台灣地址"""
        return any(city in address for city in self.city_mapping.values())

    def _create_result(
        self,
        normalized: str,
        original: str,
        confidence: float,
        warnings: list,
        is_taiwan: bool,
    ) -> Dict[str, Any]:
        """創建結果字典"""
        return {
            "normalized": normalized,
            "original": original,
            "confidence": confidence,
            "warnings": warnings,
            "is_taiwan_address": is_taiwan,
            # 簡化的組件資訊
            "components": self._extract_simple_components(normalized),
        }

    def _extract_simple_components(self, address: str) -> Dict[str, str]:
        """提取簡單組件資訊"""
        components = {"city": "", "district": "", "road": "", "number": "", "floor": ""}

        # 提取縣市
        for city in self.city_mapping.values():
            if address.startswith(city):
                components["city"] = city
                break

        # 提取區域 - 改進版本，先去掉縣市部分再匹配
        address_without_city = address
        for city in self.city_mapping.values():
            if address_without_city.startswith(city):
                address_without_city = address_without_city[len(city) :]
                break

        # 優先匹配標準區域格式 (XX區、XX鎮、XX鄉、XX市)
        district_match = re.search(
            r"([^路街大道巷弄0-9]{1,4}[區鎮鄉市])", address_without_city
        )
        if district_match:
            district = district_match.group(1)
            # 如果匹配到的區域過長，嘗試取前面較短的部分
            if len(district) > 5:
                short_match = re.search(
                    r"([^路街大道巷弄0-9]{1,3}[區鎮鄉市])", address_without_city
                )
                if short_match:
                    district = short_match.group(1)
            components["district"] = district

        # 提取道路
        road_match = re.search(r"([^區鎮鄉市]*[路街大道巷弄][^0-9]*)", address)
        if road_match:
            components["road"] = road_match.group(1)

        # 提取號碼
        number_match = re.search(r"(\d+號)", address)
        if number_match:
            components["number"] = number_match.group(1)

        # 提取樓層
        floor_match = re.search(r"(\d+樓|地下\d+樓|\d+室)", address)
        if floor_match:
            components["floor"] = floor_match.group(1)

        return components

    def is_valid_taiwan_address(self, address: str) -> bool:
        """檢查是否為有效的台灣地址"""
        result = self.normalize_address(address)
        return result["is_taiwan_address"] and result["confidence"] > 0.5


def normalize_address(address: str) -> Dict[str, Any]:
    """
    便利函數：正規化地址

    Args:
        address: 原始地址字串

    Returns:
        正規化結果字典
    """
    normalizer = AddressNormalizer()
    return normalizer.normalize_address(address)


def is_valid_taiwan_address(address: str) -> bool:
    """
    便利函數：檢查是否為有效的台灣地址

    Args:
        address: 地址字串

    Returns:
        是否為有效台灣地址
    """
    normalizer = AddressNormalizer()
    return normalizer.is_valid_taiwan_address(address)


if __name__ == "__main__":
    # 測試範例
    test_addresses = [
        "台北信義區信義路五段7號101室",
        "新北市板橋區中山路一段1號2F",
        "桃園市桃園區復興路100號B1",
        "台中市西屯區台灣大道三段99號",
        "高雄市前金區中正四路211號8樓",
    ]

    normalizer = AddressNormalizer()

    for addr in test_addresses:
        result = normalizer.normalize_address(addr)
        print(f"原始: {result['original']}")
        print(f"正規化: {result['normalized']}")
        print(f"信心度: {result['confidence']:.2f}")
        print(f"警告: {result['warnings']}")
        print("-" * 50)
