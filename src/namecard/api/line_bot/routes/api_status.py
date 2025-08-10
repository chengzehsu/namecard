"""API 狀態路由"""

from datetime import datetime

from flask import Blueprint


def create_api_status_blueprint(safe_line_bot):
    """創建 API 狀態藍圖"""
    api_status_bp = Blueprint("api_status", __name__)

    @api_status_bp.route("/api-status", methods=["GET"])
    def api_status():
        """LINE Bot API 狀態監控端點"""
        status_report = safe_line_bot.get_status_report()

        # 添加詳細的狀態信息
        detailed_status = {
            "timestamp": datetime.now().isoformat(),
            "line_bot_api": {
                "operational": status_report["is_operational"],
                "quota_exceeded": status_report["quota_exceeded"],
                "quota_reset_time": status_report["quota_reset_time"],
                "error_statistics": status_report["error_statistics"],
            },
            "service_status": {
                "healthy": not status_report["quota_exceeded"],
                "degraded_service": status_report["quota_exceeded"],
                "fallback_mode": status_report["quota_exceeded"],
            },
            "recommendations": [],
        }

        # 基於狀態提供建議
        if status_report["quota_exceeded"]:
            detailed_status["recommendations"].extend(
                [
                    "LINE Bot API 配額已達上限",
                    "考慮升級到付費方案",
                    "或等待下個月配額重置",
                    "目前系統運行在降級模式",
                ]
            )
        elif sum(status_report["error_statistics"].values()) > 10:
            detailed_status["recommendations"].extend(
                [
                    "檢測到較多 API 錯誤",
                    "建議檢查網路連接狀況",
                    "或聯繫 LINE 客服確認服務狀態",
                ]
            )
        else:
            detailed_status["recommendations"].append("系統運行正常")

        return detailed_status

    return api_status_bp
