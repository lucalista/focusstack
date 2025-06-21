from PySide6.QtWidgets import QApplication
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
import sys
import webbrowser
import subprocess
import os
import platform

PDF_FILE = "../tests/plots/vignette-r0.pdf"


class MyPdfView(QPdfView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mouseReleaseEvent(self, event):
        filepath = os.getcwd() + "/" + PDF_FILE
        try:
            if platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', filepath))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(filepath)
            else:                                   # linux variants
                subprocess.call(('xdg-open', filepath))
        except Exception:
            webbrowser.open("file://" + filepath)


def main():
    app = QApplication(sys.argv)
    document = QPdfDocument()
    document.load(PDF_FILE)
    view = MyPdfView()
    view.setWindowTitle("PDF")
    view.setDocument(document)
    view.setZoomFactor(0.25)
    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
