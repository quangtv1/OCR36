"""
workers.py — QThread cho kết nối và xử lý OCR.

Nguyên tắc bất di bất dịch: worker KHÔNG BAO GIỜ chạm vào widget.
Mọi thứ đi ra ngoài đều qua pyqtSignal.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

import pipeline


# ============================================================ KẾT NỐI

class ConnectWorker(QThread):
    """Thử models.list() với timeout ngắn, không để treo UI."""

    ok = pyqtSignal(str)        # model_name
    fail = pyqtSignal(str)      # thông báo lỗi

    def __init__(self, endpoint, api_key, timeout=5.0, parent=None):
        super().__init__(parent)
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    def run(self):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key,
                            base_url=self.endpoint,
                            timeout=self.timeout)
            models = client.models.list().data
            if not models:
                self.fail.emit("server không trả về model nào")
                return
            self.ok.emit(models[0].id)
        except Exception as e:
            self.fail.emit(str(e))


# ============================================================ OCR

class OcrWorker(QThread):
    """
    Chạy batch OCR. Hỗ trợ tạm dừng / tiếp tục / kết thúc sớm.

    Tạm dừng ở mức FILE, không giữa file: file đang chạy sẽ hoàn tất
    rồi mới dừng, vì các request cho trang của nó đã gửi lên server.
    """

    log = pyqtSignal(str, str)          # (mức, nội dung) — info|data|warn|error
    progress = pyqtSignal(int, int, int)  # (đã xong, tổng, số lỗi)
    row_done = pyqtSignal(dict)         # kết quả một file
    state_changed = pyqtSignal(str)     # "running" | "pausing" | "paused"
    finished_all = pyqtSignal(dict)     # tổng kết + đường dẫn file

    def __init__(self, files, fields, cfg, model_name, parent=None):
        super().__init__(parent)
        self.files: list[Path] = list(files)
        self.fields = dict(fields)
        self.cfg = dict(cfg)
        self.model_name = model_name

        self._resume = threading.Event()
        self._resume.set()                 # mặc định: cho chạy
        self._abort = threading.Event()

        self.writer: pipeline.TsvWriter | None = None
        self.done = 0
        self.errors = 0

    # ---------------------------------------------------- điều khiển

    def pause(self):
        """Gọi từ UI thread. Worker sẽ dừng sau khi xong file hiện tại."""
        self._resume.clear()
        self.state_changed.emit("pausing")

    def resume(self):
        self._resume.set()
        self.state_changed.emit("running")

    def finish_early(self):
        """
        Kết thúc sớm. Thứ tự QUAN TRỌNG: set abort rồi PHẢI mở _resume,
        nếu không worker đang block trong _resume.wait() sẽ không bao giờ
        thấy cờ abort và app treo lúc đóng.
        """
        self._abort.set()
        self._resume.set()

    @property
    def aborted(self) -> bool:
        return self._abort.is_set()

    # ---------------------------------------------------- vòng chạy

    def run(self):
        cfg = self.cfg
        field_keys = list(self.fields.keys())
        total = len(self.files)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=cfg["api_key"],
                            base_url=cfg["endpoint"],
                            timeout=cfg.get("request_timeout", 120))
        except Exception as e:
            self.log.emit("error", f"không tạo được client: {e}")
            self.finished_all.emit({"total": total, "ok": 0, "fail": 0,
                                    "aborted": True, "excel": "",
                                    "error": str(e)})
            return

        corrector = None
        if cfg.get("use_correction"):
            self.log.emit("info", "kết nối bộ sửa lỗi ProtonX…")
            try:
                corrector = pipeline.get_corrector(
                    cfg["correction_endpoint"],
                    cfg["correction_model"],
                    cfg.get("api_key", "EMPTY"),
                    cfg.get("correction_num_beams", 10),
                    cfg.get("protected_terms", []),
                    cfg.get("correction_use_chat", False),
                )
                self.log.emit("info", "bộ sửa lỗi ProtonX sẵn sàng (server)")
            except Exception as e:
                self.log.emit("warn", f"không kết nối được bộ sửa lỗi: {e}")
                self.log.emit("warn", "chạy tiếp mà không sửa lỗi")

        self.writer = pipeline.TsvWriter(cfg["output_dir"], field_keys)
        self.log.emit("info", f"ghi TSV: {self.writer.tsv_path.name}")

        started = time.time()
        consecutive_errors = 0
        limit = cfg.get("consecutive_error_limit", 3)

        for path in self.files:
            if self._abort.is_set():
                break

            # điểm tạm dừng
            if not self._resume.is_set():
                self.state_changed.emit("paused")
                self._resume.wait()
                if self._abort.is_set():
                    break
                self.state_changed.emit("running")

            try:
                n = pipeline.pdf_page_count(path)
                self.log.emit("info", f"{path.name} · {n} trang")

                result = pipeline.process_pdf(
                    path, self.fields, client, self.model_name, cfg,
                    corrector=corrector,
                    cancel_check=lambda: self._abort.is_set(),
                )

                data = result["data"]
                summary = "\t".join(
                    str(data.get(k, "") or "—")
                    for k in field_keys[:3]
                )
                self.log.emit("data", summary)

                empties = [k for k in field_keys if pipeline.is_empty(data.get(k))]
                for k in empties:
                    where = result["provenance"].get(k)
                    self.log.emit(
                        "warn",
                        f"{k} rỗng"
                        + (f" — trang {where}/{result['total_pages']}" if where
                           else f" — đã đọc {result['pages_processed']}")
                    )

                audit = result.get("correction_audit") or {}
                fixed = sum(1 for v in audit.values()
                            if v["status"] == "corrected")
                rejected = sum(1 for v in audit.values()
                               if v["status"].startswith("rejected"))
                if fixed or rejected:
                    self.log.emit(
                        "info",
                        f"sửa lỗi {fixed} trường · từ chối {rejected}")

                self.writer.append(result)
                self.row_done.emit(result)
                consecutive_errors = 0

            except Exception as e:
                self.errors += 1
                consecutive_errors += 1
                msg = str(e)
                self.log.emit("error", f"{path.name} — {msg}")
                if self.writer:
                    self.writer.append_error(path.name, msg)
                self.row_done.emit({"name": path.name, "error": msg})

                if consecutive_errors >= limit:
                    self.log.emit(
                        "error",
                        f"{consecutive_errors} file lỗi liên tiếp — tự tạm dừng. "
                        "Kiểm tra server rồi bấm Tiếp tục.")
                    self._resume.clear()
                    consecutive_errors = 0

            finally:
                self.done += 1
                self.progress.emit(self.done, total, self.errors)

        # ---- chốt batch
        # Không xuất Excel ở đây: việc hỏi ghi đè phải diễn ra trên UI thread.
        # Worker chỉ báo TSV đã xong, MainWindow lo phần xuất.
        elapsed = time.time() - started
        ok_count = self.done - self.errors

        if ok_count == 0:
            self.log.emit("warn", "không có file nào thành công — bỏ qua Excel")

        stats = {
            "total": total,
            "processed": self.done,
            "ok": ok_count,
            "fail": self.errors,
            "aborted": self._abort.is_set(),
            "elapsed": elapsed,
            "excel": "",
            "export_error": "",
            "tsv": str(self.writer.tsv_path) if self.writer else "",
        }
        if corrector is not None:
            stats["correction"] = dict(corrector.stats)

        self.finished_all.emit(stats)


# ============================================================ ĐẾM TRANG

class ScanWorker(QThread):
    """Quét nguồn (glob thư mục) + đếm trang từng PDF trong nền.

    Chạy trên luồng riêng để thư mục hàng trăm nghìn file không treo UI.
    Đếm trang MỘT LẦN rồi trả về để UI cache — đổi chiến lược trang sau đó
    chỉ cần tính số học, không mở lại PDF. Huỷ được qua requestInterruption().
    """

    progress = pyqtSignal(int, int)          # (đã đếm, tổng file)
    done = pyqtSignal(object, object, int)   # (files, page_counts, tổng trang)

    def __init__(self, source, strategy, parent=None):
        super().__init__(parent)
        self.source = source
        self.strategy = strategy

    def run(self):
        try:
            files = pipeline.collect_pdf_files(self.source)
        except Exception:
            files = []
        if self.isInterruptionRequested():
            return

        counts, pages, total = [], 0, len(files)
        for i, f in enumerate(files):
            if self.isInterruptionRequested():
                return
            n = pipeline.pdf_page_count(f)
            counts.append(n)
            pages += pipeline.count_selected_pages(n, self.strategy)
            if i % 100 == 0:
                self.progress.emit(i + 1, total)

        if not self.isInterruptionRequested():
            self.done.emit(files, counts, pages)
