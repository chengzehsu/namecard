#!/usr/bin/env python3
"""
Telegram Bot 主要入口點
支援新的重構架構
"""

import os
import sys

# 添加根目錄和 src 目錄到 Python 路徑
root_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, root_dir)
sys.path.insert(0, src_dir)


def main():
    """主函數"""
    try:
        # 導入並運行 Telegram Bot
        from src.namecard.api.telegram_bot.main import flask_app as app

        # 獲取環境變數
        port = int(os.environ.get("PORT", 5003))

        # 運行 Flask 應用
        app.run(host="0.0.0.0", port=port, debug=False)

    except ImportError as e:
        print(f"❌ 導入錯誤: {e}")
        print(f"當前工作目錄: {os.getcwd()}")
        print(f"Python 路徑: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
