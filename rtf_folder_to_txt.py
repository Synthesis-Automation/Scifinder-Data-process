#!/usr/bin/env python3
"""
RTF Folder Text Combiner (Qt6 GUI + CLI)

Mirrors the UI style of `Scifinder_rdf_processer.py`:
1) Pick a folder containing .rtf files (non-recursive)
2) Extract plain text (ignore images / {\pict ...}) from each RTF
3) Combine into a single Markdown file with per-file headings

If run via CLI you can specify --folder and --output to bypass the GUI.

Dependencies:
- PyQt6 (preferred) or PySide6 (fallback) for GUI
- striprtf (optional, for higher-fidelity text extraction)

Output Markdown Structure:
# Combined RTF Text

## filename.rtf
```
<extracted text>
```

Extraction Strategy:
- Try striprtf if installed
- Else perform a lightweight RTF to text conversion:
  * Remove groups starting with {\pict  (images)
  * Remove control words (e.g. \par, \tab) mapping a few to whitespace/newlines
  * Decode hex escapes (\'ab)
  * Preserve plain text characters
  * Collapse excessive blank lines
"""
from __future__ import annotations

import os
import sys
import re
import argparse
import traceback
from typing import List, Optional

# Optional high-quality extractor
try:  # pragma: no cover - optional dependency
    from striprtf.striprtf import rtf_to_text as _rtf_to_text  # type: ignore
    HAVE_STRIPRTF = True
except Exception:  # pragma: no cover
    HAVE_STRIPRTF = False
    def _rtf_to_text(data: str) -> str:  # fallback placeholder, replaced by custom logic below
        return data

# Qt binding
try:
    from PyQt6 import QtWidgets, QtCore  # type: ignore
    QtBinding = 'PyQt6'
except Exception:  # pragma: no cover
    from PySide6 import QtWidgets, QtCore  # type: ignore
    QtBinding = 'PySide6'

if hasattr(QtCore, 'Signal') and hasattr(QtCore, 'Slot'):
    Signal = QtCore.Signal
    Slot = QtCore.Slot
else:  # pragma: no cover
    Signal = None  # type: ignore
    Slot = None    # type: ignore

CONTROL_MAP = {
    'par': '\n',
    'line': '\n',
    'tab': '\t',
    'emdash': '—',
    'endash': '–',
    'lquote': '‘',
    'rquote': '’',
    'ldblquote': '“',
    'rdblquote': '”',
}

CONTROL_WORD_RE = re.compile(r'\\([a-zA-Z]+)(-?\d+)?\s?')
HEX_RE = re.compile(r"\\'[0-9a-fA-F]{2}")
PICT_GROUP_RE = re.compile(r'{\\pict[^{}]*?}')  # simplified (non-nested)


def lightweight_rtf_to_text(rtf: str) -> str:
    """Very lightweight RTF -> text converter ignoring images and most formatting."""
    # Remove \r and normalize newlines
    rtf = rtf.replace('\r', '')
    # Remove pict groups (non-nested simple removal)
    rtf = PICT_GROUP_RE.sub('', rtf)

    # Decode hex escapes
    def _hex_sub(m):
        token = m.group(0)
        hexval = token[2:]
        try:
            return bytes.fromhex(hexval).decode('latin1')
        except Exception:
            return ''
    rtf = HEX_RE.sub(_hex_sub, rtf)

    out_chars: List[str] = []
    i = 0
    length = len(rtf)
    stack_depth = 0
    while i < length:
        ch = rtf[i]
        if ch == '{':
            stack_depth += 1
            i += 1
            continue
        if ch == '}':
            stack_depth = max(0, stack_depth - 1)
            i += 1
            continue
        if ch == '\\':
            m = CONTROL_WORD_RE.match(rtf, i)
            if m:
                ctrl = m.group(1)
                replacement = CONTROL_MAP.get(ctrl, '')
                out_chars.append(replacement)
                i = m.end()
                continue
            else:
                # Escaped char like \\{ or \\}
                if i + 1 < length:
                    out_chars.append(rtf[i+1])
                    i += 2
                    continue
                i += 1
                continue
        # Plain text
        out_chars.append(ch)
        i += 1

    text = ''.join(out_chars)

    # Post cleanup
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip trailing spaces on lines
    text = '\n'.join(line.rstrip() for line in text.splitlines())
    # Remove leading/trailing whitespace
    text = text.strip() + '\n'
    return text


