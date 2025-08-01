# 🔧 名片管理 LINE Bot 代碼重構計劃

## 📊 當前狀況分析

### ❌ **主要問題**
1. **根目錄混亂**: 22 個 Python 文件散佈在根目錄
2. **職責不清**: 業務邏輯、API 處理、配置管理混雜
3. **類型缺失**: 缺乏類型注解，降低代碼可讀性
4. **同步瓶頸**: AI 處理可能導致 LINE Bot 超時
5. **錯誤處理**: 過度使用通用 Exception
6. **測試分散**: 測試文件散佈在多個位置

### ✅ **現有優勢**
- 功能完整：多名片檢測、批次處理、地址正規化
- 錯誤處理：基本的 try-catch 機制
- 模組化：合理的功能分離
- CI/CD：完整的 GitHub Actions 流程

## 🎯 重構目標

### 🏗️ **架構重組**
- 實施分層架構（API → Service → Infrastructure）
- 依賴注入和接口抽象
- 統一錯誤處理和日誌系統
- 異步處理提升性能

### 📁 **目錄結構優化**
- 清理根目錄，按功能分類
- 統一測試結構
- 分離部署配置
- 文檔和配置組織

### 🚀 **代碼品質提升**
- 添加完整類型注解
- 實施 Python 最佳實踐
- 提升測試覆蓋率
- 性能和安全優化

## 📋 重構實施計劃

## Phase 1: 基礎架構設置 🏗️

### 1.1 建立新目錄結構
```bash
# 使用 backend-architect 設計的目錄結構
namecard/
├── app/                    # 核心應用程式碼
│   ├── core/              # 業務邏輯核心
│   │   ├── interfaces/    # 接口定義
│   │   ├── services/      # 服務層
│   │   ├── models/        # 資料模型
│   │   └── utils/         # 工具類
│   ├── api/               # API 層
│   │   ├── controllers/   # 控制器
│   │   ├── middleware/    # 中間件
│   │   └── schemas/       # API 結構
│   └── infrastructure/    # 基礎設施層
│       ├── external_apis/ # 外部 API
│       ├── persistence/   # 持久化
│       └── monitoring/    # 監控
├── config/                # 配置管理
├── tests/                 # 統一測試結構
├── deployment/            # 部署配置
├── docs/                  # 文檔
└── requirements/          # 依賴管理
```

### 1.2 設置依賴注入容器
```python
# app/core/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()
    
    # 外部服務
    line_bot_client = providers.Singleton(LineBotClient)
    gemini_client = providers.Singleton(GeminiClient)
    notion_client = providers.Singleton(NotionClient)
    
    # 服務層
    card_processing_service = providers.Factory(CardProcessingService)
    batch_service = providers.Factory(BatchService)
    user_interaction_service = providers.Factory(UserInteractionService)
```

### 1.3 定義核心接口
```python
# app/core/interfaces/ai_processor.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class AIProcessorInterface(ABC):
    @abstractmethod
    async def process_single_card(self, image_data: bytes) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def process_multiple_cards(self, image_data: bytes) -> List[Dict[str, Any]]:
        pass
```

## Phase 2: 配置和基礎設施重構 ⚙️

### 2.1 重構配置系統
```python
# config/base.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"  
    PRODUCTION = "production"

@dataclass
class Config:
    # LINE Bot Configuration
    line_channel_secret: str
    line_channel_access_token: str
    
    # AI Configuration  
    google_api_key: str
    google_api_key_fallback: Optional[str]
    gemini_model: str = "gemini-2.5-pro"
    
    # Storage Configuration
    notion_api_key: str
    notion_database_id: str
    
    # Application Settings
    environment: Environment = Environment.DEVELOPMENT
    port: int = 5002
    session_timeout_minutes: int = 10
    
    @classmethod
    def from_env(cls) -> 'Config':
        # 環境變數驗證和載入邏輯
        pass
```

### 2.2 統一日誌系統
```python
# app/core/utils/logger.py
import logging
from contextlib import contextmanager

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    @contextmanager
    def operation(self, operation_name: str):
        self.logger.info(f"🚀 Starting {operation_name}")
        try:
            yield
            self.logger.info(f"✅ Completed {operation_name}")
        except Exception as e:
            self.logger.error(f"❌ Failed {operation_name}: {str(e)}")
            raise
```

