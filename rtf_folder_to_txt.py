#!/usr/bin/env python3
"""
Simple Qt6 app: pick a folder, convert all .rtf files in it to .txt (overwrite).

Dependencies:
- PyQt6 (or PySide6 as fallback)
- striprtf
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

try:
    from PyQt6 import QtWidgets
    QtBinding = "PyQt6"
except Exception:  # pragma: no cover - optional fallback
    from PySide6 import QtWidgets  # type: ignore
    QtBinding = "PySide6"  # type: ignore

try:
    from striprtf.striprtf import rtf_to_text
except Exception as e:  # pragma: no cover
    # Provide a clear error if dependency is missing.
    sys.stderr.write(
        "Missing dependency 'striprtf'. Install it with: pip install striprtf\n"
    )
    raise


def convert_single_file(rtf_path: str) -> bool:
    """Convert one RTF file to TXT in place (same basename). Returns True on success."""
    base, _ = os.path.splitext(rtf_path)
    txt_path = base + ".txt"
    # Read as bytes and decode in latin-1 to keep RTF control words intact.
    with open(rtf_path, "rb") as f:
        rtf_data = f.read().decode("latin-1", errors="ignore")
    text = rtf_to_text(rtf_data)
    # Normalize newlines to Windows-friendly CRLF for notepad compatibility.
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    with open(txt_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return True


def convert_rtf_folder_with_progress(folder: str, parent=None) -> Tuple[int, int, bool]:
    """Convert all .rtf files in folder with a progress dialog.

    Returns (converted_count, failed_count, canceled)
    """
    try:
        files = [
            os.path.join(folder, n)
            for n in os.listdir(folder)
            if n.lower().endswith(".rtf") and os.path.isfile(os.path.join(folder, n))
        ]
    except Exception:
        return (0, 0, False)

    total = len(files)
    if total == 0:
        return (0, 0, False)

    dlg = QtWidgets.QProgressDialog("Converting files…", "Cancel", 0, total, parent)
    dlg.setWindowTitle("RTF to TXT")
    dlg.setAutoClose(True)
    dlg.setAutoReset(True)
    dlg.setMinimumDuration(0)  # show immediately

    converted = 0
    failed = 0
    canceled = False

    for i, path in enumerate(files, start=1):
        if dlg.wasCanceled():
            canceled = True
            break
        dlg.setLabelText(f"Converting: {os.path.basename(path)}  ({i}/{total})")
        dlg.setValue(i - 1)
        QtWidgets.QApplication.processEvents()
        try:
            convert_single_file(path)
            converted += 1
        except Exception:
            failed += 1
        # Update to current step done
        dlg.setValue(i)
        QtWidgets.QApplication.processEvents()

    return converted, failed, canceled


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    folder = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Select a folder containing RTF files",
        os.getcwd(),
        options=QtWidgets.QFileDialog.Option.ShowDirsOnly,
    )
    if not folder:
        return 0

    converted, failed, canceled = convert_rtf_folder_with_progress(folder)

    if converted == 0 and failed == 0 and not canceled:
        msg = f"No RTF files found in:\n{folder}"
        QtWidgets.QMessageBox.information(None, "RTF to TXT", msg)
    else:
        msg_lines = [
            f"Folder: {folder}",
            f"Converted: {converted}",
            f"Failed: {failed}",
            "(Existing .txt files were overwritten)",
        ]
        if canceled:
            msg_lines.append("Conversion was canceled.")
        QtWidgets.QMessageBox.information(None, "RTF to TXT", "\n".join(msg_lines))

    # Exit after showing the result message.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
