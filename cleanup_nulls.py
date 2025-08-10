#!/usr/bin/env python3
"""清理 null bytes 的腳本"""

import os


def clean_null_bytes():
    """清理所有 Python 文件中的 null bytes"""
    cleaned_count = 0

    for root, dirs, files in os.walk("/Users/user/namecard/src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()

                    # 移除 null bytes
                    cleaned_content = content.replace(b"\x00", b"")

                    # 只有當內容變化時才寫回
                    if len(cleaned_content) != len(content):
                        with open(filepath, "wb") as f:
                            f.write(cleaned_content)
                        print(f"✅ 清理: {filepath}")
                        cleaned_count += 1

                except Exception as e:
                    print(f"❌ 錯誤處理 {filepath}: {e}")

    print(f"🎉 完成清理 {cleaned_count} 個文件中的 null bytes")


if __name__ == "__main__":
    clean_null_bytes()
