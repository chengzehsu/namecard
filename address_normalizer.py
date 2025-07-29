"""
地址正規化模組 - Address Normalizer

此模組提供台灣地址標準化功能，包括：
- 縣市名稱統一化
- 區域名稱標準化  
- 道路格式標準化
- 樓層表示法統一
- 地址格式驗證
"""

import re
from typing import Optional, Dict, Any


class AddressNormalizer:
    """地址正規化處理器"""
    
    def __init__(self):
        # 台灣縣市對照表
        self.city_mapping = {
            # 直轄市縮寫對應
            '台北': '台北市',
            '新北': '新北市', 
            '桃園': '桃園市',
            '台中': '台中市',
            '台南': '台南市',
            '高雄': '高雄市',
            
            # 完整縣市名稱（保持不變）
            '台北市': '台北市',
            '新北市': '新北市',
            '桃園市': '桃園市',
            '台中市': '台中市',
            '台南市': '台南市',
            '高雄市': '高雄市',
            '基隆市': '基隆市',
            '新竹市': '新竹市',
            '嘉義市': '嘉義市',
            '新竹縣': '新竹縣',
            '苗栗縣': '苗栗縣',
            '彰化縣': '彰化縣',
            '南投縣': '南投縣',
            '雲林縣': '雲林縣',
            '嘉義縣': '嘉義縣',
            '屏東縣': '屏東縣',
            '宜蘭縣': '宜蘭縣',
            '花蓮縣': '花蓮縣',
            '台東縣': '台東縣',
            '澎湖縣': '澎湖縣',
            '金門縣': '金門縣',
            '連江縣': '連江縣'
        }
        
        # 數字轉中文對照表
        self.number_mapping = {
            '1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
            '6': '六', '7': '七', '8': '八', '9': '九', '10': '十'
        }
    
    def normalize_address(self, address: str) -> Dict[str, Any]:
        """
        正規化地址
        
        Args:
            address: 原始地址字串
            
        Returns:
            Dict包含：
            - normalized: 正規化後的地址
            - original: 原始地址
            - components: 地址組件分析
            - confidence: 信心度 (0-1)
            - warnings: 警告訊息列表
        """
        if not address or not isinstance(address, str):
            return self._create_result("", address, {}, 0.0, ["地址為空或格式錯誤"])
        
        # 清理地址字串
        cleaned_address = self._clean_address(address)
        
        # 分析地址組件
        components = self._analyze_components(cleaned_address)
        
        # 標準化各組件
        normalized_components = self._normalize_components(components)
        
        # 重建標準化地址
        normalized_address = self._rebuild_address(normalized_components)
        
        # 計算信心度
        confidence = self._calculate_confidence(components, normalized_components)
        
        # 生成警告訊息
        warnings = self._generate_warnings(components, normalized_components)
        
        return self._create_result(
            normalized_address, 
            address, 
            normalized_components,
            confidence,
            warnings
        )
    
    def _clean_address(self, address: str) -> str:
        """清理地址字串"""
        # 移除多餘空白
        address = re.sub(r'\s+', '', address)
        
        # 移除特殊字符（保留中文、數字、常見符號）
        address = re.sub(r'[^\u4e00-\u9fff0-9A-Za-z\-()（）]', '', address)
        
        return address.strip()
    
    def _analyze_components(self, address: str) -> Dict[str, str]:
        """分析地址組件"""
        components = {
            'city': '',
            'district': '', 
            'road': '',
            'number': '',
            'floor': '',
            'remaining': address
        }
        
        working_address = address
        
        # 1. 提取縣市（優先匹配最長的）
        city_keys = sorted(self.city_mapping.keys(), key=len, reverse=True)
        for city_key in city_keys:
            if working_address.startswith(city_key):
                components['city'] = city_key
                working_address = working_address[len(city_key):]
                break
        
        # 2. 提取區域（尋找以區、鎮、鄉、市結尾的部分）
        district_pattern = r'^([^區鎮鄉市]+[區鎮鄉市])'
        district_match = re.match(district_pattern, working_address)
        if district_match:
            components['district'] = district_match.group(1)
            working_address = working_address[len(district_match.group(1)):]
        
        # 3. 先提取樓層資訊（在後面的位置）
        floor_patterns = [
            r'([0-9]+樓[^0-9]*)',  # 數字樓
            r'(地下[0-9]+樓)',      # 地下樓
            r'([0-9]+[室號])',      # 室號
            r'([BF][0-9]+)',        # B1, F1格式
            r'([0-9]+F)'            # 1F格式
        ]
        
        for pattern in floor_patterns:
            floor_match = re.search(pattern, working_address)
            if floor_match:
                components['floor'] = floor_match.group(1)
                working_address = working_address.replace(floor_match.group(1), '')
                break
        
        # 4. 提取道路和號碼（剩餘部分）
        # 尋找道路名稱（包含段數）
        road_pattern = r'([^0-9]*(?:路|街|大道|巷|弄)(?:[0-9一二三四五六七八九十]+段)?)'
        road_match = re.match(road_pattern, working_address)
        if road_match:
            components['road'] = road_match.group(1)
            working_address = working_address[len(road_match.group(1)):]
        
        # 5. 剩餘部分作為號碼
        if working_address:
            components['number'] = working_address
        
        components['remaining'] = ''
        
        return components
    
    def _normalize_components(self, components: Dict[str, str]) -> Dict[str, str]:
        """標準化各地址組件"""
        normalized = components.copy()
        
        # 標準化縣市
        city = components.get('city', '')
        normalized['city'] = self.city_mapping.get(city, city)
        
        # 標準化區域（確保有正確後綴）
        district = components.get('district', '')
        if district and not district.endswith(('區', '鎮', '鄉', '市')):
            district += '區'
        normalized['district'] = district
        
        # 標準化道路（數字段數轉中文）
        road = components.get('road', '')
        if road:
            # 轉換段數：1段 -> 一段, 2段 -> 二段
            road = re.sub(r'([0-9])段', lambda m: f"{self.number_mapping.get(m.group(1), m.group(1))}段", road)
        normalized['road'] = road
        
        # 標準化樓層
        floor = components.get('floor', '')
        if floor:
            # F格式轉樓：1F -> 1樓
            floor = re.sub(r'([0-9]+)F', r'\1樓', floor)
            # B格式轉地下樓：B1 -> 地下1樓
            floor = re.sub(r'B([0-9]+)', r'地下\1樓', floor)
        normalized['floor'] = floor
        
        # 號碼保持原樣
        normalized['number'] = components.get('number', '')
        
        return normalized
    
    def _rebuild_address(self, components: Dict[str, str]) -> str:
        """重建標準化地址"""
        parts = []
        
        # 按照標準順序重建：縣市 + 區域 + 道路 + 號碼 + 樓層
        order = ['city', 'district', 'road', 'number', 'floor']
        
        for key in order:
            if components.get(key):
                parts.append(components[key])
        
        return ''.join(parts)
    
    def _calculate_confidence(self, original_components: Dict[str, str], 
                            normalized_components: Dict[str, str]) -> float:
        """計算正規化信心度"""
        score = 0.0
        
        # 縣市識別權重 40%
        if normalized_components.get('city'):
            score += 0.4
        
        # 區域識別權重 30%
        if normalized_components.get('district'):
            score += 0.3
        
        # 道路識別權重 20%
        if normalized_components.get('road'):
            score += 0.2
        
        # 號碼識別權重 10%
        if normalized_components.get('number'):
            score += 0.1
        
        return score
    
    def _generate_warnings(self, original_components: Dict[str, str],
                          normalized_components: Dict[str, str]) -> list:
        """生成警告訊息"""
        warnings = []
        
        if not normalized_components.get('city'):
            warnings.append("無法識別縣市資訊")
        
        if not normalized_components.get('district'):
            warnings.append("無法識別區域資訊")
        
        if not normalized_components.get('road'):
            warnings.append("無法識別道路資訊")
        
        if original_components.get('remaining'):
            warnings.append(f"有未處理的地址內容: {original_components['remaining']}")
        
        return warnings
    
    def _create_result(self, normalized: str, original: str, components: Dict[str, str],
                      confidence: float, warnings: list) -> Dict[str, Any]:
        """創建結果字典"""
        return {
            'normalized': normalized,
            'original': original,
            'components': components,
            'confidence': confidence,
            'warnings': warnings,
            'is_taiwan_address': bool(components.get('city') in self.city_mapping)
        }
    
    def is_valid_taiwan_address(self, address: str) -> bool:
        """檢查是否為有效的台灣地址"""
        result = self.normalize_address(address)
        return result['is_taiwan_address'] and result['confidence'] > 0.5


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