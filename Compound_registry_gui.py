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
    QPushButton, QFileDialog, QPlainTextEdit, QMessageBox, QCheckBox, QProgressBar, QComboBox
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

        # Processing controls (compact)
        proc_flags = QHBoxLayout()
        proc_flags.addWidget(QLabel("Classify / Enrich:"))
        self.proc_force_chk = QCheckBox("Force Type")
        self.proc_fetch_smiles_chk = QCheckBox("SMILES")
        self.proc_smiles_force_chk = QCheckBox("SMILES Force")
        self.proc_fetch_props_chk = QCheckBox("Props")
        self.proc_props_force_chk = QCheckBox("Props Force")
        self.proc_dry_chk = QCheckBox("Dry")
        for w in (self.proc_force_chk, self.proc_fetch_smiles_chk, self.proc_smiles_force_chk, self.proc_fetch_props_chk, self.proc_props_force_chk, self.proc_dry_chk):
            proc_flags.addWidget(w)
        layout.addLayout(proc_flags)

        proc_opts = QHBoxLayout()
        self.proc_source_combo = QComboBox(); self.proc_source_combo.addItems(["auto","pubchem","cactus"])
        self.proc_limit_input = QLineEdit(); self.proc_limit_input.setPlaceholderText("SMILES limit")
        self.proc_delay_input = QLineEdit(); self.proc_delay_input.setPlaceholderText("Delay 0.2")
        self.proc_prog_every_input = QLineEdit(); self.proc_prog_every_input.setPlaceholderText("Progress 50")
        run_btn = QPushButton("Process Registry")
        run_btn.clicked.connect(self.on_process_registry)
        proc_opts.addWidget(QLabel("Src")); proc_opts.addWidget(self.proc_source_combo)
        proc_opts.addWidget(self.proc_limit_input)
        proc_opts.addWidget(self.proc_delay_input)
        proc_opts.addWidget(self.proc_prog_every_input)
        proc_opts.addWidget(run_btn)
        layout.addLayout(proc_opts)

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
            added, skipped = self.registry.add_to_jsonl_registry(reg_path, [cas], dry_run=False)
            return (added, skipped)
        self._run_thread(task, lambda res: self.log(f"Added CAS: added={res[0]} skipped={res[1]}") )

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
            added, skipped = self.registry.add_to_jsonl_registry(reg_path, extracted, dry_run=False)
            return (len(extracted), added, skipped)
        self._run_thread(task, lambda res: self.log(f"Scan done: found={res[0]} added={res[1]} skipped={res[2]}") )

    # Removed legacy bulk operations

    def on_process_registry(self):
        reg_path = self._resolve_registry_path()
        if not os.path.exists(reg_path):
            self.log(f"Registry file not found: {reg_path}")
            return
        force = self.proc_force_chk.isChecked()
        fetch_smiles = self.proc_fetch_smiles_chk.isChecked()
        smiles_force = self.proc_smiles_force_chk.isChecked()
        fetch_props = self.proc_fetch_props_chk.isChecked()
        props_force = self.proc_props_force_chk.isChecked()
        dry_run = self.proc_dry_chk.isChecked()
        source = self.proc_source_combo.currentText()
        try:
            limit_txt = self.proc_limit_input.text().strip()
            smiles_limit = int(limit_txt) if limit_txt else None
        except ValueError:
            self.log("Invalid SMILES limit; ignoring")
            smiles_limit = None
        try:
            delay_txt = self.proc_delay_input.text().strip()
            smiles_delay = float(delay_txt) if delay_txt else 0.2
        except ValueError:
            self.log("Invalid delay; using 0.2")
            smiles_delay = 0.2
        try:
            prog_txt = self.proc_prog_every_input.text().strip()
            progress_every = int(prog_txt) if prog_txt else 50
        except ValueError:
            self.log("Invalid progress value; using 50")
            progress_every = 50

        self.log(f"Processing registry (dry={dry_run}, force={force}, smiles={fetch_smiles}, props={fetch_props})")
        def task(signals: WorkerSignals):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                stats = process_registry_file(
                    infile=reg_path,
                    force=force,
                    dry_run=dry_run,
                    backup=not dry_run,
                    fetch_smiles=fetch_smiles,
                    smiles_force=smiles_force,
                    smiles_source=source,
                    request_timeout=8.0,
                    smiles_delay=smiles_delay,
                    smiles_limit=smiles_limit,
                    fetch_props=fetch_props,
                    props_force=props_force,
                    verbose=True,
                    progress_every=progress_every,
                )
            out_text = buf.getvalue().strip()
            if out_text:
                for line in out_text.splitlines():
                    signals.message.emit(line)
            return stats
        def on_done(stats):
            self.log(f"Process complete: total={stats['total']} updated={stats['updated']} smiles={stats.get('smiles_updated',0)} props={stats.get('props_updated',0)} generic_core={stats.get('generic_core_updates',0)}")
        self._run_thread(task, on_done)

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
