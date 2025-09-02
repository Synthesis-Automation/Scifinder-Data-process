#!/usr/bin/env python3
"""
Simple Qt6 GUI to combine SciFinder RDF/TXT exports by ReactionID and write a minimal Markdown report.

Requirements from user:
- Ask user to select a folder containing matching RDF and TXT files with the same base name.
- Do a simple recombine only (no SMILES conversion, no CAS validation, no classification/enrichment).
- Generate a single combined .md file that merges TXT and RDF data for the same ReactionID.

This tool reuses the existing parsing helpers from process_reactions.py: parse_txt and parse_rdf.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Tuple, Any
from datetime import datetime

try:
    from PyQt6 import QtWidgets, QtCore
    QT_BINDING = "PyQt6"
except Exception:
    try:
        from PySide6 import QtWidgets, QtCore  # type: ignore
        QT_BINDING = "PySide6"  # type: ignore
    except Exception:
        print("Error: Neither PyQt6 nor PySide6 is installed. Please install one of them.")
        sys.exit(1)

# Reuse only the TXT parser to get original text blocks per reaction
try:
    from process_reactions import parse_txt
except Exception as e:
    print(f"Error: Cannot import parse_txt from process_reactions.py: {e}")
    sys.exit(1)


def find_rdf_txt_pairs(folder_path: str) -> List[Tuple[str, str]]:
    """Return list of (rdf_path, txt_path) for files that share the same base name in the folder.
    Non-recursive; only the specified directory.
    """
    if not os.path.isdir(folder_path):
        return []
    files = os.listdir(folder_path)
    base_to_exts: Dict[str, Dict[str, str]] = {}
    for fname in files:
        full = os.path.join(folder_path, fname)
        if not os.path.isfile(full):
            continue
        base, ext = os.path.splitext(fname)
        ext = ext.lower()
        if ext not in {".rdf", ".txt"}:
            continue
        slot = base_to_exts.setdefault(base, {})
        slot[ext] = full
    pairs: List[Tuple[str, str]] = []
    for base, exts in base_to_exts.items():
        if ".rdf" in exts and ".txt" in exts:
            pairs.append((exts[".rdf"], exts[".txt"]))
    # Sort by base name for stable output
    pairs.sort(key=lambda p: os.path.splitext(os.path.basename(p[0]))[0])
    return pairs


def extract_txt_blocks_raw(txt_path: str) -> Dict[str, List[str]]:
    """Use parse_txt only to access per-reaction original text lines, without other processing."""
    try:
        txt_map = parse_txt(txt_path)
    except Exception:
        return {}
    out: Dict[str, List[str]] = {}
    for rid, rec in (txt_map or {}).items():
        lines = rec.get("original_text") or []
        # Ensure list of strings
        out[rid] = [str(ln) for ln in lines]
    return out


def extract_rdf_blocks_raw(rdf_path: str) -> Dict[str, List[str]]:
    """Extract raw RDF record lines per reaction id by lightly grouping $RXN/$MOL and $DTYPE/$DATUM lines.
    This avoids interpreting content; we only partition by CAS Reaction Number.
    """
    if not os.path.isfile(rdf_path):
        return {}
    with open(rdf_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]

    blocks: Dict[str, List[str]] = {}
    current_rid: str | None = None
    # pending RXN/MOL lines to attach to the next reaction id encountered
    pending_rxn_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('$RXN'):
            # capture $RXN section including subsequent $MOL blocks and until next $DTYPE/$RXN
            start_idx = i
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('$RXN') or lines[i].strip().startswith('$DTYPE'):
                    break
                # For $MOL sections, continue until 'M  END' or next control line
                i += 1
            pending_rxn_lines.extend(lines[start_idx:i])
            continue
        if line.startswith('$DTYPE'):
            key = line.split(' ', 1)[1].strip() if ' ' in line else ''
            i += 1
            # gather $DATUM and any continuation lines until next '$'
            datum_lines: List[str] = []
            if i < len(lines) and lines[i].startswith('$DATUM'):
                datum_first = lines[i]
                datum_lines.append(datum_first)
                i += 1
                while i < len(lines) and not lines[i].startswith('$'):
                    datum_lines.append(lines[i])
                    i += 1
            # If this DTYPE announces the CAS Reaction Number, switch current_rid
            if 'CAS_Reaction_Number' in key and datum_lines:
                # The datum content is after "$DATUM ", keep full lines
                # finalize previous record implicitly by switching ids
                # start a fresh block for this rid
                rid_value = datum_lines[0][len('$DATUM '):].strip() if datum_lines[0].startswith('$DATUM ') else ''
                if rid_value:
                    current_rid = rid_value
                    blk = blocks.setdefault(current_rid, [])
                    # attach any pending RXN lines captured before the id
                    if pending_rxn_lines:
                        blk.extend(pending_rxn_lines)
                        pending_rxn_lines = []
                    # also record this dtype/datum pair
                    blk.append(line)
                    blk.extend(datum_lines)
                else:
                    # no rid; ignore
                    pass
            else:
                if current_rid:
                    blk = blocks.setdefault(current_rid, [])
                    blk.append(line)
                    blk.extend(datum_lines)
            continue
        # default line: if we already have a current rid, keep it in the block; else park it until id
        if current_rid:
            blocks.setdefault(current_rid, []).append(line)
        else:
            pending_rxn_lines.append(line)
        i += 1
    return blocks


def generate_simple_markdown(raw_txt: Dict[str, List[str]], raw_rdf: Dict[str, List[str]], source_pairs: List[Tuple[str, str]], source_folder: str) -> str:
    """Create a Markdown report that contains only raw TXT and RDF blocks per ReactionID, unprocessed."""
    def _skip_line(ln: str) -> bool:
        # Remove blank lines and lines consisting only of '|' characters (e.g., '|', '||', etc.)
        s = (ln or '').strip()
        if not s:
            return True
        # if after stripping, it is only pipes
        return set(s) <= {'|'}
    lines: List[str] = []
    lines.append(f"# Combined Reaction Report\n")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"Source folder: {source_folder}\n")
    if source_pairs:
        lines.append(f"Pairs detected: {len(source_pairs)}\n")
    lines.append("\n---\n\n")
    all_ids = sorted(set(raw_txt.keys()) | set(raw_rdf.keys()))
    for rid in all_ids:
        lines.append(f"## Reaction {rid}\n\n")
        # Emit raw TXT block
        if rid in raw_txt and raw_txt[rid]:
            lines.append("**Original TXT (as-is):**\n")
            lines.append("```")
            for ln in raw_txt[rid]:
                if _skip_line(ln):
                    continue
                lines.append((ln or '') + "\n")
            lines.append("```\n\n")
        else:
            lines.append("_No TXT block found for this reaction._\n\n")
        # Emit raw RDF block
        if rid in raw_rdf and raw_rdf[rid]:
            lines.append("**Original RDF (as-is):**\n")
            lines.append("```")
            for ln in raw_rdf[rid]:
                if _skip_line(ln):
                    continue
                lines.append((ln or '') + "\n")
            lines.append("```\n\n")
        else:
            lines.append("_No RDF block found for this reaction._\n\n")
        lines.append("---\n\n")

    return "".join(lines)


class SimpleCombineGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combine SciFinder RDF/TXT to Markdown (Simple)")
        self.resize(800, 520)

        self.folder_edit = QtWidgets.QLineEdit(self)
        self.folder_btn = QtWidgets.QPushButton("Browse Folder…", self)
        self.output_edit = QtWidgets.QLineEdit(self)
        self.output_btn = QtWidgets.QPushButton("Save As…", self)
        self.run_btn = QtWidgets.QPushButton("Generate Report", self)
        self.log = QtWidgets.QPlainTextEdit(self)
        self.log.setReadOnly(True)

        form = QtWidgets.QFormLayout()
        hb1 = QtWidgets.QHBoxLayout()
        hb1.addWidget(self.folder_edit)
        hb1.addWidget(self.folder_btn)
        hb2 = QtWidgets.QHBoxLayout()
        hb2.addWidget(self.output_edit)
        hb2.addWidget(self.output_btn)
        form.addRow("Input folder:", hb1)
        form.addRow("Output .md:", hb2)
        form.addRow(self.run_btn)
        form.addRow(self.log)
        self.setLayout(form)

        self.folder_btn.clicked.connect(self._choose_folder)
        self.output_btn.clicked.connect(self._choose_output)
        self.run_btn.clicked.connect(self._run)

    def _log(self, msg: str):
        self.log.appendPlainText(msg)
        # ensure scroll to end
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _choose_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder with RDF/TXT pairs")
        if path:
            self.folder_edit.setText(path)
            # Suggest default output path
            default_out = os.path.join(path, f"combined_reactions_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
            self.output_edit.setText(default_out)

    def _choose_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Markdown Report", self.output_edit.text() or "combined_reactions.md", "Markdown (*.md)")
        if path:
            if not path.lower().endswith(".md"):
                path += ".md"
            self.output_edit.setText(path)

    def _run(self):
        folder = (self.folder_edit.text() or "").strip()
        outpath = (self.output_edit.text() or "").strip()
        if not folder or not os.path.isdir(folder):
            QtWidgets.QMessageBox.warning(self, "Missing folder", "Please select a valid input folder.")
            return
        if not outpath:
            QtWidgets.QMessageBox.warning(self, "Missing output", "Please choose an output .md path.")
            return
        try:
            self._log(f"Scanning folder: {folder}")
            pairs = find_rdf_txt_pairs(folder)
            if not pairs:
                self._log("No RDF/TXT pairs found (same basename with .rdf and .txt).")
                QtWidgets.QMessageBox.information(self, "No pairs", "No RDF/TXT pairs found in the folder.")
                return
            self._log(f"Found {len(pairs)} pair(s). Parsing…")

            # Accumulate raw blocks per ReactionID across all pairs
            raw_txt_blocks: Dict[str, List[str]] = {}
            raw_rdf_blocks: Dict[str, List[str]] = {}
            for (rdf_path, txt_path) in pairs:
                base = os.path.splitext(os.path.basename(rdf_path))[0]
                self._log(f"- Reading raw blocks: {base}")
                try:
                    txt_blocks = extract_txt_blocks_raw(txt_path)
                except Exception as e:
                    self._log(f"  ! TXT read error: {e}")
                    txt_blocks = {}
                try:
                    rdf_blocks = extract_rdf_blocks_raw(rdf_path)
                except Exception as e:
                    self._log(f"  ! RDF read error: {e}")
                    rdf_blocks = {}

                # Merge (last-writer-wins across files)
                raw_txt_blocks.update(txt_blocks)
                raw_rdf_blocks.update(rdf_blocks)

            total_rxns = len(set(raw_txt_blocks.keys()) | set(raw_rdf_blocks.keys()))
            self._log(f"Generating Markdown with {total_rxns} reaction(s)…")
            md = generate_simple_markdown(raw_txt_blocks, raw_rdf_blocks, pairs, folder)
            os.makedirs(os.path.dirname(outpath) or folder, exist_ok=True)
            with open(outpath, 'w', encoding='utf-8') as f:
                f.write(md)
            self._log(f"Report written: {outpath}")
            QtWidgets.QMessageBox.information(self, "Done", f"Report generated:\n{outpath}")
        except Exception as e:
            self._log(f"Error: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", str(e))


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = SimpleCombineGUI()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
