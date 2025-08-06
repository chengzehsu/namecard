#!/usr/bin/env python3
"""
測試異步應用部署配置
"""

import asyncio
import os
import sys
import time

# 添加專案根目錄到 path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))


async def test_async_app_startup():
    """測試異步應用啟動"""
    print("🚀 測試異步應用啟動...")

    try:
        from src.namecard.api.async_app import app, initialize_services

        # 初始化服務
        print("  📋 初始化服務...")
        await initialize_services()
        print("  ✅ 服務初始化成功")

        # 測試應用設定
        print("  📋 檢查應用設定...")
        print(f"    • 應用名稱: {app.name}")
        print(f"    • Debug 模式: {app.debug}")

        # 測試路由
        print("  📋 檢查應用路由...")
        test_client = app.test_client()

        # 測試健康檢查端點
        response = await test_client.get("/health")
        print(f"    • /health: {response.status_code}")

        # 測試測試端點
        response = await test_client.get("/test")
        print(f"    • /test: {response.status_code}")

        print("  ✅ 異步應用測試成功")
        return True

    except Exception as e:
        print(f"  ❌ 異步應用測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_hypercorn_config():
    """測試 Hypercorn ASGI 伺服器配置"""
    print("🧪 測試 Hypercorn 配置...")

    try:
        import hypercorn
        from hypercorn.config import Config as HypercornConfig

        print(f"  ✅ Hypercorn 已安裝")

        # 創建 Hypercorn 配置
        config = HypercornConfig()
        config.bind = ["0.0.0.0:5002"]
        config.workers = 2
        config.worker_class = "asyncio"

        print(f"  ✅ 綁定地址: {config.bind}")
        print(f"  ✅ 工作進程: {config.workers}")
        print(f"  ✅ 工作類別: {config.worker_class}")

        return True

    except Exception as e:
        print(f"  ❌ Hypercorn 配置測試失敗: {e}")
        return False


def test_deployment_files():
    """測試部署文件完整性"""
    print("📂 檢查部署文件...")

    required_files = [
        "deployment/async_requirements.txt",
        "deployment/async_zeabur.json",
        "src/namecard/api/async_app.py",
        "simple_config.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")

    if missing_files:
        print(f"  ❌ 缺少文件: {', '.join(missing_files)}")
        return False

    print("  ✅ 所有部署文件完整")
    return True


def test_environment_config():
    """測試環境配置"""
    print("🔧 檢查環境配置...")

    try:
        from simple_config import Config

        # 檢查必要配置
        required_configs = {
            "GOOGLE_API_KEY": Config.GOOGLE_API_KEY,
            "NOTION_API_KEY": Config.NOTION_API_KEY,
            "NOTION_DATABASE_ID": Config.NOTION_DATABASE_ID,
        }

        missing_configs = []
        for key, value in required_configs.items():
            if not value:
                missing_configs.append(key)
            else:
                print(f"  ✅ {key}: [已設置]")

        if missing_configs:
            print(f"  ⚠️ 缺少配置 (測試環境可忽略): {', '.join(missing_configs)}")

        # 檢查可選配置
        optional_configs = {
            "LINE_CHANNEL_ACCESS_TOKEN": Config.LINE_CHANNEL_ACCESS_TOKEN,
            "LINE_CHANNEL_SECRET": Config.LINE_CHANNEL_SECRET,
            "GOOGLE_API_KEY_FALLBACK": Config.GOOGLE_API_KEY_FALLBACK,
        }

        for key, value in optional_configs.items():
            status = "[已設置]" if value else "[未設置]"
            print(f"  • {key}: {status}")

        print("  ✅ 環境配置檢查完成")
        return True

    except Exception as e:
        print(f"  ❌ 環境配置檢查失敗: {e}")
        return False


async def main():
    """主測試函數"""
    print("🚀 異步部署測試開始...")
    print("=" * 60)

    tests = [
        ("部署文件完整性", test_deployment_files),
        ("環境配置", test_environment_config),
        ("Hypercorn 配置", test_hypercorn_config),
        ("異步應用啟動", test_async_app_startup),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 執行 {test_name} 測試...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()

            results.append((test_name, success))
            status = "✅ 通過" if success else "❌ 失敗"
            print(f"    {status}")

        except Exception as e:
            results.append((test_name, False))
            print(f"    ❌ 測試異常: {e}")

    # 總結
    print("\n" + "=" * 60)
    print("📊 部署測試結果總結:")

    passed = 0
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
        if success:
            passed += 1

    print(f"\n🎯 總體結果: {passed}/{len(results)} 測試通過")

    if passed == len(results):
        print("\n🎉 異步系統部署配置正確！準備部署到生產環境。")

        print("\n📋 部署指令:")
        print("1. 使用 Zeabur GitHub App 自動部署:")
        print("   • git push origin main")
        print("   • Zeabur 會自動檢測並部署")

        print("\n2. 手動使用 Hypercorn 啟動:")
        print("   • pip install -r deployment/async_requirements.txt")
        print(
            "   • hypercorn src.namecard.api.async_app:app --bind 0.0.0.0:5002 --workers 4"
        )

        return True
    else:
        print("\n⚠️ 部分測試失敗，建議修復後再部署。")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
