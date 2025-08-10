#!/usr/bin/env python3
"""
測試覆蓋率綜合評估報告
分析當前專案的測試覆蓋率狀況並提供改善建議
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def analyze_project_structure():
    """分析專案結構和主要模組"""
    print("📁 專案結構分析:")

    # 主要源碼目錄
    src_dirs = [
        "src/namecard/api",
        "src/namecard/core",
        "src/namecard/infrastructure",
        ".",  # 根目錄下的主要文件
    ]

    source_files = []
    for src_dir in src_dirs:
        if os.path.exists(src_dir):
            pattern = f"{src_dir}/**/*.py" if src_dir != "." else "*.py"
            files = glob.glob(pattern, recursive=True)
            source_files.extend(
                [f for f in files if not f.startswith("test_") and "test" not in f]
            )

    print(f"   • 發現 {len(source_files)} 個 Python 源碼文件")

    # 主要模組
    main_modules = [
        "app.py",
        "main.py",
        "simple_config.py",
        "name_card_processor.py",
        "notion_manager.py",
        "batch_manager.py",
    ]

    existing_modules = [m for m in main_modules if os.path.exists(m)]
    print(f"   • 主要模組: {len(existing_modules)}/{len(main_modules)} 存在")

    return source_files, existing_modules


def analyze_test_files():
    """分析現有測試文件狀況"""
    print("\n🧪 測試文件分析:")

    # 尋找所有測試文件
    test_patterns = ["test_*.py", "tests/**/*.py", "**/test_*.py"]

    all_test_files = []
    for pattern in test_patterns:
        files = glob.glob(pattern, recursive=True)
        all_test_files.extend(files)

    # 去重
    test_files = list(set(all_test_files))
    print(f"   • 發現 {len(test_files)} 個測試文件")

    # 分類測試文件
    working_tests = []
    broken_tests = []

    for test_file in test_files:
        try:
            # 嘗試導入測試文件檢查語法
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", test_file],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                working_tests.append(test_file)
            else:
                broken_tests.append((test_file, result.stderr))
        except Exception as e:
            broken_tests.append((test_file, str(e)))

    print(f"   • 語法正確: {len(working_tests)} 個")
    print(f"   • 有問題: {len(broken_tests)} 個")

    if broken_tests:
        print("\n   📋 有問題的測試文件:")
        for test_file, error in broken_tests[:5]:  # 只顯示前5個
            print(f"      • {test_file}: {error.split(':', 1)[-1].strip()[:100]}")
        if len(broken_tests) > 5:
            print(f"      ... 還有 {len(broken_tests) - 5} 個")

    return working_tests, broken_tests


def run_limited_coverage_test():
    """運行有限的覆蓋率測試"""
    print("\n🎯 運行覆蓋率測試:")

    # 只測試新創建的測試文件
    new_test_files = [
        "test_smart_cache.py",
        "test_performance_monitor.py",
        "test_api_quota_manager.py",
        "test_async_message_queue.py",
        "test_parallel_image_downloader.py",
    ]

    existing_new_tests = [f for f in new_test_files if os.path.exists(f)]

    if not existing_new_tests:
        print("   ❌ 沒有可運行的新測試文件")
        return None

    print(f"   • 運行 {len(existing_new_tests)} 個新創建的測試文件")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *existing_new_tests,
        "--cov=src/namecard",
        "--cov=.",
        "--cov-report=json:limited_coverage.json",
        "--tb=no",
        "-q",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if os.path.exists("limited_coverage.json"):
            with open("limited_coverage.json", "r") as f:
                coverage_data = json.load(f)

            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            covered_lines = coverage_data.get("totals", {}).get("covered_lines", 0)
            total_lines = coverage_data.get("totals", {}).get("num_statements", 0)

            print(f"   ✅ 新測試覆蓋率: {total_coverage:.2f}%")
            print(f"   • 覆蓋行數: {covered_lines}/{total_lines}")

            return coverage_data
        else:
            print("   ⚠️ 無法生成覆蓋率報告")
            print(f"   輸出: {result.stdout}")
            if result.stderr:
                print(f"   錯誤: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("   ⏰ 測試運行超時")
        return None
    except Exception as e:
        print(f"   ❌ 測試運行失敗: {e}")
        return None


def analyze_coverage_gaps(coverage_data):
    """分析覆蓋率缺口"""
    if not coverage_data:
        return

    print("\n📊 覆蓋率缺口分析:")

    files = coverage_data.get("files", {})
    if not files:
        print("   • 沒有文件覆蓋率數據")
        return

    # 按覆蓋率排序
    file_coverage = [
        (file_path, data["summary"]["percent_covered"])
        for file_path, data in files.items()
        if "summary" in data
    ]

    file_coverage.sort(key=lambda x: x[1])

    # 低覆蓋率文件 (<50%)
    low_coverage = [(f, c) for f, c in file_coverage if c < 50]
    medium_coverage = [(f, c) for f, c in file_coverage if 50 <= c < 80]
    high_coverage = [(f, c) for f, c in file_coverage if c >= 80]

    print(f"   • 低覆蓋率 (<50%): {len(low_coverage)} 個文件")
    print(f"   • 中覆蓋率 (50-80%): {len(medium_coverage)} 個文件")
    print(f"   • 高覆蓋率 (≥80%): {len(high_coverage)} 個文件")

    if low_coverage:
        print("\n   🎯 最需要改善的文件 (前10個):")
        for file_path, coverage in low_coverage[:10]:
            # 簡化文件路徑顯示
            short_path = file_path.replace("src/namecard/", "").replace(
                "/Users/user/namecard/", ""
            )
            print(f"      • {short_path}: {coverage:.1f}%")


def generate_improvement_recommendations():
    """生成改善建議"""
    print("\n💡 測試覆蓋率改善建議:")

    recommendations = [
        "1. 修復現有測試文件的導入問題",
        "   • 統一模組導入路徑",
        "   • 建立正確的 __init__.py 文件",
        "   • 修復缺少的依賴模組",
        "",
        "2. 為核心模組建立基礎測試",
        "   • app.py - 主應用邏輯測試",
        "   • name_card_processor.py - AI 處理邏輯測試",
        "   • notion_manager.py - 資料庫操作測試",
        "   • batch_manager.py - 批次處理測試",
        "",
        "3. 建立整合測試",
        "   • API 端點測試",
        "   • 完整工作流程測試",
        "   • 錯誤處理測試",
        "",
        "4. 設置 CI/CD 測試自動化",
        "   • GitHub Actions 自動測試",
        "   • 覆蓋率門檻設置 (目標 85%)",
        "   • 每日覆蓋率報告",
        "",
        "5. 性能和壓力測試",
        "   • 批次處理性能測試",
        "   • API 限流測試",
        "   • 記憶體使用測試",
    ]

    for rec in recommendations:
        print(f"   {rec}")


def main():
    """主要評估流程"""
    print("🔍 名片管理系統 - 測試覆蓋率綜合評估")
    print("=" * 60)

    # 1. 專案結構分析
    source_files, existing_modules = analyze_project_structure()

    # 2. 測試文件分析
    working_tests, broken_tests = analyze_test_files()

    # 3. 運行覆蓋率測試
    coverage_data = run_limited_coverage_test()

    # 4. 分析覆蓋率缺口
    analyze_coverage_gaps(coverage_data)

    # 5. 生成改善建議
    generate_improvement_recommendations()

    print("\n" + "=" * 60)
    print("📋 評估總結:")
    print(f"   • 源碼文件: {len(source_files)} 個")
    print(f"   • 主要模組: {len(existing_modules)} 個")
    print(f"   • 工作測試: {len(working_tests)} 個")
    print(f"   • 問題測試: {len(broken_tests)} 個")

    if coverage_data:
        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
        print(f"   • 當前覆蓋率: {total_coverage:.2f}%")
        print(f"   • 目標覆蓋率: 85.0%")
        print(f"   • 改善空間: {85.0 - total_coverage:.2f}%")

    print(f"\n✅ 評估完成！改善建議已輸出。")


if __name__ == "__main__":
    main()
