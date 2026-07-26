"""
app.py — cửa sổ chính.

Chạy:  python app.py
"""

from __future__ import annotations

import sys
from enum import Enum, auto
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

import pipeline
from workers import ConnectWorker, EstimateWorker, OcrWorker

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

    /* thanh ước lượng */
    QLabel#estBar {{ background:{C['s1']}; border-bottom:1px solid {C['line']};
        color:{C['ts']}; font-family:"{MONO}"; font-size:11px; padding:6px 12px; }}

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
        font-size:13px; selection-background-color:{C['acc_bg']};
        selection-color:{C['tp']}; }}
    QTableWidget::item {{ padding:5px 8px; border-bottom:1px solid {C['line']}; }}
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


# ==================================================== TAB CONSOLE

class ConsoleTab(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
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

    def __init__(self, fields_path, correction_policy, parent=None):
        super().__init__(parent)
        self.fields_path = Path(fields_path)
        self.policy = dict(correction_policy)
        self.fields: dict = {}
        self._snapshot: dict = {}
        self._editing = False
        self._loading = False

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
            mono = QFont(MONO, 10)
            mono.setStyleHint(QFont.Monospace)
            it_key.setFont(mono)
            self.table.setItem(r, 0, it_key)

            it_desc = QTableWidgetItem(str(desc))
            it_desc.setToolTip(str(desc))
            self.table.setItem(r, 1, it_desc)

            pol = self.policy.get(key, "skip")
            it_pol = QTableWidgetItem(POLICY_LABEL.get(pol, pol))
            it_pol.setFlags(it_pol.flags() & ~Qt.ItemIsEditable)
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
        try:
            backup = pipeline.save_fields(self.fields_path, new_fields)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không lưu được:\n{e}")
            return

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

class ResultsTab(QTableWidget):
    def __init__(self, field_keys, parent=None):
        super().__init__(0, len(field_keys) + 1, parent)
        self.field_keys = list(field_keys)
        self.setHorizontalHeaderLabels(["File"] + self.field_keys)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setDefaultSectionSize(140)
        self.setColumnWidth(0, 150)
        self._mono = QFont(MONO, 10)
        self._mono.setStyleHint(QFont.Monospace)

    def clear_rows(self):
        self.setRowCount(0)

    def add_result(self, result: dict):
        r = self.rowCount()
        self.insertRow(r)
        it_name = QTableWidgetItem(result.get("name", ""))
        it_name.setFont(self._mono)
        if result.get("error"):
            it_name.setForeground(QColor(C["dan"]))
        self.setItem(r, 0, it_name)

        if result.get("error"):
            it = QTableWidgetItem(result["error"])
            it.setForeground(QColor(C["dan"]))
            self.setItem(r, 1, it)
            self.setSpan(r, 1, 1, len(self.field_keys))
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
                self.setItem(r, c, it)

        self.scrollToBottom()


# ==================================================== CỬA SỔ CHÍNH

class MainWindow(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.state = State.DISCONNECTED
        self.model_name = ""
        self.files: list[Path] = []
        self.n_pages = 0

        self.connect_worker: ConnectWorker | None = None
        self.estimate_worker: EstimateWorker | None = None
        self.ocr_worker: OcrWorker | None = None

        self.setWindowTitle(APP_TITLE)
        self.resize(1120, 720)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_source_bar())
        root.addWidget(self._build_estimate_bar())

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.addWidget(self._build_settings_panel())
        split.addWidget(self._build_tabs())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([210, 910])
        root.addWidget(split, 1)

        root.addWidget(self._build_action_bar())

        self._apply_state()

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
        self.lbl_estimate = QLabel("Chưa chọn nguồn")
        self.lbl_estimate.setObjectName("estBar")
        return self.lbl_estimate

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
        self.ed_path.setText(path)
        self.files = pipeline.collect_pdf_files(path)
        if not self.files:
            self.lbl_estimate.setText("Không tìm thấy file PDF nào")
            self._apply_state()
            return
        self._recount()

    def _recount(self):
        if not self.files:
            return
        self.lbl_estimate.setText(f"{len(self.files)} file · đang đếm trang…")
        self.estimate_worker = EstimateWorker(
            self.files, self.cb_strategy.currentData(), self)
        self.estimate_worker.done.connect(self._on_estimate)
        self.estimate_worker.start()

    def _on_estimate(self, n_files, n_pages):
        self.n_pages = n_pages
        spp = self.cfg.get("seconds_per_page", 0.5)
        mins = max(1, round(n_pages * spp / 60))
        self.lbl_estimate.setText(
            f"{n_files} file · {n_pages:,} trang · ~{mins} phút".replace(",", "."))
        self._apply_state()

    # ------------------------------------------------ cài đặt

    def _build_settings_panel(self) -> QWidget:
        box = QGroupBox("")
        lay = QGridLayout(box)
        lay.setContentsMargins(11, 12, 11, 11)
        lay.setVerticalSpacing(4)
        r = 0

        def ro(text):
            w = QLineEdit(str(text))
            w.setObjectName("ro")
            w.setReadOnly(True)
            return w

        lay.addWidget(QLabel("Endpoint"), r, 0, 1, 2); r += 1
        lay.addWidget(ro(self.cfg["endpoint"]), r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("Model"), r, 0, 1, 2); r += 1
        self.ed_model = ro("—")
        lay.addWidget(self.ed_model, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("Chiến lược trang"), r, 0, 1, 2); r += 1
        self.cb_strategy = QComboBox()
        for key, label in pipeline.PAGE_STRATEGIES.items():
            self.cb_strategy.addItem(label, key)
        idx = self.cb_strategy.findData(self.cfg["page_strategy"])
        self.cb_strategy.setCurrentIndex(max(idx, 0))
        self.cb_strategy.currentIndexChanged.connect(lambda _: self._recount())
        lay.addWidget(self.cb_strategy, r, 0, 1, 2); r += 1

        lay.addWidget(QLabel("DPI"), r, 0)
        lay.addWidget(QLabel("Song song"), r, 1); r += 1
        lay.addWidget(ro(self.cfg["render_dpi"]), r, 0)
        lay.addWidget(ro(self.cfg["concurrency"]), r, 1); r += 1

        lay.addWidget(QLabel("Thư mục xuất"), r, 0, 1, 2); r += 1
        lay.addWidget(ro(self.cfg["output_dir"]), r, 0, 1, 2); r += 1

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{C['line']};background:{C['line']};max-height:1px;")
        lay.addWidget(line, r, 0, 1, 2); r += 1

        # Hai tuỳ chọn dạng checkbox — tương tác được, mặc định theo config.
        self.chk_correction = QCheckBox("Sửa lỗi ProtonX")
        self.chk_correction.setChecked(bool(self.cfg.get("use_correction")))
        self.chk_protect = QCheckBox("Bỏ qua tên riêng")
        self.chk_protect.setChecked(bool(self.cfg.get("protect_proper_nouns")))
        for c in (self.chk_correction, self.chk_protect):
            c.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.chk_correction, r, 0, 1, 2); r += 1
        lay.addWidget(self.chk_protect, r, 0, 1, 2); r += 1

        # Khoảng cách nhỏ rồi nút kết nối — căn giữa, cỡ bằng nút Bắt đầu.
        lay.setRowMinimumHeight(r, 14); r += 1

        self.btn_connect = QPushButton("Kết nối")
        self.btn_disconnect = QPushButton("Ngắt")
        self.btn_connect.setObjectName("pri")
        for b in (self.btn_connect, self.btn_disconnect):
            b.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)
        lay.addWidget(self.btn_connect, r, 0, 1, 2, Qt.AlignHCenter)
        lay.addWidget(self.btn_disconnect, r, 0, 1, 2, Qt.AlignHCenter)
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
            return
        self._last_tab = index

    # ------------------------------------------------ thanh hành động

    def _build_action_bar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("actBar")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # Trạng thái nằm bên trái thanh dưới.
        self.lbl_conn = QLabel("● Chưa kết nối")
        lay.addWidget(self.lbl_conn)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        self.bar.setProperty("hold", False)
        lay.addWidget(self.bar, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("count")
        lay.addWidget(self.lbl_count)

        # Đẩy cụm nút sang phải (giống margin-left:auto ở prototype).
        lay.addStretch(1)

        self.btn_start = QPushButton("Bắt đầu")
        self.btn_pause = QPushButton("Tạm dừng")
        self.btn_resume = QPushButton("Tiếp tục")
        self.btn_finish = QPushButton("Kết thúc")

        self.btn_pause.setObjectName("dan")
        for b in (self.btn_start, self.btn_resume):
            b.setObjectName("pri")

        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_resume.clicked.connect(self.on_resume)
        self.btn_finish.clicked.connect(self.on_finish)

        for b in (self.btn_start, self.btn_finish, self.btn_resume,
                  self.btn_pause):
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        return box

    # ------------------------------------------------ máy trạng thái

    def _apply_state(self):
        s = self.state
        has_files = bool(self.files)

        idle = s in (State.DISCONNECTED, State.CONNECTING, State.CONNECTED)

        # Kết nối / ngắt nằm trong panel Cài đặt.
        self.btn_connect.setVisible(s in (State.DISCONNECTED, State.CONNECTING))
        self.btn_connect.setEnabled(s == State.DISCONNECTED)
        self.btn_disconnect.setVisible(s == State.CONNECTED)

        # "Bắt đầu" luôn hiện khi chưa chạy; chỉ bật khi đã kết nối + có nguồn.
        self.btn_start.setVisible(idle)
        self.btn_start.setEnabled(s == State.CONNECTED and has_files)
        self.btn_pause.setVisible(s in (State.RUNNING, State.PAUSING))
        self.btn_pause.setEnabled(s == State.RUNNING)
        self.btn_resume.setVisible(s == State.PAUSED)
        self.btn_finish.setVisible(s == State.PAUSED)

        if s == State.CONNECTING:
            self.btn_connect.setVisible(True)
            self.btn_connect.setEnabled(False)
            self.btn_connect.setText("Đang kết nối…")
        else:
            self.btn_connect.setText("Kết nối")

        busy = s in (State.RUNNING, State.PAUSING, State.PAUSED)
        self.btn_pick_file.setEnabled(not busy)
        self.btn_pick_dir.setEnabled(not busy)
        self.cb_strategy.setEnabled(not busy)
        self.chk_correction.setEnabled(not busy)
        self.chk_protect.setEnabled(not busy)
        self.tab_meta.set_edit_allowed(
            not busy, "Không sửa được metadata khi đang chạy — Kết thúc batch trước")

        self.bar.setVisible(busy)
        self._set_prop(self.bar, "hold", s in (State.PAUSING, State.PAUSED))

        texts = {
            State.DISCONNECTED: ("● Chưa kết nối", C["ts"]),
            State.CONNECTING: ("● Đang kiểm tra kết nối…", C["ts"]),
            State.CONNECTED: (f"✓ {self.model_name}", C["ok"]),
            State.RUNNING: ("● Đang chạy", C["ok"]),
            State.PAUSING: ("● Đang tạm dừng…", C["warn"]),
            State.PAUSED: ("● Đã tạm dừng", C["warn"]),
        }
        text, color = texts[s]
        self.lbl_conn.setText(text)
        self.lbl_conn.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:500;")

    @staticmethod
    def _set_prop(widget, name, value):
        """Đặt dynamic property rồi repolish để QSS [prop] cập nhật ngay."""
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # ------------------------------------------------ hành động

    def on_connect(self):
        self.state = State.CONNECTING
        self._apply_state()
        self.tab_console.append_log("info", f"kết nối {self.cfg['endpoint']}…")
        self.connect_worker = ConnectWorker(
            self.cfg["endpoint"], self.cfg["api_key"], parent=self)
        self.connect_worker.ok.connect(self._on_connect_ok)
        self.connect_worker.fail.connect(self._on_connect_fail)
        self.connect_worker.start()

    def _on_connect_ok(self, model_name):
        self.model_name = model_name
        self.ed_model.setText(model_name)
        self.state = State.CONNECTED
        self._apply_state()
        self.tab_console.append_log("info", f"kết nối ok — model {model_name}")

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
        cfg["output_dir"] = str(APP_DIR / self.cfg["output_dir"])
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

        self.ocr_worker = OcrWorker(
            self.files, self.tab_meta.fields, cfg, self.model_name, parent=self)
        self.ocr_worker.log.connect(self.tab_console.append_log)
        self.ocr_worker.progress.connect(self._on_progress)
        self.ocr_worker.row_done.connect(self.tab_results.add_result)
        self.ocr_worker.state_changed.connect(self._on_worker_state)
        self.ocr_worker.finished_all.connect(self._on_finished)
        self.ocr_worker.start()

        self.state = State.RUNNING
        self._apply_state()

    def on_pause(self):
        if self.ocr_worker:
            self.ocr_worker.pause()
            self.state = State.PAUSING
            self._apply_state()

    def on_resume(self):
        if self.ocr_worker:
            self.ocr_worker.resume()
            self.state = State.RUNNING
            self._apply_state()

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
        self.bar.setValue(done)
        self.lbl_count.setText(f"{done}/{total}" +
                               (f" · lỗi {errors}" if errors else ""))

    def _on_worker_state(self, name):
        # Tín hiệu từ worker được Qt xếp hàng, nên có thể đến sau khi batch
        # đã chốt. Nếu đã về CONNECTED thì bỏ qua, tránh rơi lại vào PAUSED
        # và hiện nút Tiếp tục / Kết thúc cho một worker không còn chạy.
        if self.state == State.CONNECTED:
            return
        mapping = {"running": State.RUNNING,
                   "pausing": State.PAUSING,
                   "paused": State.PAUSED}
        if name in mapping:
            self.state = mapping[name]
            self._apply_state()

    def _on_finished(self, stats: dict):
        self.state = State.CONNECTED
        self._apply_state()

        secs = stats.get("elapsed", 0)
        if stats.get("ok") and secs:
            pages = max(self.n_pages, 1)
            self.cfg["seconds_per_page"] = round(secs / pages, 3)

        self.tab_console.append_log(
            "info",
            f"xong · {stats['ok']} thành công · {stats['fail']} lỗi "
            f"· {secs / 60:.1f} phút")

        if stats.get("ok") and stats.get("tsv"):
            self._export_excel(stats)

        self._show_completion(stats)

    # ------------------------------------------------ xuất Excel

    def _export_excel(self, stats: dict):
        """
        Chạy trên UI thread nên hỏi được người dùng. Đọc TSV vài trăm dòng
        rồi ghi xlsx chỉ mất vài chục ms, không cần thread riêng.
        """
        out_dir = Path(APP_DIR / self.cfg["output_dir"])
        target = pipeline.excel_target(
            out_dir, self.ed_path.text(), self.cfg.get("excel_base_name"))

        if target.exists():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("File đã tồn tại")
            box.setText(f"{target.name} đã có trong thư mục xuất.")
            box.setInformativeText(
                f"{target.parent}\n\n"
                "Ghi đè sẽ mất bản cũ. Lưu bản mới sẽ thêm timestamp vào tên.")
            b_over = box.addButton("Ghi đè", QMessageBox.DestructiveRole)
            b_new = box.addButton("Lưu bản mới", QMessageBox.AcceptRole)
            b_skip = box.addButton("Không xuất", QMessageBox.RejectRole)
            box.setDefaultButton(b_new)
            box.exec_()

            clicked = box.clickedButton()
            if clicked is b_skip:
                self.tab_console.append_log("warn", "bỏ qua xuất Excel")
                stats["export_error"] = "người dùng bỏ qua"
                return
            if clicked is b_new:
                target = pipeline.stamped_variant(target)
            elif pipeline.is_locked(target):
                # Excel đang giữ khoá ghi -> ghi đè chắc chắn thất bại
                alt = pipeline.stamped_variant(target)
                QMessageBox.warning(
                    self, "File đang mở",
                    f"{target.name} đang được mở trong Excel nên không ghi đè được.\n\n"
                    f"Sẽ lưu thành {alt.name}.")
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

    # ------------------------------------------------ popup hoàn tất

    def _show_completion(self, stats: dict):
        excel = stats.get("excel", "")
        box = QMessageBox(self)
        box.setWindowTitle("Hoàn tất")

        head = ("Đã kết thúc sớm" if stats.get("aborted")
                else f"Đã xử lý xong {stats['total']} file")
        detail = [f"{stats['ok']} thành công · {stats['fail']} lỗi"]

        corr = stats.get("correction")
        if corr:
            detail.append(
                f"sửa lỗi {corr['corrected']} · từ chối {corr['rejected']}")

        if excel:
            box.setIcon(QMessageBox.Information)
            detail.append(Path(excel).name)
        elif stats.get("export_error"):
            box.setIcon(QMessageBox.Warning)
            detail.append(f"Xuất Excel lỗi: {stats['export_error']}")
            detail.append("File TSV vẫn còn trong thư mục xuất.")
        else:
            box.setIcon(QMessageBox.Warning)
            detail.append("Không có file nào thành công — xem tab Console.")

        box.setText(head)
        box.setInformativeText("\n".join(detail))

        # Có Excel -> mở file. Không có -> mở thư mục để lấy TSV.
        label = "Mở kết quả" if excel else "Mở thư mục"
        btn_open = box.addButton(label, QMessageBox.AcceptRole)
        box.addButton("Đóng", QMessageBox.RejectRole)
        box.setDefaultButton(btn_open)
        box.exec_()

        if box.clickedButton() is btn_open:
            path = excel or str(Path(stats.get("tsv") or APP_DIR).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

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
        event.accept()


def main():
    cfg_path = APP_DIR / "config.json"
    if not cfg_path.exists():
        print(f"Thiếu {cfg_path}")
        sys.exit(1)

    cfg = pipeline.load_config(cfg_path)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    base = QFont("-apple-system" if sys.platform == "darwin" else "Segoe UI")
    base.setPixelSize(12)
    app.setFont(base)
    app.setStyleSheet(build_stylesheet())
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
