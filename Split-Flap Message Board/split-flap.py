#!/usr/bin/env python3
"""
Split-Flap Message Board
Framework: PySide6
Features:
- Borderless, draggable window
- Live text input
- Cinematic 3D-style split-flap animation (simulated via 2D transforms)
- True top/bottom bisection rendering (each half shows the correct portion of the glyph)
- Color pickers, customizable board size, fullscreen toggle
- Refresh Rate & Flip controls
- Click sound per half (external flip_click.wav in current working directory)
- Safe multimedia fallback
"""

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, Property, QUrl
)
from PySide6.QtGui import (
    QPainter, QFont, QColor, QLinearGradient, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QPushButton,
    QColorDialog, QLabel, QDialog, QSpinBox, QRadioButton, QButtonGroup, QGroupBox, QComboBox
)
import sys, random, math
from pathlib import Path

# ------------------------------------------------------
# Constants
# ------------------------------------------------------
FLAP_HEIGHT = 100
FLAP_WIDTH = 70
FONT_FAMILY = "DejaVu Sans"
MIN_GAP = 4
PADDING = 12
TOP_FLIP_MS = 200
BOTTOM_FLIP_MS = 200
SOUND_PATH = str(Path.cwd() / "flip_click.wav")

CHAR_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?@#$%&*-+= "

# ------------------------------------------------------
# FlapHalf Class
# - Renders the correct half of the full glyph by drawing
#   the full glyph into an offscreen pixmap and cropping.
# - Simulates a 3D flip by scaling in Y around the hinge.
# ------------------------------------------------------
class FlapHalf(QWidget):
    def __init__(self, char=' ', is_top=True, flap_color=QColor('#222'), text_color=QColor('#FFF'), parent=None):
        super().__init__(parent)
        self.is_top = is_top
        self._angle = 0.0  # degrees, 0..90
        self.char = char
        self.flap_color = flap_color
        self.text_color = text_color
        self._font = QFont(FONT_FAMILY, 36, QFont.Bold)
        self.setMinimumSize(FLAP_WIDTH, FLAP_HEIGHT // 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Render full glyph into offscreen pixmap (2 x half height)
        full_h = h * 2
        tmp = QPixmap(w, full_h)
        tmp.fill(Qt.transparent)
        tmp_p = QPainter(tmp)
        tmp_p.setRenderHint(QPainter.Antialiasing)
        tmp_p.setPen(self.text_color)
        tmp_p.setFont(self._font)
        fm = tmp_p.fontMetrics()
        text_w = fm.horizontalAdvance(self.char)
        # Choose baseline to vertically center glyph across the full height
        baseline_y = (full_h + fm.ascent() - fm.descent()) / 2
        tmp_p.drawText((w - text_w) / 2, baseline_y, self.char)
        tmp_p.end()

        # Crop the half we need
        if self.is_top:
            half_pix = tmp.copy(0, 0, w, h)
        else:
            half_pix = tmp.copy(0, h, w, h)

        # Compute vertical scale to simulate rotation
        angle_rad = math.radians(self._angle)
        scale_y = math.cos(angle_rad)
        # avoid exactly zero scale
        if abs(scale_y) < 0.001:
            scale_y = 0.001

        # Gradient background for depth
        grad = QLinearGradient(0, 0, 0, h)
        if self.is_top:
            grad.setColorAt(0, self.flap_color.lighter(135))
            grad.setColorAt(1, self.flap_color.darker(110))
        else:
            grad.setColorAt(0, self.flap_color)
            grad.setColorAt(1, self.flap_color.darker(160))

        # Draw the half with scaling around hinge
        painter.save()
        # hinge at bottom of top half, top of bottom half
        hinge_y = h if self.is_top else 0
        # Translate to hinge -> scale -> translate back (keeps hinge fixed)
        painter.translate(w / 2.0, hinge_y)
        painter.scale(1.0, scale_y)
        painter.translate(-w / 2.0, -hinge_y)

        # draw background and the cropped pixmap
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, w, h)
        painter.drawPixmap(0, 0, w, h, half_pix)

        # draw seam line for realism
        painter.setPen(QColor(0, 0, 0, 90))
        if self.is_top:
            painter.drawLine(0, h - 1, w, h - 1)
        else:
            painter.drawLine(0, 0, w, 0)

        painter.restore()

    # angle property used by animations
    def get_angle(self):
        return self._angle

    def set_angle(self, a):
        self._angle = float(a)
        self.update()

    angle = Property(float, get_angle, set_angle)


