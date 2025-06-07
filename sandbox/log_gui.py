import sys
import os
import re
from time import sleep
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.style import Style
from PySide6.QtWidgets import (QWidget, QTextEdit, QApplication, QMainWindow, QPushButton, QVBoxLayout, QLabel)
from PySide6.QtGui import QTextCursor, QTextOption, QFont
from PySide6.QtCore import QThread, Signal


class QtLogFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    COLORS = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red bold'
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        fmt = f"[blue3][[{color}]%(levelname).3s[/] %(asctime)s] %(message)s[/]"  # noqa
        return self.ANSI_ESCAPE.sub('', logging.Formatter(fmt).format(record).replace("\r", "").rstrip())


class HtmlRichHandler(RichHandler):
    def __init__(self, text_edit):
        self.console = Console(file=open(os.devnull, "wt"), record=True, width=100, height=20, highlight=False,
                               soft_wrap=False, color_system="truecolor", tab_size=4)
        RichHandler.__init__(self, show_time=False, show_path=False, show_level=False, markup=True,
                             console=self.console)
        self.setFormatter(QtLogFormatter())
        self.text_edit = text_edit

    def emit(self, record) -> None:
        RichHandler.emit(self, record)
        indent_width = 11*self.text_edit.fontMetrics().averageCharWidth()
        html_template = f'<p style="background-color: {{background}}; color: {{foreground}}; margin: 0; margin-left:{indent_width}px; text-indent:-{indent_width}px;white-space: pre-wrap"><code>{{code}}</code></p>'
        html = self.console.export_html(clear=True, code_format=html_template, inline_styles=True)
        self.text_edit.emit_html(html)


class QTextEditLogger(QTextEdit):
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setAcceptRichText(True)
        self.setReadOnly(True)
        font = QFont(['Menlo','DejaVu Sans Mono','consolas','Courier New','monospace'], 12, self.font().weight())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)

    def emit_html(self, html):
        pattern = r'<span style="color: #00ff00; text-decoration-color: #00ff00; font-weight: bold">(\d{2}:\d{2}:\d{2})</span>'
        replacement = r'<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">\1</span>'
        html = re.sub(pattern, replacement, re.sub(r'\s+[\n]', '\n', html))
        self.insertHtml(html)
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().maximum())  
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)
        QApplication.processEvents()
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        
    def show_new_window(self, checked):
        self.text_edit = QTextEditLogger()
        self.text_edit.resize(600, 600)
        self.text_edit.show()

    def start_thread(self):
        self.button_l.setEnabled(False)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.handler = HtmlRichHandler(self.text_edit)
        self.handler.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.log_worker = LogWorker()
        self.log_worker.log_signal.connect(self.handle_log_message)
        self.log_worker.html_signal.connect(self.handle_html_message)
        self.log_worker.end_signal.connect(self.handle_end_message)
        self.log_worker.start()

    def add_html(self, html):
        self.text_edit.insertHtml(html)

    def handle_log_message(self, level, message):
        logger = logging.getLogger()
        {
            "INFO": logger.info,
            "WARNING": logger.warning,
            "DEBUG": logger.debug,
            "ERROR": logger.error,
            "CRITICAL": logger.critical,
        }[level](message)            

    def handle_html_message(self, html):
        self.add_html(html)

    def handle_end_message(self, int):
        self.button_l.setEnabled(True)

class LogWorker(QThread):
    log_signal = Signal(str, str)
    html_signal = Signal(str)
    end_signal = Signal(int)
        
    def run(self):
        self.html_signal.emit("<h1>Begin thread</h1><br>")
        self.log_signal.emit("INFO", "This is an info message.")
        sleep(0.5)
        self.log_signal.emit("WARNING", "This is a warning message.")
        sleep(0.5)
        for i in range(10):
            self.log_signal.emit("DEBUG", f"This is a debug message {i}.")
            self.log_signal.emit("ERROR", "This is an error message.")
            self.log_signal.emit("CRITICAL", "Crash!!!")
            sleep(0.1)
        self.end_signal.emit(1)

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
    
