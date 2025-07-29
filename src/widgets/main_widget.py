# This Python file uses the following encoding: utf-8
from PySide6.QtWidgets import QWidget
import logging

from ..ui.ui_form import Ui_Widget
from utils.config import setup_logging


class MainWidget(QWidget):
    """主窗口组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setWindowTitle("行情系统")

        # 创建logger
        self.logger = setup_logging(name="main_widget")
        self.logger.debug("MainWidget initialized")

        # 初始化UI
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.logger.debug("Setting up UI components")
        # 在这里添加UI初始化代码
