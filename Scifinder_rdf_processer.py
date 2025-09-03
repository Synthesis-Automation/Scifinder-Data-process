#!/usr/bin/env python3
"""
Simple Qt6 GUI wrapper for processing RDF files only.
Lets the user pick a folder containing RDF files and processes all RDF files in the folder.
Works with PySide6 (preferred) or PyQt6 if installed.
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import List, Optional
from pathlib import Path

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


class RDFWorker(QtCore.QObject):
    finished = Signal(bool, str) if Signal else None  # type: ignore[misc]
    progress = Signal(str) if Signal else None  # type: ignore[misc]

    def __init__(self, folder_path: str, output_path: str):
        super().__init__()
        self.folder_path = folder_path
        self.output_path = output_path
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

    def _process_rdf_file(self, rdf_path: str) -> dict:
        """Process a single RDF file - placeholder function"""
        # TODO: Implement actual RDF processing logic here
        # This is currently an empty processor as requested
        
        filename = os.path.basename(rdf_path)
        self._emit(f"Processing {filename}...")
        
        # Placeholder processing - just return basic file info
        result = {
            'filename': filename,
            'filepath': rdf_path,
            'size': os.path.getsize(rdf_path),
            'status': 'processed'
        }
        
        return result

    def _write_results(self, results: List[dict]) -> None:
        """Write processing results to output file"""
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write("RDF Processing Results\n")
                f.write("=" * 50 + "\n\n")
                
                for i, result in enumerate(results, 1):
                    f.write(f"{i}. {result['filename']}\n")
                    f.write(f"   Path: {result['filepath']}\n")
                    f.write(f"   Size: {result['size']} bytes\n")
                    f.write(f"   Status: {result['status']}\n\n")
                
                f.write(f"\nTotal files processed: {len(results)}\n")
        except Exception as e:
            raise RuntimeError(f"Error writing results: {e}")

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
            
            # Process each RDF file
            results = []
            for i, rdf_file in enumerate(self.rdf_files, 1):
                self._emit(f"[{i}/{len(self.rdf_files)}] Processing {os.path.basename(rdf_file)}...")
                try:
                    result = self._process_rdf_file(rdf_file)
                    results.append(result)
                except Exception as e:
                    self._emit(f"Error processing {os.path.basename(rdf_file)}: {e}")
                    results.append({
                        'filename': os.path.basename(rdf_file),
                        'filepath': rdf_file,
                        'size': 0,
                        'status': f'error: {e}'
                    })
            
            # Write results
            self._emit("Writing results...")
            self._write_results(results)
            
            if self.finished:
                self.finished.emit(True, f"Successfully processed {len(self.rdf_files)} RDF files. Results saved to {self.output_path}")
                
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
        self.output_edit = QtWidgets.QLineEdit()
        self.btn_output = QtWidgets.QPushButton("Save As...")
        
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
        self.btn_output.clicked.connect(self.pick_output)
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
        output_box.addWidget(self.output_edit)
        output_box.addWidget(self.btn_output)
        form.addRow("Output File:", output_box)
        
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
            if not self.output_edit.text().strip():
                default_output = os.path.join(path, "rdf_processing_results.txt")
                self.output_edit.setText(default_output)

    def pick_output(self):
        """Select output file location"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Results As",
            os.getcwd(),
            "Text files (*.txt);;All files (*.*)"
        )
        if path:
            if not path.lower().endswith('.txt'):
                path += '.txt'
            self.output_edit.setText(path)

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
        output = self.output_edit.text().strip()
        
        if not folder or not os.path.isdir(folder):
            return "Please select a valid folder containing RDF files."
        
        if not output:
            return "Please specify an output file location."
        
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
        
        # Create worker and thread
        self.worker = RDFWorker(
            folder_path=self.folder_edit.text().strip(),
            output_path=self.output_edit.text().strip()
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
