#!/usr/bin/env python3

import ctypes
import os
import sys

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
        self.start = self.end = (
            event.pos() if not self.is_macos else QtGui.QCursor.pos()
        )
        self.update()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.end = event.pos() if not self.is_macos else QtGui.QCursor.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super().mouseReleaseEvent(event)

        # get correct postions by multipying the scale factor
        scale_factor = float(os.environ['GDK_SCALE'])
        x1, x2 = sorted((int(self.start.x() * scale_factor), int(self.end.x() * scale_factor)))
        y1, y2 = sorted((int(self.start.y() * scale_factor), int(self.end.y() * scale_factor)))

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
        # trim space between Chinese characters
        print(result)
        refined_result = []
        for i, c in enumerate(result):
            if i == 0 or i == len(result) - 1:
                refined_result.append(c)
                continue
            if c == ' ' and (not result[i-1].isascii()) and (not result[i+1].isascii()):
                continue
            refined_result.append(c)
        refined_result = ''.join(refined_result).strip()

        pyperclip.copy(refined_result)
        print(f'INFO: Copied "{refined_result}" to the clipboard')
        notify(f'Copied "{refined_result}" to the clipboard')
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

    if os.name == "nt":
        ctypes.windll.user32.SetProcessDPIAware()

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    snipper = Snipper(window)
    snipper.show()
    sys.exit(app.exec_())
