"""核心服務層 - 統一的服務接口和實現"""

from .address_service import AddressNormalizer
from .base_service import (
    BaseService,
    BatchManagerInterface,
    CardProcessorInterface,
    MessageClientInterface,
    StorageInterface,
)
from .batch_service import BatchManager
from .interaction_service import UserInteractionHandler
from .multi_card_service import MultiCardProcessor

# from .session_service import SessionManager  # 暫時註解，該類別不存在

__all__ = [
    # 基礎接口
    "BaseService",
    "CardProcessorInterface",
    "StorageInterface",
    "BatchManagerInterface",
    "MessageClientInterface",
    # 服務實現
    "AddressNormalizer",
    "BatchManager",
    "UserInteractionHandler",
    "MultiCardProcessor",
    # "SessionManager",  # 暫時註解
]