### 2.3 自定義異常體系
```python
# app/core/utils/exceptions.py
from enum import Enum

class ErrorCode(Enum):
    AI_PROCESSING_FAILED = "AI_001"
    NOTION_API_ERROR = "NOTION_001"
    LINE_API_ERROR = "LINE_001"
    VALIDATION_ERROR = "VALIDATION_001"

class BusinessException(Exception):
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
```

## Phase 3: 服務層重構 🔧

### 3.1 名片處理服務重構
```python
# app/core/services/card_processing/multi_card_service.py
from typing import Dict, List, Any
from ..interfaces.ai_processor import AIProcessorInterface
from ..models.business_card import BusinessCard, CardQuality

class MultiCardService:
    def __init__(
        self, 
        ai_processor: AIProcessorInterface,
        storage_service: StorageServiceInterface,
        user_interaction_service: UserInteractionService,
        logger: StructuredLogger
    ):
        self.ai_processor = ai_processor
        self.storage_service = storage_service
        self.user_interaction_service = user_interaction_service
        self.logger = logger
    
    async def process_multiple_cards(
        self, 
        image_data: bytes, 
        user_id: str
    ) -> Dict[str, Any]:
        with self.logger.operation("multi-card processing"):
            # 1. AI 識別多張名片
            cards_data = await self.ai_processor.process_multiple_cards(image_data)
            
            # 2. 轉換為業務模型
            cards = [BusinessCard.from_dict(data) for data in cards_data]
            
            # 3. 品質評估
            quality_assessment = await self._assess_cards_quality(cards)
            
            # 4. 決策邏輯
            if quality_assessment.requires_user_choice:
                return await self.user_interaction_service.create_choice_session(
                    user_id, cards, quality_assessment
                )
            
            # 5. 自動處理高品質名片
            return await self._auto_process_cards(cards)
    
    async def _assess_cards_quality(
        self, 
        cards: List[BusinessCard]
    ) -> CardQualityAssessment:
        # 品質評估邏輯
        pass
```

### 3.2 批次處理服務重構
```python
# app/core/services/batch_service.py
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class BatchSession:
    user_id: str
    start_time: datetime = field(default_factory=datetime.now)
    processed_cards: List[BusinessCard] = field(default_factory=list)
    failed_cards: List[Dict] = field(default_factory=list)
    is_active: bool = True

class BatchService:
    def __init__(self, session_timeout_minutes: int = 10):
        self._sessions: Dict[str, BatchSession] = {}
        self._lock = threading.RLock()
        self._timeout = timedelta(minutes=session_timeout_minutes)
    
    @contextmanager
    def _session_lock(self, user_id: str):
        with self._lock:
            yield self._sessions.get(user_id)
    
    async def start_batch_mode(self, user_id: str) -> Dict[str, Any]:
        with self._session_lock(user_id):
            self._sessions[user_id] = BatchSession(user_id=user_id)
            return {"success": True, "message": "批次模式已啟動"}
```

## Phase 4: API 層重構 🌐

### 4.1 控制器重構
```python
# app/api/controllers/webhook_controller.py
from flask import request, jsonify
from linebot.models import MessageEvent, TextMessage, ImageMessage

class WebhookController:
    def __init__(
        self,
        card_service: CardProcessingService,
        batch_service: BatchService,
        user_interaction_service: UserInteractionService,
        logger: StructuredLogger
    ):
        self.card_service = card_service
        self.batch_service = batch_service
        self.user_interaction_service = user_interaction_service
        self.logger = logger
    
    async def handle_message_event(self, event: MessageEvent) -> Dict[str, Any]:
        user_id = event.source.user_id
        
        if isinstance(event.message, TextMessage):
            return await self._handle_text_message(event.message.text, user_id, event.reply_token)
        elif isinstance(event.message, ImageMessage):
            return await self._handle_image_message(event.message, user_id, event.reply_token)
        
        return {"status": "unsupported_message_type"}
    
    async def _handle_image_message(
        self, 
        message: ImageMessage, 
        user_id: str, 
        reply_token: str
    ) -> Dict[str, Any]:
        with self.logger.operation(f"image processing for user {user_id}"):
            # 獲取圖片數據
            image_data = self._get_image_content(message.id)
            
            # 檢查批次模式
            if self.batch_service.is_batch_mode(user_id):
                return await self._process_batch_image(image_data, user_id, reply_token)
            else:
                return await self._process_single_image(image_data, user_id, reply_token)
```

