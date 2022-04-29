import io
import logging
import sys
from PIL import Image
import numpy as np
from googletrans import Translator
import pytesseract

from PySide6.QtCore import QDir, QPoint, QRect, QStandardPaths, Qt, QTimer, Slot, QBuffer
from PySide6.QtGui import QGuiApplication, QImageWriter
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QSizePolicy, QSpinBox,
                               QVBoxLayout, QWidget)


class CatchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowOpacity(0.3)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Catch window")


class Screenshot(QWidget):
    def __init__(self, catch_window: QWidget):
        super().__init__()

        self.trans = Trans()
        self.catch_window = catch_window
        self.original_pixmap = None

        self.translated_label = QLabel(self)
        self.translated_label.setWordWrap(True)
        self.translated_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.translated_label.setAlignment(Qt.AlignCenter)

        self.screenshot_label = QLabel(self)
        self.screenshot_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.screenshot_label.setAlignment(Qt.AlignCenter)

        screen_geometry: QRect = self.screen().geometry()
        self.screenshot_label.setMinimumSize(
            screen_geometry.width() / 8, screen_geometry.height() / 8
        )

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.screenshot_label)
        main_layout.addWidget(self.translated_label)

        options_group_box = QGroupBox("Options", self)

        self.hide_catch_window_checkbox = QCheckBox("Hide the catch Window", options_group_box)
        self.hide_screenshot_checkbox = QCheckBox("Hide the screenshot", options_group_box)
        self.auto_recognize_checkbox = QCheckBox("Auto recognize", options_group_box)
        self.hide_catch_window_checkbox.clicked.connect(self.hide_catch_window)
        self.hide_screenshot_checkbox.clicked.connect(self.hide_screenshot)
        self.auto_recognize_checkbox.clicked.connect(self.auto_recognize)

        options_group_box_layout = QGridLayout(options_group_box)
        options_group_box_layout.addWidget(self.hide_catch_window_checkbox, 0, 0, 1, 2)
        options_group_box_layout.addWidget(self.hide_screenshot_checkbox, 1, 0, 1, 2)
        options_group_box_layout.addWidget(self.auto_recognize_checkbox, 2, 0, 1, 2)

        main_layout.addWidget(options_group_box)

        buttons_layout = QHBoxLayout()
        self.new_screenshot_button = QPushButton("Recognize", self)
        self.new_screenshot_button.clicked.connect(self.shoot_screen)
        buttons_layout.addWidget(self.new_screenshot_button)

        clear_button = QPushButton("Clear", self)
        clear_button.clicked.connect(self.clear_text)
        buttons_layout.addWidget(clear_button)

        quit_screenshot_button = QPushButton("Quit", self)
        quit_screenshot_button.setShortcut(Qt.CTRL | Qt.Key_Q)
        quit_screenshot_button.clicked.connect(self.close)
        buttons_layout.addWidget(quit_screenshot_button)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        self.setWindowTitle("miku-tools")
        self.resize(400, 200)

        self.recognize_timer = QTimer(self)
        self.recognize_timer.timeout.connect(self.shoot_screen)

    def closeEvent(self, event):
        self.catch_window.close()

    def shoot_screen(self):
        """take screenshot at catch window"""
        screen = QGuiApplication.primaryScreen()
        window = self.windowHandle()
        if window:
            screen = window.screen()
        if not screen:
            return

        self.original_pixmap = screen.grabWindow(
            x=self.catch_window.x(),
            # magic number to avoid the window
            y=self.catch_window.y() + 28,
            w=self.catch_window.width(),
            h=self.catch_window.height(),
        )

        self.update_label()

    def clear_text(self):
        self.translated_label.clear()
        self.screenshot_label.clear()

    def hide_screenshot(self):
        if self.hide_screenshot_checkbox.isChecked():
            self.screenshot_label.setHidden(True)
        else:
            self.screenshot_label.setHidden(False)

    def hide_catch_window(self):
        if self.hide_catch_window_checkbox.isChecked():
            self.catch_window.setHidden(True)
        else:
            self.catch_window.setHidden(False)

    def auto_recognize(self):
        """recognize every 2000 seconds"""
        if self.auto_recognize_checkbox.isChecked():
            self.recognize_timer.start(2000)
        else:
            self.recognize_timer.stop()

    def update_label(self):
        """recognize the text, and show the translation"""
        self.screenshot_label.setPixmap(
            self.original_pixmap.scaled(
                self.screenshot_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        self.original_pixmap.save(buffer, "PNG")
        img = Image.open(io.BytesIO(buffer.data()))
        img = np.array(img)
        origin, text = self.trans.recognize(img)
        self.translated_label.setText(f"{origin}\n{text}")


class Trans:
    def __init__(self):
        self.prev_text = self.res = self.text = None
        self.trans = Translator()

    def ocr(self, image: np.array, lang='jpn'):
        text: str = pytesseract.image_to_string(image, lang=lang)
        self.text = text.replace(' ', '')
        logging.debug(f"ocr result: {self.text}")

    def translate(self, dest="zh-cn"):
        self.res = self.trans.translate(self.text, dest=dest)
        logging.info(f"{self.text} -> {self.res.text}")

    def recognize(self, image, lang='jpn', dest='zh-cn'):
        self.ocr(image, lang)
        # if already translate it, wait return the previous result
        if self.prev_text != self.text:
            self.prev_text = self.text
            self.translate()
        return self.text, self.res.text


if __name__ == "__main__":
    # logger = logging.getLogger("root")
    # logger.setLevel(logging.DEBUG)
    app = QApplication(sys.argv)
    widget = CatchWindow()
    widget.resize(750, 100)
    widget.show()
    screenshot = Screenshot(widget)
    screenshot.move(screenshot.screen().availableGeometry().topLeft() + QPoint(20, 20))
    screenshot.show()

    sys.exit(app.exec())
