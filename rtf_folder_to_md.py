#!/usr/bin/env python3
"""
PyQt6 app to extract and combine text from all RTF files in a folder
and save the result to a Markdown (.md) file.

Features:
- Select a folder containing .rtf files (optionally recurse subfolders)
- Extract plain text (images ignored) using striprtf
- Combine with per-file markdown headers
- Save to chosen .md file

Requirements (in requirements.txt): PyQt6, striprtf
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from striprtf.striprtf import rtf_to_text  # type: ignore


def _human_sort_key(p: str) -> Tuple[str, str]:
    """Sort key: (folder, filename lowercase) for stable ordering."""
    return (os.path.dirname(p).lower(), os.path.basename(p).lower())


def extract_rtf_text(path: str) -> str:
    """Extract plain text from a single RTF file.

    Uses UTF-8 decoding with errors='ignore' to be resilient to encoding issues.
    Falls back to latin-1 if content looks empty.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        text = rtf_to_text(data) or ""
        if not text.strip():
            try:
                with open(path, "r", encoding="latin-1", errors="ignore") as f:
                    data = f.read()
                text = rtf_to_text(data) or ""
            except Exception:
                pass
        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()
    except Exception as e:
        return f"[Error reading {os.path.basename(path)}: {e}]"


def combine_rtf_folder(folder: str, recurse: bool = False, add_headers: bool = True) -> Tuple[str, List[str]]:
    """Find all .rtf files in folder, extract text, and return combined Markdown string.

    Returns (markdown, file_list).
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    rtf_files: List[str] = []
    if recurse:
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.lower().endswith(".rtf"):
                    rtf_files.append(os.path.join(root, fn))
    else:
        for fn in os.listdir(folder):
            if fn.lower().endswith(".rtf"):
                rtf_files.append(os.path.join(folder, fn))

    rtf_files.sort(key=_human_sort_key)

    parts: List[str] = []
    if add_headers:
        parts.append("# Combined RTF Text\n")
    for i, path in enumerate(rtf_files):
        name = os.path.relpath(path, folder)
        txt = extract_rtf_text(path)
        if add_headers:
            parts.append(f"\n## {name}\n\n{txt}\n")
            if i < len(rtf_files) - 1:
                parts.append("\n---\n")
        else:
            parts.append(txt)

    combined = "\n".join(parts).strip() + ("\n" if parts else "")
    return combined, rtf_files


def _suggest_output_path(folder: str) -> str:
    base = os.path.basename(os.path.abspath(folder)) or "rtf_combined"
    return os.path.join(folder, f"{base}_combined.md")


def launch_gui() -> None:  # pragma: no cover - GUI runtime
    from PyQt6 import QtWidgets, QtCore

    class Worker(QtCore.QThread):
        progress = QtCore.pyqtSignal(str)
        progress_step = QtCore.pyqtSignal(int, int, str)  # (current, total, relpath)
        finished = QtCore.pyqtSignal(str, list)  # (output_markdown, files)
        failed = QtCore.pyqtSignal(str)

        def __init__(self, folder: str, recurse: bool, add_headers: bool):
            super().__init__()
            self.folder = folder
            self.recurse = recurse
            self.add_headers = add_headers

        def run(self):
            try:
                folder = self.folder
                if not os.path.isdir(folder):
                    raise FileNotFoundError(f"Folder not found: {folder}")

                # Find files first to know total
                rtf_files: List[str] = []
                if self.recurse:
                    for root, _, files in os.walk(folder):
                        for fn in files:
                            if fn.lower().endswith(".rtf"):
                                rtf_files.append(os.path.join(root, fn))
                else:
                    for fn in os.listdir(folder):
                        if fn.lower().endswith('.rtf'):
                            rtf_files.append(os.path.join(folder, fn))
                rtf_files.sort(key=_human_sort_key)

                total = len(rtf_files)
                parts: List[str] = []
                if self.add_headers:
                    parts.append("# Combined RTF Text\n")

                if total == 0:
                    self.progress.emit("No .rtf files found.")
                for idx, path in enumerate(rtf_files, start=1):
                    rel = os.path.relpath(path, folder)
                    self.progress_step.emit(idx, total, rel)
                    self.progress.emit(f"[{idx}/{total}] {rel}")
                    txt = extract_rtf_text(path)
                    if self.add_headers:
                        parts.append(f"\n## {rel}\n\n{txt}\n")
                        if idx < total:
                            parts.append("\n---\n")
                    else:
                        parts.append(txt)

                combined = "\n".join(parts).strip() + ("\n" if parts else "")
                self.finished.emit(combined, rtf_files)
            except Exception as e:
                self.failed.emit(str(e))

    class MainWin(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("RTF Folder → Markdown")
            self.resize(820, 600)
            self.worker: Optional[Worker] = None
            self._build_ui()

        def _build_ui(self):
            lay = QtWidgets.QVBoxLayout(self)

            # Folder row
            row1 = QtWidgets.QHBoxLayout()
            self.folder_edit = QtWidgets.QLineEdit()
            btn_browse = QtWidgets.QPushButton("Browse…")
            btn_browse.clicked.connect(self._choose_folder)
            row1.addWidget(QtWidgets.QLabel("Folder:"))
            row1.addWidget(self.folder_edit, 1)
            row1.addWidget(btn_browse)
            lay.addLayout(row1)

            # Options row
            row2 = QtWidgets.QHBoxLayout()
            self.chk_recurse = QtWidgets.QCheckBox("Recurse subfolders")
            self.chk_headers = QtWidgets.QCheckBox("Add per-file markdown headers")
            self.chk_headers.setChecked(True)
            row2.addWidget(self.chk_recurse)
            row2.addWidget(self.chk_headers)
            row2.addStretch(1)
            lay.addLayout(row2)

            # Output row
            row3 = QtWidgets.QHBoxLayout()
            self.output_edit = QtWidgets.QLineEdit()
            btn_out = QtWidgets.QPushButton("Save As…")
            btn_out.clicked.connect(self._choose_output)
            row3.addWidget(QtWidgets.QLabel("Output .md:"))
            row3.addWidget(self.output_edit, 1)
            row3.addWidget(btn_out)
            lay.addLayout(row3)

            # Action buttons
            row4 = QtWidgets.QHBoxLayout()
            self.btn_run = QtWidgets.QPushButton("Extract && Save")
            self.btn_run.clicked.connect(self._run)
            row4.addStretch(1)
            row4.addWidget(self.btn_run)
            lay.addLayout(row4)

            # Progress + Log panel
            self.prog = QtWidgets.QProgressBar()
            self.prog.setMinimum(0)
            self.prog.setMaximum(0)
            self.prog.setValue(0)
            lay.addWidget(self.prog)

            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            lay.addWidget(self.log, 1)

        def _choose_folder(self):
            dlg = QtWidgets.QFileDialog(self, "Select folder")
            dlg.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
            dlg.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)
            if dlg.exec():
                paths = dlg.selectedFiles()
                if paths:
                    folder = paths[0]
                    self.folder_edit.setText(folder)
                    # suggest output path
                    self.output_edit.setText(_suggest_output_path(folder))

        def _choose_output(self):
            start = self.output_edit.text().strip() or os.path.join(os.getcwd(), "combined.md")
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Markdown As", start, "Markdown (*.md)")
            if fn:
                if not fn.lower().endswith(".md"):
                    fn += ".md"
                self.output_edit.setText(fn)

        def _run(self):
            folder = self.folder_edit.text().strip()
            if not folder or not os.path.isdir(folder):
                self._log("Please select a valid folder with .rtf files.")
                return
            outp = self.output_edit.text().strip()
            if not outp:
                outp = _suggest_output_path(folder)
                self.output_edit.setText(outp)

            self._set_running(True)
            self._log(f"Scanning: {folder}")
            self.worker = Worker(folder, self.chk_recurse.isChecked(), self.chk_headers.isChecked())
            self.worker.progress.connect(self._log)
            self.worker.progress_step.connect(self._on_progress)
            self.worker.finished.connect(lambda md, files: self._on_done(md, files, outp))
            self.worker.failed.connect(self._on_failed)
            self.worker.start()

        def _on_done(self, md: str, files: List[str], outp: str):
            try:
                if not files:
                    self._log("No .rtf files found.")
                else:
                    os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
                    with open(outp, "w", encoding="utf-8", newline="") as f:
                        f.write(md)
                    self._log(f"Saved: {outp} ({len(files)} files)")
            except Exception as e:
                self._log(f"Error saving file: {e}")
            finally:
                self._set_running(False)

        def _on_failed(self, msg: str):
            self._log(f"Error: {msg}")
            self._set_running(False)

        def _set_running(self, running: bool):
            self.btn_run.setEnabled(not running)
            if running:
                # Indeterminate until we learn the total; it will be set by _on_progress
                self.prog.setMaximum(0)
                self.prog.setValue(0)
            else:
                self.prog.setMaximum(1)
                self.prog.setValue(0)

        def _log(self, msg: str):
            self.log.appendPlainText(str(msg))

        def _on_progress(self, current: int, total: int, relpath: str):
            # Initialize range when total known
            try:
                self.prog.setMaximum(total)
            except Exception:
                pass
            self.prog.setValue(current)

    app = QtWidgets.QApplication(sys.argv)
    w = MainWin()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()