### 4.2 中間件實作
```python
# app/api/middleware/logging_middleware.py
from functools import wraps
from flask import request, g
import time

def log_requests(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        g.request_id = str(uuid.uuid4())
        
        logger.info(f"Request started: {request.method} {request.path}")
        
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Request completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed in {duration:.2f}s: {str(e)}")
            raise
    
    return decorated_function
```

## Phase 5: 基礎設施層重構 🏭

### 5.1 外部 API 整合重構
```python
# app/infrastructure/external_apis/gemini_client.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class GeminiClient(AIProcessorInterface):
    def __init__(
        self, 
        api_key: str, 
        fallback_key: Optional[str] = None,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        self.primary_client = self._create_client(api_key)
        self.fallback_client = self._create_client(fallback_key) if fallback_key else None
        self.executor = executor or ThreadPoolExecutor(max_workers=3)
    
    async def process_single_card(self, image_data: bytes) -> Dict[str, Any]:
        """異步處理單張名片"""
        loop = asyncio.get_event_loop()
        
        try:
            return await loop.run_in_executor(
                self.executor,
                self._process_with_primary_api,
                image_data
            )
        except QuotaExceededException:
            if self.fallback_client:
                return await loop.run_in_executor(
                    self.executor,
                    self._process_with_fallback_api,
                    image_data
                )
            raise AIProcessingError("所有 API 配額已用完")
```

### 5.2 快取和會話管理
```python
# app/infrastructure/persistence/session_store.py
from typing import Optional, Dict, Any
import json
import time

class InMemorySessionStore:
    def __init__(self, default_ttl: int = 300):  # 5 minutes
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl: Dict[str, float] = {}
        self._default_ttl = default_ttl
    
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        self._store[key] = value
        self._ttl[key] = time.time() + (ttl or self._default_ttl)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._store:
            return None
        
        if time.time() > self._ttl[key]:
            self._cleanup_expired(key)
            return None
        
        return self._store[key]
```

## Phase 6: 資料模型和驗證 📋

### 6.1 業務模型定義
```python
# app/core/models/business_card.py
from pydantic import BaseModel, validator, Field
from typing import Optional
from enum import Enum

class DecisionInfluence(Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class CardQuality(Enum):
    EXCELLENT = "excellent"  # 信心度 > 0.9
    GOOD = "good"           # 信心度 > 0.7
    FAIR = "fair"           # 信心度 > 0.5
    POOR = "poor"           # 信心度 <= 0.5

class BusinessCard(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    decision_influence: Optional[DecisionInfluence] = None
    contact_source: str = Field(default="名片交換")
    notes: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality: CardQuality = Field(default=CardQuality.FAIR)
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def clean_phone(cls, v):
        if v:
            # 清理電話號碼格式
            return ''.join(filter(str.isdigit, v))
        return v
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusinessCard':
        # 從 AI 響應數據創建 BusinessCard 實例
        confidence = data.get('confidence_score', 0.0)
        
        return cls(
            **data,
            quality=cls._determine_quality(confidence)
        )
    
    @staticmethod
    def _determine_quality(confidence: float) -> CardQuality:
        if confidence > 0.9:
            return CardQuality.EXCELLENT
        elif confidence > 0.7:
            return CardQuality.GOOD
        elif confidence > 0.5:
            return CardQuality.FAIR
        else:
            return CardQuality.POOR
```

## Phase 7: 測試重構 🧪

### 7.1 統一測試結構
```python
# tests/unit/core/services/test_multi_card_service.py
import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

class TestMultiCardService:
    @pytest.fixture
    def mock_ai_processor(self):
        return AsyncMock(spec=AIProcessorInterface)
    
    @pytest.fixture
    def mock_storage_service(self):
        return AsyncMock(spec=StorageServiceInterface)
    
    @pytest.fixture
    def service(self, mock_ai_processor, mock_storage_service, mock_user_interaction_service):
        return MultiCardService(
            ai_processor=mock_ai_processor,
            storage_service=mock_storage_service,
            user_interaction_service=mock_user_interaction_service,
            logger=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_process_high_quality_cards_auto_processing(self, service, mock_ai_processor):
        # Given
        mock_cards_data = [
            {"name": "張三", "company": "ABC公司", "confidence_score": 0.95},
            {"name": "李四", "company": "XYZ公司", "confidence_score": 0.92}
        ]
        mock_ai_processor.process_multiple_cards.return_value = mock_cards_data
        
        # When
        result = await service.process_multiple_cards(b"image_data", "user123")
        
        # Then
        assert result['auto_processed'] is True
        assert len(result['processed_cards']) == 2
        mock_ai_processor.process_multiple_cards.assert_called_once_with(b"image_data")
```

