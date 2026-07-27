"""
app.py — cửa sổ chính.

Chạy:  python app.py
"""

from __future__ import annotations

import sys
import time
from enum import Enum, auto
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QShortcut, QSplitter, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

import pipeline
from workers import ConnectWorker, OcrWorker, ScanWorker

# Khi đóng gói bằng PyInstaller, đọc config/data cạnh file .exe để người dùng
# vẫn chỉnh sửa được; khi chạy mã nguồn thì lấy thư mục chứa app.py.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
APP_TITLE = "SaoMai OCR36 -v1.0"

MONO = "Consolas" if sys.platform == "win32" else "Menlo"

# Bảng màu lấy nguyên từ prototype.html (tông giấy ấm — paper).
C = {
    "s2": "#ffffff", "s1": "#f7f6f2", "s0": "#f1efe8",
    "chrome": "#eceae3", "line": "#e3e1da", "line2": "#d3d1c7",
    "tp": "#2c2c2a", "ts": "#73726c", "tm": "#9c9a92",
    "acc": "#185fa5", "acc_bg": "#e6f1fb", "acc_line": "#85b7eb",
    "ok": "#0f6e56", "warn": "#854f0b", "dan": "#a32d2d",
}

LOG_COLORS = {
    "info": C["ts"],
    "data": C["tp"],
    "warn": C["warn"],
    "error": C["dan"],
    "hint": C["tm"],
}

POLICY_LABEL = {"correct": "sửa", "protect": "bảo vệ", "skip": "bỏ qua"}
POLICY_COLOR = {"correct": C["ok"], "protect": C["warn"], "skip": C["tm"]}


def build_stylesheet() -> str:
    """QSS mô phỏng phong cách prototype.html cho toàn bộ ứng dụng."""
    return f"""
    QMainWindow, QWidget#central {{ background:{C['s2']}; }}
    QWidget {{ color:{C['tp']}; font-size:12px; }}
    QToolTip {{ background:{C['tp']}; color:#ffffff; border:none;
        padding:4px 7px; font-size:11px; }}

    /* thanh nguồn */
    QFrame#srcBar {{ background:{C['s2']};
        border:none; border-bottom:1px solid {C['line']}; }}
    QLabel#srcLbl {{ color:{C['ts']}; font-size:12px; }}
    QPushButton#pill {{ background:transparent; border:1px solid {C['line']};
        border-radius:6px; padding:3px 11px; color:{C['ts']}; font-size:12px; }}
    QPushButton#pill:hover {{ border-color:{C['line2']}; }}
    QPushButton#pill:checked {{ background:{C['acc_bg']};
        border-color:{C['acc_bg']}; color:{C['acc']}; }}
    QLineEdit#path {{ background:{C['s2']}; border:1px solid {C['line']};
        border-radius:6px; padding:6px 9px; font-family:"{MONO}";
        font-size:11px; color:{C['tp']}; }}

    /* thanh ước lượng (progress bar + thông tin) */
    QFrame#estBar {{ background:{C['s1']}; border:none;
        border-bottom:1px solid {C['line']}; }}
    QLabel#estText {{ color:{C['ts']}; font-family:"{MONO}"; font-size:11px; }}
    QProgressBar#prog {{ background:{C['s0']}; border:1px solid {C['line']};
        border-radius:5px; min-height:9px; max-height:9px; }}
    QProgressBar#prog::chunk {{ background:{C['acc']}; border-radius:4px; }}
    QProgressBar#prog[hold="true"]::chunk {{ background:{C['tm']}; }}

    /* panel cài đặt */
    QGroupBox {{ background:{C['s2']}; border:none;
        border-right:1px solid {C['line']}; margin-top:0; padding:8px 3px 3px; }}
    QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left;
        left:11px; top:2px; color:{C['tm']}; font-size:11px; }}
    QGroupBox QLabel {{ color:{C['ts']}; font-size:11px; }}
    QGroupBox QCheckBox {{ color:{C['ts']}; font-size:11px; spacing:7px; }}
    QGroupBox QCheckBox:disabled {{ color:{C['tm']}; }}
    QLineEdit#ro {{ background:{C['s1']}; border:none; border-radius:6px;
        padding:5px 7px; font-family:"{MONO}"; font-size:11px; color:{C['tp']}; }}
    QLineEdit#cfgin {{ font-family:"{MONO}"; font-size:11px; }}
    QLineEdit:disabled {{ background:{C['s1']}; color:{C['tm']}; }}

    QComboBox {{ background:{C['s2']}; border:1px solid {C['line']};
        border-radius:6px; padding:5px 7px; font-size:11px; color:{C['tp']}; }}
    QComboBox:hover {{ border-color:{C['line2']}; }}
    QComboBox::drop-down {{ border:none; width:18px; }}
    QComboBox QAbstractItemView {{ background:{C['s2']};
        border:1px solid {C['line2']}; border-radius:6px; padding:2px;
        selection-background-color:{C['acc_bg']}; selection-color:{C['acc']};
        outline:none; }}

    /* tabs */
    QTabWidget::pane {{ border:none; border-top:1px solid {C['line']};
        background:{C['s2']}; }}
    QTabBar {{ background:{C['s2']}; }}
    QTabBar::tab {{ background:transparent; color:{C['ts']}; padding:9px 13px;
        border:none; border-bottom:2px solid transparent; font-size:12px; }}
    QTabBar::tab:hover {{ color:{C['tp']}; }}
    QTabBar::tab:selected {{ color:{C['tp']};
        border-bottom:2px solid {C['acc_line']}; }}

    /* bảng */
    QTableWidget {{ background:{C['s2']}; border:none; gridline-color:transparent;
        font-size:12px; outline:none;
        selection-background-color:{C['s0']}; selection-color:{C['tp']}; }}
    QTableWidget::item {{ padding:4px 8px; border-bottom:1px solid {C['line']}; }}
    /* Chọn = nền xám nhạt (không sáng), giữ nguyên màu chữ để đọc/copy. */
    QTableWidget::item:selected {{ background:{C['s0']}; color:{C['tp']}; }}
    QTableWidget::item:focus {{ outline:none; }}
    QHeaderView::section {{ background:{C['s1']}; color:{C['ts']}; border:none;
        border-bottom:1px solid {C['line']}; padding:6px 10px;
        font-size:11px; font-weight:400; }}
    QTableCornerButton::section {{ background:{C['s1']}; border:none; }}

    /* console */
    QTextEdit#console {{ background:{C['s2']}; border:none; padding:6px 10px; }}

    /* ô nhập */
    QLineEdit {{ background:{C['s2']}; border:1px solid {C['line']};
        border-radius:6px; padding:5px 7px; color:{C['tp']}; }}
    QLineEdit:focus {{ border:1px solid {C['acc_line']}; }}

    /* nút */
    QPushButton {{ background:{C['s2']}; border:1px solid {C['line2']};
        border-radius:6px; padding:6px 12px; color:{C['tp']}; font-size:12px; }}
    QPushButton[mini="true"] {{ padding:5px 10px; font-size:11px; }}
    QPushButton:hover {{ background:{C['s1']}; }}
    QPushButton:pressed {{ background:{C['s0']}; }}
    QPushButton:disabled {{ color:{C['tm']}; border-color:{C['line']};
        background:{C['s2']}; }}
    QPushButton#pri {{ background:{C['acc']}; border-color:{C['acc']};
        color:#ffffff; font-weight:500; }}
    QPushButton#pri:hover {{ background:#2069b4; }}
    QPushButton#pri:disabled {{ background:#accae6; border-color:#accae6;
        color:#eef4fb; }}
    QPushButton#dan {{ background:{C['dan']}; border-color:{C['dan']};
        color:#ffffff; font-weight:500; }}
    QPushButton#dan:hover {{ background:#b83a3a; }}
    QPushButton#dan:disabled {{ background:#dcb3b3; border-color:#dcb3b3;
        color:#f7e9e9; }}

    /* thanh hành động */
    QFrame#actBar {{ background:{C['s1']}; border:none;
        border-top:1px solid {C['line']}; }}
    QLabel#count {{ color:{C['ts']}; font-family:"{MONO}"; font-size:11px; }}

    /* progress */
    QProgressBar {{ background:{C['line2']}; border:none;
        border-radius:3px; max-height:5px; }}
    QProgressBar::chunk {{ background:{C['acc']}; border-radius:3px; }}
    QProgressBar[hold="true"]::chunk {{ background:{C['tm']}; }}

    /* splitter */
    QSplitter::handle:horizontal {{ background:{C['line']}; width:1px; }}

    /* scrollbar */
    QScrollBar:vertical {{ background:{C['s1']}; width:10px; margin:0; }}
    QScrollBar::handle:vertical {{ background:{C['line2']};
        border-radius:5px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{C['tm']}; }}
    QScrollBar:horizontal {{ background:{C['s1']}; height:10px; margin:0; }}
    QScrollBar::handle:horizontal {{ background:{C['line2']};
        border-radius:5px; min-width:24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}
    """


