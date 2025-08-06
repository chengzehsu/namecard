#!/usr/bin/env python3
"""
新 LINE TOKEN 驗證腳本
在更改正式環境前，先在本地驗證新 TOKEN 是否有效
"""

import os
import sys
from linebot import LineBotApi
from linebot.exceptions import InvalidSignatureError, LineBotApiError

def verify_line_token(access_token, channel_secret):
    """驗證 LINE TOKEN 有效性"""
    print("🔍 驗證新 LINE TOKEN...")
    
    try:
        # 1. 測試 Access Token
        line_bot_api = LineBotApi(access_token)
        
        # 2. 獲取 Bot 資訊 (這是最安全的測試方法)
        bot_info = line_bot_api.get_bot_info()
        
        print(f"✅ Access Token 驗證通過")
        print(f"   Bot 名稱: {bot_info.display_name}")
        print(f"   Bot ID: {bot_info.user_id}")
        print(f"   狀態圖片: {bot_info.picture_url}")
        
        # 3. 測試 Channel Secret (格式驗證)
        if len(channel_secret) == 32 and all(c in '0123456789abcdef' for c in channel_secret.lower()):
            print(f"✅ Channel Secret 格式正確")
        else:
            print(f"⚠️ Channel Secret 格式可能有問題")
            
        # 4. 測試配額狀態
        try:
            quota = line_bot_api.get_message_quota()
            print(f"✅ API 配額檢查通過")
            print(f"   類型: {quota.type}")
            print(f"   剩餘: {quota.value}")
        except:
            print(f"📊 無法獲取配額信息 (可能是免費方案)")
            
        return True, bot_info.display_name
        
    except LineBotApiError as e:
        print(f"❌ LINE API 錯誤: {e.status_code} - {e.error.message}")
        return False, str(e)
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        return False, str(e)

def main():
    print("🤖 LINE TOKEN 驗證工具")
    print("=" * 50)
    
    # 獲取新的 TOKEN (從用戶輸入或環境變數)
    new_access_token = input("🔑 請輸入新的 LINE_CHANNEL_ACCESS_TOKEN: ").strip()
    new_channel_secret = input("🔒 請輸入新的 LINE_CHANNEL_SECRET: ").strip()
    
    if not new_access_token or not new_channel_secret:
        print("❌ TOKEN 不能為空")
        return False
        
    # 驗證新 TOKEN
    success, result = verify_line_token(new_access_token, new_channel_secret)
    
    if success:
        print(f"\n🎉 驗證成功！Bot 名稱: {result}")
        print(f"✅ 可以安全地更新到正式環境")
        
        # 生成環境變數設置指令
        print(f"\n📋 Zeabur 環境變數設置:")
        print(f"LINE_CHANNEL_ACCESS_TOKEN = {new_access_token}")
        print(f"LINE_CHANNEL_SECRET = {new_channel_secret}")
        
        return True
    else:
        print(f"\n❌ 驗證失敗: {result}")
        print(f"🚫 請勿更新到正式環境")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)