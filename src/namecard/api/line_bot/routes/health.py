"""健康檢查路由"""

from flask import Blueprint


def create_health_blueprint(notion_manager, card_processor):
    """創建健康檢查藍圖"""
    health_bp = Blueprint("health", __name__)

    @health_bp.route("/health", methods=["GET"])
    def health_check():
        """健康檢查端點"""
        return {"status": "healthy", "message": "LINE Bot is running"}

    @health_bp.route("/test", methods=["GET"])
    def test_services():
        """測試各服務連接狀態"""
        results = {}

        # 測試 Notion 連接
        notion_test = notion_manager.test_connection()
        results["notion"] = notion_test

        # 測試 Gemini (簡單檢查)
        try:
            # 檢查是否能創建處理器實例
            card_processor.__class__()
            results["gemini"] = {"success": True, "message": "Gemini 連接正常"}
        except Exception as e:
            results["gemini"] = {"success": False, "error": str(e)}

        return results

    return health_bp
