#!/usr/bin/env python3
"""
自動化測試覆蓋率監控設置 - Tool Evaluator Agent 實作
設置 pytest-cov 集成、覆蓋率報告生成和 CI/CD 覆蓋率閾值檢查
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


class TestCoverageSetup:
    """測試覆蓋率設置管理器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.coverage_threshold = 85  # 85% 覆蓋率目標

        # 測試覆蓋率配置
        self.coverage_config = {
            "source": "src/namecard",
            "exclude_patterns": [
                "*/tests/*",
                "*/test_*",
                "*/__pycache__/*",
                "*/migrations/*",
                "setup.py",
                "conftest.py",
            ],
            "report_formats": ["term-missing", "html", "xml", "json"],
            "html_directory": "htmlcov",
            "xml_file": "coverage.xml",
            "json_file": "coverage.json",
        }

        print("🚀 測試覆蓋率監控設置器初始化完成")

    def install_coverage_tools(self) -> bool:
        """安裝覆蓋率工具"""
        print("📦 安裝測試覆蓋率工具...")

        tools = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-html>=3.1.0",
            "pytest-xdist>=3.0.0",  # 並行測試
            "coverage>=7.0.0",
        ]

        try:
            for tool in tools:
                print(f"   - 安裝 {tool}")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", tool],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    print(f"❌ 安裝失敗: {tool}")
                    print(f"   錯誤: {result.stderr}")
                    return False

            print("✅ 測試覆蓋率工具安裝完成")
            return True

        except Exception as e:
            print(f"❌ 安裝過程中發生錯誤: {e}")
            return False

    def create_pytest_config(self) -> bool:
        """創建 pytest 配置"""
        print("⚙️ 創建 pytest 配置...")

        pytest_config = f"""# pytest 配置文件
[tool:pytest]
# 測試目錄
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 覆蓋率配置
addopts = --cov={self.coverage_config['source']}
    --cov-report=term-missing
    --cov-report=html:{self.coverage_config['html_directory']}
    --cov-report=xml:{self.coverage_config['xml_file']}
    --cov-report=json:{self.coverage_config['json_file']}
    --cov-fail-under={self.coverage_threshold}
    --strict-markers
    --strict-config
    -v

# 覆蓋率排除規則
[coverage:run]
source = {self.coverage_config['source']}
omit =
    */tests/*
    */test_*
    */__pycache__/*
    */migrations/*
    setup.py
    conftest.py

[coverage:report]
# 顯示缺失的行數
show_missing = True
# 跳過覆蓋率 100% 的文件
skip_covered = False
# 精確度
precision = 2
# 排除正則表達式
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\\bProtocol\\):
    @(abc\\.)?abstractmethod

[coverage:html]
directory = {self.coverage_config['html_directory']}
title = NameCard 測試覆蓋率報告

[coverage:xml]
output = {self.coverage_config['xml_file']}

[coverage:json]
output = {self.coverage_config['json_file']}
"""

        try:
            config_file = self.project_root / "setup.cfg"
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(pytest_config)

            print(f"✅ pytest 配置已創建: {config_file}")
            return True

        except Exception as e:
            print(f"❌ 創建 pytest 配置失敗: {e}")
            return False

    def create_coverage_script(self) -> bool:
        """創建覆蓋率測試腳本"""
        print("📝 創建覆蓋率測試腳本...")

        coverage_script = '''#!/usr/bin/env python3
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
        sys.executable, "-m", "pytest",
        "--cov=src/namecard",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=json:coverage.json",
        "--cov-fail-under=85",
        "-v"
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

        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)

        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)

        print(f"\\n📊 覆蓋率報告摘要:")
        print(f"   - 整體覆蓋率: {total_coverage:.2f}%")

        # 按文件顯示覆蓋率
        files = coverage_data.get('files', {})
        if files:
            print(f"   - 測試文件數: {len(files)}")

            # 找出覆蓋率最低的文件
            low_coverage_files = [
                (file, data['summary']['percent_covered'])
                for file, data in files.items()
                if data['summary']['percent_covered'] < 80
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
            print(f"\\n📄 詳細報告: file://{html_dir.absolute()}/index.html")

    except Exception as e:
        print(f"⚠️ 生成覆蓋率摘要失敗: {e}")


def main():
    parser = argparse.ArgumentParser(description="運行測試覆蓋率分析")
    parser.add_argument("--fast", action="store_true", help="快速模式，跳過長時間測試")
    parser.add_argument("--specific", type=str, help="運行特定測試文件或模式")

    args = parser.parse_args()

    success = run_coverage_tests(
        fast_mode=args.fast,
        specific_tests=args.specific
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
'''

        try:
            script_file = self.project_root / "run_coverage.py"
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(coverage_script)

            # 設置執行權限
            os.chmod(script_file, 0o755)

            print(f"✅ 覆蓋率測試腳本已創建: {script_file}")
            return True

        except Exception as e:
            print(f"❌ 創建覆蓋率測試腳本失敗: {e}")
            return False

    def update_github_actions(self) -> bool:
        """更新 GitHub Actions 以包含覆蓋率檢查"""
        print("🔧 更新 GitHub Actions 覆蓋率檢查...")

        github_dir = self.project_root / ".github" / "workflows"
        if not github_dir.exists():
            github_dir.mkdir(parents=True)

        # 覆蓋率檢查工作流
        coverage_workflow = """name: 測試覆蓋率監控

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # 每日執行一次覆蓋率檢查
    - cron: '0 8 * * *'

jobs:
  coverage:
    name: 📊 測試覆蓋率分析
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.9, 3.11]

    steps:
    - uses: actions/checkout@v4

    - name: 設置 Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: 安裝依賴
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-html coverage

    - name: 運行測試覆蓋率分析
      run: |
        python -m pytest \\
          --cov=src/namecard \\
          --cov-report=term-missing \\
          --cov-report=xml:coverage.xml \\
          --cov-report=json:coverage.json \\
          --cov-report=html:htmlcov \\
          --cov-fail-under=85 \\
          -v

    - name: 生成覆蓋率徽章
      if: matrix.python-version == '3.11'
      run: |
        pip install coverage-badge
        coverage-badge -o coverage.svg

    - name: 上傳覆蓋率報告到 Codecov
      if: matrix.python-version == '3.11'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: true

    - name: 上傳 HTML 覆蓋率報告
      if: matrix.python-version == '3.11'
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/

    - name: 覆蓋率趨勢檢查
      if: matrix.python-version == '3.11'
      run: |
        python -c "
        import json
        with open('coverage.json', 'r') as f:
            data = json.load(f)
        coverage = data['totals']['percent_covered']
        print(f'當前覆蓋率: {coverage:.2f}%')

        if coverage < 85:
            print('❌ 覆蓋率低於目標 85%')
            exit(1)
        elif coverage >= 90:
            print('🎉 覆蓋率優秀 (≥90%)')
        else:
            print('✅ 覆蓋率達標')
        "

    - name: 覆蓋率評論 (PR)
      if: github.event_name == 'pull_request' && matrix.python-version == '3.11'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const coverage = JSON.parse(fs.readFileSync('coverage.json', 'utf8'));
          const coveragePercent = coverage.totals.percent_covered.toFixed(2);

          const comment = `## 📊 測試覆蓋率報告

          **整體覆蓋率**: ${coveragePercent}%

          ${coveragePercent >= 90 ? '🎉 優秀!' :
            coveragePercent >= 85 ? '✅ 達標' : '❌ 需要改善'}

          **目標**: 85%
          **狀態**: ${coveragePercent >= 85 ? '通過' : '未通過'}

          詳細報告請查看 Actions 中的 coverage-report artifact。
          `;

          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });

  coverage-diff:
    name: 📈 覆蓋率變化分析
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: 設置 Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11

    - name: 安裝依賴
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov diff-cover

    - name: 運行覆蓋率 (當前分支)
      run: |
        python -m pytest --cov=src/namecard --cov-report=xml:coverage-current.xml

    - name: 切換到基礎分支
      run: |
        git checkout ${{ github.base_ref }}

    - name: 運行覆蓋率 (基礎分支)
      run: |
        python -m pytest --cov=src/namecard --cov-report=xml:coverage-base.xml || true

    - name: 比較覆蓋率差異
      run: |
        diff-cover coverage-current.xml --compare-branch=origin/${{ github.base_ref }} --fail-under=85
"""

        try:
            workflow_file = github_dir / "test-coverage.yml"
            with open(workflow_file, "w", encoding="utf-8") as f:
                f.write(coverage_workflow)

            print(f"✅ GitHub Actions 覆蓋率工作流已創建: {workflow_file}")
            return True

        except Exception as e:
            print(f"❌ 更新 GitHub Actions 失敗: {e}")
            return False

    def create_coverage_badge_script(self) -> bool:
        """創建覆蓋率徽章生成腳本"""
        print("🏷️ 創建覆蓋率徽章生成腳本...")

        badge_script = '''#!/usr/bin/env python3
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
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "--cov=src/namecard",
            "--cov-report=json:coverage.json",
            "--quiet"
        ], capture_output=True)

        if result.returncode != 0:
            print("❌ 測試運行失敗")
            return False

        # 讀取覆蓋率數據
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("❌ 覆蓋率文件不存在")
            return False

        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)

        coverage_percent = coverage_data['totals']['percent_covered']

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
        badge_url = f"https://img.shields.io/badge/coverage-{coverage_percent:.1f}%25-{color}"

        print(f"📊 當前覆蓋率: {coverage_percent:.2f}%")
        print(f"🏷️ 徽章 URL: {badge_url}")

        # 更新 README.md 中的徽章
        readme_file = Path("README.md")
        if readme_file.exists():
            content = readme_file.read_text(encoding='utf-8')

            # 查找並替換覆蓋率徽章
            import re
            badge_pattern = r'!\[Coverage\]\(https://img\.shields\.io/badge/coverage-[^)]+\)'
            new_badge = f"![Coverage]({badge_url})"

            if re.search(badge_pattern, content):
                content = re.sub(badge_pattern, new_badge, content)
                readme_file.write_text(content, encoding='utf-8')
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
'''

        try:
            script_file = self.project_root / "generate_coverage_badge.py"
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(badge_script)

            os.chmod(script_file, 0o755)

            print(f"✅ 覆蓋率徽章腳本已創建: {script_file}")
            return True

        except Exception as e:
            print(f"❌ 創建覆蓋率徽章腳本失敗: {e}")
            return False

    def create_pre_commit_hooks(self) -> bool:
        """創建 pre-commit hooks 以確保測試覆蓋率"""
        print("🪝 創建 pre-commit hooks...")

        pre_commit_config = """# Pre-commit hooks 配置
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: pretty-format-json
        args: ['--autofix']

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: local
    hooks:
      - id: pytest-coverage
        name: 測試覆蓋率檢查
        entry: python -m pytest --cov=src/namecard --cov-fail-under=85 --quiet
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]

      - id: coverage-report
        name: 生成覆蓋率報告
        entry: python run_coverage.py --fast
        language: system
        pass_filenames: false
        always_run: false
        stages: [manual]
"""

        try:
            config_file = self.project_root / ".pre-commit-config.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(pre_commit_config)

            print(f"✅ Pre-commit 配置已創建: {config_file}")

            # 安裝 pre-commit hooks
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pre-commit"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["pre-commit", "install"], check=True, capture_output=True
                )
                print("✅ Pre-commit hooks 已安裝")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Pre-commit hooks 安裝失敗: {e}")

            return True

        except Exception as e:
            print(f"❌ 創建 pre-commit hooks 失敗: {e}")
            return False

    def create_coverage_requirements(self) -> bool:
        """創建覆蓋率測試專用依賴文件"""
        print("📋 創建覆蓋率測試依賴文件...")

        coverage_requirements = """# 測試覆蓋率專用依賴
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-html>=3.1.0
pytest-xdist>=3.0.0
pytest-mock>=3.10.0
coverage>=7.0.0
coverage-badge>=1.1.0
diff-cover>=7.0.0

# 代碼品質工具
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.0.0

# Pre-commit
pre-commit>=3.0.0

# 額外的測試工具
factory-boy>=3.2.0
freezegun>=1.2.0
responses>=0.23.0
"""

        try:
            req_file = self.project_root / "requirements-test.txt"
            with open(req_file, "w", encoding="utf-8") as f:
                f.write(coverage_requirements)

            print(f"✅ 測試依賴文件已創建: {req_file}")
            return True

        except Exception as e:
            print(f"❌ 創建測試依賴文件失敗: {e}")
            return False

    def run_initial_coverage_check(self) -> Dict[str, Any]:
        """運行初始覆蓋率檢查"""
        print("🔍 運行初始覆蓋率檢查...")

        try:
            # 運行覆蓋率測試
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=src/namecard",
                    "--cov-report=json:coverage.json",
                    "--cov-report=term-missing",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                print("⚠️ 部分測試失敗，但繼續分析覆蓋率...")

            # 讀取覆蓋率數據
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    coverage_data = json.load(f)

                total_coverage = coverage_data["totals"]["percent_covered"]
                files_coverage = coverage_data.get("files", {})

                # 分析覆蓋率
                analysis = {
                    "total_coverage": total_coverage,
                    "files_count": len(files_coverage),
                    "target_coverage": self.coverage_threshold,
                    "status": (
                        "達標" if total_coverage >= self.coverage_threshold else "需要改善"
                    ),
                    "low_coverage_files": [],
                }

                # 找出低覆蓋率文件
                for file_path, file_data in files_coverage.items():
                    file_coverage = file_data["summary"]["percent_covered"]
                    if file_coverage < 80:
                        analysis["low_coverage_files"].append(
                            {"file": file_path, "coverage": file_coverage}
                        )

                print(f"\n📊 初始覆蓋率分析結果:")
                print(f"   - 整體覆蓋率: {total_coverage:.2f}%")
                print(f"   - 目標覆蓋率: {self.coverage_threshold}%")
                print(f"   - 狀態: {analysis['status']}")
                print(f"   - 測試文件數: {analysis['files_count']}")

                if analysis["low_coverage_files"]:
                    print(f"   - 需要改善的文件 (<80%):")
                    for file_info in analysis["low_coverage_files"]:
                        print(
                            f"     * {file_info['file']}: {file_info['coverage']:.1f}%"
                        )

                return analysis

            else:
                print("❌ 覆蓋率數據文件不存在")
                return {"error": "覆蓋率數據文件不存在"}

        except Exception as e:
            print(f"❌ 覆蓋率檢查失敗: {e}")
            return {"error": str(e)}

    def setup_all(self) -> bool:
        """執行完整的覆蓋率監控設置"""
        print("🚀 開始設置測試覆蓋率監控系統...")
        print("=" * 60)

        success_count = 0
        total_steps = 7

        # 1. 安裝工具
        if self.install_coverage_tools():
            success_count += 1

        # 2. 創建 pytest 配置
        if self.create_pytest_config():
            success_count += 1

        # 3. 創建覆蓋率腳本
        if self.create_coverage_script():
            success_count += 1

        # 4. 更新 GitHub Actions
        if self.update_github_actions():
            success_count += 1

        # 5. 創建徽章腳本
        if self.create_coverage_badge_script():
            success_count += 1

        # 6. 創建 pre-commit hooks
        if self.create_pre_commit_hooks():
            success_count += 1

        # 7. 創建測試依賴
        if self.create_coverage_requirements():
            success_count += 1

        print("\n" + "=" * 60)
        print(f"📈 設置完成統計: {success_count}/{total_steps} 成功")

        if success_count == total_steps:
            print("✅ 測試覆蓋率監控系統設置完成")

            # 運行初始覆蓋率檢查
            print("\n🔍 運行初始覆蓋率檢查...")
            analysis = self.run_initial_coverage_check()

            if "error" not in analysis:
                print("\n🎯 使用建議:")
                print("   - 運行所有測試: python run_coverage.py")
                print("   - 快速測試: python run_coverage.py --fast")
                print("   - 生成徽章: python generate_coverage_badge.py")
                print("   - 查看 HTML 報告: open htmlcov/index.html")
                print("   - 安裝 pre-commit: pre-commit install")

            return True
        else:
            print("⚠️ 部分設置失敗，請檢查錯誤信息")
            return False


# ==========================================
# 主程式入口
# ==========================================


def main():
    """主程式"""
    print("🧪 Testing Agents 協作：自動化測試覆蓋率監控設置")
    print("主導 Agent: Tool Evaluator")
    print("協作 Agents: Test Writer/Fixer, Performance Benchmarker")
    print("=" * 60)

    # 創建設置管理器
    setup_manager = TestCoverageSetup()

    # 執行完整設置
    success = setup_manager.setup_all()

    if success:
        print("\n🎉 測試覆蓋率監控系統已成功設置！")
        print("\n🔧 下一步操作:")
        print("   1. 提交變更到 Git: git add . && git commit -m 'feat: 添加測試覆蓋率監控'")
        print("   2. 推送到遠程: git push origin main")
        print("   3. 檢查 GitHub Actions 執行結果")
        print("   4. 查看覆蓋率報告並改善低覆蓋率模組")
    else:
        print("\n❌ 設置過程中遇到問題，請檢查上方錯誤信息")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
