#!/usr/bin/env python3
"""
名片識別測試腳本
用於測試 Gemini AI 是否能正確識別名片資訊
"""

import io
import json
import sys

from name_card_processor import NameCardProcessor
from PIL import Image, ImageDraw, ImageFont


def create_test_business_card():
    """建立一張測試名片圖片"""
    # 建立白色背景的圖片
    width, height = 400, 250
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # 嘗試使用系統字體，如果沒有就用預設字體
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except:
        # 如果找不到字體，使用預設字體
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 繪製名片內容
    y_pos = 20

    # 公司名稱
    draw.text((20, y_pos), "台灣科技股份有限公司", fill="black", font=font_medium)
    y_pos += 30

    # 姓名
    draw.text((20, y_pos), "王大明 David Wang", fill="black", font=font_large)
    y_pos += 35

    # 職稱
    draw.text(
        (20, y_pos), "技術經理 / Technical Manager", fill="black", font=font_medium
    )
    y_pos += 25

    # 聯絡資訊
    draw.text(
        (20, y_pos), "📧 david.wang@techcorp.com.tw", fill="black", font=font_small
    )
    y_pos += 20

    draw.text((20, y_pos), "📱 0912-345-678", fill="black", font=font_small)
    y_pos += 20

    draw.text((20, y_pos), "☎️ (02) 2123-4567", fill="black", font=font_small)
    y_pos += 20

    draw.text(
        (20, y_pos), "🏢 台北市信義區信義路五段7號", fill="black", font=font_small
    )

    return img


def test_name_card_processing():
    """測試名片處理功能"""
    print("🧪 開始測試名片識別功能...")

    try:
        # 建立處理器
        processor = NameCardProcessor()
        print("✅ NameCardProcessor 初始化成功")

        # 建立測試名片
        test_card = create_test_business_card()
        print("✅ 測試名片圖片建立成功")

        # 儲存測試圖片（使用相對路徑）
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_image_path = os.path.join(current_dir, "test_business_card.png")
        test_card.save(test_image_path)
        print("💾 測試名片已儲存為 test_business_card.png")

        # 轉換為 bytes
        img_byte_arr = io.BytesIO()
        test_card.save(img_byte_arr, format="PNG")
        image_bytes = img_byte_arr.getvalue()

        # 測試識別
        print("🔍 正在使用 Gemini AI 識別名片...")
        result = processor.extract_info_from_image(image_bytes)

        if "error" in result:
            print(f"❌ 識別失敗: {result['error']}")
            if "raw_response" in result:
                print(f"原始回應: {result['raw_response']}")
        else:
            print("✅ 名片識別成功！")
            print("\n📋 識別結果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # 顯示格式化結果
            print("\n📊 格式化顯示:")
            print(f"👤 姓名: {result.get('name', 'N/A')}")
            print(f"🏢 公司: {result.get('company', 'N/A')}")
            print(f"💼 職稱: {result.get('title', 'N/A')}")
            print(f"📧 Email: {result.get('email', 'N/A')}")
            print(f"📞 電話: {result.get('phone', 'N/A')}")
            print(f"⚡ 決策影響力: {result.get('decision_influence', 'N/A')}")
            print(f"📝 備註: {result.get('notes', 'N/A')}")

    except Exception as e:
        print(f"❌ 測試過程發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_name_card_processing()