def extract_rtf_text(path: str) -> str:
    try:
        data = open(path, 'r', encoding='latin1', errors='ignore').read()
    except Exception:
        try:
            data = open(path, 'rb').read().decode('utf-8', errors='ignore')
        except Exception as e:
            return f"[ERROR reading {os.path.basename(path)}: {e}]\n"

    if HAVE_STRIPRTF:
        try:
            return _rtf_to_text(data).strip() + '\n'
        except Exception:
            pass
    # Fallback
    return lightweight_rtf_to_text(data)


class RTFWorker(QtCore.QObject):
    finished = Signal(bool, str) if Signal else None  # type: ignore
    progress = Signal(str) if Signal else None  # type: ignore

    def __init__(self, folder: str, output_md: str):
        super().__init__()
        self.folder = folder
        self.output_md = output_md
        self.rtf_files: List[str] = []

    def _emit(self, msg: str):
        sig = getattr(self, 'progress', None)
        if sig:
            try:
                sig.emit(msg)
            except Exception:
                pass

    def _scan(self):
        self.rtf_files = []
        try:
            for f in os.listdir(self.folder):
                if f.lower().endswith('.rtf'):
                    fp = os.path.join(self.folder, f)
                    if os.path.isfile(fp):
                        self.rtf_files.append(fp)
        except Exception as e:
            raise RuntimeError(f"Error scanning folder: {e}")
        self.rtf_files.sort()

    def _write_markdown(self, sections: List[str]):
        heading = ["# Combined RTF Text", "", f"Source folder: {self.folder}", "",]
        content = '\n'.join(heading + sections)
        with open(self.output_md, 'w', encoding='utf-8') as f:
            f.write(content)

    @Slot() if Slot else (lambda f: f)
    def run(self):  # pragma: no cover - executed in thread
        try:
            self._emit("Scanning for RTF files...")
            self._scan()
            if not self.rtf_files:
                if self.finished:
                    self.finished.emit(False, "No RTF files found.")
                return
            self._emit(f"Found {len(self.rtf_files)} RTF files.")
            sections: List[str] = []
            for i, path in enumerate(self.rtf_files, 1):
                base = os.path.basename(path)
                self._emit(f"[{i}/{len(self.rtf_files)}] Extracting {base}...")
                text = extract_rtf_text(path)
                if not text.strip():
                    text = "[Empty or unreadable content]\n"
                section = f"## {base}\n\n```\n{text}```\n"
                sections.append(section)
            self._emit("Writing markdown output...")
            self._write_markdown(sections)
            if self.finished:
                self.finished.emit(True, f"Wrote {len(self.rtf_files)} files into {self.output_md}")
        except Exception as e:
            if self.finished:
                self.finished.emit(False, f"Error: {e}\n\n{traceback.format_exc()}")


class RTFProcessorWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTF Folder Text Combiner")
        self.resize(700, 500)

        self.folder_edit = QtWidgets.QLineEdit()
        self.btn_folder = QtWidgets.QPushButton("Browse Folder...")
        self.output_md_edit = QtWidgets.QLineEdit()
        self.btn_output_md = QtWidgets.QPushButton("Save As...")

        self.file_list = QtWidgets.QListWidget()
        self.file_count_label = QtWidgets.QLabel("No folder selected")

        self.btn_run = QtWidgets.QPushButton("Combine RTF Text")
        self.btn_quit = QtWidgets.QPushButton("Quit")

        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(150)

        self._setup_layout()

        self.btn_folder.clicked.connect(self.pick_folder)
        self.btn_output_md.clicked.connect(self.pick_output)
        self.btn_run.clicked.connect(self.run_processing)
        self.btn_quit.clicked.connect(self.close)

        self.thread = None
        self.worker = None
        self.rtf_files: List[str] = []
        self.btn_run.setEnabled(False)

    def _setup_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("RTF Folder Text Combiner")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        folder_box = QtWidgets.QHBoxLayout(); folder_box.addWidget(self.folder_edit); folder_box.addWidget(self.btn_folder)
        form.addRow("RTF Folder:", folder_box)
        output_box = QtWidgets.QHBoxLayout(); output_box.addWidget(self.output_md_edit); output_box.addWidget(self.btn_output_md)
        form.addRow("Output Markdown:", output_box)
        note = QtWidgets.QLabel("Each RTF becomes a section; images are ignored."); note.setStyleSheet("font-style: italic; color: #666;")
        form.addRow("", note)
        layout.addLayout(form)

        group = QtWidgets.QGroupBox("RTF Files Found"); gl = QtWidgets.QVBoxLayout(group)
        gl.addWidget(self.file_count_label); gl.addWidget(self.file_list)
        layout.addWidget(group)

        bl = QtWidgets.QHBoxLayout(); bl.addStretch(); bl.addWidget(self.btn_run); bl.addWidget(self.btn_quit)
        layout.addLayout(bl)

        log_group = QtWidgets.QGroupBox("Processing Log"); lg = QtWidgets.QVBoxLayout(log_group); lg.addWidget(self.log); layout.addWidget(log_group)

    def log_msg(self, text: str):
        self.log.appendPlainText(text)

    def pick_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder with RTF files", os.getcwd(), options=QtWidgets.QFileDialog.Option.ShowDirsOnly)
        if path:
            self.folder_edit.setText(path)
            self._update_file_list()
            if not self.output_md_edit.text().strip():
                self.output_md_edit.setText(os.path.join(path, "combined_rtf_text.md"))

    def pick_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Markdown As", os.getcwd(), "Markdown files (*.md);;All files (*.*)")
        if path:
            if not path.lower().endswith('.md'):
                path += '.md'
            self.output_md_edit.setText(path)

    def _update_file_list(self):
        self.file_list.clear(); self.rtf_files = []
        folder = self.folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            self.file_count_label.setText("No valid folder selected"); self.btn_run.setEnabled(False); return
        try:
            for f in os.listdir(folder):
                if f.lower().endswith('.rtf'):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp):
                        self.rtf_files.append(fp); self.file_list.addItem(f)
            count = len(self.rtf_files)
            if count == 0:
                self.file_count_label.setText("No RTF files found in this folder"); self.btn_run.setEnabled(False)
            else:
                self.file_count_label.setText(f"Found {count} RTF file{'s' if count != 1 else ''}"); self.btn_run.setEnabled(True)
        except Exception as e:
            self.file_count_label.setText(f"Error reading folder: {e}"); self.btn_run.setEnabled(False)

    def validate_inputs(self) -> Optional[str]:
        folder = self.folder_edit.text().strip(); out_md = self.output_md_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            return "Please select a valid folder containing RTF files."
        if not out_md:
            return "Please specify an output Markdown file."
        if not self.rtf_files:
            return "No RTF files found in the selected folder."
        return None

    def run_processing(self):
        err = self.validate_inputs()
        if err:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", err); return
        self.setEnabled(False); self.log.clear(); self.log_msg("Starting RTF extraction...")
        output_md = self.output_md_edit.text().strip()
        self.worker = RTFWorker(self.folder_edit.text().strip(), output_md)
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        if getattr(self.worker, 'finished', None):
            self.worker.finished.connect(self.on_finished)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
        if getattr(self.worker, 'progress', None):
            self.worker.progress.connect(self.log_msg)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.setEnabled(True))
        self.thread.finished.connect(lambda: setattr(self, 'worker', None))
        self.thread.finished.connect(lambda: setattr(self, 'thread', None))
        self.thread.start()

    def on_finished(self, success: bool, message: str):
        self.setEnabled(True); self.log_msg(message)
        if success:
            QtWidgets.QMessageBox.information(self, "RTF Extraction Complete", message)
        else:
            QtWidgets.QMessageBox.critical(self, "RTF Extraction Error", message)


def run_cli(folder: str, output_md: str) -> int:
    worker = RTFWorker(folder, output_md)
    try:
        worker._scan()
        if not worker.rtf_files:
            print("No RTF files found.")
            return 1
        sections: List[str] = []
        for i, path in enumerate(worker.rtf_files, 1):
            print(f"[{i}/{len(worker.rtf_files)}] {os.path.basename(path)}")
            text = extract_rtf_text(path)
            if not text.strip():
                text = "[Empty or unreadable content]\n"
            section = f"## {os.path.basename(path)}\n\n```\n{text}```\n"
            sections.append(section)
        worker._write_markdown(sections)
        print(f"Wrote {len(worker.rtf_files)} files into {output_md}")
        return 0
    except Exception as e:
        print("Error:", e)
        print(traceback.format_exc())
        return 2


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description="Combine text from RTF files into a Markdown document.")
    parser.add_argument('--folder', help='Folder containing .rtf files')
    parser.add_argument('--output', help='Output markdown file (.md)')
    args = parser.parse_args()

    if args.folder and args.output:
        return sys.exit(run_cli(args.folder, args.output))

    # Launch GUI
    if hasattr(QtWidgets, 'QApplication'):
        try:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass
    app = QtWidgets.QApplication(sys.argv)
    win = RTFProcessorWindow(); win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
