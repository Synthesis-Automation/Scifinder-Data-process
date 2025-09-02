#!/usr/bin/env python3
"""
Process a pre-combined Markdown file (from Combine_reaction_data.py) into:
- A summary Markdown report (human-readable)
- A JSONL export (raw TXT/RDF per reaction)

Input format assumption:
- Sections begin with lines like:  ## Reaction <CAS Reaction Number>
- Each section may contain blocks:
  **Original TXT (as-is):** followed by ``` fenced block
  **Original RDF (as-is):** followed by ``` fenced block

No chemical processing is performed. Content is preserved, with optional removal of
blank lines and lines consisting only of '|' characters for readability.
"""
from __future__ import annotations

import os
import sys
import json
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


def _skip_line(ln: str) -> bool:
    s = (ln or '').strip()
    if not s:
        return True
    return set(s) <= {'|'}


def parse_combined_markdown(path: str) -> Dict[str, Dict[str, List[str]]]:
    """Parse the combined reactions markdown file into a dict:
    { rid: { 'txt': [lines], 'rdf': [lines] } }
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    records: Dict[str, Dict[str, List[str]]] = {}
    rid: str | None = None
    in_fence = False
    current_block: str | None = None  # 'txt' or 'rdf'

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip('\n')

        if line.startswith('## Reaction '):
            rid = line[len('## Reaction '):].strip()
            records.setdefault(rid, {'txt': [], 'rdf': []})
            in_fence = False
            current_block = None
            i += 1
            continue

        # Detect block headers
        if line.strip().startswith('**Original TXT'):
            current_block = 'txt'
            in_fence = False
            i += 1
            continue
        if line.strip().startswith('**Original RDF'):
            current_block = 'rdf'
            in_fence = False
            i += 1
            continue

        # Fenced code blocks: start/stop on line that's exactly ```
        if line.strip() == '```':
            in_fence = not in_fence
            i += 1
            continue

        # Capture lines inside fences into the current block
        if in_fence and rid and current_block in {'txt', 'rdf'}:
            records[rid][current_block].append(line)
            i += 1
            continue

        i += 1

    return records


def generate_markdown(records: Dict[str, Dict[str, List[str]]], source_file: str) -> str:
    """Create a human-readable Markdown with only raw TXT/RDF code blocks per reaction."""
    out: List[str] = []
    out.append("# Reaction Data Report\n\n")
    out.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    out.append(f"**Source File:** {source_file}\n")
    out.append(f"**Total Reactions:** {len(records)}\n\n")
    out.append("---\n\n")

    for rid in sorted(records.keys()):
        out.append(f"## Reaction {rid}\n\n")

        txt_lines = records[rid].get('txt') or []
        rdf_lines = records[rid].get('rdf') or []

        out.append("**Original TXT (as-is):**\n")
        out.append("`````\n")  # use 5 backticks to avoid interference if content contains ```
        for ln in txt_lines:
            if _skip_line(ln):
                continue
            out.append(ln.rstrip('\n') + "\n")
        out.append("`````\n\n")

        out.append("**Original RDF (as-is):**\n")
        out.append("`````\n")
        for ln in rdf_lines:
            if _skip_line(ln):
                continue
            out.append(ln.rstrip('\n') + "\n")
        out.append("`````\n\n")

        out.append("---\n\n")

    return "".join(out)


def write_jsonl(records: Dict[str, Dict[str, List[str]]], out_path: str) -> None:
    with open(out_path, 'w', encoding='utf-8') as f:
        for rid in sorted(records.keys()):
            obj = {
                'reaction_id': rid,
                'original_txt': [ln for ln in records[rid].get('txt') or [] if not _skip_line(ln)],
                'original_rdf': [ln for ln in records[rid].get('rdf') or [] if not _skip_line(ln)],
                'source': 'combined_markdown',
                'export_timestamp': datetime.now().isoformat(),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class CombinedMDGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Process Combined Reaction Markdown → Report + JSONL")
        self.resize(820, 540)

        self.input_edit = QtWidgets.QLineEdit(self)
        self.input_btn = QtWidgets.QPushButton("Browse…", self)
        self.output_edit = QtWidgets.QLineEdit(self)
        self.output_btn = QtWidgets.QPushButton("Save As…", self)
        self.run_btn = QtWidgets.QPushButton("Generate", self)
        self.log = QtWidgets.QPlainTextEdit(self)
        self.log.setReadOnly(True)

        form = QtWidgets.QFormLayout()
        hb1 = QtWidgets.QHBoxLayout()
        hb1.addWidget(self.input_edit)
        hb1.addWidget(self.input_btn)
        hb2 = QtWidgets.QHBoxLayout()
        hb2.addWidget(self.output_edit)
        hb2.addWidget(self.output_btn)
        form.addRow("Input combined .md:", hb1)
        form.addRow("Output report .md:", hb2)
        form.addRow(self.run_btn)
        form.addRow(self.log)
        self.setLayout(form)

        self.input_btn.clicked.connect(self._choose_input)
        self.output_btn.clicked.connect(self._choose_output)
        self.run_btn.clicked.connect(self._run)

    def _log(self, msg: str):
        self.log.appendPlainText(msg)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _choose_input(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Combined Markdown", "", "Markdown (*.md)")
        if path:
            self.input_edit.setText(path)
            # Suggest default output path
            base = os.path.splitext(path)[0]
            self.output_edit.setText(base + "_report.md")

    def _choose_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Report Markdown", self.output_edit.text() or "", "Markdown (*.md)")
        if path:
            if not path.lower().endswith('.md'):
                path += '.md'
            self.output_edit.setText(path)

    def _run(self):
        inp = (self.input_edit.text() or '').strip()
        out_md = (self.output_edit.text() or '').strip()
        if not inp or not os.path.isfile(inp):
            QtWidgets.QMessageBox.warning(self, "Missing input", "Please choose a combined Markdown file.")
            return
        if not out_md:
            QtWidgets.QMessageBox.warning(self, "Missing output", "Please choose an output Markdown path.")
            return
        try:
            self._log(f"Reading: {inp}")
            records = parse_combined_markdown(inp)
            self._log(f"Found {len(records)} reaction(s)")
            md = generate_markdown(records, inp)
            os.makedirs(os.path.dirname(out_md) or os.getcwd(), exist_ok=True)
            with open(out_md, 'w', encoding='utf-8') as f:
                f.write(md)
            out_jsonl = os.path.splitext(out_md)[0] + ".jsonl"
            write_jsonl(records, out_jsonl)
            self._log(f"Report: {out_md}")
            self._log(f"JSONL:  {out_jsonl}")
            QtWidgets.QMessageBox.information(self, "Done", f"Report and JSONL generated.\n\n{out_md}\n{out_jsonl}")
        except Exception as e:
            self._log(f"Error: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", str(e))


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = CombinedMDGUI()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
