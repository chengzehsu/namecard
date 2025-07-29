import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # LINE Bot 設定
    LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

    # Google Gemini API 設定
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = "gemini-2.5-pro"

    # Notion API 設定
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

    @classmethod
    def validate_config(cls):
        """驗證必要的環境變數是否已設定"""
        required_vars = [
            "LINE_CHANNEL_SECRET",
            "LINE_CHANNEL_ACCESS_TOKEN",
            "GOOGLE_API_KEY",
            "NOTION_API_KEY",
            "NOTION_DATABASE_ID",
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing_vars)}")

        return True
