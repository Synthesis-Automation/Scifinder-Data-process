#!/usr/bin/env python3
"""
Simple Qt6 GUI wrapper for processing RDF files only.
Lets the user pick a folder containing RDF files and processes all RDF files in the folder.
Generates Markdown and JSONL outputs similar to combined_md_to_rich_report.py.
Works with PySide6 (preferred) or PyQt6 if installed.
"""
from __future__ import annotations

import os
import sys
import traceback
import tempfile
from typing import List, Optional, Dict, Any

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

# Import processing functions from the existing modules
try:
    from process_reactions import parse_rdf, assemble_rows, load_cas_maps
except Exception as e:
    print(f"Error: Cannot import processing helpers: {e}")
    sys.exit(1)

try:
    from reaction_markdown_generator import ReactionMarkdownGenerator
except Exception as e:
    print(f"Error: Cannot import ReactionMarkdownGenerator: {e}")
    sys.exit(1)

# Detect RDKit availability
try:
    from rdkit import Chem  # type: ignore
    RDKIT_AVAILABLE = True
except Exception:
    Chem = None  # type: ignore
    RDKIT_AVAILABLE = False


class RDFWorker(QtCore.QObject):
    finished = Signal(bool, str) if Signal else None  # type: ignore[misc]
    progress = Signal(str) if Signal else None  # type: ignore[misc]

    def __init__(self, folder_path: str, output_md_path: str, output_jsonl_path: str):
        super().__init__()
        self.folder_path = folder_path
        self.output_md_path = output_md_path
        self.output_jsonl_path = output_jsonl_path
        self.rdf_files = []

    def _emit(self, msg: str):
        """Emit progress message"""
        sig = getattr(self, 'progress', None)
        if sig:
            try:
                sig.emit(msg)
            except Exception:
                pass

    def _find_rdf_files(self) -> List[str]:
        """Find all RDF files in the specified folder"""
        rdf_files = []
        try:
            for file in os.listdir(self.folder_path):
                if file.lower().endswith('.rdf'):
                    full_path = os.path.join(self.folder_path, file)
                    if os.path.isfile(full_path):
                        rdf_files.append(full_path)
        except Exception as e:
            raise RuntimeError(f"Error scanning folder: {e}")
        
        return sorted(rdf_files)

    def _load_default_cas_maps(self) -> Dict[str, Dict[str, str]]:
        """Load default CAS mapping files"""
        here = os.path.dirname(os.path.abspath(__file__))
        paths: List[str] = []
        
        # Try merged registry first, then individual files
        merged = os.path.join(here, 'cas_registry_merged.jsonl')
        if os.path.exists(merged):
            paths.append(merged)
        else:
            for cand in ['cas_dictionary.jsonl', 'comprehensive_cas_registry.jsonl']:
                p = os.path.join(here, cand)
                if os.path.exists(p):
                    paths.append(p)
        
        return load_cas_maps(paths) if paths else {}

    def _create_minimal_txt_map(self, rdf_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create a minimal TXT map from RDF data (since we only have RDF)"""
        txt_map: Dict[str, Dict[str, Any]] = {}
        # Lightweight regex patterns (mirrors logic in process_reactions but simplified)
        import re, math
        re_time = re.compile(r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hrs|hour|hours|min|mins|minute|minutes|d|day|days)\b", re.I)
        re_temp = re.compile(r"(?P<val>-?\d+(?:\.\d+)?)\s*[^A-Za-z0-9]{0,3}C\b")
        re_rt = re.compile(r"\brt\b|room temperature", re.I)

        for rid, rdf_data in rdf_map.items():
            notes = rdf_data.get('notes') or []
            all_condition_lines: List[str] = []
            # Use notes lines as condition lines source (SciFinder often stores experimental snippets here)
            for ln in notes:
                if isinstance(ln, str) and ln.strip():
                    all_condition_lines.append(ln.strip())

            # Aggregate time and temperature heuristically from notes
            total_h = 0.0
            max_c = -math.inf
            had_rt = False
            for ln in all_condition_lines:
                # Skip DOI-like lines
                if re.search(r"\b10\.\d{4,9}/", ln):
                    continue
                # time
                for m in re_time.finditer(ln):
                    try:
                        val = float(m.group('val'))
                    except ValueError:
                        continue
                    unit = m.group('unit').lower()
                    if unit.startswith('min'):
                        total_h += val / 60.0
                    elif unit in ('d', 'day', 'days'):
                        total_h += val * 24.0
                    else:
                        total_h += val
                if re.search(r"\bovernight\b", ln, re.I):
                    total_h += 16.0
                # temperature
                for m in re_temp.finditer(ln):
                    try:
                        valc = float(m.group('val'))
                    except ValueError:
                        continue
                    if valc > max_c:
                        max_c = valc
                if re_rt.search(ln):
                    had_rt = True

            temperature_c = max_c if max_c != -math.inf else (25.0 if had_rt else None)
            time_h = round(total_h, 3) if total_h > 0 else None

            txt_map[rid] = {
                'original_text': [],
                'all_condition_lines': all_condition_lines,
                'time_h': time_h,
                'temperature_c': round(temperature_c, 1) if temperature_c is not None else None,
                'title': rdf_data.get('title', ''),
                'authors': rdf_data.get('authors', ''),
                'citation': rdf_data.get('citation', ''),
                'doi': '',
                'reagents': [],
                'catalysts': [],
                'solvents': [],
                'txt_yield': None,
            }
        
        return txt_map

    def _extract_temp_time_from_md(self, md_path: str) -> Dict[str, Dict[str, Optional[float]]]:
        """Parse a markdown file to map CAS Reaction Number -> {temperature_c, time_h}.

        Heuristics:
        - Within each block following a line like "CAS Reaction Number: <ID>",
          accumulate time across all occurrences and take the max temperature.
        - Recognize units h/hr/hrs/hour/min/mins/minute/day/days; minutes converted to hours; days*24.
        - Recognize temperatures like "80 C" or "80 °C"; recognize 'rt'/'room temperature' as 25 °C when no numeric temp.
        - Ignore 'reflux' for temperature.
        """
        result: Dict[str, Dict[str, Optional[float]]] = {}
        if not os.path.exists(md_path):
            return result

        import re, math
        re_time = re.compile(r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|min|mins|minute|minutes|d|day|days)(?![A-Za-z0-9])", re.I)
        re_temp_c = re.compile(r"(-?\d+(?:\.\d+)?)\s*[^A-Za-z0-9]{0,3}C\b")
        re_rt = re.compile(r"\brt\b|room temperature", re.I)
        re_rid = re.compile(r"^\s*CAS Reaction Number:\s*(\S+)\s*$", re.I)

        current_id: Optional[str] = None
        agg_time: float = 0.0
        agg_max_c: float = -math.inf
        had_rt: bool = False

        def _flush():
            nonlocal current_id, agg_time, agg_max_c, had_rt
            if current_id:
                temp_c: Optional[float]
                if agg_max_c != -math.inf:
                    temp_c = round(agg_max_c, 1)
                elif had_rt:
                    temp_c = 25.0
                else:
                    temp_c = None
                time_h = round(agg_time, 3) if agg_time > 0 else None
                result[current_id] = {"temperature_c": temp_c, "time_h": time_h}
            current_id = None
            agg_time = 0.0
            agg_max_c = -math.inf
            had_rt = False

        try:
            with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                for raw in f:
                    line = raw.rstrip("\n")
                    m_id = re_rid.match(line)
                    if m_id:
                        # flush previous block
                        _flush()
                        current_id = m_id.group(1).strip()
                        continue
                    if not current_id:
                        continue
                    # Accumulate within current block
                    for m in re_time.finditer(line):
                        try:
                            val = float(m.group(1))
                        except Exception:
                            continue
                        unit = (m.group(2) or "").lower()
                        if unit.startswith("min"):
                            agg_time += val / 60.0
                        elif unit in ("d", "day", "days"):
                            agg_time += val * 24.0
                        else:
                            agg_time += val
                    mtemp = re_temp_c.findall(line)
                    for t in mtemp:
                        try:
                            v = float(t)
                        except Exception:
                            continue
                        if v > agg_max_c:
                            agg_max_c = v
                    if re_rt.search(line):
                        had_rt = True
            # flush last block
            _flush()
        except Exception:
            return result

        return result

    def _process_rdf_files(self) -> Dict[str, Dict[str, Any]]:
        """Process all RDF files and combine them into a single RDF map"""
        combined_rdf_map: Dict[str, Dict[str, Any]] = {}
        seen_ids: set[str] = set()
        for i, rdf_file in enumerate(self.rdf_files, 1):
            filename = os.path.basename(rdf_file)
            self._emit(f"[{i}/{len(self.rdf_files)}] Processing {filename}...")
            try:
                # Parse individual RDF file
                rdf_map = parse_rdf(rdf_file)
                # Merge reactions without prefixing filename to the ID; keep first occurrence only
                added = 0
                skipped = 0
                for rid, data in rdf_map.items():
                    data['source_file'] = filename
                    if rid in seen_ids or rid in combined_rdf_map:
                        skipped += 1
                        continue
                    seen_ids.add(rid)
                    combined_rdf_map[rid] = data
                    added += 1
                msg_tail = f" (added {added}"
                if skipped:
                    msg_tail += f", skipped dups {skipped}"
                msg_tail += ")"
                self._emit(f"  Found {len(rdf_map)} reactions in {filename}{msg_tail}")
            except Exception as e:
                self._emit(f"  Error processing {filename}: {e}")
                continue
        return combined_rdf_map

    def _generate_outputs(self, rows: List[Dict[str, Any]], cas_map: Dict[str, Dict[str, str]]) -> None:
        """Generate Markdown and JSONL outputs using ReactionMarkdownGenerator"""
        self._emit("Generating Markdown report...")
        
        # Create generator instance
        generator = ReactionMarkdownGenerator()
        generator.cas_map = cas_map
        
        # Generate markdown report
        source_name = f"RDF_Folder_{os.path.basename(self.folder_path)}"
        generator.generate_markdown_report(rows, self.output_md_path, source_name)
        
        # Generate JSONL export
        self._emit("Generating JSONL export...")
        generator.generate_jsonl_export(rows, self.output_jsonl_path, source_name)

    @Slot() if Slot else (lambda f: f)
    def run(self):
        """Main processing function"""
        try:
            # Find all RDF files
            self._emit("Scanning folder for RDF files...")
            self.rdf_files = self._find_rdf_files()
            
            if not self.rdf_files:
                if self.finished:
                    self.finished.emit(False, "No RDF files found in the selected folder.")
                return
            
            self._emit(f"Found {len(self.rdf_files)} RDF files.")
            
            # Process all RDF files and combine them
            self._emit("Processing RDF files...")
            combined_rdf_map = self._process_rdf_files()
            
            if not combined_rdf_map:
                if self.finished:
                    self.finished.emit(False, "No valid reactions found in RDF files.")
                return
            
            # Count MOL blocks for diagnostics
            rct_mol_count = sum(1 for v in combined_rdf_map.values() if v.get('rct_mol'))
            pro_mol_count = sum(1 for v in combined_rdf_map.values() if v.get('pro_mol'))
            self._emit(f"RDF parsed. Reactions with reactant MOL blocks: {rct_mol_count}; with product MOL blocks: {pro_mol_count}")
            self._emit(f"RDKit available: {RDKIT_AVAILABLE}")
            
            # Load CAS mappings
            self._emit("Loading CAS mappings...")
            cas_map = self._load_default_cas_maps()
            
            # Create minimal TXT map (since we only have RDF)
            self._emit("Creating minimal TXT mapping...")
            txt_map = self._create_minimal_txt_map(combined_rdf_map)
            
            # Assemble rows using the same pipeline as original
            self._emit("Assembling reaction rows...")
            rows = assemble_rows(txt_map, combined_rdf_map, cas_map, txt_preferred=False)
            self._emit(f"Assembled {len(rows)} rows")

            # Override Temperature_C and Time_h from dataset/temp_time.md when available
            here = os.path.dirname(os.path.abspath(__file__))
            md_path = os.path.join(here, 'dataset', 'temp_time.md')
            md_map = self._extract_temp_time_from_md(md_path)
            if md_map:
                overridden = 0
                for row in rows:
                    rid = row.get('ReactionID')
                    if not rid:
                        continue
                    mt = md_map.get(rid)
                    if not mt:
                        continue
                    t_c = mt.get('temperature_c')
                    t_h = mt.get('time_h')
                    if t_c is not None:
                        row['Temperature_C'] = t_c
                    if t_h is not None:
                        row['Time_h'] = t_h
                    if (t_c is not None) or (t_h is not None):
                        overridden += 1
                self._emit(f"Applied temp/time overrides from temp_time.md for {overridden} reactions.")

            # Override ReactionType using the parent folder name (e.g., ...\Suzuki\2023-2025 -> 'Suzuki')
            try:
                norm_folder = os.path.normpath(self.folder_path)
                parent_dir = os.path.basename(os.path.dirname(norm_folder))
                if parent_dir:
                    for r in rows:
                        r['ReactionType'] = parent_dir
                self._emit(f"Reaction type set to folder category: {parent_dir}")
            except Exception:
                # Non-fatal; keep existing reaction types if path parsing fails
                pass
            
            # Count rows with SMILES for diagnostics
            smi_rows = sum(1 for r in rows if (r.get('ReactantSMILES') or r.get('ProductSMILES')))
            self._emit(f"Rows with SMILES: {smi_rows} / {len(rows)}")
            
            if smi_rows == 0:
                if not RDKIT_AVAILABLE:
                    self._emit("Note: RDKit is not available; SMILES generation from MOL blocks is disabled.")
                elif (rct_mol_count + pro_mol_count) == 0:
                    self._emit("Note: No MOL/CTAB blocks found in RDF content; SMILES cannot be generated.")
                else:
                    self._emit("Warning: MOL blocks found and RDKit available, but SMILES are empty. MOL data may be malformed.")
            
            # Generate outputs
            self._generate_outputs(rows, cas_map)
            
            if self.finished:
                self.finished.emit(True, f"Successfully processed {len(self.rdf_files)} RDF files with {len(rows)} reactions.\nMarkdown: {self.output_md_path}\nJSONL: {self.output_jsonl_path}")
                
        except Exception as e:
            msg = f"Error: {e}\n\n{traceback.format_exc()}"
            if self.finished:
                self.finished.emit(False, msg)


class RDFProcessorWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SciFinder RDF Processor")
        self.resize(700, 500)
        
        # Input controls
        self.folder_edit = QtWidgets.QLineEdit()
        self.btn_folder = QtWidgets.QPushButton("Browse Folder...")
        self.output_md_edit = QtWidgets.QLineEdit()
        self.btn_output_md = QtWidgets.QPushButton("Save As...")
        
        # File list display
        self.file_list = QtWidgets.QListWidget()
        self.file_count_label = QtWidgets.QLabel("No folder selected")
        
        # Control buttons
        self.btn_run = QtWidgets.QPushButton("Process RDF Files")
        self.btn_quit = QtWidgets.QPushButton("Quit")
        
        # Log output
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        
        # Setup layout
        self._setup_layout()
        
        # Connect signals
        self.btn_folder.clicked.connect(self.pick_folder)
        self.btn_output_md.clicked.connect(self.pick_output)
        self.btn_run.clicked.connect(self.run_processing)
        self.btn_quit.clicked.connect(self.close)
        
        # Runtime state
        self.thread = None
        self.worker = None
        self.rdf_files = []
        
        # Initialize button states
        self.btn_run.setEnabled(False)

    def _setup_layout(self):
        """Setup the GUI layout"""
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("SciFinder RDF File Processor")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Form layout for inputs
        form = QtWidgets.QFormLayout()
        
        # Folder selection
        folder_box = QtWidgets.QHBoxLayout()
        folder_box.addWidget(self.folder_edit)
        folder_box.addWidget(self.btn_folder)
        form.addRow("RDF Folder:", folder_box)
        
        # Output file selection
        output_box = QtWidgets.QHBoxLayout()
        output_box.addWidget(self.output_md_edit)
        output_box.addWidget(self.btn_output_md)
        form.addRow("Output Markdown:", output_box)
        
        # Add note about JSONL
        note_label = QtWidgets.QLabel("Note: JSONL file will be automatically created alongside the Markdown file")
        note_label.setStyleSheet("font-style: italic; color: #666;")
        form.addRow("", note_label)
        
        layout.addLayout(form)
        
        # File list section
        file_group = QtWidgets.QGroupBox("RDF Files Found")
        file_layout = QtWidgets.QVBoxLayout(file_group)
        file_layout.addWidget(self.file_count_label)
        file_layout.addWidget(self.file_list)
        layout.addWidget(file_group)
        
        # Control buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.btn_run)
        button_layout.addWidget(self.btn_quit)
        layout.addLayout(button_layout)
        
        # Log section
        log_group = QtWidgets.QGroupBox("Processing Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group)

    def log_msg(self, text: str):
        """Add a message to the log"""
        self.log.appendPlainText(text)

    def pick_folder(self):
        """Select folder containing RDF files"""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "Select folder with RDF files", 
            os.getcwd(), 
            options=QtWidgets.QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self.folder_edit.setText(path)
            self._update_file_list()
            
            # Suggest default output file
            if not self.output_md_edit.text().strip():
                default_output = os.path.join(path, "rdf_reactions_rich.md")
                self.output_md_edit.setText(default_output)

    def pick_output(self):
        """Select output markdown file location"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Markdown Report As",
            os.getcwd(),
            "Markdown files (*.md);;All files (*.*)"
        )
        if path:
            if not path.lower().endswith('.md'):
                path += '.md'
            self.output_md_edit.setText(path)

    def _update_file_list(self):
        """Update the list of RDF files found in the selected folder"""
        folder_path = self.folder_edit.text().strip()
        self.file_list.clear()
        self.rdf_files = []
        
        if not folder_path or not os.path.isdir(folder_path):
            self.file_count_label.setText("No valid folder selected")
            self.btn_run.setEnabled(False)
            return
        
        try:
            # Find RDF files
            for file in os.listdir(folder_path):
                if file.lower().endswith('.rdf'):
                    full_path = os.path.join(folder_path, file)
                    if os.path.isfile(full_path):
                        self.rdf_files.append(full_path)
                        self.file_list.addItem(file)
            
            # Update UI
            count = len(self.rdf_files)
            if count == 0:
                self.file_count_label.setText("No RDF files found in this folder")
                self.btn_run.setEnabled(False)
            else:
                self.file_count_label.setText(f"Found {count} RDF file{'s' if count != 1 else ''}")
                self.btn_run.setEnabled(True)
                
        except Exception as e:
            self.file_count_label.setText(f"Error reading folder: {e}")
            self.btn_run.setEnabled(False)

    def validate_inputs(self) -> Optional[str]:
        """Validate user inputs"""
        folder = self.folder_edit.text().strip()
        output_md = self.output_md_edit.text().strip()
        
        if not folder or not os.path.isdir(folder):
            return "Please select a valid folder containing RDF files."
        
        if not output_md:
            return "Please specify an output Markdown file location."
        
        if not self.rdf_files:
            return "No RDF files found in the selected folder."
        
        return None

    def run_processing(self):
        """Start the RDF processing"""
        err = self.validate_inputs()
        if err:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", err)
            return
        
        # Disable UI during processing
        self.setEnabled(False)
        self.log.clear()
        self.log_msg("Starting RDF processing...")
        
        # Calculate output paths
        output_md = self.output_md_edit.text().strip()
        output_jsonl = os.path.splitext(output_md)[0] + '.jsonl'
        
        # Create worker and thread
        self.worker = RDFWorker(
            folder_path=self.folder_edit.text().strip(),
            output_md_path=output_md,
            output_jsonl_path=output_jsonl
        )
        
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        
        # Connect signals
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
        self.thread.finished.connect(lambda: self.setEnabled(True))
        self.thread.finished.connect(lambda: setattr(self, 'worker', None))
        self.thread.finished.connect(lambda: setattr(self, 'thread', None))
        
        # Start processing
        self.thread.start()

    def on_finished(self, success: bool, message: str):
        """Handle processing completion"""
        self.setEnabled(True)
        self.log_msg(message)
        
        if success:
            QtWidgets.QMessageBox.information(self, "Processing Complete", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Processing Error", message)


def main():
    """Main application entry point"""
    if hasattr(QtWidgets, 'QApplication'):
        try:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass
    
    app = QtWidgets.QApplication(sys.argv)
    window = RDFProcessorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