class State(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RUNNING = auto()
    PAUSING = auto()
    PAUSED = auto()
    DONE = auto()          # đã xử lý xong: hiện "Kết quả" / "Chạy lại"


# ==================================================== TAB CONSOLE

class ConsoleTab(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)   # luôn wrap theo bề rộng
        # Giới hạn số dòng để batch lớn (hàng vạn file) không phình bộ nhớ.
        self.document().setMaximumBlockCount(5000)
        f = QFont(MONO, 10)
        f.setStyleHint(QFont.Monospace)
        self.setFont(f)
        self.append_log("hint", "Bấm “Kết nối server API” để bắt đầu.")

    def append_log(self, level: str, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        color = LOG_COLORS.get(level, LOG_COLORS["info"])
        prefix = "" if level in ("data", "hint") else f"[{ts}] "
        safe = (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("\t", " &nbsp;| "))
        weight = "500" if level == "data" else "400"
        style = "font-style:italic;" if level == "hint" else ""
        self.append(
            f'<span style="color:{color};font-weight:{weight};{style}">'
            f'{prefix}{safe}</span>'
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


# ==================================================== TAB METADATA

class MetadataTab(QWidget):
    """Bảng ba cột: Trường | Mô tả | Sửa lỗi. Chỉ cột Mô tả sửa được."""

    saved = pyqtSignal(int)     # số trường đã đổi — để ghi log Console

    def __init__(self, fields_path, correction_policy, parent=None):
        super().__init__(parent)
        self.fields_path = Path(fields_path)
        self.policy = dict(correction_policy)
        self.fields: dict = {}
        self._snapshot: dict = {}
        self._editing = False
        self._loading = False
        # Font ô 12px (đặt rõ ràng vì QSS không áp cỡ vào item bảng).
        self._font = QFont()
        self._font.setPixelSize(12)
        self._mono = QFont(MONO)
        self._mono.setPixelSize(12)
        self._mono.setStyleHint(QFont.Monospace)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QHBoxLayout()
        bar.setContentsMargins(11, 7, 11, 7)
        self.lbl_file = QLabel(self.fields_path.name)
        self.lbl_file.setStyleSheet(
            f"color:{C['tm']};font-family:'{MONO}';font-size:11px;")
        self.lbl_dirty = QLabel("")
        self.lbl_dirty.setStyleSheet(f"color:{C['warn']};font-size:11px;")

        self.btn_edit = QPushButton("Sửa")
        self.btn_undo = QPushButton("Hoàn tác")
        self.btn_save = QPushButton("Lưu")
        self.btn_save.setObjectName("pri")
        self.btn_edit.clicked.connect(self.enter_edit)
        self.btn_undo.clicked.connect(self.cancel_edit)
        self.btn_save.clicked.connect(self.save)

        bar.addWidget(self.lbl_file)
        bar.addStretch(1)
        bar.addWidget(self.lbl_dirty)
        bar.addWidget(self.btn_edit)
        bar.addWidget(self.btn_undo)
        bar.addWidget(self.btn_save)
        root.addLayout(bar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Trường", "Mô tả", "Sửa lỗi"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(2, 80)
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table)

        self.reload()
        self._apply_edit_state()

    # ---- dữ liệu

    def reload(self):
        try:
            self.fields = pipeline.load_fields(self.fields_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi",
                                 f"Không đọc được {self.fields_path.name}\n{e}")
            self.fields = {}
        self._populate()

    def _populate(self):
        self._loading = True
        self.table.setRowCount(0)
        for key, desc in self.fields.items():
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_key = QTableWidgetItem(key)
            it_key.setFlags(it_key.flags() & ~Qt.ItemIsEditable)
            it_key.setFont(self._mono)
            self.table.setItem(r, 0, it_key)

            it_desc = QTableWidgetItem(str(desc))
            it_desc.setToolTip(str(desc))
            it_desc.setFont(self._font)
            self.table.setItem(r, 1, it_desc)

            pol = self.policy.get(key, "skip")
            it_pol = QTableWidgetItem(POLICY_LABEL.get(pol, pol))
            it_pol.setFlags(it_pol.flags() & ~Qt.ItemIsEditable)
            it_pol.setFont(self._font)
            it_pol.setTextAlignment(Qt.AlignCenter)
            it_pol.setForeground(QColor(POLICY_COLOR.get(pol, C["tm"])))
            self.table.setItem(r, 2, it_pol)

        self.table.resizeRowsToContents()
        self._loading = False
        self._refresh_dirty()

    def _current(self) -> dict:
        out = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0).text()
            v = self.table.item(r, 1).text()
            out[k] = v
        return out

    # ---- chế độ sửa

    def enter_edit(self):
        self._editing = True
        self._snapshot = self._current()
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked
                                   | QAbstractItemView.SelectedClicked
                                   | QAbstractItemView.EditKeyPressed)
        self._apply_edit_state()

    def cancel_edit(self):
        if self.dirty_count() and QMessageBox.question(
                self, "Hoàn tác",
                f"Bỏ {self.dirty_count()} thay đổi chưa lưu?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._editing = False
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._populate()
        self._apply_edit_state()

    def save(self):
        new_fields = self._current()
        empty = [k for k, v in new_fields.items() if not v.strip()]
        if empty:
            QMessageBox.warning(self, "Mô tả rỗng",
                                "Các trường sau chưa có mô tả:\n"
                                + "\n".join(empty))
            return
        n_changed = self.dirty_count()
        try:
            backup = pipeline.save_fields(self.fields_path, new_fields)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không lưu được:\n{e}")
            return

        self.saved.emit(n_changed)
        self.fields = new_fields
        self._editing = False
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._populate()
        self._apply_edit_state()

        msg = f"Đã lưu {self.fields_path.name}"
        if backup:
            msg += f"\nBản sao lưu: {backup.name}"
        QMessageBox.information(self, "Đã lưu", msg)

    def dirty_count(self) -> int:
        if not self._editing:
            return 0
        cur = self._current()
        return sum(1 for k, v in cur.items() if self._snapshot.get(k) != v)

    def _on_item_changed(self, _item):
        if not self._loading:
            self._refresh_dirty()

    def _refresh_dirty(self):
        n = self.dirty_count()
        self.lbl_dirty.setText(f"{n} thay đổi chưa lưu" if n else "")
        self.btn_save.setEnabled(self._editing and n > 0)

    def _apply_edit_state(self):
        self.btn_edit.setVisible(not self._editing)
        self.btn_undo.setVisible(self._editing)
        self.btn_save.setVisible(self._editing)
        self.setStyleSheet(
            f"MetadataTab{{border:2px solid {C['acc_line']};}}"
            if self._editing else "")
        self._refresh_dirty()

    @property
    def editing(self) -> bool:
        return self._editing

    def set_edit_allowed(self, allowed: bool, reason=""):
        self.btn_edit.setEnabled(allowed)
        self.btn_edit.setToolTip("" if allowed else reason)


# ==================================================== TAB KẾT QUẢ

class ResultsTab(QWidget):
    """Bảng kết quả (QTableWidget): cột document_title rộng 1.5×, canh trái,
    kéo thả chỉnh rộng cột, công tắc 'Xuống dòng' để wrap ô, chọn hàng nền xám
    nhạt + Ctrl/Cmd+C copy."""

    COL_W = 150            # bề rộng cột thường (px)
    TITLE_MULT = 1.5       # document_title rộng gấp 1.5

    def __init__(self, field_keys, parent=None):
        super().__init__(parent)
        self.field_keys = list(field_keys)
        # Font ô 12px rõ ràng (QSS px không áp vào item bảng).
        self._font = QFont()
        self._font.setPixelSize(12)
        self._mono = QFont(MONO)
        self._mono.setPixelSize(12)
        self._mono.setStyleHint(QFont.Monospace)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Công cụ (số dòng + công tắc wrap) đặt ở góc phải thanh tab.
        self.tools = QWidget()
        tlay = QHBoxLayout(self.tools)
        tlay.setContentsMargins(0, 0, 11, 0)
        tlay.setSpacing(10)
        self.lbl_rows = QLabel("0 dòng")
        self.lbl_rows.setObjectName("count")
        self.chk_wrap = QCheckBox("Xuống dòng")
        self.chk_wrap.setCursor(Qt.PointingHandCursor)
        self.chk_wrap.toggled.connect(self._apply_wrap)
        tlay.addWidget(self.lbl_rows)
        tlay.addWidget(self.chk_wrap)

        self.table = QTableWidget(0, len(self.field_keys) + 1)
        self.table.setHorizontalHeaderLabels(["File"] + self.field_keys)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)

        hh = self.table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)   # canh trái header
        hh.setSectionResizeMode(QHeaderView.Interactive)         # kéo thả chỉnh rộng
        hh.setStretchLastSection(False)
        hh.setDefaultSectionSize(self.COL_W)
        hh.sectionResized.connect(self._on_section_resized)
        self.table.setColumnWidth(0, self.COL_W)
        for c, key in enumerate(self.field_keys, start=1):
            w = (int(self.COL_W * self.TITLE_MULT)
                 if key == "document_title" else self.COL_W)
            self.table.setColumnWidth(c, w)
        root.addWidget(self.table)

        # Chọn ô/hàng rồi Ctrl/Cmd+C để copy text.
        sc = QShortcut(QKeySequence.Copy, self.table)
        sc.activated.connect(self._copy_selection)

    def _copy_selection(self):
        rng = self.table.selectedRanges()
        if not rng:
            return
        r = rng[0]
        lines = []
        for row in range(r.topRow(), r.bottomRow() + 1):
            cells = []
            for col in range(r.leftColumn(), r.rightColumn() + 1):
                it = self.table.item(row, col)
                cells.append(it.text() if it else "")
            lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def _on_section_resized(self, *_):
        if self.chk_wrap.isChecked():
            self.table.resizeRowsToContents()

    # ---- API dùng bởi MainWindow

    def clear_rows(self):
        self.table.setRowCount(0)
        self.lbl_rows.setText("0 dòng")

    def add_result(self, result: dict):
        t = self.table
        r = t.rowCount()
        t.insertRow(r)

        it_name = QTableWidgetItem(result.get("name", ""))
        it_name.setFont(self._mono)
        it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
        if result.get("error"):
            it_name.setForeground(QColor(C["dan"]))
        t.setItem(r, 0, it_name)

        if result.get("error"):
            it = QTableWidgetItem(result["error"])
            it.setForeground(QColor(C["dan"]))
            it.setFont(self._font)
            it.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            t.setItem(r, 1, it)
            t.setSpan(r, 1, 1, len(self.field_keys))
        else:
            data = result.get("data") or {}
            for c, key in enumerate(self.field_keys, start=1):
                val = data.get(key, "")
                if pipeline.is_empty(val):
                    it = QTableWidgetItem("— trống")
                    it.setForeground(QColor(C["warn"]))
                else:
                    it = QTableWidgetItem(str(val))
                    it.setToolTip(str(val))
                it.setFont(self._font)
                it.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                t.setItem(r, c, it)

        if self.chk_wrap.isChecked():
            t.resizeRowToContents(r)
        t.scrollToBottom()
        self.lbl_rows.setText(f"{t.rowCount()} dòng")

    def _apply_wrap(self):
        on = self.chk_wrap.isChecked()
        self.table.setWordWrap(on)
        self.table.setTextElideMode(Qt.ElideNone if on else Qt.ElideRight)
        self.table.resizeRowsToContents()


