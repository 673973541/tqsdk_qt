#!/usr/bin/env python3
"""行情系统主入口文件"""
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.app import MarketApp


def main():
    """主函数"""
    app = MarketApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
