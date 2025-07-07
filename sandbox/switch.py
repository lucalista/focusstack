import sys
sys.path.append('../')
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
from config.config import config
config.init(DISABLE_TQDM=True)
from core.logging import setup_logging
from gui.main_window import MainWindow
from gui.menu import DONT_USE_NATIVE_MENU
from retouch.image_editor_ui import ImageEditorUI
from gui.gui_utils import disable_macos_special_menu_items


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App Unificata")
        self.setGeometry(100, 100, 800, 600)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.app1 = MainWindow()
        self.app2 = ImageEditorUI()
        self.stacked_widget.addWidget(self.app1)
        self.stacked_widget.addWidget(self.app2)
        self.create_menu()
        self.set_initial_app()

    def create_menu(self):
        menubar = self.menuBar()
        app_menu = menubar.addMenu("Applicazione")
        switch_to_app1 = QAction("Project", self)
        switch_to_app1.triggered.connect(lambda: self.switch_app(0))
        switch_to_app2 = QAction("Retouch", self)
        switch_to_app2.triggered.connect(lambda: self.switch_app(1))
        app_menu.addAction(switch_to_app1)
        app_menu.addAction(switch_to_app2)

    def switch_app(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def set_initial_app(self):
        import sys
        if "--app2" in sys.argv:
            self.switch_app(1)
        else:
            self.switch_app(0)


if __name__ == "__main__":
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG,
                  log_file="logs/focusstack.log", disable_console=True)
    app = QApplication(sys.argv)
    if DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec())
