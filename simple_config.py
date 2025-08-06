"""
簡化配置類 - 用於異步系統
"""

import os
from typing import Optional


class Config:
    """簡化的配置類"""

    # LINE Bot 配置
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")

    # Telegram Bot 配置
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Google AI 配置
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_API_KEY_FALLBACK: str = os.getenv("GOOGLE_API_KEY_FALLBACK", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    # Notion 配置
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")

    # 效能配置
    MAX_CONCURRENT: int = int(os.getenv("MAX_CONCURRENT", "20"))
    CACHE_MEMORY_MB: int = int(os.getenv("CACHE_MEMORY_MB", "200"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    @classmethod
    def validate(cls) -> bool:
        """驗證必要的配置是否存在"""
        required_fields = ["GOOGLE_API_KEY", "NOTION_API_KEY", "NOTION_DATABASE_ID"]

        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)

        if missing:
            print(f"❌ 缺少必要配置: {', '.join(missing)}")
            return False

        print("✅ 配置驗證通過")
        return True

    @classmethod
    def show_config(cls):
        """顯示目前配置（隱藏敏感資訊）"""
        print("📋 目前配置:")
        print(
            f"  LINE_CHANNEL_ACCESS_TOKEN: {'[已設置]' if cls.LINE_CHANNEL_ACCESS_TOKEN else '[未設置]'}"
        )
        print(
            f"  LINE_CHANNEL_SECRET: {'[已設置]' if cls.LINE_CHANNEL_SECRET else '[未設置]'}"
        )
        print(
            f"  TELEGRAM_BOT_TOKEN: {'[已設置]' if cls.TELEGRAM_BOT_TOKEN else '[未設置]'}"
        )
        print(f"  GOOGLE_API_KEY: {'[已設置]' if cls.GOOGLE_API_KEY else '[未設置]'}")
        print(
            f"  GOOGLE_API_KEY_FALLBACK: {'[已設置]' if cls.GOOGLE_API_KEY_FALLBACK else '[未設置]'}"
        )
        print(f"  GEMINI_MODEL: {cls.GEMINI_MODEL}")
        print(f"  NOTION_API_KEY: {'[已設置]' if cls.NOTION_API_KEY else '[未設置]'}")
        print(
            f"  NOTION_DATABASE_ID: {'[已設置]' if cls.NOTION_DATABASE_ID else '[未設置]'}"
        )
        print(f"  MAX_CONCURRENT: {cls.MAX_CONCURRENT}")
        print(f"  CACHE_MEMORY_MB: {cls.CACHE_MEMORY_MB}")
        print(f"  WORKERS: {cls.WORKERS}")


if __name__ == "__main__":
    Config.show_config()
    Config.validate()