### 7.2 整合測試
```python
# tests/integration/test_card_processing_flow.py
import pytest
from app.main import create_app
from app.core.container import Container

@pytest.fixture
def app():
    app = create_app(environment="testing")
    return app

@pytest.fixture 
def client(app):
    return app.test_client()

class TestCardProcessingFlow:
    def test_single_card_processing_end_to_end(self, client):
        # 模擬完整的單張名片處理流程
        pass
    
    def test_multi_card_user_interaction_flow(self, client):
        # 模擬多名片用戶互動流程
        pass
```

## Phase 8: 部署和配置重構 📦

### 8.1 應用入口統一
```python
# main.py
from app.main import create_app
from config.settings import get_config

def main():
    config = get_config()
    app = create_app(config)
    
    if config.environment == Environment.DEVELOPMENT:
        app.run(host='0.0.0.0', port=config.port, debug=config.debug)
    else:
        # 生產環境使用 WSGI 服務器
        return app

if __name__ == '__main__':
    main()
```

### 8.2 部署配置分離
```python
# deployment/platforms/railway/railway_app.py
from main import main

app = main()  # Railway 專用入口

# deployment/platforms/zeabur/zeabur_app.py  
from main import main

app = main()  # Zeabur 專用入口
```

## 📈 實施時程和里程碑

### Week 1-2: 基礎架構
- [ ] 建立新目錄結構
- [ ] 設置依賴注入容器
- [ ] 定義核心接口
- [ ] 重構配置系統

### Week 3-4: 服務層
- [ ] 重構名片處理服務
- [ ] 重構批次處理服務
- [ ] 實作用戶互動服務
- [ ] 統一錯誤處理

### Week 5-6: API 和基礎設施層
- [ ] 重構 Flask 控制器
- [ ] 實作中間件系統
- [ ] 重構外部 API 整合
- [ ] 實作異步處理

### Week 7-8: 測試和部署
- [ ] 重構測試套件
- [ ] 更新部署配置
- [ ] 性能測試和優化
- [ ] 文檔更新

## 🎯 預期成果

### 📊 **量化指標**
- **代碼組織**: 根目錄文件從 22 個減少到 5 個以下
- **測試覆蓋率**: 從 ~60% 提升到 90%+
- **響應時間**: AI 處理超時問題解決，響應時間穩定在 3 秒內
- **維護性**: 循環複雜度降低 40%，代碼重複率降低 60%

### 🚀 **質量提升**
- **類型安全**: 100% 類型注解覆蓋
- **錯誤處理**: 統一的異常體系和錯誤報告
- **日誌系統**: 結構化日誌和操作追蹤
- **異步處理**: 避免 LINE Bot 超時問題

### 🔧 **開發效率**
- **模組化**: 清晰的職責分離和依賴管理
- **測試友好**: 依賴注入和 mock 友好的設計
- **擴展性**: 新功能添加更加容易
- **文檔完整**: API 文檔和開發指南

## 📋 風險評估和緩解

### ⚠️ **主要風險**
1. **向後兼容性**: 重構可能破壞現有功能
2. **性能回歸**: 新架構可能影響性能
3. **部署複雜性**: 新目錄結構可能影響部署
4. **學習成本**: 團隊需要適應新架構

### 🛡️ **緩解策略**
1. **漸進式重構**: 逐步遷移，保持功能完整性
2. **充分測試**: 每個階段都進行全面測試
3. **性能監控**: 持續監控關鍵性能指標
4. **文檔和培訓**: 提供詳細的遷移指南

## 🎉 總結

這個重構計劃將把現有的名片管理 LINE Bot 從單體架構轉換為現代化、可維護、高性能的分層架構系統。通過使用專業 agents 的建議和 Python 最佳實踐，我們將顯著提升代碼質量、開發效率和系統可靠性。

**關鍵成功因素**:
- 循序漸進的實施方式
- 充分的測試覆蓋
- 清晰的職責分離
- 現代化的 Python 開發實踐

準備好開始重構了嗎？讓我們使用專業 agents 來實施這個計劃！🚀