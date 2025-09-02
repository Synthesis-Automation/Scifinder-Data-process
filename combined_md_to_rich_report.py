#!/usr/bin/env python3
"""
Rich processor for pre-combined Markdown files (from Combine_reaction_data.py).

Workflow:
- Open a combined Markdown file with sections like:
  ## Reaction <ID>
  **Original TXT (as-is):**  ``` ... ```
  **Original RDF (as-is):**  ``` ... ```
- Reconstruct minimal TXT/RDF maps per ReactionID.
- Load CAS mappings.
- Run the same processing as the original pipeline (assemble_rows) to compute
  CAS pairing, roles, dedup, SMILES (from MOL), etc.
- Generate outputs:
  - Markdown (rich, validated) using ReactionMarkdownGenerator formatter
  - JSONL (analysis-optimized) using the same generator
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
from typing import Dict, List, Tuple, Any
from datetime import datetime

try:
    from PyQt6 import QtWidgets
    QT_BINDING = "PyQt6"
except Exception:
    try:
        from PySide6 import QtWidgets  # type: ignore
        QT_BINDING = "PySide6"
    except Exception:
        print("Error: Neither PyQt6 nor PySide6 is installed. Please install one of them.")
        sys.exit(1)

try:
    from process_reactions import parse_rdf, assemble_rows, load_cas_maps
except Exception as e:
    print(f"Error: Cannot import processing helpers: {e}")
    sys.exit(1)

try:
    # We reuse the formatter and JSONL generator to keep behavior identical
    from reaction_markdown_generator import ReactionMarkdownGenerator
except Exception as e:
    print(f"Error: Cannot import ReactionMarkdownGenerator: {e}")
    sys.exit(1)

# Detect RDKit availability so we can explain missing SMILES clearly
try:
    from rdkit import Chem  # type: ignore
    RDKIT_AVAILABLE = True
except Exception:
    Chem = None  # type: ignore
    RDKIT_AVAILABLE = False


def parse_combined_markdown(path: str) -> Dict[str, Dict[str, List[str]]]:
    """Parse a combined Markdown file into per-reaction TXT/RDF blocks.

    Robust to code fences that begin with backticks followed by inline content
    (e.g., "```$RXN" or "```Steps: 1, Yield: 50%"), which some generators emit.
    In such cases, the remainder after the backticks is treated as the first
    line within the fenced block.
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    records: Dict[str, Dict[str, List[str]]] = {}
    rid: str | None = None
    in_fence = False
    current_block: str | None = None  # 'txt' or 'rdf'

    def _starts_code_fence(s: str) -> Tuple[bool, str]:
        t = s.lstrip()
        if t.startswith('```'):
            # return (is_fence, remainder_after_backticks)
            return True, t[3:]
        if t.startswith('`````'):
            return True, t[5:]
        return False, ''

    for raw in lines:
        line = raw.rstrip('\n')
        stripped = line.strip()
        if line.startswith('## Reaction '):
            rid = line[len('## Reaction '):].strip()
            records.setdefault(rid, {'txt': [], 'rdf': []})
            in_fence = False
            current_block = None
            continue
        if stripped.startswith('**Original TXT'):
            current_block = 'txt'
            continue
        if stripped.startswith('**Original RDF'):
            current_block = 'rdf'
            continue

        # Handle code fence open/close, including inline-start form
        is_fence, remainder = _starts_code_fence(line)
        if is_fence:
            # Toggle fence state
            was_in = in_fence
            in_fence = not in_fence
            # If this is an opening fence (we were not previously in one)
            # and there is non-empty remainder, treat it as first content line
            if (not was_in) and rid and current_block in {'txt', 'rdf'}:
                rem = remainder.strip()
                # If remainder looks like a language tag (e.g., "python"), skip it;
                # otherwise treat as content. Heuristic: language tags are simple words.
                if rem and not rem.isalpha():
                    records[rid][current_block].append(rem)
            continue

        if in_fence and rid and current_block in {'txt', 'rdf'}:
            records[rid][current_block].append(line)
            continue
    return records


def compute_time_and_temp_from_txt(lines: List[str]) -> Tuple[Any, Any]:
    """Best-effort time (h) and temperature (C) from original TXT lines.
    Matches the heuristics in process_reactions (rt=25C, overnight=16h).
    """
    import re, math
    RE_TIME = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hrs|hour|hours|min|mins|minute|minutes|d|day|days)\b", re.I)
    RE_TEMP_C = re.compile(r"(?P<val>-?\d+(?:\.\d+)?)\s*[^A-Za-z0-9]{0,3}C\b")
    total_h = 0.0
    max_c = -math.inf
    had_rt = False
    for ln in lines or []:
        for m in RE_TIME.finditer(ln):
            num = float(m.group('num'))
            unit = m.group('unit').lower()
            if unit.startswith('min'):
                total_h += num / 60.0
            elif unit.startswith('d'):
                total_h += num * 24.0
            else:
                total_h += num
        if re.search(r"\bovernight\b", ln, re.I):
            total_h += 16.0
        for m in RE_TEMP_C.finditer(ln):
            val = float(m.group('val'))
            if val > max_c:
                max_c = val
        if re.search(r"\brt\b|room temperature", ln, re.I):
            had_rt = True
    temperature_c = max_c if max_c != -math.inf else (25.0 if had_rt else None)
    return (round(total_h, 3) if total_h > 0 else None,
            round(temperature_c, 1) if temperature_c is not None else None)


