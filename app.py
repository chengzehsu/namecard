#!/usr/bin/env python3
"""
LINE Bot 名片管理系統主入口
支援名片掃描 → Gemini AI 識別 → Notion 存儲的完整流程
"""

import os
import sys
from datetime import datetime

# 添加 src 目錄到 Python 路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def log_startup_info():
    """顯示啟動資訊"""
    print("=" * 60)
    print("🤖 LINE Bot 名片管理系統")
    print("=" * 60)
    print(f"📅 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔄 功能流程:")
    print("  📱 LINE 掃描名片 → 🤖 Gemini AI 識別 → 📊 Notion 存儲")
    print()
    print("✨ 支援功能:")
    print("  • 單張名片識別")
    print("  • 批次處理模式")
    print("  • 多名片檢測")
    print("  • 地址正規化")
    print("  • API 備用機制")
    print()


def main():
    """主函數"""
    try:
        log_startup_info()

        # 導入並啟動 LINE Bot
        print("📋 正在載入 LINE Bot 模組...")
        from src.namecard.api.line_bot.main import app as line_app

        print("✅ LINE Bot 模組載入成功")

        # 配置檢查
        from simple_config import Config

        print("🔧 驗證配置...")

        if not Config.validate():
            print("❌ 配置驗證失敗，請檢查環境變數")
            print("💡 必要環境變數:")
            print("   - LINE_CHANNEL_ACCESS_TOKEN")
            print("   - LINE_CHANNEL_SECRET")
            print("   - GOOGLE_API_KEY")
            print("   - NOTION_API_KEY")
            print("   - NOTION_DATABASE_ID")
            sys.exit(1)

        print("✅ 配置驗證通過")

        # 獲取端口配置
        port = int(os.environ.get("PORT", 5002))
        debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

        print(f"🚀 LINE Bot 啟動中...")
        print(f"   端口: {port}")
        print(f"   除錯模式: {debug_mode}")
        print(f"   健康檢查: http://localhost:{port}/health")
        print(f"   Webhook: http://localhost:{port}/callback")
        print()
        print("⚡ 系統已就緒，等待 LINE 用戶訊息...")
        print("=" * 60)

        # 啟動 Flask 應用
        line_app.run(
            host="0.0.0.0",
            port=port,
            debug=debug_mode,
            use_reloader=False,  # 生產環境關閉重載器
        )

    except ImportError as e:
        print(f"❌ 模組導入失敗: {e}")
        print(f"📁 當前目錄: {os.getcwd()}")
        print(f"🐍 Python 路徑: {sys.path}")
        print("\n💡 解決建議:")
        print("   1. 檢查 src/namecard/ 目錄結構")
        print("   2. 確認所有必要的 Python 套件已安裝")
        print("   3. 執行 pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"❌ 系統啟動失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
