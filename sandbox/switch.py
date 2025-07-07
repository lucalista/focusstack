import sys
sys.path.append('../')
import os
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QTimer
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
        self.project_window = MainWindow()
        self.retouch_window = ImageEditorUI()
        self.stacked_widget.addWidget(self.project_window)
        self.stacked_widget.addWidget(self.retouch_window)
        self.create_menu()
        self.set_initial_app()

    def create_menu(self):
        menubar = self.menuBar()
        app_menu = menubar.addMenu("Applicazione")
        switch_to_project_window = QAction("Project", self)
        switch_to_project_window.triggered.connect(lambda: self.switch_app(0))
        switch_to_retouch_window = QAction("Retouch", self)
        switch_to_retouch_window.triggered.connect(lambda: self.switch_app(1))
        app_menu.addAction(switch_to_project_window)
        app_menu.addAction(switch_to_retouch_window)

    def switch_app(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def set_initial_app(self):
        import sys
        if "--retouch-window" in sys.argv:
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
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        if not os.path.isfile(file_to_open):
            print(f"File not found: {file_to_open}")
            file_to_open = None
    if file_to_open:
        extension = file_to_open.split('.')[-1]
        if extension == 'fsp':
            main_app.switch_app(0)
            QTimer.singleShot(100, lambda: main_app.project_window.open_project(file_to_open))
        elif extension in ['tif', 'tiff']:
            main_app.switch_app(1)
            QTimer.singleShot(100, lambda: main_app.retouch_window.open_file(file_to_open))
        else:
            print(f"File extension: {extension} not supported.")
    sys.exit(app.exec())
