"""
簡化配置類 - 用於異步系統
"""

import os

# 載入環境變數文件
try:
    from dotenv import load_dotenv

    load_dotenv()  # 載入 .env 文件
except ImportError:
    pass  # 如果沒有安裝 python-dotenv，忽略


class Config:
    """簡化的配置類"""

    # LINE Bot 配置
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")

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
        # 基礎必要配置
        required_fields = ["GOOGLE_API_KEY", "NOTION_API_KEY", "NOTION_DATABASE_ID"]

        # LINE Bot 特定配置（如果要使用 LINE Bot）
        line_fields = ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"]

        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)

        # 檢查 LINE Bot 配置（如果任一存在，則兩者都必須存在）
        line_token = getattr(cls, "LINE_CHANNEL_ACCESS_TOKEN", "")
        line_secret = getattr(cls, "LINE_CHANNEL_SECRET", "")

        if line_token or line_secret:  # 如果設置了任一個
            for field in line_fields:
                if not getattr(cls, field):
                    missing.append(field)

        if missing:
            print(f"❌ 缺少必要配置: {', '.join(missing)}")
            print(
                "💡 LINE Bot 需要設置: LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET"
            )
            return False

        print("✅ 配置驗證通過")
        return True

    @classmethod
    def show_config(cls):
        """顯示目前配置（隱藏敏感資訊）"""
        print("📋 目前配置:")
        token_status = "[已設置]" if cls.LINE_CHANNEL_ACCESS_TOKEN else "[未設置]"
        print(f"  LINE_CHANNEL_ACCESS_TOKEN: {token_status}")
        print(
            f"  LINE_CHANNEL_SECRET: {'[已設置]' if cls.LINE_CHANNEL_SECRET else '[未設置]'}"
        )
        print(f"  GOOGLE_API_KEY: {'[已設置]' if cls.GOOGLE_API_KEY else '[未設置]'}")
        fallback_status = "[已設置]" if cls.GOOGLE_API_KEY_FALLBACK else "[未設置]"
        print(f"  GOOGLE_API_KEY_FALLBACK: {fallback_status}")
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