def build_txt_map(records: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, Any]]:
    txt_map: Dict[str, Dict[str, Any]] = {}
    for rid, blocks in records.items():
        txt_lines = list(blocks.get('txt') or [])
        time_h, temp_c = compute_time_and_temp_from_txt(txt_lines)
        txt_map[rid] = {
            'original_text': txt_lines,
            'all_condition_lines': txt_lines,
            'time_h': time_h,
            'temperature_c': temp_c,
            # Optional placeholders; parse_txt would normally set these
            'title': '', 'authors': '', 'citation': '', 'doi': '',
            'reagents': [], 'catalysts': [], 'solvents': [],
            'txt_yield': None,
        }
    return txt_map


def build_rdf_file(records: Dict[str, Dict[str, List[str]]]) -> str:
    """Write a temporary RDF file containing concatenated per-reaction RDF blocks."""
    # Concatenate exactly as captured; parse_rdf can handle multiple records.
    tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.rdf', encoding='utf-8', newline='')
    with tmp as f:
        for rid in records.keys():
            for ln in records[rid].get('rdf') or []:
                f.write(ln.rstrip('\n') + '\n')
    return tmp.name


def load_default_cas_maps(context_dir: str) -> Dict[str, Dict[str, str]]:
    paths: List[str] = []
    merged = os.path.join(context_dir, 'cas_registry_merged.jsonl')
    if os.path.exists(merged):
        paths.append(merged)
    else:
        for cand in ['cas_dictionary.jsonl', 'comprehensive_cas_registry.jsonl']:
            p = os.path.join(context_dir, cand)
            if os.path.exists(p):
                paths.append(p)
    return load_cas_maps(paths) if paths else {}


class CombinedMDRichGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Process Combined Markdown → Rich Report + JSONL")
        self.resize(860, 560)

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
            base = os.path.splitext(path)[0]
            self.output_edit.setText(base + "_rich.md")

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
            self._log(f"Reading combined Markdown: {inp}")
            records = parse_combined_markdown(inp)
            self._log(f"Found {len(records)} reaction(s)")

            # Build minimal maps
            txt_map = build_txt_map(records)
            tmp_rdf = build_rdf_file(records)
            self._log("Parsing RDF blocks…")
            rdf_map = parse_rdf(tmp_rdf)
            # Diagnostics: count MOL blocks captured from RDF
            rct_mol_n = sum(1 for v in rdf_map.values() if v.get('rct_mol'))
            pro_mol_n = sum(1 for v in rdf_map.values() if v.get('pro_mol'))
            self._log(f"RDF parsed. Reactions with reactant MOL blocks: {rct_mol_n}; with product MOL blocks: {pro_mol_n}")
            self._log(f"RDKit available: {RDKIT_AVAILABLE}")

            # Load CAS maps
            here = os.path.dirname(os.path.abspath(__file__))
            self._log("Loading CAS mappings…")
            cas_map = load_default_cas_maps(here)

            # Assemble rows (same pipeline as original)
            self._log("Assembling rows…")
            rows = assemble_rows(txt_map, rdf_map, cas_map)
            self._log(f"Assembled {len(rows)} rows")
            # Diagnostics: count rows where SMILES were produced
            smi_rows = sum(1 for r in rows if (r.get('ReactantSMILES') or r.get('ProductSMILES')))
            self._log(f"Rows with SMILES: {smi_rows} / {len(rows)}")
            if smi_rows == 0:
                if not RDKIT_AVAILABLE:
                    self._log("Note: RDKit is not available in this Python environment; SMILES generation from MOL blocks is disabled.")
                elif (rct_mol_n + pro_mol_n) == 0:
                    self._log("Note: No MOL/CTAB blocks were found in the RDF content; SMILES cannot be generated from RDF without structures.")
                else:
                    self._log("Warning: MOL blocks were found and RDKit is available, but SMILES are still empty. The MOL data may be malformed.")

            # Generate outputs using the same formatter
            gen = ReactionMarkdownGenerator()
            gen.cas_map = cas_map
            # Reuse the generator's writer methods
            self._log("Writing Markdown report…")
            gen.generate_markdown_report(rows, out_md, os.path.basename(inp))
            out_jsonl = os.path.splitext(out_md)[0] + '.jsonl'
            self._log("Writing JSONL export…")
            gen.generate_jsonl_export(rows, out_jsonl, os.path.basename(inp))

            # Done
            self._log(f"Done. Report: {out_md}")
            self._log(f"JSONL:  {out_jsonl}")
            QtWidgets.QMessageBox.information(self, "Done", f"Report and JSONL generated.\n\n{out_md}\n{out_jsonl}")
        except Exception as e:
            self._log(f"Error: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
        finally:
            # Clean temp files if present
            try:
                if 'tmp_rdf' in locals() and os.path.exists(tmp_rdf):
                    os.unlink(tmp_rdf)
            except Exception:
                pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = CombinedMDRichGUI()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
