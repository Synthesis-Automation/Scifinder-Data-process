#!/usr/bin/env python3
"""PyQt6 GUI (simplified) for CAS JSONL Registry Maintenance.

Features retained:
- Add single CAS to registry jsonl.
- Process registry (classify compound_type + optional SMILES / property enrichment).

Removed (per user request): CSV bulk add, text scan, bulk update existing list.
"""

from __future__ import annotations
import sys, os, traceback, io, contextlib
from datetime import datetime
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QPlainTextEdit, QMessageBox, QProgressBar
)

from Compound_registry_generator import ComprehensiveCASRegistry
from Process_compound_registry import process_file as process_registry_file

# ---------------- Worker Infra -----------------
class WorkerSignals(QObject):
    message = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)

class ThreadedWorker(QThread):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            ret = self.fn(self.signals, *self.args, **self.kwargs)
            self.signals.result.emit(ret)
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(f"{e}\n{tb}")
        finally:
            self.signals.finished.emit()

# --------------- Utility logging ---------------
class LogMixin:
    def log(self, text: str):
        if not text.endswith('\n'):
            text += '\n'
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_view.appendPlainText(f"[{timestamp}] {text}")

class CASRegistryGUI(QWidget, LogMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAS JSONL Registry Tool")
        self.resize(720, 480)
        self.registry = ComprehensiveCASRegistry()
        self.threads: List[QThread] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Registry path row
        path_row = QHBoxLayout()
        self.jsonl_path_input = QLineEdit(); self.jsonl_path_input.setPlaceholderText("cas_registry_merged.jsonl (auto if blank)")
        pick_btn = QPushButton("Browse…")
        pick_btn.clicked.connect(lambda: self._pick_file(self.jsonl_path_input, 'JSONL Files (*.jsonl);;All Files (*.*)'))
        path_row.addWidget(QLabel("Registry")); path_row.addWidget(self.jsonl_path_input,1); path_row.addWidget(pick_btn)
        layout.addLayout(path_row)

        # Single CAS add row
        add_row = QHBoxLayout()
        self.add_single_input = QLineEdit(); self.add_single_input.setPlaceholderText("Enter CAS to add")
        add_btn = QPushButton("Add CAS")
        add_btn.clicked.connect(self.on_add_single)
        add_row.addWidget(QLabel("Add")); add_row.addWidget(self.add_single_input,1); add_row.addWidget(add_btn)
        layout.addLayout(add_row)
        # Text / Markdown scan row
        text_row = QHBoxLayout()
        self.add_text_input = QLineEdit(); self.add_text_input.setPlaceholderText("Text/Markdown file to scan for CAS")
        txt_browse = QPushButton("Browse…")
        txt_browse.clicked.connect(lambda: self._pick_file(self.add_text_input, 'Text/Markdown (*.txt *.md);;All Files (*.*)'))
        scan_btn = QPushButton("Scan & Add")
        scan_btn.clicked.connect(self.on_add_text)
        text_row.addWidget(QLabel("Scan")); text_row.addWidget(self.add_text_input,1); text_row.addWidget(txt_browse); text_row.addWidget(scan_btn)
        layout.addLayout(text_row)

        # Log view
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumBlockCount(4000)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_view, 1)

        # Progress bar
        self.progress = QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); layout.addWidget(self.progress)

    def _resolve_registry_path(self) -> str:
        p = self.jsonl_path_input.text().strip()
        if not p:
            p = os.path.join(os.getcwd(), 'cas_registry_merged.jsonl')
        return p

    # ---- Actions ----
    def on_add_single(self):
        cas = self.add_single_input.text().strip()
        if not cas:
            return
        reg_path = self._resolve_registry_path()
        def task(signals: WorkerSignals):
            class Streamer:
                def __init__(self, emit):
                    self._buf=''; self.emit=emit
                def write(self, data):
                    self._buf += data
                    while '\n' in self._buf:
                        line, self._buf = self._buf.split('\n',1)
                        if line.strip():
                            self.emit(line)
                def flush(self):
                    if self._buf.strip():
                        self.emit(self._buf.strip()); self._buf=''
            streamer = Streamer(signals.message.emit)
            with contextlib.redirect_stdout(streamer):
                added, skipped = self.registry.add_to_jsonl_registry(reg_path, [cas], dry_run=False)
            streamer.flush()
            return (added, skipped)
        self._run_thread(task, lambda res: self._post_add_process(reg_path, f"Added CAS: added={res[0]} skipped={res[1]}") )

    def on_add_text(self):
        path = self.add_text_input.text().strip()
        if not path:
            return
        if not os.path.exists(path):
            self.log(f"File not found: {path}")
            return
        reg_path = self._resolve_registry_path()
        self.log(f"Scanning file for CAS: {os.path.basename(path)}")
        def task(signals: WorkerSignals):
            extracted = self.registry.extract_cas_from_text(path)
            class Streamer:
                def __init__(self, emit):
                    self._buf=''; self.emit=emit
                def write(self, data):
                    self._buf += data
                    while '\n' in self._buf:
                        line, self._buf = self._buf.split('\n',1)
                        if line.strip():
                            self.emit(line)
                def flush(self):
                    if self._buf.strip():
                        self.emit(self._buf.strip()); self._buf=''
            streamer = Streamer(signals.message.emit)
            with contextlib.redirect_stdout(streamer):
                added, skipped = self.registry.add_to_jsonl_registry(reg_path, extracted, dry_run=False)
            streamer.flush()
            return (len(extracted), added, skipped)
        self._run_thread(task, lambda res: self._post_add_process(reg_path, f"Scan done: found={res[0]} added={res[1]} skipped={res[2]}") )

    # Automatic post-add processing (assign type + fetch SMILES with defaults)
    def _post_add_process(self, reg_path: str, prefix_log: str):
        self.log(prefix_log)
        if not os.path.exists(reg_path):
            return
        self.log("Running automatic classification & SMILES enrichment...")
        def task(signals: WorkerSignals):
            class Streamer:
                def __init__(self, emit):
                    self._buf = ''
                    self.emit = emit
                def write(self, data):
                    self._buf += data
                    while '\n' in self._buf:
                        line, self._buf = self._buf.split('\n',1)
                        if line.strip():
                            self.emit(line)
                def flush(self):
                    if self._buf.strip():
                        self.emit(self._buf.strip())
                        self._buf = ''
            streamer = Streamer(signals.message.emit)
            with contextlib.redirect_stdout(streamer):
                stats = process_registry_file(
                    infile=reg_path,
                    force=False,
                    dry_run=False,
                    backup=True,
                    fetch_smiles=True,
                    smiles_force=False,
                    smiles_source="auto",
                    request_timeout=8.0,
                    smiles_delay=0.2,
                    smiles_limit=None,
                    fetch_props=True,
                    props_force=False,
                    verbose=True,
                    progress_every=50,
                )
            streamer.flush()
            return stats
        def done(stats):
            self.log(
                f"Auto process complete: total={stats['total']} type_updates={stats['updated']} smiles={stats.get('smiles_updated',0)} props={stats.get('props_updated',0)}"
            )
            if stats.get('smiles_updated',0) == 0 and stats.get('props_updated',0) == 0:
                self.log("Note: No SMILES/properties updated. Ensure 'requests' is installed and you have internet access. Run 'pip install requests' if missing.")
        self._run_thread(task, done)

    # ---- Thread helpers ----
    def _run_thread(self, fn, on_result=None):
        self.progress.show(); self.progress.setRange(0,0)
        worker = ThreadedWorker(fn)
        worker.signals.message.connect(self.log)
        worker.signals.error.connect(lambda e: self.log(f"ERROR: {e}"))
        if on_result:
            worker.signals.result.connect(on_result)
        worker.signals.finished.connect(lambda: self._thread_done(worker))
        self.threads.append(worker)
        worker.start()

    def _thread_done(self, worker: QThread):
        if worker in self.threads:
            self.threads.remove(worker)
        if not self.threads:
            self.progress.hide()

    # ---- Helpers ----
    def _pick_file(self, line: QLineEdit, filter_str: str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", os.getcwd(), filter_str)
        if path:
            line.setText(path)
    def _warn(self, text: str):
        QMessageBox.warning(self, "Warning", text)

# --------------- Entrypoint ----------------------
def launch_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    gui = CASRegistryGUI()
    gui.show()
    return app.exec()

if __name__ == '__main__':
    sys.exit(launch_gui())
