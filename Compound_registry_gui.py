#!/usr/bin/env python3
"""PyQt6 GUI for Comprehensive CAS Registry Tool.

Features implemented (parity with CLI):
- Validate single CAS (format + checksum + type + manual name)
- Lookup CAS (manual + PubChem if available)
- Batch CSV validate/correct and save output
- Build registry from folder of CSV files
- JSONL registry augmentation: add single CAS / CSV list / scan text file
- Update existing JSONL entries (fill missing fields)

Design:
- QTabWidget with tabs: Validate, Lookup, Batch Validate, Build Registry, JSONL Add/Update
- ThreadedWorker (QThread) for long running tasks; UI remains responsive
- Central log panel (QPlainTextEdit) with timestamped messages; also optional status bar messages
- File/folder pickers using QFileDialog
- Drag & drop support for files into relevant line edits (basic)

Dependencies: PyQt6 (already declared in requirements.txt)

"""
from __future__ import annotations
import sys, os, csv, traceback, re
from datetime import datetime
from pathlib import Path
from typing import List, Iterable, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QPlainTextEdit, QFormLayout, QMessageBox, QSpinBox,
    QTextEdit, QCheckBox, QGroupBox, QProgressBar
)

from Compound_registry_generator import ComprehensiveCASRegistry

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

