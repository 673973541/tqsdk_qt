"""应用程序主类"""

import sys
from PySide6.QtWidgets import QApplication

from .widgets.main_widget import MainWidget
from .utils.config import setup_logging, Config


class MarketApp:
    """行情应用程序主类"""

    def __init__(self):
        self.config = Config()
        self.logger = setup_logging()
        self.app = None
        self.main_widget = None

    def run(self):
        """运行应用程序"""
        self.logger.info(f"Starting {self.config.app_name} v{self.config.version}")

        # 创建QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(self.config.app_name)
        self.app.setApplicationVersion(self.config.version)

        # 创建主窗口
        self.logger.info("Creating main widget")
        self.main_widget = MainWidget()
        self.main_widget.show()

        # 运行事件循环
        self.logger.info("Starting event loop")
        return self.app.exec()

    def quit(self):
        """退出应用程序"""
        if self.app:
            self.logger.info("Quitting application")
            self.app.quit()
