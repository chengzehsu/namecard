#!/usr/bin/env python3
"""
測試覆蓋率執行腳本
使用方法：
    python run_coverage.py              # 運行所有測試
    python run_coverage.py --fast       # 快速測試（跳過長時間測試）
    python run_coverage.py --specific   # 只測試特定模組
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_coverage_tests(fast_mode: bool = False, specific_tests: str = None):
    """運行覆蓋率測試"""
    print("🧪 開始運行測試覆蓋率分析...")

    # 基本 pytest 命令
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=src/namecard",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=json:coverage.json",
        "--cov-fail-under=85",
        "-v",
    ]

    # 快速模式：跳過長時間測試
    if fast_mode:
        cmd.extend(["-m", "not slow"])
        print("⚡ 快速模式：跳過長時間測試")

    # 特定測試
    if specific_tests:
        cmd.append(specific_tests)
        print(f"🎯 運行特定測試: {specific_tests}")

    # 並行測試（如果可用）
    try:
        import pytest_xdist

        cmd.extend(["-n", "auto"])
        print("🚀 啟用並行測試")
    except ImportError:
        pass

    print(f"執行命令: {' '.join(cmd)}")

    # 運行測試
    result = subprocess.run(cmd, cwd=Path.cwd())

    if result.returncode == 0:
        print("✅ 測試覆蓋率分析完成")

        # 生成覆蓋率報告摘要
        generate_coverage_summary()

        return True
    else:
        print("❌ 測試覆蓋率分析失敗")
        return False


def generate_coverage_summary():
    """生成覆蓋率報告摘要"""
    try:
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("⚠️ 覆蓋率 JSON 文件不存在")
            return

        with open(coverage_file, "r") as f:
            coverage_data = json.load(f)

        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

        print(f"\n📊 覆蓋率報告摘要:")
        print(f"   - 整體覆蓋率: {total_coverage:.2f}%")

        # 按文件顯示覆蓋率
        files = coverage_data.get("files", {})
        if files:
            print(f"   - 測試文件數: {len(files)}")

            # 找出覆蓋率最低的文件
            low_coverage_files = [
                (file, data["summary"]["percent_covered"])
                for file, data in files.items()
                if data["summary"]["percent_covered"] < 80
            ]

            if low_coverage_files:
                print("   - 需要改善的文件 (<80%):")
                for file, coverage in sorted(low_coverage_files, key=lambda x: x[1]):
                    print(f"     * {file}: {coverage:.1f}%")
            else:
                print("   - ✅ 所有文件覆蓋率都 ≥80%")

        # HTML 報告提示
        html_dir = Path("htmlcov")
        if html_dir.exists():
            print(f"\n📄 詳細報告: file://{html_dir.absolute()}/index.html")

    except Exception as e:
        print(f"⚠️ 生成覆蓋率摘要失敗: {e}")


def main():
    parser = argparse.ArgumentParser(description="運行測試覆蓋率分析")
    parser.add_argument("--fast", action="store_true", help="快速模式，跳過長時間測試")
    parser.add_argument("--specific", type=str, help="運行特定測試文件或模式")

    args = parser.parse_args()

    success = run_coverage_tests(fast_mode=args.fast, specific_tests=args.specific)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
