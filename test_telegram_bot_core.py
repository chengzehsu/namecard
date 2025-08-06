#!/usr/bin/env python3
"""
Telegram Bot 核心功能測試套件
測試 src/namecard/api/telegram_bot/main.py 的核心邏輯
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# 添加項目路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "./"))

# 測試標記
pytestmark = [pytest.mark.unit, pytest.mark.telegram_bot]


class TestTelegramBotCore:
    """Telegram Bot 核心功能測試"""

    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """設置測試環境"""
        # Mock 環境變數
        self.env_vars = {
            "TELEGRAM_BOT_TOKEN": "test_token_123",
            "GOOGLE_API_KEY": "test_google_key",
            "NOTION_API_KEY": "test_notion_key",
            "NOTION_DATABASE_ID": "test_database_id",
            "PORT": "5003",
        }

        with patch.dict(os.environ, self.env_vars):
            yield

    def test_flask_app_creation(self):
        """測試 Flask 應用創建"""
        with patch("src.namecard.api.telegram_bot.main.Config") as mock_config:
            mock_config.validate.return_value = True
            mock_config.TELEGRAM_BOT_TOKEN = "test_token"

            # 重新導入模組以觸發初始化
            import importlib

            if "src.namecard.api.telegram_bot.main" in sys.modules:
                importlib.reload(sys.modules["src.namecard.api.telegram_bot.main"])
            else:
                from src.namecard.api.telegram_bot import main

            # 驗證 Flask 應用存在
            assert hasattr(main, "flask_app")
            assert main.flask_app is not None

    def test_config_validation_success(self):
        """測試配置驗證成功"""
        with patch("src.namecard.api.telegram_bot.main.Config") as mock_config:
            mock_config.TELEGRAM_BOT_TOKEN = "valid_token"
            mock_config.validate.return_value = True

            # 重新導入以觸發配置檢查
            import importlib

            if "src.namecard.api.telegram_bot.main" in sys.modules:
                module = importlib.reload(
                    sys.modules["src.namecard.api.telegram_bot.main"]
                )
            else:
                from src.namecard.api.telegram_bot import main as module

            # 驗證配置被標記為有效
            # 這需要檢查模組級別的 config_valid 變數
            assert hasattr(module, "config_valid")

    def test_config_validation_failure(self):
        """測試配置驗證失敗"""
        with patch("src.namecard.api.telegram_bot.main.Config") as mock_config:
            mock_config.TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
            mock_config.validate.return_value = False
            mock_config.show_config = Mock()

            with patch("builtins.print") as mock_print:
                # 重新導入以觸發配置檢查
                import importlib

                if "src.namecard.api.telegram_bot.main" in sys.modules:
                    importlib.reload(sys.modules["src.namecard.api.telegram_bot.main"])
                else:
                    from src.namecard.api.telegram_bot import main

                # 驗證錯誤訊息被打印
                mock_print.assert_called()
                mock_config.show_config.assert_called()

    def test_log_message_function(self):
        """測試統一日誌函數"""
        from src.namecard.api.telegram_bot.main import log_message

        with patch("builtins.print") as mock_print:
            with patch("sys.stdout.flush") as mock_flush:
                result = log_message("Test message", "INFO")

                # 驗證日誌格式
                assert "INFO: Test message" in result
                assert datetime.now().strftime("%Y-%m-%d") in result

                # 驗證調用了 print 和 flush
                mock_print.assert_called()
                mock_flush.assert_called()

    @pytest.mark.asyncio
    async def test_start_command_handler(self):
        """測試 /start 命令處理"""
        # 這需要導入實際的處理器函數
        try:
            from src.namecard.api.telegram_bot.main import start
        except ImportError:
            pytest.skip("無法導入 start 函數")

        # Mock Telegram Update 和 Context
        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        # 調用處理器
        await start(mock_update, mock_context)

        # 驗證回覆被發送
        mock_update.message.reply_text.assert_called_once()

        # 檢查回覆內容包含歡迎訊息
        call_args = mock_update.message.reply_text.call_args
        reply_text = call_args[0][0]
        assert "歡迎" in reply_text or "Welcome" in reply_text

    @pytest.mark.asyncio
    async def test_help_command_handler(self):
        """測試 /help 命令處理"""
        try:
            from src.namecard.api.telegram_bot.main import help_command
        except ImportError:
            pytest.skip("無法導入 help_command 函數")

        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await help_command(mock_update, mock_context)

        # 驗證回覆被發送
        mock_update.message.reply_text.assert_called_once()

        # 檢查回覆內容包含幫助訊息
        call_args = mock_update.message.reply_text.call_args
        reply_text = call_args[0][0]
        assert (
            "使用說明" in reply_text
            or "help" in reply_text.lower()
            or "指令" in reply_text
            or "command" in reply_text.lower()
        )

    @pytest.mark.asyncio
    async def test_batch_command_handler(self):
        """測試 /batch 命令處理"""
        try:
            from src.namecard.api.telegram_bot.main import batch_command
        except ImportError:
            pytest.skip("無法導入 batch_command 函數")

        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        with patch(
            "src.namecard.api.telegram_bot.main.batch_manager"
        ) as mock_batch_manager:
            mock_batch_manager.start_batch.return_value = True

            await batch_command(mock_update, mock_context)

            # 驗證批次管理器被調用
            mock_batch_manager.start_batch.assert_called_once_with(12345)

            # 驗證回覆被發送
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_image_message_handler(self):
        """測試圖片訊息處理"""
        try:
            from src.namecard.api.telegram_bot.main import handle_image
        except ImportError:
            pytest.skip("無法導入 handle_image 函數")

        # Mock 圖片訊息
        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = [Mock()]  # 模擬圖片數組
        mock_update.message.photo[-1].file_id = "test_file_id"
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()
        mock_context.bot.get_file = AsyncMock()

        # Mock 文件下載
        mock_file = Mock()
        mock_file.download_to_drive = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch(
                "src.namecard.api.telegram_bot.main.get_ultra_fast_processor"
            ) as mock_processor:
                mock_processor.return_value.process_image.return_value = {
                    "success": True,
                    "results": [{"name": "測試", "company": "公司"}],
                }

                await handle_image(mock_update, mock_context)

                # 驗證圖片被下載
                mock_context.bot.get_file.assert_called_once()

                # 驗證處理器被調用
                mock_processor.assert_called_once()

    def test_flask_webhook_endpoint(self):
        """測試 Flask webhook 端點"""
        from src.namecard.api.telegram_bot.main import flask_app

        with flask_app.test_client() as client:
            # 測試健康檢查端點
            response = client.get("/health")
            assert response.status_code == 200

            # 測試根端點
            response = client.get("/")
            assert response.status_code == 200

    def test_flask_webhook_post(self):
        """測試 Flask webhook POST 請求"""
        from src.namecard.api.telegram_bot.main import flask_app

        with flask_app.test_client() as client:
            # Mock Telegram webhook 數據
            webhook_data = {
                "update_id": 123,
                "message": {
                    "message_id": 456,
                    "from": {"id": 789, "first_name": "Test"},
                    "chat": {"id": 789, "type": "private"},
                    "date": 1234567890,
                    "text": "/start",
                },
            }

            with patch("src.namecard.api.telegram_bot.main.telegram_app") as mock_app:
                mock_app.process_update = AsyncMock()

                response = client.post(
                    "/telegram-webhook",
                    json=webhook_data,
                    content_type="application/json",
                )

                # Webhook 應該接受請求
                assert response.status_code in [200, 202]


class TestTelegramBotErrorHandling:
    """Telegram Bot 錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_invalid_image_handling(self):
        """測試無效圖片處理"""
        try:
            from src.namecard.api.telegram_bot.main import handle_image
        except ImportError:
            pytest.skip("無法導入 handle_image 函數")

        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = []  # 空圖片數組
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()

        await handle_image(mock_update, mock_context)

        # 應該發送錯誤訊息
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        error_message = call_args[0][0]
        assert "錯誤" in error_message or "error" in error_message.lower()

    @pytest.mark.asyncio
    async def test_api_quota_exceeded_handling(self):
        """測試 API 配額超限處理"""
        try:
            from src.namecard.api.telegram_bot.main import handle_image
        except ImportError:
            pytest.skip("無法導入 handle_image 函數")

        mock_update = Mock()
        mock_update.effective_chat.id = 12345
        mock_update.message.photo = [Mock()]
        mock_update.message.photo[-1].file_id = "test_file_id"
        mock_update.message.reply_text = AsyncMock()

        mock_context = Mock()
        mock_context.bot.get_file = AsyncMock()
        mock_file = Mock()
        mock_file.download_to_drive = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        with patch(
            "src.namecard.api.telegram_bot.main.get_ultra_fast_processor"
        ) as mock_processor:
            # 模擬 API 配額超限
            mock_processor.return_value.process_image.side_effect = Exception(
                "Quota exceeded"
            )

            await handle_image(mock_update, mock_context)

            # 應該發送適當的錯誤訊息
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args
            error_message = call_args[0][0]
            assert (
                "配額" in error_message
                or "quota" in error_message.lower()
                or "錯誤" in error_message
                or "error" in error_message.lower()
            )


class TestTelegramBotPerformance:
    """Telegram Bot 性能測試"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """測試並發訊息處理性能"""
        try:
            from src.namecard.api.telegram_bot.main import start
        except ImportError:
            pytest.skip("無法導入 start 函數")

        # 創建多個並發請求
        tasks = []
        for i in range(10):
            mock_update = Mock()
            mock_update.effective_chat.id = 12345 + i
            mock_update.message.reply_text = AsyncMock()

            mock_context = Mock()

            task = asyncio.create_task(start(mock_update, mock_context))
            tasks.append(task)

        # 等待所有任務完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 驗證沒有異常
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"並發處理失敗: {result}")

    @pytest.mark.performance
    def test_memory_usage_under_load(self):
        """測試負載下的記憶體使用"""
        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # 模擬高負載
            from src.namecard.api.telegram_bot.main import log_message

            for i in range(1000):
                log_message(f"Test message {i}", "INFO")

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # 記憶體增長不應該超過 50MB
            assert (
                memory_increase < 50 * 1024 * 1024
            ), f"記憶體增長過多: {memory_increase} bytes"

        except ImportError:
            pytest.skip("psutil 不可用，跳過記憶體測試")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-m", "not performance"])