# ==================================================== POPUP KẾT NỐI LẠI

class ReconnectDialog(QDialog):
    """Hiện khi mất kết nối server giữa batch. Bấm 'Kết nối lại' để thử; thành
    công thì đóng (UI tiếp tục), thất bại thì báo và giữ tạm dừng."""

    def __init__(self, endpoint, api_key, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mất kết nối server")
        self.setMinimumWidth(380)
        self.endpoint = endpoint
        self.api_key = api_key
        self._worker = None
        self.reconnected = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(12)
        self.lbl = QLabel(
            f"Mất kết nối tới server:\n{message}\n\n"
            "Batch đã tạm dừng. Thử kết nối lại?")
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)

        btns = QHBoxLayout()
        self.btn_pause = QPushButton("Để tạm dừng")
        self.btn_retry = QPushButton("Kết nối lại")
        self.btn_retry.setObjectName("pri")
        for b in (self.btn_pause, self.btn_retry):
            b.setCursor(Qt.PointingHandCursor)
        self.btn_pause.clicked.connect(self.reject)
        self.btn_retry.clicked.connect(self._retry)
        btns.addStretch(1)
        btns.addWidget(self.btn_pause)
        btns.addWidget(self.btn_retry)
        lay.addLayout(btns)

    def _retry(self):
        self.btn_retry.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.lbl.setText("Đang thử kết nối lại…")
        self._worker = ConnectWorker(self.endpoint, self.api_key, parent=self)
        self._worker.ok.connect(self._ok)
        self._worker.fail.connect(self._fail)
        self._worker.start()

    def _ok(self, _model):
        self.reconnected = True
        self.accept()

    def _fail(self, msg):
        self.lbl.setText(f"Vẫn chưa kết nối được:\n{msg}\n\nThử lại?")
        self.btn_retry.setEnabled(True)
        self.btn_pause.setEnabled(True)


