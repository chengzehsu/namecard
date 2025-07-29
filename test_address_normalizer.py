"""
地址正規化測試檔案

測試各種地址格式的正規化功能，包括：
- 台灣地址標準化
- 縣市名稱統一化
- 區域格式標準化
- 樓層表示法統一
- 異常地址處理
"""

import unittest
from address_normalizer import AddressNormalizer, normalize_address, is_valid_taiwan_address


class TestAddressNormalizer(unittest.TestCase):
    """地址正規化測試類別"""
    
    def setUp(self):
        """設置測試環境"""
        self.normalizer = AddressNormalizer()
    
    def test_taiwan_city_normalization(self):
        """測試台灣縣市名稱標準化"""
        test_cases = [
            ("台北信義區信義路五段7號", "台北市信義區信義路五段7號"),
            ("新北板橋區中山路一段1號", "新北市板橋區中山路一段1號"),
            ("桃園桃園區復興路100號", "桃園市桃園區復興路100號"),
            ("台中西屯區台灣大道三段99號", "台中市西屯區台灣大道三段99號"),
            ("台南中西區民權路一段200號", "台南市中西區民權路一段200號"),
            ("高雄前金區中正四路211號", "高雄市前金區中正四路211號"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.normalizer.normalize_address(original)
                self.assertEqual(result['normalized'], expected)
                self.assertTrue(result['is_taiwan_address'])
                self.assertGreater(result['confidence'], 0.7)
    
    def test_district_normalization(self):
        """測試區域名稱標準化"""
        test_cases = [
            ("台北市信義信義路五段7號", "台北市信義區信義路五段7號"),
            ("新北市板橋中山路一段1號", "新北市板橋區中山路一段1號"),
            ("台中市西屯台灣大道三段99號", "台中市西屯區台灣大道三段99號"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.normalizer.normalize_address(original)
                self.assertEqual(result['normalized'], expected)
    
    def test_floor_normalization(self):
        """測試樓層表示法標準化"""
        test_cases = [
            ("台北市信義區信義路五段7號1F", "台北市信義區信義路五段7號1樓"),
            ("台北市信義區信義路五段7號B1", "台北市信義區信義路五段7號地下1樓"),
            ("台北市信義區信義路五段7號10F", "台北市信義區信義路五段7號10樓"),
            ("台北市信義區信義路五段7號B2", "台北市信義區信義路五段7號地下2樓"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.normalizer.normalize_address(original)
                self.assertEqual(result['normalized'], expected)
    
    def test_road_segment_normalization(self):
        """測試道路段數標準化"""
        test_cases = [
            ("台北市信義區信義路5段7號", "台北市信義區信義路五段7號"),
            ("新北市板橋區中山路1段1號", "新北市板橋區中山路一段1號"),
            ("台中市西屯區台灣大道3段99號", "台中市西屯區台灣大道三段99號"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.normalizer.normalize_address(original)
                self.assertEqual(result['normalized'], expected)
    
    def test_address_component_analysis(self):
        """測試地址組件分析"""
        address = "台北市信義區信義路五段7號101室"
        result = self.normalizer.normalize_address(address)
        
        components = result['components']
        self.assertEqual(components['city'], '台北市')
        self.assertEqual(components['district'], '信義區')
        self.assertEqual(components['road'], '信義路五段')
        self.assertEqual(components['number'], '7號')
        self.assertEqual(components['floor'], '101室')
    
    def test_confidence_calculation(self):
        """測試信心度計算"""
        # 完整地址應該有高信心度
        complete_address = "台北市信義區信義路五段7號101室"
        result = self.normalizer.normalize_address(complete_address)
        self.assertGreater(result['confidence'], 0.8)
        
        # 不完整地址應該有較低信心度
        incomplete_address = "信義路7號"
        result = self.normalizer.normalize_address(incomplete_address)
        self.assertLess(result['confidence'], 0.8)
    
    def test_warning_generation(self):
        """測試警告訊息生成"""
        # 缺少縣市的地址
        address_no_city = "信義區信義路五段7號"
        result = self.normalizer.normalize_address(address_no_city)
        self.assertIn("無法識別縣市資訊", result['warnings'])
        
        # 缺少區域的地址
        address_no_district = "台北市信義路五段7號"
        result = self.normalizer.normalize_address(address_no_district)
        self.assertIn("無法識別區域資訊", result['warnings'])
    
    def test_invalid_addresses(self):
        """測試無效地址處理"""
        invalid_addresses = [
            "",
            None,
            "   ",
            "abc123",
            "12345",
            "!@#$%^&*()",
        ]
        
        for invalid_addr in invalid_addresses:
            with self.subTest(address=invalid_addr):
                result = self.normalizer.normalize_address(invalid_addr)
                self.assertEqual(result['confidence'], 0.0)
                self.assertFalse(result['is_taiwan_address'])
                self.assertTrue(len(result['warnings']) > 0)
    
    def test_non_taiwan_addresses(self):
        """測試非台灣地址處理"""
        non_taiwan_addresses = [
            "東京都新宿區新宿1-1-1",
            "北京市朝陽區建國門外大街1號",
            "香港中環皇后大道中1號",
            "上海市浦東新區陸家嘴環路1000號",
        ]
        
        for address in non_taiwan_addresses:
            with self.subTest(address=address):
                result = self.normalizer.normalize_address(address)
                self.assertFalse(result['is_taiwan_address'])
                # 非台灣地址仍會嘗試處理，但信心度會較低
                self.assertLessEqual(result['confidence'], 0.4)
    
    def test_address_cleaning(self):
        """測試地址清理功能"""
        messy_addresses = [
            ("  台北市  信義區  信義路五段7號  ", "台北市信義區信義路五段7號"),
            ("台北市信義區信義路五段7號!!!", "台北市信義區信義路五段7號"),
            ("台北市\t信義區\n信義路五段7號", "台北市信義區信義路五段7號"),
        ]
        
        for messy, expected in messy_addresses:
            with self.subTest(messy=messy):
                result = self.normalizer.normalize_address(messy)
                # 清理後的地址應該接近預期結果
                self.assertIn("台北市", result['normalized'])
                self.assertIn("信義區", result['normalized'])
                self.assertIn("信義路", result['normalized'])
    
    def test_convenience_functions(self):
        """測試便利函數"""
        # 測試 normalize_address 便利函數
        address = "台北市信義區信義路五段7號"
        result1 = normalize_address(address)
        result2 = self.normalizer.normalize_address(address)
        self.assertEqual(result1['normalized'], result2['normalized'])
        
        # 測試 is_valid_taiwan_address 便利函數
        self.assertTrue(is_valid_taiwan_address("台北市信義區信義路五段7號"))
        self.assertFalse(is_valid_taiwan_address("東京都新宿區新宿1-1-1"))
        self.assertFalse(is_valid_taiwan_address(""))
    
    def test_complex_addresses(self):
        """測試複雜地址格式"""
        complex_addresses = [
            "台北市信義區信義路五段7號台北101大樓35樓A室",
            "新北市板橋區縣民大道二段7號15樓之1",
            "台中市西屯區文心路三段123號B1-1",
            "高雄市前金區中正四路211號8樓之2",
        ]
        
        for address in complex_addresses:
            with self.subTest(address=address):
                result = self.normalizer.normalize_address(address)
                self.assertTrue(result['is_taiwan_address'])
                self.assertGreater(result['confidence'], 0.5)
                # 檢查基本組件是否被識別
                self.assertTrue(result['components']['city'])
                self.assertTrue(result['components']['district'])


class TestAddressNormalizerIntegration(unittest.TestCase):
    """地址正規化整合測試"""
    
    def test_real_world_examples(self):
        """測試真實世界的地址範例"""
        real_addresses = [
            # 一般商業地址
            "台北市信義區信義路五段7號35樓",
            "新北市板橋區中山路一段161號",
            "桃園市桃園區復興路95號3樓",
            "台中市西屯區文心路三段241號",
            "台南市中西區民權路一段205號",
            "高雄市前金區中正四路211號",
            
            # 政府機關地址
            "台北市中正區重慶南路一段122號",
            "新北市板橋區中山路一段161號25樓",
            
            # 學校地址  
            "台北市大安區羅斯福路四段1號",
            "新竹市東區光復路二段101號",
            
            # 醫院地址
            "台北市中正區中山南路7號",
            "高雄市三民區自由一路100號",
        ]
        
        normalizer = AddressNormalizer()
        
        for address in real_addresses:
            with self.subTest(address=address):
                result = normalizer.normalize_address(address)
                
                # 基本檢查
                self.assertTrue(result['is_taiwan_address'])
                self.assertGreater(result['confidence'], 0.6)
                self.assertTrue(result['components']['city'])
                self.assertTrue(result['components']['district'])
                
                # 正規化結果不應為空
                self.assertTrue(result['normalized'].strip())
                
                # 正規化結果應包含主要城市名稱
                city_names = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市', '新竹市']
                self.assertTrue(any(city in result['normalized'] for city in city_names))


def run_tests():
    """執行所有測試"""
    print("🧪 開始執行地址正規化測試...")
    
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加測試類別
    suite.addTests(loader.loadTestsFromTestCase(TestAddressNormalizer))
    suite.addTests(loader.loadTestsFromTestCase(TestAddressNormalizerIntegration))
    
    # 執行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 測試結果報告
    print(f"\n📊 測試結果統計:")
    print(f"✅ 通過: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失敗: {len(result.failures)}")
    print(f"💥 錯誤: {len(result.errors)}")
    print(f"📈 總計: {result.testsRun}")
    
    if result.failures:
        print(f"\n❌ 失敗的測試:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
    
    if result.errors:
        print(f"\n💥 錯誤的測試:")
        for test, traceback in result.errors:
            error_lines = traceback.split('\n')
            error_msg = error_lines[-2] if len(error_lines) > 1 else str(traceback)
            print(f"  - {test}: {error_msg}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    
    if success:
        print("\n🎉 所有測試通過！地址正規化功能運作正常。")
    else:
        print("\n⚠️ 部分測試未通過，請檢查實作。")
        exit(1)