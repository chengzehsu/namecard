#!/usr/bin/env python3
"""
模擬 LINE Bot webhook 測試
這個腳本模擬用戶發送消息和圖片給 LINE Bot
"""

import base64
import hashlib
import hmac
import io
import json

from name_card_processor import NameCardProcessor
from notion_manager import NotionManager
from PIL import Image, ImageDraw, ImageFont

from config import Config


def create_test_business_card():
    """建立測試名片"""
    width, height = 400, 250
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # 繪製名片內容
    y_pos = 20
    draw.text((20, y_pos), "台灣創新科技有限公司", fill="black", font=font_medium)
    y_pos += 40
    draw.text((20, y_pos), "林董事長 Chairman Lin", fill="black", font=font_large)
    y_pos += 30
    draw.text((20, y_pos), "董事長", fill="black", font=font_medium)
    y_pos += 25
    draw.text(
        (20, y_pos), "📧 chairman@innovate-tech.com.tw", fill="black", font=font_medium
    )
    y_pos += 20
    draw.text((20, y_pos), "📱 0988-123-456", fill="black", font=font_medium)
    y_pos += 20
    draw.text((20, y_pos), "☎️ (02) 2700-8888", fill="black", font=font_medium)

    return img


def simulate_text_message():
    """模擬文字訊息：help"""
    print("🔸 模擬用戶發送文字訊息: 'help'")

    help_text = """🤖 名片管理 LINE Bot 使用說明

📸 **上傳名片圖片**
- 直接傳送名片照片給我
- 我會自動識別名片資訊並存入 Notion

💡 **功能特色:**
- 使用 Google Gemini AI 識別文字
- 自動整理聯絡資訊
- 直接存入 Notion 資料庫
- 支援中英文名片

❓ 需要幫助請輸入 "help" """

    print("🤖 Bot 回應:")
    print(help_text)
    return True


def simulate_image_message():
    """模擬圖片訊息：名片識別"""
    print("\n🔸 模擬用戶上傳名片圖片...")

    try:
        # 建立測試名片
        test_card = create_test_business_card()
        print("✅ 測試名片圖片建立成功")

        # 轉換為 bytes
        img_byte_arr = io.BytesIO()
        test_card.save(img_byte_arr, format="PNG")
        image_bytes = img_byte_arr.getvalue()

        print("🤖 Bot 回應: 📸 收到名片圖片！正在使用 AI 識別中，請稍候...")

        # 使用 Gemini 識別名片
        processor = NameCardProcessor()
        extracted_info = processor.extract_info_from_image(image_bytes)

        if "error" in extracted_info:
            error_message = f"❌ 名片識別失敗: {extracted_info['error']}"
            print(f"🤖 Bot 回應: {error_message}")
            return False

        print("🔍 Gemini AI 識別結果:")
        for key, value in extracted_info.items():
            print(f"  {key}: {value}")

        # 存入 Notion
        print("\n💾 正在存入 Notion 資料庫...")
        notion_manager = NotionManager()
        notion_result = notion_manager.create_name_card_record(extracted_info)

        if notion_result["success"]:
            success_message = f"""✅ 名片資訊已成功存入 Notion！

👤 **姓名:** {extracted_info.get('name', 'N/A')}
🏢 **公司:** {extracted_info.get('company', 'N/A')}  
💼 **職稱:** {extracted_info.get('title', 'N/A')}
📧 **Email:** {extracted_info.get('email', 'N/A')}
📞 **電話:** {extracted_info.get('phone', 'N/A')}
⚡ **決策影響力:** {extracted_info.get('decision_influence', 'N/A')}

🔗 **Notion 頁面:** {notion_result['url']}"""

            print("🤖 Bot 回應:")
            print(success_message)
            return True
        else:
            error_message = f"❌ Notion 存入失敗: {notion_result['error']}"
            print(f"🤖 Bot 回應: {error_message}")
            return False

    except Exception as e:
        error_message = f"❌ 處理過程中發生錯誤: {str(e)}"
        print(f"🤖 Bot 回應: {error_message}")
        return False


def main():
    """主函數：模擬完整的 LINE Bot 對話"""
    print("🎭 LINE Bot 名片管理系統 - 模擬測試")
    print("=" * 50)

    # 檢查配置
    try:
        Config.validate_config()
        print("✅ 系統配置正常")
    except Exception as e:
        print(f"❌ 配置錯誤: {e}")
        return

    print("\n📱 開始模擬 LINE Bot 對話...")

    # 模擬文字訊息
    simulate_text_message()

    # 模擬圖片訊息
    result = simulate_image_message()

    if result:
        print("\n🎉 模擬測試完成！你的 LINE Bot 名片管理系統完全正常運作！")
        print("\n📋 接下來的步驟:")
        print("1. 設定 LINE Bot webhook URL")
        print("2. 加你的 LINE Bot 為好友")
        print("3. 開始使用名片管理功能")
    else:
        print("\n❌ 測試中遇到問題，請檢查配置")


if __name__ == "__main__":
    main()
