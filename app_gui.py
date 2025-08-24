#!/usr/bin/env python3
"""
Simple Qt6 GUI wrapper for process_reactions.
Lets the user pick RDF/TXT inputs, optional CAS maps, output CSV, and runs processing.
Works with PySide6 (preferred) or PyQt6 if installed.
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import List, Optional


from PyQt6 import QtWidgets, QtCore
QtBinding = 'PyQt6'


# Bind Signal/Slot names across PySide6/PyQt6
if hasattr(QtCore, 'Signal') and hasattr(QtCore, 'Slot'):
    Signal = QtCore.Signal
    Slot = QtCore.Slot
elif hasattr(QtCore, 'pyqtSignal') and hasattr(QtCore, 'pyqtSlot'):
    Signal = QtCore.pyqtSignal  # type: ignore[attr-defined]
    Slot = QtCore.pyqtSlot      # type: ignore[attr-defined]
else:  # pragma: no cover
    Signal = None  # type: ignore
    Slot = None    # type: ignore

# Import processing functions from the existing module
from process_reactions import (
    parse_txt,
    parse_rdf,
    assemble_rows,
    write_csv,
    load_cas_maps,
)


class Worker(QtCore.QObject):
    finished = Signal(bool, str) if Signal else None  # type: ignore[misc]

    def __init__(self, rdf_path: str, txt_path: str, out_path: str, cas_maps: Optional[List[str]], auto_detect_maps: bool):
        super().__init__()
        self.rdf_path = rdf_path
        self.txt_path = txt_path
        self.out_path = out_path
        self.cas_maps = cas_maps or []
        self.auto_detect_maps = auto_detect_maps

    @Slot() if Slot else (lambda f: f)
    def run(self):  # heavy work off UI thread
        try:
            txt = parse_txt(self.txt_path)
            rdf = parse_rdf(self.rdf_path)

            cas_map_paths: List[str] = list(self.cas_maps)
            if self.auto_detect_maps:
                here = os.path.dirname(os.path.abspath(__file__))
                maybe = [
                    os.path.join(here, 'Buchwald', 'cas_dictionary.csv'),
                    os.path.join(here, 'Ullman', '新建文件夹', 'ullmann_cas_to_name_mapping.csv'),
                ]
                cas_map_paths.extend([p for p in maybe if os.path.exists(p)])
            cas_map = load_cas_maps(cas_map_paths) if cas_map_paths else {}

            rows = assemble_rows(txt, rdf, cas_map)
            write_csv(rows, self.out_path)
            if self.finished:
                self.finished.emit(True, f"Wrote {len(rows)} rows to {self.out_path}")
        except Exception as e:
            msg = f"Error: {e}\n\n{traceback.format_exc()}"
            if self.finished:
                self.finished.emit(False, msg)


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SciFinder Reaction Processor")
        self.resize(700, 360)

        # Inputs
        self.rdf_edit = QtWidgets.QLineEdit()
        self.txt_edit = QtWidgets.QLineEdit()
        self.out_edit = QtWidgets.QLineEdit()
        self.cas_edit = QtWidgets.QLineEdit()
        self.cas_edit.setReadOnly(True)

        self.btn_rdf = QtWidgets.QPushButton("Browse RDF…")
        self.btn_txt = QtWidgets.QPushButton("Browse TXT…")
        self.btn_out = QtWidgets.QPushButton("Save CSV…")
        self.btn_cas = QtWidgets.QPushButton("Add CAS Map(s)…")

        self.chk_auto = QtWidgets.QCheckBox("Auto-detect built-in CAS maps")
        self.chk_auto.setChecked(True)

        # Actions
        self.btn_run = QtWidgets.QPushButton("Run")
        self.btn_quit = QtWidgets.QPushButton("Quit")

        # Log output
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)

        form = QtWidgets.QFormLayout()
        form.addRow("RDF:", self._hbox(self.rdf_edit, self.btn_rdf))
        form.addRow("TXT:", self._hbox(self.txt_edit, self.btn_txt))
        form.addRow("Output CSV:", self._hbox(self.out_edit, self.btn_out))
        form.addRow(self.chk_auto)
        form.addRow("CAS Map(s):", self._hbox(self.cas_edit, self.btn_cas))

        btns = self._hbox(self.btn_run, self.btn_quit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.log, 1)
        layout.addLayout(btns)

        # Signals
        self.btn_rdf.clicked.connect(self.pick_rdf)
        self.btn_txt.clicked.connect(self.pick_txt)
        self.btn_out.clicked.connect(self.pick_out)
        self.btn_cas.clicked.connect(self.pick_cas)
        self.chk_auto.toggled.connect(self.on_auto_toggle)
        self.btn_run.clicked.connect(self.run_job)
        self.btn_quit.clicked.connect(self.close)

        # runtime state
        self.cas_paths = []
        self.thread = None
        self.worker = None

    def _hbox(self, *widgets):
        box = QtWidgets.QHBoxLayout()
        for w in widgets:
            if isinstance(w, QtWidgets.QWidget):
                box.addWidget(w)
            else:
                box.addLayout(w)
        return box

    def log_msg(self, text: str):
        self.log.appendPlainText(text)

    def pick_rdf(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select RDF", os.getcwd(), "RDF files (*.rdf);;All files (*.*)")
        if path:
            self.rdf_edit.setText(path)
            self.suggest_out()

    def pick_txt(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select TXT", os.getcwd(), "Text files (*.txt);;All files (*.*)")
        if path:
            self.txt_edit.setText(path)
            self.suggest_out()

    def pick_out(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save CSV", os.getcwd(), "CSV files (*.csv)")
        if path:
            if not path.lower().endswith('.csv'):
                path += '.csv'
            self.out_edit.setText(path)

    def pick_cas(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select CAS Map CSV(s)", os.getcwd(), "CSV files (*.csv);;All files (*.*)")
        if files:
            self.cas_paths = files
            self.cas_edit.setText("; ".join(files))

    def on_auto_toggle(self, checked: bool):
        self.btn_cas.setEnabled(not checked)
        self.cas_edit.setEnabled(not checked)

    def suggest_out(self):
        rdf = self.rdf_edit.text().strip()
        txt = self.txt_edit.text().strip()
        if rdf and txt and not self.out_edit.text().strip():
            base_rdf = os.path.splitext(os.path.basename(rdf))[0]
            base_txt = os.path.splitext(os.path.basename(txt))[0]
            # choose the longer common prefix as a hint; fallback to 'reactions'
            common = os.path.commonprefix([base_rdf, base_txt]) or 'reactions'
            out = os.path.join(os.path.dirname(rdf), f"{common}_merged.csv")
            self.out_edit.setText(out)

    def validate_inputs(self) -> Optional[str]:
        rdf = self.rdf_edit.text().strip()
        txt = self.txt_edit.text().strip()
        out = self.out_edit.text().strip()
        if not rdf or not os.path.exists(rdf):
            return "Please select a valid RDF file."
        if not txt or not os.path.exists(txt):
            return "Please select a valid TXT file."
        if not out:
            return "Please choose an output CSV path."
        return None

    def run_job(self):
        err = self.validate_inputs()
        if err:
            QtWidgets.QMessageBox.warning(self, "Missing input", err)
            return
        self.setEnabled(False)
        self.log.clear()
        self.log_msg("Starting…")

        self.worker = Worker(
            rdf_path=self.rdf_edit.text().strip(),
            txt_path=self.txt_edit.text().strip(),
            out_path=self.out_edit.text().strip(),
            cas_maps=self.cas_paths,
            auto_detect_maps=self.chk_auto.isChecked(),
        )

        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        sig = getattr(self.worker, 'finished', None)
        if sig:
            sig.connect(self.on_finished)
            sig.connect(self.thread.quit)
            sig.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Always re-enable UI when the thread finishes (safety net)
        self.thread.finished.connect(lambda: self.setEnabled(True))
        # cleanup references when done
        self.thread.finished.connect(lambda: setattr(self, 'worker', None))
        self.thread.finished.connect(lambda: setattr(self, 'thread', None))
        self.thread.start()

    def on_finished(self, ok: bool, message: str):
        self.setEnabled(True)
        self.log_msg(message)
        if ok:
            QtWidgets.QMessageBox.information(self, "Done", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", message)


def main():
    if hasattr(QtWidgets, 'QApplication'):
        try:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
