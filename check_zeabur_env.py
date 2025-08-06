#!/usr/bin/env python3
"""
檢查 Zeabur 環境變數的診斷腳本
用於驗證環境變數是否正確設置並可被讀取
"""

import os
import sys

print("=== Zeabur 環境變數診斷 ===")
print(f"當前工作目錄: {os.getcwd()}")
print(f"Python 版本: {sys.version}")

# 檢查所有環境變數
print("\n=== 所有環境變數 ===")
all_env_vars = dict(os.environ)
sensitive_keys = ["TOKEN", "KEY", "SECRET", "API"]

for key, value in sorted(all_env_vars.items()):
    # 隱藏敏感信息
    if any(sensitive in key.upper() for sensitive in sensitive_keys):
        if value:
            masked_value = (
                value[:8] + "..." + value[-4:] if len(value) > 12 else "***設置***"
            )
            print(f"{key}: {masked_value}")
        else:
            print(f"{key}: ❌ 空值")
    else:
        print(f"{key}: {value}")

print("\n=== 必要環境變數檢查 ===")
required_vars = {
    "TELEGRAM_BOT_TOKEN": "Telegram Bot API Token",
    "GOOGLE_API_KEY": "Google Gemini AI API Key",
    "NOTION_API_KEY": "Notion Integration API Key",
    "NOTION_DATABASE_ID": "Notion Database ID",
}

all_good = True
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: 已設置 ({description})")
    else:
        print(f"❌ {var}: 未設置 ({description})")
        all_good = False

print(f"\n=== 整體狀態 ===")
if all_good:
    print("✅ 所有必要環境變數都已正確設置！")

    # 測試配置讀取
    try:
        sys.path.insert(0, "/opt/zeabur/src")
        sys.path.insert(0, "/opt/zeabur")
        from simple_config import Config

        print("✅ Config 類可正常導入")

        valid = Config.validate()
        print(f"✅ Config 驗證結果: {'通過' if valid else '失敗'}")

    except Exception as e:
        print(f"⚠️  Config 驗證錯誤: {e}")

else:
    print("❌ 存在缺失的環境變數，請檢查 Zeabur 設置")
    print("\n💡 解決方案：")
    print("1. 前往 Zeabur Dashboard > 你的專案 > 服務設置")
    print("2. 找到 'Environment Variables' 或 'Variables' 標籤")
    print("3. 確保以下變數都已設置：")
    for var, desc in required_vars.items():
        if not os.getenv(var):
            print(f"   - {var}")
    print("4. 設置完成後點擊 'Redeploy' 重新部署")

print(f"\n=== 部署資訊 ===")
print(f"PORT: {os.getenv('PORT', '未設置')}")
print(f"PYTHON_VERSION: {os.getenv('PYTHON_VERSION', '未設置')}")
print(f"FLASK_ENV: {os.getenv('FLASK_ENV', '未設置')}")
print(f"SERVICE_TYPE: {os.getenv('SERVICE_TYPE', '未設置')}")
