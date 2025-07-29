# 測試指南 - Testing Guide

## 📋 測試架構概覽

本專案採用全面的測試策略，包含單元測試、整合測試和端到端測試。

### 🏗️ 測試目錄結構

```
tests/
├── __init__.py                    # 測試包初始化
├── conftest.py                   # pytest 配置和共享 fixtures
├── unit/                         # 單元測試
│   ├── __init__.py
│   ├── test_batch_manager.py     # 批次管理器測試
│   ├── test_notion_manager.py    # Notion 管理器測試
│   ├── test_name_card_processor.py # 名片處理器測試
│   └── test_line_handlers.py     # LINE Bot 處理器測試
├── integration/                  # 整合測試
│   ├── __init__.py
│   └── test_end_to_end_workflow.py # 端到端工作流程測試
├── fixtures/                     # 測試數據
└── mocks/                       # 模擬對象
```

## 🧪 測試類型

### 1. 單元測試 (Unit Tests)

測試單個模組或函數的功能，使用模擬對象隔離外部依賴。

**覆蓋範圍：**
- `BatchManager` - 批次處理邏輯
- `NotionManager` - Notion API 整合
- `NameCardProcessor` - Gemini AI 名片識別
- `LINE Handlers` - LINE Bot 訊息處理

**執行命令：**
```bash
# 執行所有單元測試
pytest tests/unit/ -v

# 執行特定測試文件
pytest tests/unit/test_batch_manager.py -v

# 執行特定測試方法
pytest tests/unit/test_batch_manager.py::TestBatchManager::test_start_batch_mode_new_user -v
```

### 2. 整合測試 (Integration Tests)

測試多個組件之間的交互，驗證端到端工作流程。

**覆蓋範圍：**
- 完整名片處理流程
- 批次處理工作流程
- 錯誤處理和恢復
- 地址正規化整合

**執行命令：**
```bash
# 執行整合測試
pytest tests/integration/ -v

# 執行端到端測試
pytest tests/integration/test_end_to_end_workflow.py -v
```

## 🚀 執行測試

### 本地測試環境設置

1. **安裝測試依賴：**
```bash
pip install -r requirements-test.txt
```

2. **設置環境變數：**
```bash
# 測試環境變數（使用模擬值）
export LINE_CHANNEL_ACCESS_TOKEN="test_token"
export LINE_CHANNEL_SECRET="test_secret"
export GOOGLE_API_KEY="test_key"
export NOTION_API_KEY="test_notion_key"
export NOTION_DATABASE_ID="test_db_id"
```

3. **執行所有測試：**
```bash
# 執行所有測試並生成覆蓋率報告
pytest tests/ --cov=. --cov-report=html:htmlcov --cov-report=term-missing

# 只執行標記為 unit 的測試
pytest -m unit

# 只執行標記為 integration 的測試  
pytest -m integration
```

### CI/CD 自動化測試

GitHub Actions 會自動執行以下測試流程：

1. **代碼品質檢查**
   - flake8 語法檢查
   - black 代碼格式檢查
   - isort import 排序檢查

2. **測試執行**
   - 單元測試
   - 整合測試
   - 覆蓋率檢查（最低 70%）

3. **安全掃描**
   - bandit 安全漏洞掃描
   - safety 依賴安全檢查

## 📊 測試覆蓋率

### 當前覆蓋率目標

- **整體覆蓋率**: ≥ 70%
- **單元測試覆蓋率**: ≥ 85%
- **關鍵模組覆蓋率**: ≥ 90%

### 覆蓋率報告

```bash
# 生成 HTML 覆蓋率報告
pytest --cov=. --cov-report=html:htmlcov

# 查看詳細覆蓋率
pytest --cov=. --cov-report=term-missing

# 設置最低覆蓋率門檻
pytest --cov=. --cov-fail-under=70
```

## 🎯 測試最佳實踐

### 1. 測試命名規範

```python
def test_[功能]_[情境]_[預期結果]():
    """
    測試 [具體功能] 在 [特定情境] 下的 [預期行為]
    """
    pass

# 例如：
def test_start_batch_mode_new_user_success():
    """測試新用戶開始批次模式成功"""
    pass
```

### 2. 使用 Fixtures

```python
@pytest.fixture
def sample_card_data():
    """提供測試用的名片數據"""
    return {
        "name": "張三",
        "company": "測試公司",
        "email": "test@example.com"
    }

def test_create_record(sample_card_data):
    """使用 fixture 提供的測試數據"""
    pass
```

### 3. 模擬外部依賴

```python
@patch('notion_client.Client')
def test_notion_integration(mock_client):
    """模擬 Notion API 調用"""
    mock_client.return_value.pages.create.return_value = {"id": "test_id"}
    # 測試邏輯...
```

### 4. 測試標記

```python
@pytest.mark.unit
def test_basic_function():
    """單元測試標記"""
    pass

@pytest.mark.integration  
def test_workflow():
    """整合測試標記"""
    pass

@pytest.mark.slow
def test_performance():
    """耗時測試標記"""
    pass
```

## 🐛 測試除錯

### 常見問題解決

1. **模組導入失敗**
```bash
# 設置 Python 路徑
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 或在測試中添加
import sys
sys.path.append('.')
```

2. **Mock 對象問題**
```python
# 確保 mock 在正確的位置
@patch('module.ClassName')  # ✅ 正確
@patch('test_module.ClassName')  # ❌ 錯誤
```

3. **異步測試**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## 📈 持續改進

### 測試策略演進

1. **第一階段** ✅ - 建立基礎測試框架
2. **第二階段** 🔄 - 提高測試覆蓋率到 85%
3. **第三階段** ⏳ - 加入性能測試和負載測試
4. **第四階段** ⏳ - 實現自動化測試數據生成

### 測試指標監控

- 覆蓋率趨勢分析
- 測試執行時間優化
- 失敗率統計和分析
- 代碼品質指標追蹤

---

## 📚 相關資源

- [pytest 官方文檔](https://docs.pytest.org/)
- [pytest-cov 覆蓋率插件](https://pytest-cov.readthedocs.io/)
- [Python Mock 使用指南](https://docs.python.org/3/library/unittest.mock.html)
- [專案 CI/CD 配置](.github/workflows/ci-cd.yml)