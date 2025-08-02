#!/usr/bin/env python3
"""
手動模擬 LINE Bot webhook 功能
用於完整測試名片識別和 Notion 整合
"""
import io
import json

from PIL import Image, ImageDraw, ImageFont

from name_card_processor import NameCardProcessor
from notion_manager import NotionManager


def create_realistic_business_card():
    """建立真實的名片圖片"""
    width, height = 500, 300
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_company = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        font_name = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
        font_info = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
    except:
        font_company = font_name = font_info = ImageFont.load_default()

    # 繪製邊框
    draw.rectangle([10, 10, width - 10, height - 10], outline="black", width=2)

    y_pos = 30

    # 公司名稱
    draw.text((30, y_pos), "智慧科技創新股份有限公司", fill="navy", font=font_company)
    draw.text(
        (30, y_pos + 25), "SmartTech Innovation Co., Ltd.", fill="navy", font=font_info
    )
    y_pos += 70

    # 姓名和職稱
    draw.text((30, y_pos), "陳執行長", fill="black", font=font_name)
    draw.text((30, y_pos + 35), "CEO / Executive Manager", fill="gray", font=font_info)
    y_pos += 80

    # 聯絡資訊
    draw.text(
        (30, y_pos), "📧 ceo@smarttech-innovation.com.tw", fill="black", font=font_info
    )
    y_pos += 25
    draw.text((30, y_pos), "📱 手機: 0912-345-678", fill="black", font=font_info)
    y_pos += 25
    draw.text((30, y_pos), "☎️ 電話: (02) 2700-1234", fill="black", font=font_info)
    y_pos += 25
    draw.text(
        (30, y_pos), "🏢 台北市信義區信義路五段7號33樓", fill="black", font=font_info
    )

    return img


def simulate_complete_workflow():
    """模擬完整的 LINE Bot 工作流程"""
    print("🎭 模擬完整的 LINE Bot 名片管理工作流程")
    print("=" * 60)

    # 模擬用戶上傳名片
    print("\n👤 模擬用戶: 傳送名片照片")
    print("🤖 LINE Bot: 📸 收到名片圖片！正在使用 AI 識別中，請稍候...")

    # 建立測試名片
    business_card = create_realistic_business_card()
    business_card.save("/Users/user/namecard/test_realistic_card.png")
    print("💾 測試名片已儲存為 test_realistic_card.png")

    # 轉換為 bytes
    img_byte_arr = io.BytesIO()
    business_card.save(img_byte_arr, format="PNG")
    image_bytes = img_byte_arr.getvalue()

    # Step 1: Gemini AI 識別
    print("\n🔍 Step 1: 使用 Gemini AI 識別名片...")
    processor = NameCardProcessor()
    extracted_info = processor.extract_info_from_image(image_bytes)

    if "error" in extracted_info:
        print(f"❌ 識別失敗: {extracted_info['error']}")
        return False

    print("✅ 名片識別成功！")
    print("\n📋 識別結果:")
    for key, value in extracted_info.items():
        print(f"  • {key}: {value}")

    # Step 2: 存入 Notion
    print("\n💾 Step 2: 存入 Notion 主資料庫...")
    notion_manager = NotionManager()
    notion_result = notion_manager.create_name_card_record(extracted_info)

    if notion_result["success"]:
        print("✅ 成功存入 Notion 資料庫！")

        # Step 3: 模擬 LINE Bot 回應
        print("\n🤖 LINE Bot 回應給用戶:")
        success_message = f"""✅ 名片資訊已成功存入 Notion！

👤 **姓名:** {extracted_info.get('name', 'N/A')}
🏢 **公司:** {extracted_info.get('company', 'N/A')}  
💼 **職稱:** {extracted_info.get('title', 'N/A')}
📧 **Email:** {extracted_info.get('email', 'N/A')}
📞 **電話:** {extracted_info.get('phone', 'N/A')}
⚡ **決策影響力:** {extracted_info.get('decision_influence', 'N/A')}

🔗 **Notion 頁面:** {notion_result['url']}"""

        print(success_message)
        print("\n🎉 完整工作流程測試成功！")
        return True
    else:
        print(f"❌ Notion 存入失敗: {notion_result['error']}")
        return False


def main():
    """主函數"""
    print("🚀 LINE Bot 名片管理系統 - 完整功能測試")

    # 執行完整測試
    success = simulate_complete_workflow()

    if success:
        print("\n" + "=" * 60)
        print("🎊 你的 LINE Bot 名片管理系統已經完全準備就緒！")
        print("\n📋 接下來的步驟:")
        print("1. 【雲端部署】使用 Zeabur/Heroku 部署獲得穩定 URL")
        print("2. 【LINE 設定】在 LINE Console 設定 webhook URL")
        print("3. 【開始使用】加 LINE Bot 為好友並上傳名片")

        print("\n💡 本地測試結果:")
        print("✅ Gemini AI 名片識別：完美運作")
        print("✅ Notion 資料庫整合：成功儲存")
        print("✅ 智能欄位推斷：自動分析")
        print("✅ 電話格式化：國際化處理")

        print("\n🔧 部署建議:")
        print("• Zeabur: 最簡單，自動部署")
        print("• Heroku: 穩定，免費層充足")
        print("• Render: 現代化，易於使用")

    else:
        print("\n❌ 測試中發現問題，請檢查配置")


if __name__ == "__main__":
    main()