# ==================================================== CỬA SỔ CHÍNH

class MainWindow(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.state = State.DISCONNECTED
        self.model_name = ""
        self.files: list[Path] = []
        self.n_pages = 0
        self.last_excel = ""        # xlsx của lần chạy gần nhất (mở bằng "Kết quả")
        self.last_output_dir = ""   # fallback mở thư mục khi không có xlsx
        self._run_output_dir = ""   # thư mục xuất đã resolve của lần chạy
        self._reconnecting = False  # đang mở popup kết nối lại (tránh mở nhiều)
        self._conn_lost = False     # mất kết nối server giữa batch (đồng bộ status)
        self._wanted_model = ""     # model do người dùng chỉ định (endpoint ngoài)
        self._run_started = 0.0     # mốc thời gian bắt đầu batch (ETA thực tế)
        self._current_file = ""     # tên PDF đang xử lý
        self._file_t0 = 0.0         # mốc thời gian file hiện tại (đếm giây)
        self._tick_count = 0        # đếm nhịp để nhấp nháy icon chậm
        self._last_elapsed = 0.0    # tổng thời gian chạy của batch vừa xong

        self.connect_worker: ConnectWorker | None = None
        self.scan_worker: ScanWorker | None = None
        self.ocr_worker: OcrWorker | None = None
        self.page_counts: list[int] = []    # số trang mỗi PDF (cache khi quét)

        self.setWindowTitle(APP_TITLE)
        self.resize(1120, 720)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_source_bar())
        root.addWidget(self._build_estimate_bar())   # gồm cả progress bar

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.addWidget(self._build_settings_panel())
        split.addWidget(self._build_tabs())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([210, 910])
        self.split = split
        root.addWidget(split, 1)

        root.addWidget(self._build_action_bar())

        # Nhịp 500ms: cập nhật đồng hồ giây file hiện tại + nhấp nháy icon chậm.
        self._tick = QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._on_tick)

        self._apply_state()

        # Console = nhật ký thao tác. Ghi tóm tắt khi khởi động.
        self.tab_meta.saved.connect(
            lambda n: self._log("info", f"lưu metadata — {n} trường thay đổi"))
        self._log("info", f"khởi động · endpoint {self.cfg['endpoint']} "
                          f"· {len(self.tab_meta.fields)} trường metadata")

    def _log(self, level, text):
        """Ghi một dòng tóm tắt vào Console (nhật ký thao tác)."""
        self.tab_console.append_log(level, text)

    # ------------------------------------------------ nguồn

    def _build_source_bar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("srcBar")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        lbl = QLabel("Nguồn")
        lbl.setObjectName("srcLbl")
        lay.addWidget(lbl)

        self.ed_path = QLineEdit()
        self.ed_path.setObjectName("path")
        self.ed_path.setPlaceholderText("chưa chọn nguồn")
        self.ed_path.setReadOnly(True)
        lay.addWidget(self.ed_path, 1)

        # Hai nút ở cuối hàng — bấm là mở ngay hộp thoại tương ứng.
        self.btn_pick_file = QPushButton("File PDF")
        self.btn_pick_dir = QPushButton("Thư mục")
        for b in (self.btn_pick_file, self.btn_pick_dir):
            b.setObjectName("pill")
            b.setCursor(Qt.PointingHandCursor)
        self.btn_pick_file.clicked.connect(self.on_pick_file)
        self.btn_pick_dir.clicked.connect(self.on_pick_dir)
        lay.addWidget(self.btn_pick_file)
        lay.addWidget(self.btn_pick_dir)
        return box

    def _build_estimate_bar(self) -> QWidget:
        # Hàng tiến trình: [Tiến trình] [progress bar] [x/y] ngay sau bar.
        box = QFrame()
        box.setObjectName("estBar")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        lbl = QLabel("Tiến trình")
        lbl.setObjectName("estText")
        lay.addWidget(lbl)

        self.bar = QProgressBar()
        self.bar.setObjectName("prog")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(9)
        self.bar.setProperty("hold", False)
        lay.addWidget(self.bar, 1)

        self.lbl_count = QLabel("")       # x/y ngay sau progress bar
        self.lbl_count.setObjectName("count")
        lay.addWidget(self.lbl_count)
        return box

    def on_pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file PDF", "", "PDF (*.pdf)")
        if path:
            self._set_source(path)

    def on_pick_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if path:
            self._set_source(path)

    def _set_source(self, path: str):
        # Nguồn mới → rời trạng thái DONE, ẩn "Kết quả"/"Chạy lại", chỉ còn "Bắt đầu".
        if self.state == State.DONE:
            self.state = State.CONNECTED
            self.last_excel = ""
            self.last_output_dir = ""

        self.ed_path.setText(path)
        self._log("info", f"chọn nguồn: {path}")
        self._start_scan(path)

    def _start_scan(self, path: str):
        """Quét nguồn trong luồng nền (glob + đếm trang) để thư mục rất lớn
        không treo UI. Huỷ lần quét trước để tránh chồng luồng và số liệu cũ."""
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.requestInterruption()

        self.files = []
        self.page_counts = []
        self.n_pages = 0
        self.lbl_count.setText("")
        self.lbl_estimate.setText("Đang quét nguồn…")
        self._apply_state()          # "Bắt đầu" bị khoá khi chưa có file

        self.scan_worker = ScanWorker(path, self.cb_strategy.currentData(), self)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.done.connect(self._on_scan_done)
        self.scan_worker.start()

    def _on_scan_progress(self, counted, total):
        self.lbl_estimate.setText(f"Đang quét… {counted}/{total} file")

    def _on_scan_done(self, files, counts, n_pages):
        self.files = list(files)
        self.page_counts = list(counts)
        self.n_pages = n_pages
        # Reset progress bar + x/y (trên) về 0 theo số file mới.
        self.bar.setRange(0, max(1, len(self.files)))
        self.bar.setValue(0)
        self.lbl_count.setText(f"0/{len(self.files)}" if self.files else "")
        if not self.files:
            self.lbl_estimate.setText("Không tìm thấy file PDF nào")
            self._log("warn", "quét xong — không tìm thấy file PDF")
        else:
            self._update_estimate_label()
            self._log("info", f"quét xong — {len(self.files)} file · "
                              f"{self.n_pages:,} trang".replace(",", "."))
        self._apply_state()

    @staticmethod
    def _fmt_dur(secs) -> str:
        secs = int(secs)
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}p{secs % 60:02d}s"

    def _info_text(self) -> str:
        """'x file · y trang · thời gian' — thời gian là ước lượng khi chưa chạy,
        là thời gian thực tế khi đang chạy / đã xong."""
        if not self.files:
            return "Chưa chọn nguồn"
        pages = f"{self.n_pages:,}".replace(",", ".")
        base = f"{len(self.files)} file · {pages} trang"
        if self.state == State.RUNNING and self._run_started:
            return f"{base} · {self._fmt_dur(time.monotonic() - self._run_started)}"
        if self.state == State.DONE and self._last_elapsed:
            return f"{base} · {self._fmt_dur(self._last_elapsed)}"
        spp = self.cfg.get("seconds_per_page", 0.5)
        mins = max(1, round(self.n_pages * spp / 60))
        return f"{base} · ~{mins} phút"

    def _update_estimate_label(self):
        self.lbl_estimate.setText(self._info_text())

    def _recompute_estimate(self):
        """Đổi chiến lược trang: tính lại từ số trang đã cache — KHÔNG mở lại PDF."""
        if not self.page_counts:
            return
        strat = self.cb_strategy.currentData()
        self.n_pages = sum(
            pipeline.count_selected_pages(n, strat) for n in self.page_counts)
        self._update_estimate_label()
        self._log("info", f"chiến lược trang: {self.cb_strategy.currentText()} "
                          f"· {self.n_pages:,} trang".replace(",", "."))
        self._apply_state()

    # ------------------------------------------------ cài đặt

    def _build_settings_panel(self) -> QWidget:
        box = QGroupBox("")
        lay = QGridLayout(box)
        lay.setContentsMargins(11, 12, 11, 11)
        lay.setVerticalSpacing(4)
        r = 0

        def editable(text):
            # Ô sửa được (nền trắng, có viền) — khoá khi đang chạy batch.
            w = QLineEdit(str(text))
            w.setObjectName("cfgin")
            return w

        # Sửa được khi chưa chạy. Endpoint/API key/Model chỉ đổi khi CHƯA kết nối.
        self.ed_endpoint = editable(self.cfg["endpoint"])
        self.ed_apikey = editable(self.cfg.get("api_key", ""))
        self.ed_apikey.setEchoMode(QLineEdit.Password)
        self.ed_apikey.setPlaceholderText("để trống nếu server không cần key")
        self.ed_model = editable("—")
        self.ed_model.setPlaceholderText("tự lấy từ server, hoặc gõ vd gpt-4o")
        self.ed_dpi = editable(self.cfg["render_dpi"])
        self.ed_concurrency = editable(self.cfg["concurrency"])
        self.ed_outdir = editable(self.cfg["output_dir"])

        lay.addWidget(QLabel("Endpoint"), r, 0, 1, 2); r += 1
        lay.addWidget(self.ed_endpoint, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("API key"), r, 0, 1, 2); r += 1
        lay.addWidget(self.ed_apikey, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("Model"), r, 0, 1, 2); r += 1
        lay.addWidget(self.ed_model, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("Chiến lược trang"), r, 0, 1, 2); r += 1
        self.cb_strategy = QComboBox()
        for key, label in pipeline.PAGE_STRATEGIES.items():
            self.cb_strategy.addItem(label, key)
        idx = self.cb_strategy.findData(self.cfg["page_strategy"])
        self.cb_strategy.setCurrentIndex(max(idx, 0))
        self.cb_strategy.currentIndexChanged.connect(
            lambda _: self._recompute_estimate())
        lay.addWidget(self.cb_strategy, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("DPI"), r, 0)
        lay.addWidget(QLabel("Song song"), r, 1); r += 1
        lay.addWidget(self.ed_dpi, r, 0)
        lay.addWidget(self.ed_concurrency, r, 1); r += 1

        lay.addWidget(QLabel("Thư mục xuất"), r, 0, 1, 2); r += 1
        lay.addWidget(self.ed_outdir, r, 0, 1, 2); r += 1

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{C['line']};background:{C['line']};max-height:1px;")
        lay.addWidget(line, r, 0, 1, 2); r += 1

        # Hai tuỳ chọn dạng checkbox — tương tác được, mặc định theo config.
        self.chk_correction = QCheckBox("Sửa lỗi chính tả")
        self.chk_correction.setChecked(bool(self.cfg.get("use_correction")))
        self.chk_protect = QCheckBox("Bỏ qua tên riêng")
        self.chk_protect.setChecked(bool(self.cfg.get("protect_proper_nouns")))
        for c in (self.chk_correction, self.chk_protect):
            c.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.chk_correction, r, 0, 1, 2); r += 1
        lay.addWidget(self.chk_protect, r, 0, 1, 2); r += 1

        lay.setRowMinimumHeight(r, 12); r += 1

        # Khối kết nối trên một hàng: trạng thái bên trái, nút Kết nối/Ngắt phải.
        self.lbl_conn = QLabel("● Chưa kết nối")
        self.btn_connect = QPushButton("Kết nối")
        self.btn_disconnect = QPushButton("Ngắt")
        self.btn_connect.setObjectName("pri")
        for b in (self.btn_connect, self.btn_disconnect):
            b.setProperty("mini", True)
            b.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)

        conn_row = QWidget()
        h = QHBoxLayout(conn_row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(self.lbl_conn)
        h.addStretch(1)
        h.addWidget(self.btn_connect)
        h.addWidget(self.btn_disconnect)
        lay.addWidget(conn_row, r, 0, 1, 2)
        r += 1

        lay.setRowStretch(r, 1)
        return box

    # ------------------------------------------------ tabs

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        fields_path = APP_DIR / self.cfg["fields_file"]

        self.tab_meta = MetadataTab(fields_path, self.cfg["correction_policy"])
        self.tab_console = ConsoleTab()
        self.field_keys = list(self.tab_meta.fields.keys())
        self.tab_results = ResultsTab(self.field_keys)

        self.tabs.addTab(self.tab_meta, "Metadata")
        self.tabs.addTab(self.tab_console, "Console")
        self.tabs.addTab(self.tab_results, "Kết quả")

        # Công cụ tab Kết quả nằm ở góc phải thanh tab, chỉ hiện khi mở tab đó.
        self.tabs.setCornerWidget(self.tab_results.tools, Qt.TopRightCorner)
        self.tab_results.tools.setVisible(False)

        self.tabs.setCurrentIndex(1)
        self.tabs.currentChanged.connect(self._guard_tab_switch)
        self._last_tab = 1
        return self.tabs

    def _guard_tab_switch(self, index):
        """Không cho rời tab Metadata khi đang sửa dở."""
        if self.tab_meta.editing and index != 0:
            QMessageBox.information(
                self, "Đang sửa metadata",
                "Lưu hoặc hoàn tác thay đổi trước khi chuyển tab.")
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(0)
            self.tabs.blockSignals(False)
            self.tab_results.tools.setVisible(False)
            return
        self._last_tab = index
        # Công cụ wrap chỉ hiện ở tab Kết quả (index 2).
        self.tab_results.tools.setVisible(index == 2)

    # ------------------------------------------------ thanh hành động

    def _build_action_bar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("actBar")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # Trạng thái + tên file (khi chạy), rồi 'x file · y trang · thời gian'.
        self.lbl_run = QLabel("")
        self.lbl_run.setTextFormat(Qt.RichText)
        lay.addWidget(self.lbl_run)

        self.lbl_estimate = QLabel("Chưa chọn nguồn")
        self.lbl_estimate.setObjectName("estText")
        lay.addWidget(self.lbl_estimate)

        lay.addStretch(1)

        self.btn_start = QPushButton("Bắt đầu")
        self.btn_pause = QPushButton("Tạm dừng")
        self.btn_resume = QPushButton("Tiếp tục")
        self.btn_finish = QPushButton("Kết thúc")
        self.btn_result = QPushButton("Kết quả")     # mở xlsx sau khi xong
        self.btn_rerun = QPushButton("Chạy lại")     # chạy lại cùng nguồn

        self.btn_pause.setObjectName("dan")
        for b in (self.btn_start, self.btn_resume, self.btn_result):
            b.setObjectName("pri")

        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_resume.clicked.connect(self.on_resume)
        self.btn_finish.clicked.connect(self.on_finish)
        self.btn_rerun.clicked.connect(self.on_start)
        self.btn_result.clicked.connect(self.on_open_result)

        for b in (self.btn_start, self.btn_finish, self.btn_resume,
                  self.btn_pause, self.btn_rerun, self.btn_result):
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        return box

    # ------------------------------------------------ máy trạng thái

    def _apply_state(self):
        s = self.state
        has_files = bool(self.files)

        # Chưa chạy = hiện "Bắt đầu"; đã xong = hiện "Kết quả"/"Chạy lại".
        idle = s in (State.DISCONNECTED, State.CONNECTING, State.CONNECTED)

        # Kết nối / ngắt nằm trong panel Cài đặt (DONE vẫn đang kết nối).
        self.btn_connect.setVisible(s in (State.DISCONNECTED, State.CONNECTING))
        self.btn_connect.setEnabled(s == State.DISCONNECTED)
        self.btn_disconnect.setVisible(s in (State.CONNECTED, State.DONE))

        # "Bắt đầu" luôn hiện khi chưa chạy; chỉ bật khi đã kết nối + có nguồn.
        self.btn_start.setVisible(idle)
        self.btn_start.setEnabled(s == State.CONNECTED and has_files)
        self.btn_pause.setVisible(s in (State.RUNNING, State.PAUSING))
        self.btn_pause.setEnabled(s == State.RUNNING)
        self.btn_resume.setVisible(s == State.PAUSED)
        self.btn_finish.setVisible(s == State.PAUSED)

        # Sau khi xong: "Kết quả" (mở xlsx) + "Chạy lại".
        self.btn_result.setVisible(s == State.DONE)
        self.btn_result.setEnabled(bool(self.last_excel or self.last_output_dir))
        self.btn_result.setText("Kết quả" if self.last_excel else "Mở thư mục")
        self.btn_rerun.setVisible(s == State.DONE)
        self.btn_rerun.setEnabled(has_files)

        busy = s in (State.RUNNING, State.PAUSING, State.PAUSED)
        self.btn_pick_file.setEnabled(not busy)
        self.btn_pick_dir.setEnabled(not busy)
        self.cb_strategy.setEnabled(not busy)
        self.chk_correction.setEnabled(not busy)
        self.chk_protect.setEnabled(not busy)

        # Ô cài đặt sửa được khi chưa chạy; Endpoint/API key/Model chỉ đổi khi
        # đã ngắt kết nối (đổi giữa lúc kết nối là vô nghĩa, phải kết nối lại).
        for w in (self.ed_dpi, self.ed_concurrency, self.ed_outdir):
            w.setEnabled(not busy)
        for w in (self.ed_endpoint, self.ed_apikey, self.ed_model):
            w.setEnabled(s in (State.DISCONNECTED, State.CONNECTING))
        self.tab_meta.set_edit_allowed(
            not busy, "Không sửa được metadata khi đang chạy — Kết thúc batch trước")

        # Progress bar hiện khi đã có nguồn hoặc đang chạy/đã xong; GIỮ sau khi xong.
        self.bar.setVisible(
            has_files or s in (State.RUNNING, State.PAUSING,
                               State.PAUSED, State.DONE))
        self._set_prop(self.bar, "hold", s in (State.PAUSING, State.PAUSED))

        # Trạng thái kết nối (trong panel Cài đặt, dưới nút Kết nối/Ngắt).
        if s == State.DISCONNECTED:
            ctext, ccolor = "● Chưa kết nối", C["ts"]
        elif s == State.CONNECTING:
            ctext, ccolor = "● Đang kết nối…", C["ts"]
        elif self._conn_lost:       # rớt kết nối giữa batch → báo đỏ
            ctext, ccolor = "✗ Mất kết nối", C["dan"]
        else:                       # CONNECTED / RUNNING / PAUSING / PAUSED / DONE
            ctext, ccolor = "✓ Đã kết nối", C["ok"]
        self.lbl_conn.setText(ctext)
        self.lbl_conn.setStyleSheet(
            f"color:{ccolor};font-size:11px;font-weight:500;")

        # Nhịp đếm giây + nhấp nháy icon chỉ chạy khi đang RUNNING.
        if s == State.RUNNING:
            if not self._tick.isActive():
                self._tick.start()
        else:
            self._tick.stop()
        self._refresh_run_label()

    def _on_tick(self):
        self._tick_count += 1
        self._refresh_run_label()
        # Cập nhật 'thời gian thực hiện' đang chạy ở thanh dưới.
        if self.state == State.RUNNING:
            self.lbl_estimate.setText(self._info_text())

    def _on_file_started(self, name):
        self._current_file = name
        self._file_t0 = time.monotonic()
        self._refresh_run_label()

    def _refresh_run_label(self):
        """Mô tả tiến trình ở thanh dưới: icon nhấp nháy chậm + tên file + giây."""
        s = self.state
        ok, warn = C["ok"], C["warn"]
        if s == State.RUNNING:
            blink_on = (self._tick_count // 2) % 2 == 0      # 1s sáng / 1s mờ
            dot = ok if blink_on else "#bfe0d5"
            html = (f'<span style="color:{dot};font-size:9px">●</span> '
                    f'<span style="color:{ok};font-weight:600">Đang chạy</span>')
            if self._current_file:
                secs = int(time.monotonic() - self._file_t0) if self._file_t0 else 0
                name = (self._current_file.replace("&", "&amp;")
                        .replace("<", "&lt;").replace(">", "&gt;"))
                html += (f'<span style="color:{C["ts"]}"> · {name} · '
                         f'{secs}s</span>')
            self.lbl_run.setText(html)
        elif s == State.PAUSING:
            self.lbl_run.setText(
                f'<span style="color:{warn};font-weight:600">● Đang tạm dừng…</span>')
        elif s == State.PAUSED:
            self.lbl_run.setText(
                f'<span style="color:{warn};font-weight:600">● Đã tạm dừng</span>')
        elif s == State.DONE:
            self.lbl_run.setText(
                f'<span style="color:{ok};font-weight:600">✓ Đã xong</span>')
        else:
            self.lbl_run.setText("")

    @staticmethod
    def _set_prop(widget, name, value):
        """Đặt dynamic property rồi repolish để QSS [prop] cập nhật ngay."""
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @staticmethod
    def _int_field(widget, default, lo=None, hi=None):
        """Đọc số nguyên từ ô cài đặt; gõ sai thì về mặc định, kẹp trong [lo,hi]."""
        try:
            v = int(str(widget.text()).strip())
        except (ValueError, TypeError):
            v = int(default)
        if lo is not None:
            v = max(lo, v)
        if hi is not None:
            v = min(hi, v)
        widget.setText(str(v))       # chuẩn hoá lại hiển thị
        return v

    def _resolved_output_dir(self) -> str:
        raw = self.ed_outdir.text().strip() or str(self.cfg["output_dir"])
        p = Path(raw)
        return str(p if p.is_absolute() else (APP_DIR / p))

    # ------------------------------------------------ hành động

    def on_connect(self):
        endpoint = self.ed_endpoint.text().strip()
        if not endpoint:
            QMessageBox.warning(self, "Thiếu endpoint",
                                "Nhập địa chỉ endpoint server trước khi kết nối.")
            return
        # Ghi nhớ giá trị vừa sửa cho phiên (endpoint ngoài như OpenAI/Gemini).
        self._conn_lost = False
        self.cfg["endpoint"] = endpoint
        self.cfg["api_key"] = self.ed_apikey.text().strip() or "EMPTY"
        wanted = self.ed_model.text().strip()
        self._wanted_model = "" if wanted in ("", "—") else wanted

        self.state = State.CONNECTING
        self._apply_state()
        self.tab_console.append_log("info", f"kết nối {endpoint}…")
        self.connect_worker = ConnectWorker(
            endpoint, self.cfg["api_key"], parent=self)
        self.connect_worker.ok.connect(self._on_connect_ok)
        self.connect_worker.fail.connect(self._on_connect_fail)
        self.connect_worker.start()

    def _on_connect_ok(self, server_model):
        # Ưu tiên model người dùng chỉ định (endpoint nhiều model như OpenAI/
        # Gemini); nếu để trống thì dùng model đầu tiên server trả về (vLLM).
        self.model_name = self._wanted_model or server_model
        self.ed_model.setText(self.model_name)
        self.state = State.CONNECTED
        self._apply_state()
        self.tab_console.append_log(
            "info", f"kết nối ok — model {self.model_name}")

    def _on_connect_fail(self, message):
        self.state = State.DISCONNECTED
        self._apply_state()
        self.tab_console.append_log("error", f"kết nối thất bại: {message}")
        QMessageBox.critical(self, "Không kết nối được",
                             f"{self.cfg['endpoint']}\n\n{message}")

    def on_disconnect(self):
        self.model_name = ""
        self.ed_model.setText("—")
        self.state = State.DISCONNECTED
        self._apply_state()
        self._log("info", "đã ngắt kết nối server")

    def on_start(self):
        if not self.files:
            return

        threshold = self.cfg.get("page_estimate_warn_threshold", 500)
        if self.n_pages > threshold:
            spp = self.cfg.get("seconds_per_page", 0.5)
            mins = max(1, round(self.n_pages * spp / 60))
            if QMessageBox.question(
                    self, "Khối lượng lớn",
                    f"Sẽ OCR {self.n_pages:,} trang, ước tính ~{mins} phút.\n"
                    "Tiếp tục?".replace(",", "."),
                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return

        cfg = dict(self.cfg)
        cfg["page_strategy"] = self.cb_strategy.currentData()
        cfg["render_dpi"] = self._int_field(self.ed_dpi, self.cfg["render_dpi"],
                                            lo=50, hi=600)
        cfg["concurrency"] = self._int_field(
            self.ed_concurrency, self.cfg["concurrency"], lo=1, hi=64)
        cfg["output_dir"] = self._resolved_output_dir()
        self._run_output_dir = cfg["output_dir"]     # để _export_excel dùng lại
        cfg["use_correction"] = self.chk_correction.isChecked()
        cfg["protect_proper_nouns"] = self.chk_protect.isChecked()
        if not cfg.get("protect_proper_nouns"):
            cfg["correction_policy"] = {
                k: ("correct" if v == "protect" else v)
                for k, v in cfg["correction_policy"].items()
            }

        self.tab_results.clear_rows()
        self.bar.setRange(0, len(self.files))
        self.bar.setValue(0)
        self.tabs.setCurrentIndex(1)
        self._run_started = time.monotonic()     # mốc để tính ETA thực tế

        self._log(
            "info",
            f"bắt đầu OCR · {len(self.files)} file · "
            f"{self.cb_strategy.currentText()} · DPI {cfg['render_dpi']} · "
            f"song song {cfg['concurrency']} · sửa lỗi "
            f"{'bật' if cfg['use_correction'] else 'tắt'}")

        self.ocr_worker = OcrWorker(
            self.files, self.tab_meta.fields, cfg, self.model_name, parent=self)
        self.ocr_worker.log.connect(self.tab_console.append_log)
        self.ocr_worker.progress.connect(self._on_progress)
        self.ocr_worker.row_done.connect(self.tab_results.add_result)
        self.ocr_worker.state_changed.connect(self._on_worker_state)
        self.ocr_worker.file_started.connect(self._on_file_started)
        self.ocr_worker.connection_lost.connect(self._on_connection_lost)
        self.ocr_worker.finished_all.connect(self._on_finished)
        self._current_file = ""
        self._file_t0 = 0.0
        self.ocr_worker.start()

        self.state = State.RUNNING
        self._apply_state()
        # Đưa focus vào Console (tránh nhảy vào ô cài đặt khi các ô bị khoá).
        self.tab_console.setFocus()

    def on_pause(self):
        if self.ocr_worker:
            self.ocr_worker.pause()
            self.state = State.PAUSING
            self._apply_state()
            self._log("warn", "tạm dừng theo yêu cầu")

    def on_resume(self):
        if self.ocr_worker:
            self._conn_lost = False     # người dùng chủ động tiếp tục
            self.ocr_worker.resume()
            self.state = State.RUNNING
            self._apply_state()
            self._log("info", "tiếp tục batch")

    def _on_connection_lost(self, message):
        """Worker đã tự tạm dừng do mất kết nối. Hỏi kết nối lại; thành công thì
        tiếp tục batch, không thì để tạm dừng (dùng Tiếp tục/Kết thúc sau)."""
        if self._reconnecting:
            return
        self._reconnecting = True
        self._conn_lost = True          # đồng bộ status → "✗ Mất kết nối"
        self.state = State.PAUSED
        self._apply_state()

        dlg = ReconnectDialog(self.cfg["endpoint"], self.cfg["api_key"],
                              message, self)
        dlg.exec_()
        self._reconnecting = False

        if dlg.reconnected and self.ocr_worker and self.ocr_worker.isRunning():
            self._conn_lost = False
            self.tab_console.append_log("info", "kết nối lại OK — tiếp tục batch")
            self.ocr_worker.resume()
            self.state = State.RUNNING
            self._apply_state()
        else:
            self.tab_console.append_log(
                "warn", "vẫn tạm dừng — bấm Tiếp tục khi server sẵn sàng")
            self._apply_state()         # giữ status "✗ Mất kết nối"

    def on_finish(self):
        if not self.ocr_worker:
            return
        if QMessageBox.question(
                self, "Kết thúc batch",
                "Chốt batch với những file đã xử lý và xuất Excel?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self.tab_console.append_log("warn", "kết thúc sớm theo yêu cầu")
        self.ocr_worker.finish_early()

    # ------------------------------------------------ tín hiệu worker

    def _on_progress(self, done, total, errors):
        # x/y ngay sau progress bar (thời gian đã dời xuống thanh dưới).
        self.bar.setValue(done)
        txt = f"{done}/{total}"
        if errors:
            txt += f" · lỗi {errors}"
        self.lbl_count.setText(txt)

    def _on_worker_state(self, name):
        # Tín hiệu từ worker được Qt xếp hàng, nên có thể đến sau khi batch
        # đã chốt. Nếu đã rời trạng thái chạy thì bỏ qua, tránh rơi lại vào
        # PAUSED và hiện nút Tiếp tục / Kết thúc cho một worker không còn chạy.
        if self.state in (State.CONNECTED, State.DONE):
            return
        mapping = {"running": State.RUNNING,
                   "pausing": State.PAUSING,
                   "paused": State.PAUSED}
        if name in mapping:
            self.state = mapping[name]
            self._apply_state()

    def _on_finished(self, stats: dict):
        self._current_file = ""          # dừng đồng hồ file
        self.state = State.DONE          # đặt sớm để _info_text dùng thời gian thực
        # Giữ progress bar ở mức số file THÀNH CÔNG (100% nếu không lỗi).
        total = max(1, stats.get("total", 1))
        self.bar.setRange(0, total)
        self.bar.setValue(stats.get("ok", 0))
        self.lbl_count.setText(
            f"{stats.get('ok', 0)}/{stats.get('total', 0)} thành công"
            + (f" · {stats.get('fail', 0)} lỗi" if stats.get("fail") else ""))
        secs = stats.get("elapsed", 0)
        self._last_elapsed = secs        # để '_info_text' hiện thời gian thực
        self.lbl_estimate.setText(self._info_text())
        if stats.get("ok") and secs:
            pages = max(self.n_pages, 1)
            self.cfg["seconds_per_page"] = round(secs / pages, 3)

        self.tab_console.append_log(
            "info",
            f"xong · {stats['ok']} thành công · {stats['fail']} lỗi "
            f"· {secs / 60:.1f} phút")

        if stats.get("ok") and stats.get("tsv"):
            self._export_excel(stats)

        # Lưu đường dẫn để nút "Kết quả" mở; không còn popup hoàn tất.
        self.last_excel = stats.get("excel", "")
        self.last_output_dir = self._run_output_dir or str(
            Path(APP_DIR / self.cfg["output_dir"]))
        self.tab_console.append_log(
            "info", f"đã xuất Excel: {Path(self.last_excel).name}"
            if self.last_excel else "không có Excel — mở thư mục để lấy TSV")

        self.tabs.setCurrentIndex(2)      # hiện tab Kết quả
        self.state = State.DONE
        self._apply_state()

    def on_open_result(self):
        """Nút 'Kết quả': mở xlsx; nếu không có thì mở thư mục xuất."""
        target = self.last_excel or self.last_output_dir
        if target:
            self._log("info", f"mở {'kết quả' if self.last_excel else 'thư mục'}: "
                              f"{Path(target).name}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    # ------------------------------------------------ xuất Excel

    def _export_excel(self, stats: dict):
        """
        Chạy trên UI thread. Excel MẶC ĐỊNH ghi đè file cùng tên (ket_qua_<nguồn>.xlsx);
        chỉ khi file đang mở trong Excel (bị khoá) mới lưu bản có timestamp.
        (TSV thì mỗi lần chạy đã là file mới theo thời gian.)
        """
        out_dir = Path(self._run_output_dir or (APP_DIR / self.cfg["output_dir"]))
        target = pipeline.excel_target(
            out_dir, self.ed_path.text(), self.cfg.get("excel_base_name"))

        # File đang mở trong Excel -> không ghi đè được -> lưu bản timestamp.
        if target.exists() and pipeline.is_locked(target):
            alt = pipeline.stamped_variant(target)
            self.tab_console.append_log(
                "warn", f"{target.name} đang mở — lưu {alt.name}")
            target = alt

        try:
            p = pipeline.export_excel(stats["tsv"], target)
            stats["excel"] = str(p)
            self.tab_console.append_log("info", f"đã xuất Excel: {p.name}")
        except PermissionError:
            alt = pipeline.stamped_variant(target)
            try:
                p = pipeline.export_excel(stats["tsv"], alt)
                stats["excel"] = str(p)
                self.tab_console.append_log(
                    "warn", f"{target.name} bị khoá — đã lưu {p.name}")
            except Exception as e:
                stats["export_error"] = str(e)
                self.tab_console.append_log("error", f"xuất Excel thất bại: {e}")
        except Exception as e:
            stats["export_error"] = str(e)
            self.tab_console.append_log("error", f"xuất Excel thất bại: {e}")

    # ------------------------------------------------ đóng app

    def closeEvent(self, event):
        if self.ocr_worker and self.ocr_worker.isRunning():
            if QMessageBox.question(
                    self, "Đang chạy",
                    "Batch chưa xong. Dừng và thoát?\n"
                    "Dữ liệu đã xử lý vẫn còn trong file TSV.",
                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                event.ignore()
                return
            self.ocr_worker.finish_early()
            self.ocr_worker.wait(15000)

        # Dừng các luồng nền còn lại để tránh crash "QThread destroyed while
        # running" khi đóng app lúc đang quét thư mục hoặc đang kết nối.
        for w in (self.scan_worker, self.connect_worker):
            if w and w.isRunning():
                w.requestInterruption()
                w.wait(6000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    base = QFont("-apple-system" if sys.platform == "darwin" else "Segoe UI")
    base.setPixelSize(12)
    app.setFont(base)
    app.setStyleSheet(build_stylesheet())

    # Đọc config với hàng rào lỗi — bản exe để config.json cạnh file, người dùng
    # có thể sửa hỏng JSON; báo lỗi rõ ràng thay vì crash im lặng lúc mở.
    cfg_path = APP_DIR / "config.json"
    try:
        if not cfg_path.exists():
            raise FileNotFoundError(f"Thiếu {cfg_path.name} cạnh ứng dụng")
        cfg = pipeline.load_config(cfg_path)
    except Exception as e:
        QMessageBox.critical(None, APP_TITLE,
                             f"Không đọc được cấu hình:\n{cfg_path}\n\n{e}")
        sys.exit(1)

    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
