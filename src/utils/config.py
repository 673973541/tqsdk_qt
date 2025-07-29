"""配置管理模块"""

import logging
import os
from pathlib import Path


def setup_logging(level=logging.DEBUG, name="app"):
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


class Config:
    """应用配置类"""

    def __init__(self):
        self.app_name = "行情系统"
        self.version = "1.0.0"
        self.window_title = "Market Trading System"

        # 路径配置
        self.root_dir = Path(__file__).parent.parent.parent
        self.resources_dir = self.root_dir / "resources"
        self.ui_dir = self.root_dir / "src" / "ui"

    def get_ui_file_path(self, filename):
        """获取UI文件路径"""
        return self.ui_dir / filename

    def get_resource_path(self, filename):
        """获取资源文件路径"""
        return self.resources_dir / filename
