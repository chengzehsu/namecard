#!/usr/bin/env python3
"""
快速檢查 Zeabur 部署狀態
"""
import os
import sys

# 添加路徑以支持不同的部署路徑
possible_paths = ["/opt/zeabur", "/opt/zeabur/src", ".", "./src"]

for path in possible_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

print("🔍 Zeabur 部署狀態檢查")
print(f"工作目錄: {os.getcwd()}")

# 檢查環境變數
required_vars = [
    "TELEGRAM_BOT_TOKEN",
    "GOOGLE_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
]
print(f"\n📋 環境變數檢查:")

env_status = {}
for var in required_vars:
    value = os.getenv(var)
    if value:
        # 只顯示前後幾個字符，保護隱私
        masked = f"{value[:6]}...{value[-4:]}" if len(value) > 10 else "***"
        print(f"✅ {var}: {masked}")
        env_status[var] = True
    else:
        print(f"❌ {var}: 未設置")
        env_status[var] = False

# 檢查配置類
print(f"\n⚙️ 配置模組檢查:")
try:
    from simple_config import Config

    print("✅ simple_config 導入成功")

    # 檢查配置驗證
    valid = Config.validate()
    print(f"{'✅' if valid else '❌'} 配置驗證: {'通過' if valid else '失敗'}")

    # 顯示實際配置值狀態
    print(f"\n📊 實際配置狀態:")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ 有值' if Config.TELEGRAM_BOT_TOKEN else '❌ 空值'}")
    print(f"GOOGLE_API_KEY: {'✅ 有值' if Config.GOOGLE_API_KEY else '❌ 空值'}")
    print(f"NOTION_API_KEY: {'✅ 有值' if Config.NOTION_API_KEY else '❌ 空值'}")
    print(f"NOTION_DATABASE_ID: {'✅ 有值' if Config.NOTION_DATABASE_ID else '❌ 空值'}")

except ImportError as e:
    print(f"❌ simple_config 導入失敗: {e}")
except Exception as e:
    print(f"❌ 配置檢查錯誤: {e}")

# 總結
all_set = all(env_status.values())
print(f"\n🎯 總結:")
if all_set:
    print("✅ 環境變數設置完整，請檢查其他部署問題")
else:
    print("❌ 環境變數設置不完整")
    print("💡 請前往 Zeabur Dashboard 設置缺失的環境變數")

print(f"\n📍 如果環境變數都已設置但仍無法讀取，可能原因：")
print(f"1. Zeabur 服務沒有正確重新部署")
print(f"2. 環境變數設置在錯誤的服務上")
print(f"3. 變數名稱拼寫錯誤")
print(f"4. 服務重啟後環境變數沒有生效")
