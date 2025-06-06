import sys
import os
import re
from time import sleep
import logging
from logging import Handler, NOTSET
from rich.logging import RichHandler
from rich.console import Console
from PySide6.QtWidgets import QTextEdit, QApplication, QMainWindow
from PySide6.QtGui import QTextCursor, QTextOption, QFont

class QTextEditLogger(QTextEdit, Handler):
    """A QTextEdit logger that uses RichHandler to format log messages."""
    def __init__(self, parent=None, level=NOTSET):
        QTextEdit.__init__(self, parent)
        Handler.__init__(self,level=level)
        self.console = Console(file=open(os.devnull, "wt"), record=True, width=100, height=12, soft_wrap=False, color_system="truecolor", tab_size=4)
        self.rich_handler = RichHandler(show_time=False, show_path=False, show_level=True, markup=True, console=self.console, level=self.level)
        self.rich_handler.setLevel(self.level)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setAcceptRichText(True)
        self.setReadOnly(True)
        font = QFont(['Menlo','DejaVu Sans Mono','consolas','Courier New','monospace'], 16, self.font().weight())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)

    def emit(self, record) -> None:
        """Override the emit method to handle log records."""
        self.rich_handler.emit(record)
        indent_width = 11*self.fontMetrics().averageCharWidth()
        html_template = f'<p style="background-color: {{background}}; color: {{foreground}}; margin: 0; margin-left:{indent_width}px; text-indent:-{indent_width}px;white-space: pre-wrap"><code>{{code}}</code></p>'
        html = self.console.export_html(clear=True, code_format=html_template, inline_styles=True)
        # remove padding at end of string, since that stems from console width wich is invalid here
        html = re.sub(r'\s+[\n]', '\n', html) 
        self.insertHtml(html)
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().maximum())  
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QTextEdit Example")

        # Create a QTextEdit widget
        self.text_edit = QTextEditLogger(self)
        self.setCentralWidget(self.text_edit)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(600, 600)
    window.show()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(window.text_edit)
    logger.info("This is an info message.")
    sleep(.5)
    logger.warning("This is a warning message.")
    sleep(.5)
    for i in range(10):
        logger.debug(f"This is a debug message {i}.")
    logger.error("This is an error message.")
    sys.exit(app.exec())
