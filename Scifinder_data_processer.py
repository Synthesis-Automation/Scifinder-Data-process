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
import csv  # for TSV writing
import json  # for filtering JSON-array fields


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
    progress = Signal(str) if Signal else None  # type: ignore[misc]

    def __init__(self, rdf_path: Optional[str], txt_path: Optional[str], out_path: str, cas_maps: Optional[List[str]], auto_detect_maps: bool, folder_path: Optional[str] = None, drop_empty_core: bool = False, drop_empty_ligand: bool = False):
        super().__init__()
        self.rdf_path = rdf_path or ''
        self.txt_path = txt_path or ''
        self.out_path = out_path
        self.cas_maps = cas_maps or []
        self.auto_detect_maps = auto_detect_maps
        self.folder_path = folder_path or ''
        self.drop_empty_core = drop_empty_core
        self.drop_empty_ligand = drop_empty_ligand

    def _emit(self, msg: str):
        sig = getattr(self, 'progress', None)
        if sig:
            try:
                sig.emit(msg)
            except Exception:
                pass

    def _build_cas_map(self):
        cas_map_paths: List[str] = list(self.cas_maps)
        if self.auto_detect_maps:
            here = os.path.dirname(os.path.abspath(__file__))
            maybe = [
                os.path.join(here, 'Buchwald', 'cas_dictionary.csv'),
                os.path.join(here, 'Ullman', '新建文件夹', 'ullmann_cas_to_name_mapping.csv'),
            ]
            cas_map_paths.extend([p for p in maybe if os.path.exists(p)])
        return load_cas_maps(cas_map_paths) if cas_map_paths else {}

    def _run_single(self):
        self._emit("Parsing TXT…")
        txt = parse_txt(self.txt_path)
        self._emit("Parsing RDF…")
        rdf = parse_rdf(self.rdf_path)
        self._emit("Loading CAS maps…")
        cas_map = self._build_cas_map()
        self._emit("Assembling rows…")
        rows = assemble_rows(txt, rdf, cas_map)
        rows = self._apply_filters(rows)
        self._emit(f"Writing output to {self.out_path}…")
        self._write_output(rows)
        return rows

    def _run_folder(self):
        folder = self.folder_path
        self._emit(f"Scanning folder: {folder}")
        try:
            names = os.listdir(folder)
        except Exception as e:
            raise RuntimeError(f"Cannot list folder: {e}")
        # Case-insensitive index of basenames -> available extensions
        base_to_exts = {}
        for n in names:
            p = os.path.join(folder, n)
            if not os.path.isfile(p):
                continue
            base, ext = os.path.splitext(n)
            base_low = base.lower()
            ext_low = ext.lower()
            base_to_exts.setdefault(base_low, set()).add(ext_low)
        pairs = []
        for base_low, exts in base_to_exts.items():
            if '.rdf' in exts and '.txt' in exts:
                rdf_n = next((n for n in names if os.path.splitext(n)[0].lower() == base_low and os.path.splitext(n)[1].lower() == '.rdf'), base_low + '.rdf')
                txt_n = next((n for n in names if os.path.splitext(n)[0].lower() == base_low and os.path.splitext(n)[1].lower() == '.txt'), base_low + '.txt')
                pairs.append((os.path.join(folder, rdf_n), os.path.join(folder, txt_n)))
        if not pairs:
            return [], 0
        self._emit(f"Found {len(pairs)} RDF/TXT pairs.")
        agg_txt = {}
        agg_rdf = {}
        for idx, (rdf_p, txt_p) in enumerate(sorted(pairs), start=1):
            self._emit(f"[{idx}/{len(pairs)}] Parsing: {os.path.basename(txt_p)} + {os.path.basename(rdf_p)}")
            try:
                t = parse_txt(txt_p)
                r = parse_rdf(rdf_p)
                agg_txt.update(t)
                agg_rdf.update(r)
            except Exception as e:
                self._emit(f"Failed pair: {txt_p} / {rdf_p}: {e}")
        self._emit("Loading CAS maps…")
        cas_map = self._build_cas_map()
        self._emit("Assembling combined rows…")
        rows = assemble_rows(agg_txt, agg_rdf, cas_map)
        rows = self._apply_filters(rows)
        self._emit(f"Writing output to {self.out_path}…")
        self._write_output(rows)
        return rows, len(pairs)

    def _apply_filters(self, rows: List[dict]) -> List[dict]:
        """Optionally filter out reactions with empty CatalystCore or Ligand arrays.
        - CatalystCore is considered empty if both CatalystCoreDetail and CatalystCoreGeneric are empty arrays.
        - Ligand is considered empty if its array is empty.
        """
        if not (self.drop_empty_core or self.drop_empty_ligand):
            return rows
        kept: List[dict] = []
        removed_core = 0
        removed_lig = 0
        for r in rows:
            try:
                core_detail = json.loads(r.get('CatalystCoreDetail', '[]') or '[]')
            except Exception:
                core_detail = []
            try:
                core_generic = json.loads(r.get('CatalystCoreGeneric', '[]') or '[]')
            except Exception:
                core_generic = []
            try:
                ligand = json.loads(r.get('Ligand', '[]') or '[]')
            except Exception:
                ligand = []

            empty_core = (len(core_detail) == 0 and len(core_generic) == 0)
            empty_lig = (len(ligand) == 0)

            drop = False
            if self.drop_empty_core and empty_core:
                removed_core += 1
                drop = True
            if self.drop_empty_ligand and empty_lig:
                removed_lig += 1
                drop = True
            if not drop:
                kept.append(r)
        self._emit(f"Filtered out {removed_core} with empty CatalystCore and {removed_lig} with empty Ligand. Remaining: {len(kept)}")
        return kept

    @Slot() if Slot else (lambda f: f)
    def run(self):  # heavy work off UI thread
        try:
            if self.folder_path:
                rows, npairs = self._run_folder()
                if self.finished:
                    self.finished.emit(True, f"Processed {npairs} pairs. Wrote {len(rows)} rows to {self.out_path}")
            else:
                rows = self._run_single()
                if self.finished:
                    self.finished.emit(True, f"Wrote {len(rows)} rows to {self.out_path}")
        except Exception as e:
            msg = f"Error: {e}\n\n{traceback.format_exc()}"
            if self.finished:
                self.finished.emit(False, msg)

    def _write_output(self, rows: List[dict]):
        """Write rows to .tsv if the extension is .tsv; else use CSV helper."""
        out_ext = os.path.splitext(self.out_path)[1].lower()
        if out_ext == '.tsv':
            # Keep the same column order as process_reactions.write_csv
            cols = [
                'ReactionID', 'ReactionType', 'CatalystCoreDetail', 'CatalystCoreGeneric', 'Ligand', 'FullCatalyticSystem',
                'Reagent', 'ReagentRole', 'Solvent', 'Temperature_C', 'Time_h',
                'Yield_%', 'ReactantSMILES', 'ProductSMILES', 'Reference',
                'CondKey', 'CondSig', 'FamSig', 'RawCAS', 'RawData',
                'RCTName', 'PROName', 'RGTName', 'CATName', 'SOLName',
            ]
            with open(self.out_path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                for r in rows:
                    w.writerow({k: r.get(k, '') for k in cols})
        else:
            # Fallback to CSV using existing helper
            write_csv(rows, self.out_path)


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SciFinder Reaction Processor")
        self.resize(780, 440)

        # Mode selection
        self.radio_single = QtWidgets.QRadioButton("Single RDF/TXT pair")
        self.radio_folder = QtWidgets.QRadioButton("Process a folder of pairs")
        self.radio_single.setChecked(True)

        # Inputs
        self.rdf_edit = QtWidgets.QLineEdit()
        self.txt_edit = QtWidgets.QLineEdit()
        self.out_edit = QtWidgets.QLineEdit()
        self.cas_edit = QtWidgets.QLineEdit()
        self.cas_edit.setReadOnly(True)

        self.btn_rdf = QtWidgets.QPushButton("Browse RDF…")
        self.btn_txt = QtWidgets.QPushButton("Browse TXT…")
        self.btn_out = QtWidgets.QPushButton("Save As…")
        self.btn_cas = QtWidgets.QPushButton("Add CAS Map(s)…")

        # Folder processing controls
        self.folder_edit = QtWidgets.QLineEdit()
        self.btn_folder = QtWidgets.QPushButton("Browse Folder…")

        # Options
        self.chk_auto = QtWidgets.QCheckBox("Auto-detect built-in CAS maps")
        self.chk_auto.setChecked(True)

        # Filters
        self.chk_drop_empty_core = QtWidgets.QCheckBox("Remove reactions with empty CatalystCore")
        self.chk_drop_empty_ligand = QtWidgets.QCheckBox("Remove reactions with empty Ligand")

        # Actions
        self.btn_run = QtWidgets.QPushButton("Run")
        self.btn_quit = QtWidgets.QPushButton("Quit")

        # Log output
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)

        form = QtWidgets.QFormLayout()
        form.addRow("Mode:", self._hbox(self.radio_single, self.radio_folder))
        form.addRow("RDF:", self._hbox(self.rdf_edit, self.btn_rdf))
        form.addRow("TXT:", self._hbox(self.txt_edit, self.btn_txt))
        form.addRow("Folder:", self._hbox(self.folder_edit, self.btn_folder))
        form.addRow("Output file:", self._hbox(self.out_edit, self.btn_out))
        form.addRow(self.chk_auto)
        form.addRow(self.chk_drop_empty_core)
        form.addRow(self.chk_drop_empty_ligand)
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
        self.btn_folder.clicked.connect(self.pick_folder)
        self.radio_single.toggled.connect(self.on_mode_toggle)

        # runtime state
        self.cas_paths = []
        self.thread = None
        self.worker = None
        # initialize mode state
        self.on_mode_toggle(self.radio_single.isChecked())

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

    def pick_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder with RDF/TXT pairs", os.getcwd(), options=QtWidgets.QFileDialog.Option.ShowDirsOnly)
        if path:
            self.folder_edit.setText(path)
            if not self.out_edit.text().strip():
                self.out_edit.setText(os.path.join(path, "reactions.tsv"))

    def pick_out(self):
        # Default to TSV; allow CSV as alternative
        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save As",
            os.getcwd(),
            "TSV files (*.tsv);;CSV files (*.csv)"
        )
        if path:
            low = path.lower()
            if not (low.endswith('.tsv') or low.endswith('.csv')):
                # Choose .tsv by default
                path += '.tsv'
            self.out_edit.setText(path)

    def pick_cas(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select CAS Map CSV(s)", os.getcwd(), "CSV files (*.csv);;All files (*.*)")
        if files:
            self.cas_paths = files
            self.cas_edit.setText("; ".join(files))

    def on_auto_toggle(self, checked: bool):
        self.btn_cas.setEnabled(not checked)
        self.cas_edit.setEnabled(not checked)

    def on_mode_toggle(self, single_checked: bool):
        is_single = bool(single_checked)
        for w in [self.rdf_edit, self.txt_edit, self.btn_rdf, self.btn_txt]:
            w.setEnabled(is_single)
        self.folder_edit.setEnabled(not is_single)
        self.btn_folder.setEnabled(not is_single)
        # Suggest output for folder mode
        if not is_single and self.folder_edit.text().strip() and not self.out_edit.text().strip():
            self.out_edit.setText(os.path.join(self.folder_edit.text().strip(), "reactions.tsv"))

    def suggest_out(self):
        rdf = self.rdf_edit.text().strip()
        txt = self.txt_edit.text().strip()
        if rdf and txt and not self.out_edit.text().strip():
            base_rdf = os.path.splitext(os.path.basename(rdf))[0]
            base_txt = os.path.splitext(os.path.basename(txt))[0]
            # choose the longer common prefix as a hint; fallback to 'reactions'
            common = os.path.commonprefix([base_rdf, base_txt]) or 'reactions'
            out = os.path.join(os.path.dirname(rdf), f"{common}_merged.tsv")
            self.out_edit.setText(out)

    def validate_inputs(self) -> Optional[str]:
        out = self.out_edit.text().strip()
        if self.radio_single.isChecked():
            rdf = self.rdf_edit.text().strip()
            txt = self.txt_edit.text().strip()
            if not rdf or not os.path.exists(rdf):
                return "Please select a valid RDF file."
            if not txt or not os.path.exists(txt):
                return "Please select a valid TXT file."
            if not out:
                return "Please choose an output CSV path."
            return None
        else:
            folder = self.folder_edit.text().strip()
            if not folder or not os.path.isdir(folder):
                return "Please select a valid folder."
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

        if self.radio_single.isChecked():
            self.worker = Worker(
                rdf_path=self.rdf_edit.text().strip(),
                txt_path=self.txt_edit.text().strip(),
                out_path=self.out_edit.text().strip(),
                cas_maps=self.cas_paths,
                auto_detect_maps=self.chk_auto.isChecked(),
                drop_empty_core=self.chk_drop_empty_core.isChecked(),
                drop_empty_ligand=self.chk_drop_empty_ligand.isChecked(),
            )
        else:
            self.worker = Worker(
                rdf_path=None,
                txt_path=None,
                out_path=self.out_edit.text().strip(),
                cas_maps=self.cas_paths,
                auto_detect_maps=self.chk_auto.isChecked(),
                folder_path=self.folder_edit.text().strip(),
                drop_empty_core=self.chk_drop_empty_core.isChecked(),
                drop_empty_ligand=self.chk_drop_empty_ligand.isChecked(),
            )

        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        sig = getattr(self.worker, 'finished', None)
        if sig:
            sig.connect(self.on_finished)
            sig.connect(self.thread.quit)
            sig.connect(self.worker.deleteLater)
        prog = getattr(self.worker, 'progress', None)
        if prog:
            prog.connect(self.log_msg)
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
