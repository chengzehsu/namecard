#!/usr/bin/env python3
"""
Phase 5 部署準備檢查腳本
檢查所有修改是否已準備好部署
"""

import os
import subprocess
import sys
from datetime import datetime


def log_message(message, level="INFO"):
    """統一日誌輸出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")


def check_syntax():
    """檢查語法錯誤"""
    log_message("🔍 檢查 Python 語法...")

    python_files = [
        "src/namecard/api/telegram_bot/main.py",
        "src/namecard/infrastructure/ai/ultra_fast_processor.py",
        "src/namecard/infrastructure/ai/high_performance_processor.py",
        "src/namecard/core/services/batch_image_collector.py",
        "src/namecard/infrastructure/messaging/telegram_client.py",
    ]

    syntax_errors = []

    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                subprocess.run(
                    [sys.executable, "-m", "py_compile", file_path],
                    check=True,
                    capture_output=True,
                )
                log_message(f"✅ {file_path}: 語法正確")
            except subprocess.CalledProcessError as e:
                syntax_errors.append(f"{file_path}: {e.stderr.decode()}")
                log_message(f"❌ {file_path}: 語法錯誤", "ERROR")
        else:
            log_message(f"⚠️ {file_path}: 文件不存在", "WARNING")

    return len(syntax_errors) == 0, syntax_errors


def check_imports():
    """檢查關鍵模組導入"""
    log_message("📦 檢查關鍵模組導入...")

    import_checks = [
        (
            "UltraFastProcessor",
            "from src.namecard.infrastructure.ai.ultra_fast_processor import UltraFastProcessor",
        ),
        (
            "BatchImageCollector",
            "from src.namecard.core.services.batch_image_collector import BatchImageCollector",
        ),
        (
            "TelegramBotHandler",
            "from src.namecard.infrastructure.messaging.telegram_client import TelegramBotHandler",
        ),
        ("Main Module", "import src.namecard.api.telegram_bot.main"),
    ]

    import_errors = []

    for name, import_statement in import_checks:
        try:
            exec(import_statement)
            log_message(f"✅ {name}: 導入成功")
        except Exception as e:
            import_errors.append(f"{name}: {str(e)}")
            log_message(f"❌ {name}: 導入失敗 - {e}", "ERROR")

    return len(import_errors) == 0, import_errors


def check_phase5_integration():
    """檢查 Phase 5 整合狀況"""
    log_message("🚀 檢查 Phase 5 整合狀況...")

    main_file = "src/namecard/api/telegram_bot/main.py"

    if not os.path.exists(main_file):
        return False, [f"{main_file} 不存在"]

    with open(main_file, "r", encoding="utf-8") as f:
        content = f.read()

    phase5_indicators = [
        "Phase 5",
        "process_telegram_photos_batch_ultra_fast",
        "ultra_fast_processor",
        "真正批次處理",
    ]

    found_indicators = []
    missing_indicators = []

    for indicator in phase5_indicators:
        if indicator in content:
            found_indicators.append(indicator)
        else:
            missing_indicators.append(indicator)

    log_message(f"✅ 找到 Phase 5 指標: {found_indicators}")

    if missing_indicators:
        log_message(f"❌ 缺少 Phase 5 指標: {missing_indicators}", "ERROR")
        return False, missing_indicators

    return True, []


def check_deployment_files():
    """檢查部署文件"""
    log_message("📂 檢查部署相關文件...")

    required_files = ["requirements.txt", "simple_config.py", ".deploy_trigger"]

    optional_files = [
        "requirements-telegram.txt",
        "Procfile.telegram",
        "deployment/scripts/deploy_telegram_manual.sh",
    ]

    missing_required = []
    missing_optional = []

    for file_path in required_files:
        if os.path.exists(file_path):
            log_message(f"✅ 必要文件存在: {file_path}")
        else:
            missing_required.append(file_path)
            log_message(f"❌ 缺少必要文件: {file_path}", "ERROR")

    for file_path in optional_files:
        if os.path.exists(file_path):
            log_message(f"✅ 可選文件存在: {file_path}")
        else:
            missing_optional.append(file_path)
            log_message(f"⚠️ 可選文件缺失: {file_path}", "WARNING")

    return len(missing_required) == 0, missing_required, missing_optional


def check_git_status():
    """檢查 Git 狀態"""
    log_message("📝 檢查 Git 狀態...")

    try:
        # 檢查是否有未提交的更改
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )

        if result.stdout.strip():
            log_message("⚠️ 有未提交的更改:", "WARNING")
            for line in result.stdout.strip().split("\n"):
                log_message(f"  {line}", "WARNING")
            return False, ["有未提交的更改"]
        else:
            log_message("✅ 沒有未提交的更改")
            return True, []

    except subprocess.CalledProcessError as e:
        log_message(f"❌ Git 狀態檢查失敗: {e}", "ERROR")
        return False, [f"Git 狀態檢查失敗: {e}"]


def update_deploy_trigger():
    """更新部署觸發文件"""
    log_message("🔄 更新部署觸發文件...")

    try:
        with open(".deploy_trigger", "a") as f:
            f.write(
                f"# Phase 5 batch processing deployment: {datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')}\n"
            )

        log_message("✅ 部署觸發文件已更新")
        return True

    except Exception as e:
        log_message(f"❌ 更新部署觸發文件失敗: {e}", "ERROR")
        return False


def run_deployment_check():
    """執行完整的部署檢查"""
    log_message("🚀 開始 Phase 5 部署準備檢查")
    log_message("=" * 60)

    all_checks_passed = True
    issues = []

    # 1. 語法檢查
    syntax_ok, syntax_errors = check_syntax()
    if not syntax_ok:
        all_checks_passed = False
        issues.extend(syntax_errors)

    # 2. 導入檢查
    import_ok, import_errors = check_imports()
    if not import_ok:
        all_checks_passed = False
        issues.extend(import_errors)

    # 3. Phase 5 整合檢查
    phase5_ok, phase5_errors = check_phase5_integration()
    if not phase5_ok:
        all_checks_passed = False
        issues.extend(phase5_errors)

    # 4. 部署文件檢查
    deploy_ok, missing_required, missing_optional = check_deployment_files()
    if not deploy_ok:
        all_checks_passed = False
        issues.extend(missing_required)

    # 5. Git 狀態檢查
    git_ok, git_issues = check_git_status()
    if not git_ok:
        # Git 問題不阻止部署，只是警告
        log_message("⚠️ Git 狀態有問題，但不阻止部署", "WARNING")

    # 總結
    log_message("=" * 60)
    log_message("📊 部署檢查結果總結:")

    checks = [
        ("語法檢查", syntax_ok),
        ("模組導入", import_ok),
        ("Phase 5 整合", phase5_ok),
        ("部署文件", deploy_ok),
        ("Git 狀態", git_ok),
    ]

    for check_name, result in checks:
        status = "✅ 通過" if result else "❌ 失敗"
        log_message(f"  {check_name}: {status}")

    if all_checks_passed:
        log_message("🎉 所有檢查通過！準備部署 Phase 5 批次處理優化！")

        # 更新部署觸發
        if update_deploy_trigger():
            log_message("🚀 部署觸發已更新，可以進行部署")

        log_message("📋 部署建議:")
        log_message("  1. 提交所有更改到 Git")
        log_message("  2. 推送到 main 分支觸發自動部署")
        log_message("  3. 監控部署過程和日誌")
        log_message("  4. 測試批次處理功能")

        return True
    else:
        log_message("⚠️ 部分檢查失敗，建議修復後再部署:")
        for issue in issues:
            log_message(f"   - {issue}", "ERROR")

        return False


if __name__ == "__main__":
    try:
        success = run_deployment_check()
        exit(0 if success else 1)
    except Exception as e:
        log_message(f"❌ 部署檢查執行失敗: {e}", "ERROR")
        import traceback

        traceback.print_exc()
        exit(1)
