#!/usr/bin/env python3
"""
覆蓋率徽章生成器
生成 README.md 中使用的覆蓋率徽章
"""

import json
import subprocess
import sys
from pathlib import Path


def generate_coverage_badge():
    """生成覆蓋率徽章"""
    try:
        # 運行測試生成覆蓋率數據
        print("🧪 運行測試生成覆蓋率數據...")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=src/namecard",
                "--cov-report=json:coverage.json",
                "--quiet",
            ],
            capture_output=True,
        )

        if result.returncode != 0:
            print("❌ 測試運行失敗")
            return False

        # 讀取覆蓋率數據
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("❌ 覆蓋率文件不存在")
            return False

        with open(coverage_file, "r") as f:
            coverage_data = json.load(f)

        coverage_percent = coverage_data["totals"]["percent_covered"]

        # 確定徽章顏色
        if coverage_percent >= 90:
            color = "brightgreen"
        elif coverage_percent >= 80:
            color = "green"
        elif coverage_percent >= 70:
            color = "yellow"
        elif coverage_percent >= 60:
            color = "orange"
        else:
            color = "red"

        # 生成徽章 URL
        badge_url = (
            f"https://img.shields.io/badge/coverage-{coverage_percent:.1f}%25-{color}"
        )

        print(f"📊 當前覆蓋率: {coverage_percent:.2f}%")
        print(f"🏷️ 徽章 URL: {badge_url}")

        # 更新 README.md 中的徽章
        readme_file = Path("README.md")
        if readme_file.exists():
            content = readme_file.read_text(encoding="utf-8")

            # 查找並替換覆蓋率徽章
            import re

            badge_pattern = (
                r"!\[Coverage\]\(https://img\.shields\.io/badge/coverage-[^)]+\)"
            )
            new_badge = f"![Coverage]({badge_url})"

            if re.search(badge_pattern, content):
                content = re.sub(badge_pattern, new_badge, content)
                readme_file.write_text(content, encoding="utf-8")
                print("✅ README.md 徽章已更新")
            else:
                print("⚠️ README.md 中未找到覆蓋率徽章")

        return True

    except Exception as e:
        print(f"❌ 生成覆蓋率徽章失敗: {e}")
        return False


if __name__ == "__main__":
    success = generate_coverage_badge()
    sys.exit(0 if success else 1)
