"""LINE Bot 工具函數和共用實例"""

from simple_config import Config
from src.namecard.core.services.batch_service import BatchManager
from src.namecard.core.services.interaction_service import UserInteractionHandler
from src.namecard.core.services.multi_card_service import MultiCardProcessor
from src.namecard.infrastructure.ai.card_processor import NameCardProcessor
from src.namecard.infrastructure.messaging.line_client import LineBotApiHandler
from src.namecard.infrastructure.storage.notion_client import NotionManager
from src.namecard.utils.pr_creator import PRCreator

# 全域實例（延遲初始化）
_card_processor = None
_notion_manager = None
_batch_manager = None
_pr_creator = None
_multi_card_processor = None
_user_interaction_handler = None
_safe_line_bot = None


def get_card_processor():
    """獲取名片處理器實例"""
    global _card_processor
    if _card_processor is None:
        _card_processor = NameCardProcessor()
    return _card_processor


def get_notion_manager():
    """獲取 Notion 管理器實例"""
    global _notion_manager
    if _notion_manager is None:
        _notion_manager = NotionManager()
    return _notion_manager


def get_batch_manager():
    """獲取批次管理器實例"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchManager()
    return _batch_manager


def get_pr_creator():
    """獲取 PR 創建器實例"""
    global _pr_creator
    if _pr_creator is None:
        _pr_creator = PRCreator()
    return _pr_creator


def get_multi_card_processor():
    """獲取多名片處理器實例"""
    global _multi_card_processor
    if _multi_card_processor is None:
        _multi_card_processor = MultiCardProcessor()
    return _multi_card_processor


def get_user_interaction_handler():
    """獲取用戶交互處理器實例"""
    global _user_interaction_handler
    if _user_interaction_handler is None:
        _user_interaction_handler = UserInteractionHandler()
    return _user_interaction_handler


def get_safe_line_bot():
    """獲取安全 LINE Bot 客戶端實例"""
    global _safe_line_bot
    if _safe_line_bot is None:
        _safe_line_bot = LineBotApiHandler(Config.LINE_CHANNEL_ACCESS_TOKEN)
    return _safe_line_bot


def initialize_all_services():
    """初始化所有服務（用於啟動時預加載）"""
    services = {
        "card_processor": get_card_processor(),
        "notion_manager": get_notion_manager(),
        "batch_manager": get_batch_manager(),
        "pr_creator": get_pr_creator(),
        "multi_card_processor": get_multi_card_processor(),
        "user_interaction_handler": get_user_interaction_handler(),
        "safe_line_bot": get_safe_line_bot(),
    }

    print("✅ 所有處理器初始化成功")
    return services
