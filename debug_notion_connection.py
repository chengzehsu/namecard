#!/usr/bin/env python3
"""
診斷 Notion 連接問題
"""

import os
import sys
import requests

# 添加路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)

def test_notion_api_directly():
    """直接測試 Notion API"""
    print("🔍 直接測試 Notion API 連接...")
    
    # 這裡需要實際的 API Key 才能測試
    print("💡 由於本地沒有 API Key，無法直接測試")
    print("📋 但可以提供診斷建議")

def analyze_common_notion_issues():
    """分析常見 Notion 問題"""
    print("🔍 分析常見 Notion API 問題...")
    
    print("\n📋 常見問題檢查清單:")
    
    print("\n1️⃣ API Key 格式問題:")
    print("   ✅ 正確格式: secret_xxxxxxxxxx (以 'secret_' 開頭)")
    print("   ❌ 錯誤: 只有部分字符、包含空格、缺少前綴")
    
    print("\n2️⃣ Integration 權限問題:")
    print("   ✅ Integration 需要連接到目標資料庫")
    print("   ✅ 在資料庫頁面點擊 'Share' → 添加您的 Integration")
    print("   ✅ 確保 Integration 有 'Read' 和 'Write' 權限")
    
    print("\n3️⃣ Database ID 問題:")
    print("   ✅ 正確格式: 32位字符 (如: a1b2c3d4e5f67890...)")
    print("   ❌ 錯誤: 包含連字符、URL 格式、頁面 ID")
    
    print("\n4️⃣ API Token 過期:")
    print("   ✅ Notion API Keys 通常不會過期")
    print("   ✅ 但 Integration 可能被刪除或停用")

def provide_fixing_steps():
    """提供修復步驟"""
    print("\n🔧 修復步驟建議:")
    
    print("\n📝 步驟 1: 重新創建 Notion Integration")
    print("   1. 前往 https://www.notion.so/my-integrations")
    print("   2. 點擊 '+ New integration'")
    print("   3. 填寫名稱: '名片管理系統'")
    print("   4. 選擇 Associated workspace")
    print("   5. 點擊 'Submit' 創建")
    print("   6. 複製 'Internal Integration Token' (以 secret_ 開頭)")
    
    print("\n📝 步驟 2: 連接資料庫")
    print("   1. 開啟您的名片資料庫頁面")
    print("   2. 點擊右上角 '...' → 'Share'")
    print("   3. 點擊 'Invite' → 搜尋您的 Integration 名稱")
    print("   4. 選擇 Integration 並給予權限")
    print("   5. 點擊 'Invite'")
    
    print("\n📝 步驟 3: 獲取 Database ID")
    print("   1. 在資料庫頁面複製 URL")
    print("   2. URL 格式: https://notion.so/xxx/DATABASE_ID?v=xxx")
    print("   3. 提取 DATABASE_ID 部分 (32位字符)")
    print("   4. 移除任何連字符 (-)")
    
    print("\n📝 步驟 4: 更新 Zeabur 環境變數")
    print("   1. 前往 Zeabur Dashboard → 您的專案")
    print("   2. 點擊服務 → 'Variables' 標籤")
    print("   3. 更新 NOTION_API_KEY (完整的 secret_xxx)")
    print("   4. 更新 NOTION_DATABASE_ID (32位字符)")
    print("   5. 點擊 'Save' → 'Redeploy'")

def test_zeabur_service():
    """測試 Zeabur 服務狀態"""
    print("\n🔍 測試 Zeabur 服務狀態...")
    
    try:
        response = requests.get("https://namecard-app.zeabur.app/test", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print("📊 當前服務狀態:")
            for service, status in data.items():
                if isinstance(status, dict):
                    success = status.get('success', False)
                    message = status.get('message', status.get('error', 'Unknown'))
                    emoji = "✅" if success else "❌"
                    print(f"   {service}: {emoji} {message}")
                    
                    # 針對 notion 錯誤提供具體建議
                    if service == 'notion' and not success:
                        error_msg = message.lower()
                        if 'invalid' in error_msg or 'unauthorized' in error_msg:
                            print(f"      💡 建議: API Key 可能無效或過期")
                        elif 'not_found' in error_msg:
                            print(f"      💡 建議: Database ID 可能錯誤")
                        elif 'forbidden' in error_msg:
                            print(f"      💡 建議: Integration 沒有資料庫權限")
        else:
            print(f"❌ 服務狀態檢查失敗: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 無法連接到服務: {e}")

def main():
    """主診斷函數"""
    print("🔍 Notion 連接問題診斷")
    print("=" * 50)
    
    test_notion_api_directly()
    analyze_common_notion_issues()
    provide_fixing_steps()
    test_zeabur_service()
    
    print("\n" + "=" * 50)
    print("💡 下一步動作:")
    print("1. 🔄 重新創建 Notion Integration 和 API Key")
    print("2. 📋 確認資料庫權限設置")
    print("3. 🚀 更新 Zeabur 環境變數並重新部署")
    print("4. 🧪 再次測試服務連接")

if __name__ == "__main__":
    main()