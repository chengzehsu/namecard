#!/usr/bin/env python3
"""
測試環境變數載入問題
"""
import os
import sys
from pathlib import Path

print("🔍 環境變數載入診斷")

# 1. 檢查當前路徑和工作目錄
print(f"\n📍 路徑診斷:")
print(f"__file__: {__file__}")
print(f"當前工作目錄: {os.getcwd()}")
print(f"Python 路徑: {sys.path[:3]}...")  # 只顯示前3個

# 2. 檢查原始環境變數
print(f"\n🔧 原始環境變數:")
env_vars = [
    "TELEGRAM_BOT_TOKEN",
    "GOOGLE_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
]
for var in env_vars:
    value = os.environ.get(var, "")
    if value:
        masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***已設置***"
        print(f"{var}: {masked}")
    else:
        print(f"{var}: ❌ 未設置")

# 3. 模擬 telegram bot main.py 的路徑設置
print(f"\n🛤️  模擬 main.py 路徑設置:")
main_py_path = (
    Path(__file__).parent / "src" / "namecard" / "api" / "telegram_bot" / "main.py"
)
simulated_root = main_py_path.parent.parent.parent.parent.parent
print(f"模擬 root_dir: {simulated_root}")

# 添加到 Python 路徑
if str(simulated_root) not in sys.path:
    sys.path.insert(0, str(simulated_root))
    print(f"✅ 已添加 root_dir 到 Python 路徑")

# 4. 嘗試載入 simple_config
print(f"\n⚙️ 嘗試載入 simple_config:")
try:
    # 重新載入以確保使用最新路徑
    if "simple_config" in sys.modules:
        del sys.modules["simple_config"]

    from simple_config import Config

    print(f"✅ simple_config 載入成功")

    # 檢查 Config 中的值
    print(f"\n📊 Config 中的實際值:")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ 有值' if Config.TELEGRAM_BOT_TOKEN else '❌ 空值'}")
    print(f"GOOGLE_API_KEY: {'✅ 有值' if Config.GOOGLE_API_KEY else '❌ 空值'}")
    print(f"NOTION_API_KEY: {'✅ 有值' if Config.NOTION_API_KEY else '❌ 空值'}")
    print(f"NOTION_DATABASE_ID: {'✅ 有值' if Config.NOTION_DATABASE_ID else '❌ 空值'}")

    # 執行驗證
    print(f"\n🔍 Config.validate() 結果:")
    valid = Config.validate()
    print(f"驗證結果: {'✅ 通過' if valid else '❌ 失敗'}")

    if not valid:
        print(f"\n💡 如果環境變數已設置但 Config 中為空，可能原因:")
        print(f"1. 環境變數設置後沒有重啟服務")
        print(f"2. 變數名稱大小寫不匹配")
        print(f"3. 變數值包含多餘的空格或特殊字符")
        print(f"4. Zeabur 環境變數沒有正確應用到運行時")

except ImportError as e:
    print(f"❌ simple_config 載入失敗: {e}")
    print(f"當前 Python 路徑: {sys.path}")
except Exception as e:
    print(f"❌ Config 處理錯誤: {e}")

# 5. 建議解決方案
print(f"\n💡 建議解決步驟:")
print(f"1. 在 Zeabur Dashboard 中重新檢查環境變數設置")
print(f"2. 確認變數名稱完全匹配（大小寫敏感）")
print(f"3. 重新部署服務確保環境變數生效")
print(f"4. 檢查 Zeabur 服務日誌中的啟動信息")
