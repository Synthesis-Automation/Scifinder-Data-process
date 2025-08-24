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


def convert_rtf_folder(folder: str) -> Tuple[int, int]:
    """Convert all .rtf files in folder to .txt with same basename.

    Returns a tuple: (converted_count, failed_count)
    """
    converted = 0
    failed = 0
    try:
        entries = os.listdir(folder)
    except Exception:
        return (0, 0)

    for name in entries:
        if not name.lower().endswith(".rtf"):
            continue
        rtf_path = os.path.join(folder, name)
        if not os.path.isfile(rtf_path):
            continue
        base, _ = os.path.splitext(rtf_path)
        txt_path = base + ".txt"
        try:
            # Read as bytes and decode in latin-1 to keep RTF control words intact.
            with open(rtf_path, "rb") as f:
                rtf_data = f.read().decode("latin-1", errors="ignore")
            text = rtf_to_text(rtf_data)
            # Normalize newlines to Windows-friendly CRLF for notepad compatibility.
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
            with open(txt_path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            converted += 1
        except Exception:
            failed += 1
    return converted, failed


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

    converted, failed = convert_rtf_folder(folder)

    if converted == 0 and failed == 0:
        msg = f"No RTF files found in:\n{folder}"
        QtWidgets.QMessageBox.information(None, "RTF to TXT", msg)
    else:
        msg_lines = [
            f"Folder: {folder}",
            f"Converted: {converted}",
            f"Failed: {failed}",
            "(Existing .txt files were overwritten)",
        ]
        QtWidgets.QMessageBox.information(None, "RTF to TXT", "\n".join(msg_lines))

    # Exit after showing the result message.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