# --------------- Main GUI ----------------------
class CASRegistryGUI(QWidget, LogMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAS Registry Tool")
        self.resize(900, 650)
        self.registry = ComprehensiveCASRegistry()
        self.threads: List[QThread] = []
        self._build_ui()

    # UI construction
    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Shared log
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_view, 2)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0,0)  # hidden/inactive by default
        self.progress.hide()
        layout.addWidget(self.progress)

        self._tab_validate()
        self._tab_lookup()
        self._tab_batch()
        self._tab_build_registry()
        self._tab_jsonl()

    # ---------------- Tabs ------------------
    def _tab_validate(self):
        w = QWidget()
        form = QFormLayout(w)
        self.validate_input = QLineEdit()
        btn = QPushButton("Validate")
        btn.clicked.connect(self.on_validate)
        form.addRow("CAS Number", self.validate_input)
        form.addRow(btn)
        self.tabs.addTab(w, "Validate")

    def _tab_lookup(self):
        w = QWidget()
        form = QFormLayout(w)
        self.lookup_input = QLineEdit()
        btn = QPushButton("Lookup")
        btn.clicked.connect(self.on_lookup)
        self.lookup_result = QTextEdit(); self.lookup_result.setReadOnly(True)
        form.addRow("CAS Number", self.lookup_input)
        form.addRow(btn)
        form.addRow(QLabel("Result"), self.lookup_result)
        self.tabs.addTab(w, "Lookup")

    def _tab_batch(self):
        w = QWidget(); v = QVBoxLayout(w)
        top = QHBoxLayout()
        self.batch_csv_input = QLineEdit(); self.batch_csv_input.setPlaceholderText("Input CSV with Name,CAS columns")
        pick_in = QPushButton("Browse…")
        pick_in.clicked.connect(lambda: self._pick_file(self.batch_csv_input, 'CSV Files (*.csv)'))
        top.addWidget(QLabel("Input CSV")); top.addWidget(self.batch_csv_input,1); top.addWidget(pick_in)

        top2 = QHBoxLayout()
        self.batch_out_input = QLineEdit(); self.batch_out_input.setPlaceholderText("Output CSV (auto if blank)")
        pick_out = QPushButton("Save As…")
        pick_out.clicked.connect(lambda: self._pick_save_file(self.batch_out_input, 'CSV Files (*.csv)'))
        top2.addWidget(QLabel("Output CSV")); top2.addWidget(self.batch_out_input,1); top2.addWidget(pick_out)

        run_btn = QPushButton("Run Batch Validate")
        run_btn.clicked.connect(self.on_batch_validate)

        v.addLayout(top); v.addLayout(top2); v.addWidget(run_btn)
        self.tabs.addTab(w, "Batch Validate")

    def _tab_build_registry(self):
        w = QWidget(); v = QVBoxLayout(w)
        h1 = QHBoxLayout()
        self.folder_input = QLineEdit(); self.folder_input.setPlaceholderText("Folder containing CSV files")
        pick_folder = QPushButton("Browse…")
        pick_folder.clicked.connect(lambda: self._pick_folder(self.folder_input))
        h1.addWidget(QLabel("CSV Folder")); h1.addWidget(self.folder_input,1); h1.addWidget(pick_folder)

        h2 = QHBoxLayout()
        self.registry_output_input = QLineEdit(); self.registry_output_input.setPlaceholderText("Output registry CSV")
        pick_out = QPushButton("Save As…")
        pick_out.clicked.connect(lambda: self._pick_save_file(self.registry_output_input, 'CSV Files (*.csv)'))
        h2.addWidget(QLabel("Output CSV")); h2.addWidget(self.registry_output_input,1); h2.addWidget(pick_out)

        btn = QPushButton("Build Registry")
        btn.clicked.connect(self.on_build_registry)

        v.addLayout(h1); v.addLayout(h2); v.addWidget(btn)
        self.tabs.addTab(w, "Build Registry")

    def _tab_jsonl(self):
        w = QWidget(); v = QVBoxLayout(w)

        # Registry path
        hreg = QHBoxLayout()
        self.jsonl_path_input = QLineEdit(); self.jsonl_path_input.setPlaceholderText("cas_registry_merged.jsonl (auto if blank)")
        pick_reg = QPushButton("Browse…")
        pick_reg.clicked.connect(lambda: self._pick_file(self.jsonl_path_input, 'JSONL Files (*.jsonl);;All Files (*.*)'))
        hreg.addWidget(QLabel("Registry JSONL")); hreg.addWidget(self.jsonl_path_input,1); hreg.addWidget(pick_reg)
        v.addLayout(hreg)

        # Add single CAS
        hsingle = QHBoxLayout()
        self.add_single_input = QLineEdit(); self.add_single_input.setPlaceholderText("Single CAS to add")
        btn_single = QPushButton("Add CAS")
        btn_single.clicked.connect(self.on_add_single)
        hsingle.addWidget(QLabel("Single CAS")); hsingle.addWidget(self.add_single_input,1); hsingle.addWidget(btn_single)
        v.addLayout(hsingle)

        # Add from CSV
        hcsv = QHBoxLayout()
        self.add_csv_input = QLineEdit(); self.add_csv_input.setPlaceholderText("CSV with CAS list")
        btn_csv = QPushButton("Browse CSV…")
        btn_csv.clicked.connect(lambda: self._pick_file(self.add_csv_input, 'CSV Files (*.csv);;All Files (*.*)'))
        add_csv_btn = QPushButton("Add CSV CAS")
        add_csv_btn.clicked.connect(self.on_add_csv)
        hcsv.addWidget(QLabel("CSV File")); hcsv.addWidget(self.add_csv_input,1); hcsv.addWidget(btn_csv); hcsv.addWidget(add_csv_btn)
        v.addLayout(hcsv)

        # Add from text
        htxt = QHBoxLayout()
        self.add_text_input = QLineEdit(); self.add_text_input.setPlaceholderText("Text file to scan")
        btn_txt = QPushButton("Browse Text…")
        btn_txt.clicked.connect(lambda: self._pick_file(self.add_text_input, 'Text Files (*.txt *.md);;All Files (*.*)'))
        add_text_btn = QPushButton("Scan & Add")
        add_text_btn.clicked.connect(self.on_add_text)
        htxt.addWidget(QLabel("Text File")); htxt.addWidget(self.add_text_input,1); htxt.addWidget(btn_txt); htxt.addWidget(add_text_btn)
        v.addLayout(htxt)

        # Update existing
        hupd = QHBoxLayout()
        self.update_selected_input = QLineEdit(); self.update_selected_input.setPlaceholderText("CAS list (comma-separated) blank=all")
        btn_upd = QPushButton("Update Existing")
        btn_upd.clicked.connect(self.on_update_existing)
        self.dry_run_chk = QCheckBox("Dry Run")
        hupd.addWidget(QLabel("Update CAS")); hupd.addWidget(self.update_selected_input,1); hupd.addWidget(self.dry_run_chk); hupd.addWidget(btn_upd)
        v.addLayout(hupd)

        self.tabs.addTab(w, "JSONL Add/Update")

    # ---------------- Event handlers ----------------
    def on_validate(self):
        cas = self.validate_input.text().strip()
        if not cas:
            return
        valid_format = self.registry.validate_cas_format(cas)
        checksum_valid = self.registry.calculate_cas_checksum(cas) if valid_format else False
        msg = [f"CAS: {cas}", f"Format valid: {valid_format}", f"Checksum valid: {checksum_valid}"]
        if cas in self.registry.manual_corrections:
            msg.append(f"Manual name: {self.registry.manual_corrections[cas]}")
        ctype = self.registry.get_compound_type(cas)
        if ctype:
            msg.append(f"Type: {ctype}")
        self.log('\n'.join(msg))

    def on_lookup(self):
        cas = self.lookup_input.text().strip()
        if not cas:
            return
        def task(signals: WorkerSignals):
            signals.message.emit(f"Looking up {cas}…")
            lines = []
            if cas in self.registry.manual_corrections:
                lines.append(f"Manual name: {self.registry.manual_corrections[cas]}")
            online = self.registry.lookup_pubchem(cas)
            if online:
                lines.append(f"PubChem Name: {online.get('name')}")
                lines.append(f"Formula: {online.get('formula')}")
                lines.append(f"MW: {online.get('molecular_weight')}")
            ctype = self.registry.get_compound_type(cas)
            if ctype:
                lines.append(f"Type: {ctype}")
            return '\n'.join(lines) or 'No data.'
        self._run_thread(task, lambda res: self.lookup_result.setPlainText(res))

    def on_batch_validate(self):
        in_csv = self.batch_csv_input.text().strip()
        if not in_csv:
            self._warn("Select input CSV")
            return
        out_csv = self.batch_out_input.text().strip() or in_csv.replace('.csv', '_corrected.csv')
        def task(signals: WorkerSignals):
            signals.message.emit(f"Batch validating {in_csv}")
            self.registry.batch_validate_csv(in_csv, out_csv)
            return out_csv
        self._run_thread(task, lambda path: self.log(f"Batch complete → {path}"))

    def on_build_registry(self):
        folder = self.folder_input.text().strip()
        if not folder:
            self._warn("Select folder")
            return
        out_csv = self.registry_output_input.text().strip() or "comprehensive_cas_registry.csv"
        def task(signals: WorkerSignals):
            signals.message.emit(f"Building registry from {folder}")
            self.registry.build_registry_from_folder(folder, out_csv)
            return out_csv
        self._run_thread(task, lambda path: self.log(f"Registry built → {path}"))

    def _resolve_registry_path(self) -> str:
        p = self.jsonl_path_input.text().strip()
        if not p:
            p = os.path.join(os.getcwd(), 'cas_registry_merged.jsonl')
        return p

    def on_add_single(self):
        cas = self.add_single_input.text().strip()
        if not cas:
            return
        reg_path = self._resolve_registry_path()
        def task(signals: WorkerSignals):
            added, skipped = self.registry.add_to_jsonl_registry(reg_path, [cas], dry_run=False)
            return (added, skipped)
        self._run_thread(task, lambda res: self.log(f"Add single: added={res[0]} skipped={res[1]}"))

    def on_add_csv(self):
        csv_path = self.add_csv_input.text().strip()
        if not csv_path:
            return
        reg_path = self._resolve_registry_path()
        def task(signals: WorkerSignals):
            todo: List[str] = []
            with open(csv_path,'r',encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row: todo.append(row[0].strip())
            added, skipped = self.registry.add_to_jsonl_registry(reg_path, todo, dry_run=False)
            return (added, skipped)
        self._run_thread(task, lambda res: self.log(f"Add CSV: added={res[0]} skipped={res[1]}"))

    def on_add_text(self):
        txt_path = self.add_text_input.text().strip()
        if not txt_path:
            return
        reg_path = self._resolve_registry_path()
        def task(signals: WorkerSignals):
            extracted = self.registry.extract_cas_from_text(txt_path)
            added, skipped = self.registry.add_to_jsonl_registry(reg_path, extracted, dry_run=False)
            return (len(extracted), added, skipped)
        self._run_thread(task, lambda res: self.log(f"Scanned {res[0]} CAS; added={res[1]} skipped={res[2]}"))

    def on_update_existing(self):
        reg_path = self._resolve_registry_path()
        cas_list_text = self.update_selected_input.text().strip()
        cas_list = [c.strip() for c in cas_list_text.split(',') if c.strip()] if cas_list_text else None
        dry = self.dry_run_chk.isChecked()
        def task(signals: WorkerSignals):
            updated, not_found = self.registry.update_jsonl_registry(reg_path, cas_list, dry_run=dry)
            return (updated, not_found, dry)
        self._run_thread(task, lambda res: self.log(f"Update existing: updated={res[0]} not_found={res[1]} dry={res[2]}"))

    # --------------- Thread helper ---------------
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

    # --------------- Helpers ----------------------
    def _pick_file(self, line: QLineEdit, filter_str: str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", os.getcwd(), filter_str)
        if path:
            line.setText(path)
    def _pick_save_file(self, line: QLineEdit, filter_str: str):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", os.getcwd(), filter_str)
        if path:
            line.setText(path)
    def _pick_folder(self, line: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", os.getcwd())
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