# ------------------------------------------------------
# FlapWidget (composite of two halves)
# ------------------------------------------------------
class FlapWidget(QWidget):
    def __init__(self, char=' ', flap_color=QColor('#111'), text_color=QColor('#FFF'), sound_effect=None, sound_enabled=True, parent=None):
        super().__init__(parent)
        self.flap_color = flap_color
        self.text_color = text_color
        self.sound_effect = sound_effect
        self.sound_enabled = sound_enabled
        self._current = char
        self._next = char

        self.top_half = FlapHalf(char, True, flap_color, text_color, parent=self)
        self.bottom_half = FlapHalf(char, False, flap_color, text_color, parent=self)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.top_half)
        layout.addWidget(self.bottom_half)

        self.setMinimumSize(FLAP_WIDTH, FLAP_HEIGHT)

    def play_click(self):
        if self.sound_effect and self.sound_enabled:
            try:
                self.sound_effect.play()
            except Exception:
                pass

    def animate_to(self, new_char):
        if new_char is None:
            new_char = ' '
        if new_char == self._current:
            return
        self._next = new_char

        # Top half: 0 -> 90
        top_anim = QPropertyAnimation(self.top_half, b"angle", self)
        top_anim.setStartValue(0.0)
        top_anim.setEndValue(90.0)
        top_anim.setDuration(TOP_FLIP_MS)
        top_anim.setEasingCurve(QEasingCurve.InOutCubic)

        # Connect finish -> swap text and start bottom animation
        top_anim.finished.connect(lambda: self._on_top_finished())
        # play click and start
        self.play_click()
        top_anim.start()

    def _on_top_finished(self):
        # swap glyphs
        self._current = self._next
        self.top_half.char = self._current
        self.bottom_half.char = self._current
        # reset top_half angle to 0 so it appears closed for new char
        self.top_half.set_angle(0.0)
        # set bottom to flat (90) and animate to 0
        self.bottom_half.set_angle(90.0)

        bottom_anim = QPropertyAnimation(self.bottom_half, b"angle", self)
        bottom_anim.setStartValue(90.0)
        bottom_anim.setEndValue(0.0)
        bottom_anim.setDuration(BOTTOM_FLIP_MS)
        bottom_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.play_click()
        bottom_anim.start()

    def set_flap_color(self, color: QColor):
        self.flap_color = color
        self.top_half.flap_color = color
        self.bottom_half.flap_color = color
        self.top_half.update(); self.bottom_half.update(); self.update()

    def set_text_color(self, color: QColor):
        self.text_color = color
        self.top_half.text_color = color
        self.bottom_half.text_color = color
        self.top_half.update(); self.bottom_half.update(); self.update()


# ------------------------------------------------------
# CustomizationDialog
# ------------------------------------------------------
class CustomizationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Board Customization")
        self.setModal(True)
        layout = QVBoxLayout(self)

        # radio size selectors
        self.radio_group = QButtonGroup(self)
        sizes_box = QGroupBox("Select Board Size")
        size_layout = QVBoxLayout()
        self.small_radio = QRadioButton("Small (3 x 15)")
        self.medium_radio = QRadioButton("Medium (6 x 20)")
        self.large_radio = QRadioButton("Large (9 x 25)")
        self.custom_radio = QRadioButton("Custom Size")
        for r in [self.small_radio, self.medium_radio, self.large_radio, self.custom_radio]:
            self.radio_group.addButton(r)
            size_layout.addWidget(r)
        sizes_box.setLayout(size_layout)
        layout.addWidget(sizes_box)

        # custom spinboxes
        self.custom_row = QSpinBox(); self.custom_row.setRange(1, 20)
        self.custom_col = QSpinBox(); self.custom_col.setRange(1, 30)
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Rows:")); custom_layout.addWidget(self.custom_row)
        custom_layout.addWidget(QLabel("Cols:")); custom_layout.addWidget(self.custom_col)
        layout.addLayout(custom_layout)

        # preview
        self.preview = QWidget(self)
        self.preview_layout = QGridLayout(self.preview)
        self.preview_layout.setSpacing(2)
        layout.addWidget(self.preview)

        # buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply"); cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(apply_btn); btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        apply_btn.clicked.connect(self.accept); cancel_btn.clicked.connect(self.reject)

        for btn in [self.small_radio, self.medium_radio, self.large_radio, self.custom_radio]:
            btn.toggled.connect(self.update_preview)
        self.custom_row.valueChanged.connect(self.update_preview)
        self.custom_col.valueChanged.connect(self.update_preview)

        self.small_radio.setChecked(True)
        self.custom_row.setValue(3); self.custom_col.setValue(15)
        self.update_preview()

    def get_size(self):
        if self.small_radio.isChecked(): return 3, 15
        if self.medium_radio.isChecked(): return 6, 20
        if self.large_radio.isChecked(): return 9, 25
        return self.custom_row.value(), self.custom_col.value()

    def update_preview(self):
        for i in reversed(range(self.preview_layout.count())):
            w = self.preview_layout.itemAt(i).widget()
            self.preview_layout.removeWidget(w); w.setParent(None)
        rows, cols = self.get_size()
        for r in range(rows):
            for c in range(cols):
                placeholder = FlapWidget(' ', QColor('#333'), QColor('#777'))
                self.preview_layout.addWidget(placeholder, r, c)


