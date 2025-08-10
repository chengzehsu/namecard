"""LINE Bot 路由模組"""

from .api_status import create_api_status_blueprint
from .health import create_health_blueprint

__all__ = [
    "create_health_blueprint",
    "create_api_status_blueprint",
]
