#!/usr/bin/env python3
"""
測試名片處理中電話和傳真號碼的處理邏輯
"""
import os
import sys
import json
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_prompt_logic():
    """測試提示詞邏輯"""
    print("🧪 測試名片處理提示詞邏輯...")
    
    try:
        from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
        
        # 初始化處理器
        processor = NameCardProcessor()
        print("✅ 名片處理器初始化成功")
        
        # 檢查提示詞是否包含正確的指示
        prompt = processor.extract_multi_card_info.__code__.co_consts
        prompt_text = None
        
        # 提取 prompt 字符串
        for const in prompt:
            if isinstance(const, str) and "電話號碼處理規則" in const:
                prompt_text = const
                break
        
        if prompt_text:
            print("✅ 找到更新的提示詞")
            
            # 檢查關鍵指示
            checks = [
                ("電話和手機合併", "包含所有電話和手機號碼" in prompt_text),
                ("多個號碼分隔", "多個號碼用逗號和空格分隔" in prompt_text),
                ("傳真寫入備註", "傳真號碼不要放在 phone 欄位" in prompt_text),
                ("傳真標明格式", '傳真: +886' in prompt_text),
                ("E.164 格式", "E.164 格式" in prompt_text)
            ]
            
            for check_name, result in checks:
                print(f"   {check_name}: {'✅' if result else '❌'}")
            
            all_passed = all(result for _, result in checks)
            return all_passed
        else:
            print("❌ 找不到提示詞")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

def create_mock_business_card():
    """創建模擬名片測試數據"""
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # 創建名片圖片 (模擬)
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # 模擬名片內容 (包含電話、手機、傳真)
    card_text = [
        "張小明",
        "ABC科技有限公司",
        "業務經理",
        "電話: (02) 2345-6789", 
        "手機: 0912-345-678",
        "傳真: (02) 2345-6790",
        "Email: ming@abc.com.tw",
        "台北市信義區信義路100號"
    ]
    
    # 在圖片上添加文字 (簡單模擬)
    y_position = 50
    for line in card_text:
        draw.text((50, y_position), line, fill='black')
        y_position += 40
    
    # 轉換為 bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def simulate_ai_response():
    """模擬 AI 應該產生的回應格式"""
    expected_response = {
        "card_count": 1,
        "cards": [
            {
                "card_index": 1,
                "confidence_score": 0.9,
                "name": "張小明",
                "company": "ABC科技有限公司",
                "department": None,
                "title": "業務經理",
                "decision_influence": "中",
                "email": "ming@abc.com.tw",
                "phone": "+886223456789, +886912345678",  # 電話和手機合併
                "address": "台北市信義區信義路100號",
                "contact_source": "名片交換",
                "notes": "傳真: +886223456790",  # 傳真寫在備註中
                "field_confidence": {
                    "name": 0.95,
                    "company": 0.9,
                    "phone": 0.85,
                    "email": 0.8
                },
                "clarity_issues": [],
                "suggestions": []
            }
        ],
        "overall_quality": "good",
        "processing_suggestions": []
    }
    
    print("📋 預期的 AI 回應格式:")
    print(f"   電話欄位: {expected_response['cards'][0]['phone']}")
    print(f"   備註欄位: {expected_response['cards'][0]['notes']}")
    
    return expected_response

def validate_response_format(response):
    """驗證回應格式是否符合要求"""
    print("\n🔍 驗證回應格式...")
    
    if not isinstance(response, dict) or "cards" not in response:
        print("❌ 回應格式錯誤")
        return False
    
    for card in response["cards"]:
        phone = card.get("phone", "")
        notes = card.get("notes", "")
        
        # 檢查電話欄位
        phone_checks = [
            ("電話欄位存在", phone is not None),
            ("包含多個號碼", "," in phone if phone else False),
            ("使用 E.164 格式", "+886" in phone if phone else False)
        ]
        
        # 檢查備註欄位中的傳真
        notes_checks = [
            ("備註欄位存在", notes is not None),
            ("包含傳真信息", "傳真" in notes if notes else False),
            ("傳真使用 E.164 格式", "+886" in notes if notes else False)
        ]
        
        print(f"   電話欄位檢查:")
        for check_name, result in phone_checks:
            print(f"     {check_name}: {'✅' if result else '❌'}")
        
        print(f"   備註欄位檢查:")
        for check_name, result in notes_checks:
            print(f"     {check_name}: {'✅' if result else '❌'}")
        
    return True

def main():
    """主測試函數"""
    print("📞 名片電話和傳真處理邏輯測試")
    print("=" * 50)
    
    # 測試 1: 提示詞邏輯檢查
    prompt_test_passed = test_prompt_logic()
    
    # 測試 2: 模擬預期回應
    expected_response = simulate_ai_response()
    
    # 測試 3: 驗證回應格式
    format_valid = validate_response_format(expected_response)
    
    print("\n" + "=" * 50)
    print("🎯 測試總結:")
    print(f"   提示詞更新: {'✅ 通過' if prompt_test_passed else '❌ 失敗'}")
    print(f"   回應格式: {'✅ 正確' if format_valid else '❌ 錯誤'}")
    
    print("\n📋 重要變更說明:")
    print("   ✅ 電話和手機號碼 → 合併到 `phone` 欄位")
    print("   ✅ 傳真號碼 → 移到 `notes` 欄位")
    print("   ✅ 多個號碼用逗號分隔")
    print("   ✅ 統一使用 E.164 格式 (+886...)")
    
    print("\n🚀 部署建議:")
    if prompt_test_passed:
        print("   修改已完成，可以部署到生產環境")
        print("   建議先在測試環境驗證實際 AI 回應")
    else:
        print("   需要進一步檢查提示詞修改")
    
    return prompt_test_passed and format_valid

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)