# ------------------------------------------------------
# RefreshRateDialog
# ------------------------------------------------------
class RefreshRateDialog(QDialog):
    def __init__(self, parent=None, current_ms=0):
        super().__init__(parent)
        self.setWindowTitle('Refresh Rate')
        self.setModal(True)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.value_spin = QSpinBox(); self.value_spin.setRange(0, 9999)
        self.unit_combo = QComboBox(); self.unit_combo.addItems(['Seconds', 'Minutes'])
        row.addWidget(QLabel('Interval:')); row.addWidget(self.value_spin); row.addWidget(self.unit_combo)
        layout.addLayout(row)
        btn_row = QHBoxLayout(); apply = QPushButton('Apply'); cancel = QPushButton('Cancel')
        btn_row.addWidget(apply); btn_row.addWidget(cancel); layout.addLayout(btn_row)
        apply.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        if current_ms and current_ms > 0:
            if current_ms >= 60000 and current_ms % 60000 == 0:
                self.unit_combo.setCurrentText('Minutes'); self.value_spin.setValue(current_ms // 60000)
            else:
                self.unit_combo.setCurrentText('Seconds'); self.value_spin.setValue(max(1, current_ms // 1000))

    def get_interval_ms(self):
        val = self.value_spin.value(); unit = self.unit_combo.currentText()
        return val * 60 * 1000 if unit == 'Minutes' else val * 1000


# ------------------------------------------------------
# Main board
# ------------------------------------------------------
class SplitFlapBoard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.flap_color, self.text_color = QColor('#111'), QColor('#FFF')
        self.rows, self.cols = 3, 15
        self._drag_pos = None

        # sound init BEFORE building board
        try:
            from PySide6.QtMultimedia import QSoundEffect
            self.sound_effect = QSoundEffect()
            self.sound_effect.setSource(QUrl.fromLocalFile(SOUND_PATH))
            self.sound_effect.setVolume(0.25)
            self.sound_enabled = True
        except Exception as e:
            print("Warning: QSoundEffect unavailable or flip_click.wav missing:", e)
            self.sound_effect, self.sound_enabled = None, False

        # UI
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        ctrl_row = QHBoxLayout()

        self.input = QLineEdit(self)
        self.input.setPlaceholderText('Type message here...')
        self.input.textChanged.connect(self.on_text_changed)
        ctrl_row.addWidget(self.input, 1)

        self.btn_customize = QPushButton('Customize'); self.btn_customize.clicked.connect(self.open_customize_dialog); ctrl_row.addWidget(self.btn_customize)
        self.btn_refresh_rate = QPushButton('Refresh Rate'); self.btn_refresh_rate.clicked.connect(self.open_refresh_dialog); ctrl_row.addWidget(self.btn_refresh_rate)
        self.btn_flip = QPushButton('Flip'); self.btn_flip.clicked.connect(self.trigger_flip_sequence); ctrl_row.addWidget(self.btn_flip)
        self.btn_sound = QPushButton('Sound: On'); self.btn_sound.setCheckable(True); self.btn_sound.setChecked(self.sound_enabled); self.btn_sound.toggled.connect(self._toggle_sound); ctrl_row.addWidget(self.btn_sound)
        self.btn_flap_color = QPushButton('Flap Color'); self.btn_flap_color.clicked.connect(self.pick_flap_color); ctrl_row.addWidget(self.btn_flap_color)
        self.btn_text_color = QPushButton('Text Color'); self.btn_text_color.clicked.connect(self.pick_text_color); ctrl_row.addWidget(self.btn_text_color)
        self.btn_fullscreen = QPushButton('Fullscreen'); self.btn_fullscreen.clicked.connect(self.toggle_fullscreen); ctrl_row.addWidget(self.btn_fullscreen)
        self.btn_close = QPushButton('✕'); self.btn_close.clicked.connect(self.close); ctrl_row.addWidget(self.btn_close)

        self._main_layout.addLayout(ctrl_row)

        self.flap_container = QWidget(self)
        self.flap_layout = QGridLayout(self.flap_container)
        self.flap_layout.setSpacing(MIN_GAP)
        self._main_layout.addWidget(self.flap_container, 1)

        self.status = QLabel('Drag to move. Double-click toggles fullscreen.')
        self._main_layout.addWidget(self.status)

        self.flaps = []
        self.build_board(self.rows, self.cols)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.trigger_flip_sequence)
        self.refresh_interval_ms = 0

    def _toggle_sound(self, checked):
        self.sound_enabled = bool(checked)
        self.btn_sound.setText(f"Sound: {'On' if self.sound_enabled else 'Off'}")

    def build_board(self, rows, cols):
        for i in reversed(range(self.flap_layout.count())):
            w = self.flap_layout.itemAt(i).widget()
            self.flap_layout.removeWidget(w)
            w.setParent(None)
        self.flaps = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                f = FlapWidget(' ', self.flap_color, self.text_color, parent=self, sound_effect=self.sound_effect, sound_enabled=self.sound_enabled)
                self.flap_layout.addWidget(f, r, c)
                row_list.append(f)
            self.flaps.append(row_list)
        self.rows, self.cols = rows, cols

    def on_text_changed(self, text):
        chars = list(text) if text else []
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                ch = chars[idx] if idx < len(chars) else ' '
                f = self.flaps[r][c]
                f._current = ch
                f.top_half.char = ch
                f.bottom_half.char = ch
                f.top_half.update(); f.bottom_half.update()
                idx += 1

    def open_refresh_dialog(self):
        dlg = RefreshRateDialog(self, current_ms=self.refresh_interval_ms)
        dlg.raise_(); dlg.activateWindow()
        if dlg.exec_():
            ms = dlg.get_interval_ms()
            self.refresh_interval_ms = ms
            if ms > 0: self.refresh_timer.start(ms)
            else: self.refresh_timer.stop()

    def trigger_flip_sequence(self):
        original_text = self.input.text() or ''
        final_chars = []
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                final_chars.append(original_text[idx] if idx < len(original_text) else ' ')

        cycles = 3
        per_flap_delay = 120
        per_flip_total = TOP_FLIP_MS + BOTTOM_FLIP_MS + 20

        base_row_delay = 0
        for r in range(self.rows):
            for c in range(self.cols):
                flap = self.flaps[r][c]
                final_char = final_chars[r * self.cols + c]
                start_time = base_row_delay + c * per_flap_delay
                for j in range(cycles):
                    t = start_time + j * per_flip_total
                    ch = random.choice(CHAR_POOL)
                    QTimer.singleShot(t, lambda f=flap, chx=ch: f.animate_to(chx))
                end_t = start_time + cycles * per_flip_total
                QTimer.singleShot(end_t, lambda f=flap, chx=final_char: f.animate_to(chx))
            row_duration = self.cols * per_flap_delay + cycles * per_flip_total + 200
            base_row_delay += row_duration

    def open_customize_dialog(self):
        dlg = CustomizationDialog(self)
        dlg.raise_(); dlg.activateWindow()
        if dlg.exec_():
            r, c = dlg.get_size(); self.build_board(r, c)

    def pick_flap_color(self):
        col = QColorDialog.getColor(self.flap_color, self)
        if col.isValid():
            self.flap_color = col
            for row in self.flaps:
                for f in row: f.set_flap_color(col)

    def pick_text_color(self):
        col = QColorDialog.getColor(self.text_color, self)
        if col.isValid():
            self.text_color = col
            for row in self.flaps:
                for f in row: f.set_text_color(col)

    def open_refresh_dialog(self):
        dlg = RefreshRateDialog(self, current_ms=self.refresh_interval_ms)
        dlg.raise_(); dlg.activateWindow()
        if dlg.exec_():
            ms = dlg.get_interval_ms(); self.refresh_interval_ms = ms
            if ms > 0: self.refresh_timer.start(ms)
            else: self.refresh_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self.toggle_fullscreen()

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()


# ------------------------------------------------------
# Main
# ------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    win = SplitFlapBoard()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
