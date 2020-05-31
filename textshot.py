#!/usr/bin/env python3

import ctypes
import os
import sys

import platform
import pyperclip
import pyscreenshot as ImageGrab
import pytesseract
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

try:
    from pynotifier import Notification
except ImportError:
    pass


class Snipper(QtWidgets.QWidget):
    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        super().__init__(parent=parent, flags=flags)

        self.setWindowTitle("TextShot")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )

        self.is_macos = sys.platform.startswith("darwin")
        if self.is_macos:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
        else:
            self.setWindowState(self.windowState() | Qt.WindowFullScreen)

        self.setStyleSheet("background-color: black")
        self.setWindowOpacity(0.5)

        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        self.start, self.end = QtCore.QPoint(), QtCore.QPoint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QtWidgets.QApplication.quit()

        return super().keyPressEvent(event)

    def paintEvent(self, event):
        if self.start == self.end:
            return super().paintEvent(event)

        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 3))
        painter.setBrush(QtGui.QColor(255, 255, 255, 100))

        if self.is_macos:
            start, end = (self.mapFromGlobal(self.start), self.mapFromGlobal(self.end))
        else:
            start, end = self.start, self.end

        painter.drawRect(QtCore.QRect(start, end))
        return super().paintEvent(event)

    def mousePressEvent(self, event):
        self.start = self.end = QtGui.QCursor.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.end = QtGui.QCursor.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super().mouseReleaseEvent(event)

        scaleFactor = 1.0
        # Require further fix to work for multiple monitors with different scale factors
        if platform.system() == "Linux":
            if float(os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']) == 0.0:
                if "QT_SCALE_FACTOR" in os.environ:
                    scaleFactor = float(os.environ['QT_SCALE_FACTOR'])
                elif "QT_SCREEN_SCALE_FACTORS" in os.environ:
                    qtScreenScaleFactors = {f.split('=')[0]:float(f.split('=')[1]) for f in os.environ['QT_SCREEN_SCALE_FACTORS'].split(';') if f}
                    scaleFactor = qtScreenScaleFactors['DP1']
            else:
                scaleFactor = float(os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'])

        x1, x2 = sorted((int(self.start.x() * scaleFactor), int(self.end.x() * scaleFactor)))
        y1, y2 = sorted((int(self.start.y() * scaleFactor), int(self.end.y() * scaleFactor)))

        self.hide()
        QtWidgets.QApplication.processEvents()
        shot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        processImage(shot)
        QtWidgets.QApplication.quit()


def processImage(img):
    try:
        result = pytesseract.image_to_string(
            img, timeout=2, lang=(sys.argv[1] if len(sys.argv) > 1 else None)
        )
    except RuntimeError as error:
        print(f"ERROR: An error occurred when trying to process the image: {error}")
        notify(f"An error occurred when trying to process the image: {error}")
        return

    if result:
        pyperclip.copy(result)
        print(f'INFO: Copied "{result}" to the clipboard')
        notify(f'Copied "{result}" to the clipboard')
    else:
        print(f"INFO: Unable to read text from image, did not copy")
        notify(f"Unable to read text from image, did not copy")


def notify(msg):
    try:
        Notification(title="TextShot", description=msg).send()
    except (SystemError, NameError):
        trayicon = QtWidgets.QSystemTrayIcon(
            QtGui.QIcon(
                QtGui.QPixmap.fromImage(QtGui.QImage(1, 1, QtGui.QImage.Format_Mono))
            )
        )
        trayicon.show()
        trayicon.showMessage("TextShot", msg, QtWidgets.QSystemTrayIcon.NoIcon)
        trayicon.hide()


if __name__ == "__main__":
    try:
        pytesseract.get_tesseract_version()
    except EnvironmentError:
        notify(
            "Tesseract is either not installed or cannot be reached.\n"
            "Have you installed it and added the install directory to your system path?"
        )
        print(
            "ERROR: Tesseract is either not installed or cannot be reached.\n"
            "Have you installed it and added the install directory to your system path?"
        )
        sys.exit()

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    snipper = Snipper(window)
    snipper.show()
    sys.exit(app.exec_())
