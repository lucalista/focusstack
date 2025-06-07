import sys
sys.path.append('../')
from gui.logging import QTextEditLogger, LogManager
from PySide6.QtWidgets import (QWidget, QApplication, QMainWindow, QPushButton, QVBoxLayout)


class MainWindow(QMainWindow, LogManager):
    def __init__(self):
        QMainWindow.__init__(self)
        LogManager.__init__(self)
        self.setWindowTitle("Main Window")
        layout = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        self.button_w = QPushButton("New window")
        layout.addWidget(self.button_w)
        self.button_w.clicked.connect(self.show_new_window)
        self.button_l = QPushButton("Start thread")
        layout.addWidget(self.button_l)
        self.button_l.clicked.connect(self.start_thread)
        self.setCentralWidget(widget)

    def before_thread_begins(self):
        self.button_l.setEnabled(False)

    def _do_handle_end_message(self, int):
        self.button_l.setEnabled(True)

    def show_new_window(self, checked):
        text_edit = QTextEditLogger()
        text_edit.resize(600, 600)
        text_edit.show()
        self.add_tex_edit(text_edit)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
