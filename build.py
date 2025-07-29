#!/usr/bin/env python3
"""构建脚本 - 生成UI文件"""
import os
import subprocess
from pathlib import Path


def build_ui():
    """构建UI文件"""
    project_root = Path(__file__).parent
    ui_file = project_root / "resources" / "form.ui"
    output_file = project_root / "src" / "ui" / "ui_form.py"

    if not ui_file.exists():
        print(f"UI文件不存在: {ui_file}")
        return False

    print(f"正在生成UI文件: {ui_file} -> {output_file}")

    try:
        subprocess.run(
            ["pyside6-uic", str(ui_file), "-o", str(output_file)], check=True
        )
        print("UI文件生成成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成UI文件失败: {e}")
        return False
    except FileNotFoundError:
        print("找不到 pyside6-uic 命令，请确保已安装 PySide6")
        return False


if __name__ == "__main__":
    build_ui()
