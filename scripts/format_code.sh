#!/bin/bash
set -e

echo "🔧 代碼格式化腳本 - 本地開發工具"
echo "================================"

# 檢查是否安裝了必要工具
echo "📦 檢查格式化工具..."

if ! command -v black &> /dev/null; then
    echo "❌ 未安裝 black，正在安裝..."
    pip install black
fi

if ! command -v isort &> /dev/null; then
    echo "❌ 未安裝 isort，正在安裝..."
    pip install isort
fi

if ! command -v flake8 &> /dev/null; then
    echo "❌ 未安裝 flake8，正在安裝..."
    pip install flake8
fi

echo "✅ 格式化工具檢查完成"
echo ""

# 運行格式化
echo "🎨 執行代碼格式化..."

# 1. Black 格式化
echo "📝 運行 black..."
black . --exclude="\.venv|venv|env|__pycache__|\.git"

# 2. isort 排序
echo "📦 運行 isort..."
isort . --skip-glob="*.venv/*" --skip-glob="*venv/*" --skip-glob="*env/*" --skip-glob="*__pycache__/*"

# 3. 檢查結果
echo ""
echo "🔍 檢查格式化結果..."

# Black 檢查
if black --check --diff . --exclude="\.venv|venv|env|__pycache__|\.git" > /dev/null 2>&1; then
    echo "✅ Black 格式檢查通過"
else
    echo "⚠️ Black 可能需要再次運行"
fi

# isort 檢查
if isort --check-only --diff . --skip-glob="*.venv/*" --skip-glob="*venv/*" --skip-glob="*env/*" --skip-glob="*__pycache__/*" > /dev/null 2>&1; then
    echo "✅ Import 排序檢查通過"
else
    echo "⚠️ Import 排序可能需要再次運行"
fi

# Flake8 檢查 (可選)
echo "🔍 運行 flake8 代碼品質檢查..."
if flake8 . --exclude=.venv,venv,env,.git,.github,__pycache__,.pytest_cache,.tox --ignore=E203,W503,F541 --max-line-length=160; then
    echo "✅ Flake8 檢查通過"
else
    echo "⚠️ Flake8 發現一些問題，請檢查上方輸出"
fi

echo ""
echo "🎉 代碼格式化完成！"
echo ""
echo "💡 提示："
echo "- 格式化後的代碼已準備好提交"
echo "- 建議設置 pre-commit hooks：pip install pre-commit && pre-commit install"
echo "- CI/CD 會自動檢查並修復格式問題"