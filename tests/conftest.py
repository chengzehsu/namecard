"""
Pytest configuration and shared fixtures for namecard tests
"""
import os
import pytest
from unittest.mock import Mock, patch
import tempfile


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables"""
    test_vars = {
        "LINE_CHANNEL_ACCESS_TOKEN": "test_line_token",
        "LINE_CHANNEL_SECRET": "test_line_secret",
        "GOOGLE_API_KEY": "test_google_key",
        "NOTION_API_KEY": "test_notion_key",
        "NOTION_DATABASE_ID": "test_db_id",
        "GEMINI_MODEL": "gemini-1.5-flash"
    }
    
    # Store original values
    original_values = {}
    for key, value in test_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original values
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_line_bot_api():
    """Mock LINE Bot API"""
    with patch('linebot.LineBotApi') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_webhook_handler():
    """Mock LINE Webhook Handler"""
    with patch('linebot.WebhookHandler') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_gemini_model():
    """Mock Google Gemini AI model"""
    with patch('google.generativeai.GenerativeModel') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '{"name": "張三", "company": "測試公司", "title": "經理"}'
        mock_instance.generate_content.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def mock_notion_client():
    """Mock Notion client"""
    with patch('notion_client.Client') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Mock successful page creation
        mock_instance.pages.create.return_value = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page_id"
        }
        
        yield mock_instance


@pytest.fixture
def sample_line_event():
    """Sample LINE webhook event data"""
    return {
        "type": "message",
        "message": {
            "id": "test_message_id",
            "type": "text",
            "text": "test message"
        },
        "source": {
            "userId": "test_user_id",
            "type": "user"
        },
        "replyToken": "test_reply_token",
        "timestamp": 1234567890
    }


@pytest.fixture
def sample_image_event():
    """Sample LINE image message event"""
    return {
        "type": "message",
        "message": {
            "id": "test_image_id",
            "type": "image"
        },
        "source": {
            "userId": "test_user_id",
            "type": "user"
        },
        "replyToken": "test_reply_token",
        "timestamp": 1234567890
    }


@pytest.fixture
def sample_card_data():
    """Sample extracted name card data"""
    return {
        "name": "張三",
        "company": "測試科技公司",
        "department": "技術部",
        "title": "資深工程師",
        "decision_influence": "中",
        "email": "zhang.san@test.com",
        "phone": "+886912345678",
        "address": "台北市信義區信義路五段7號",
        "contact_source": "名片交換",
        "notes": "專精於軟體開發"
    }


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        # Create a minimal PNG file (1x1 pixel)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        f.write(png_data)
        f.flush()
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except OSError:
        pass


@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    with patch('flask.Flask') as mock:
        mock_instance = Mock()
        mock_instance.test_client.return_value = Mock()
        mock.return_value = mock_instance
        yield mock_instance