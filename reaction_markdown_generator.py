#!/usr/bin/env python3
"""
Standalone Reaction Markdown Generator

This tool:
1. Scans a folder for matching RDF/TXT pairs
2. Processes each pair using the existing parsing logic
3. Generates a centralized markdown report with detailed reaction information

Features:
- Interactive GUI for folder selection
- Automatic RDF/TXT pair detection
- Rich markdown output with reaction details
- CAS number mapping and compound identification
- Reaction type classification (Buchwald, Ullmann, Other)

Dependencies:
- PyQt6 (or PySide6 as fallback)
- process_reactions module (for parsing logic)
"""
from __future__ import annotations

import os
import sys
import json
import re
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

try:
    from PyQt6 import QtWidgets, QtCore
    QtBinding = "PyQt6"
except Exception:  # pragma: no cover - optional fallback
    try:
        from PySide6 import QtWidgets, QtCore  # type: ignore
        QtBinding = "PySide6"  # type: ignore
    except Exception:
        print("Error: Neither PyQt6 nor PySide6 is installed. Please install one of them.")
        sys.exit(1)

# Import processing functions from the existing module
try:
    from process_reactions import (
        parse_txt,
        parse_rdf,
        assemble_rows,
        load_cas_maps,
        infer_reaction_type,
    )
except ImportError as e:
    print(f"Error: Cannot import process_reactions module: {e}")
    sys.exit(1)


class ReactionMarkdownGenerator:
    """Main class for generating markdown reports from RDF/TXT pairs."""
    
    def __init__(self):
        self.cas_map = {}
        
    def find_rdf_txt_pairs(self, folder_path: str) -> List[Tuple[str, str]]:
        """Find matching RDF/TXT pairs in the specified folder."""
        if not os.path.isdir(folder_path):
            return []
            
        files = os.listdir(folder_path)
        base_to_files = defaultdict(dict)
        
        # Group files by base name
        for file in files:
            if os.path.isfile(os.path.join(folder_path, file)):
                base, ext = os.path.splitext(file)
                base_to_files[base.lower()][ext.lower()] = file
        
        # Find pairs
        pairs = []
        for base, extensions in base_to_files.items():
            if '.rdf' in extensions and '.txt' in extensions:
                rdf_file = os.path.join(folder_path, extensions['.rdf'])
                txt_file = os.path.join(folder_path, extensions['.txt'])
                pairs.append((rdf_file, txt_file))
        
        return sorted(pairs)
    
    def load_cas_mappings(self, folder_path: str) -> Dict[str, Dict[str, str]]:
        """Load CAS mappings from known locations."""
        cas_map_paths = []
        
        # Auto-detect built-in CAS maps
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_paths = [
            os.path.join(here, 'Buchwald', 'cas_dictionary.csv'),
            os.path.join(here, 'Ullman', '新建文件夹', 'ullmann_cas_to_name_mapping.csv'),
            os.path.join(folder_path, 'cas_dictionary.csv'),
            os.path.join(folder_path, 'cas_mapping.csv'),
        ]
        
        for path in maybe_paths:
            if os.path.exists(path):
                cas_map_paths.append(path)
        
        return load_cas_maps(cas_map_paths) if cas_map_paths else {}
    
    def format_compound_list(self, compound_list: List[str], title: str) -> str:
        """Format a list of compounds for markdown output."""
        if not compound_list:
            return f"**{title}:** None\n"
        
        result = f"**{title}:**\n"
        for compound in compound_list:
            if '|' in compound:
                name, cas = compound.split('|', 1)
                if name.strip() and cas.strip():
                    result += f"  - {name.strip()} (CAS: {cas.strip()})\n"
                elif name.strip():
                    result += f"  - {name.strip()}\n"
                elif cas.strip():
                    result += f"  - CAS: {cas.strip()}\n"
            else:
                result += f"  - {compound}\n"
        
        return result + "\n"
    
    def format_reaction_conditions(self, row: Dict[str, Any]) -> str:
        """Format reaction conditions for markdown output."""
        conditions = []
        
        temp = row.get('Temperature_C', '')
        if temp:
            conditions.append(f"Temperature: {temp}°C")
        
        time = row.get('Time_h', '')
        if time:
            conditions.append(f"Time: {time} hours")
        
        yield_pct = row.get('Yield_%', '')
        if yield_pct:
            conditions.append(f"Yield: {yield_pct}%")
        
        if conditions:
            return "**Reaction Conditions:**\n" + "\n".join(f"  - {cond}" for cond in conditions) + "\n\n"
        return ""
    
    def format_smiles(self, row: Dict[str, Any]) -> str:
        """Format SMILES data for markdown output."""
        reactant_smiles = row.get('ReactantSMILES', '').strip()
        product_smiles = row.get('ProductSMILES', '').strip()
        
        if not reactant_smiles and not product_smiles:
            return ""
        
        result = "**SMILES:**\n"
        if reactant_smiles:
            result += f"  - Reactants: `{reactant_smiles}`\n"
        if product_smiles:
            result += f"  - Products: `{product_smiles}`\n"
        
        return result + "\n"
    
    def format_reference(self, row: Dict[str, Any]) -> str:
        """Format reference information for markdown output."""
        reference = row.get('Reference', '').strip()
        if reference:
            return f"**Reference:** {reference}\n\n"
        return ""
    
    def generate_reaction_markdown(self, row: Dict[str, Any]) -> str:
        """Generate markdown content for a single reaction."""
        reaction_id = row.get('ReactionID', 'Unknown')
        reaction_type = row.get('ReactionType', 'Unknown')
        
        markdown = f"## Reaction {reaction_id}\n\n"
        markdown += f"**Type:** {reaction_type}\n\n"
        
        # Parse JSON fields
        try:
            catalyst_core = json.loads(row.get('CatalystCoreDetail', '[]'))
            catalyst_generic = json.loads(row.get('CatalystCoreGeneric', '[]'))
            ligands = json.loads(row.get('Ligand', '[]'))
            full_catalytic = json.loads(row.get('FullCatalyticSystem', '[]'))
            reagents = json.loads(row.get('Reagent', '[]'))
            reagent_roles = json.loads(row.get('ReagentRole', '[]'))
            solvents = json.loads(row.get('Solvent', '[]'))
        except json.JSONDecodeError:
            catalyst_core = []
            catalyst_generic = []
            ligands = []
            full_catalytic = []
            reagents = []
            reagent_roles = []
            solvents = []
        
        # Format catalytic system
        if full_catalytic:
            markdown += self.format_compound_list(full_catalytic, "Full Catalytic System")
        
        if catalyst_core:
            markdown += self.format_compound_list(catalyst_core, "Catalyst Core")
        
        if catalyst_generic:
            markdown += f"**Generic Catalyst:** {', '.join(catalyst_generic)}\n\n"
        
        if ligands:
            markdown += self.format_compound_list(ligands, "Ligands")
        
        # Format reagents with roles
        if reagents:
            markdown += "**Reagents:**\n"
            for i, reagent in enumerate(reagents):
                role = reagent_roles[i] if i < len(reagent_roles) else "UNK"
                if '|' in reagent:
                    name, cas = reagent.split('|', 1)
                    if name.strip() and cas.strip():
                        markdown += f"  - {name.strip()} (CAS: {cas.strip()}) - Role: {role}\n"
                    elif name.strip():
                        markdown += f"  - {name.strip()} - Role: {role}\n"
                    elif cas.strip():
                        markdown += f"  - CAS: {cas.strip()} - Role: {role}\n"
                else:
                    markdown += f"  - {reagent} - Role: {role}\n"
            markdown += "\n"
        
        if solvents:
            markdown += self.format_compound_list(solvents, "Solvents")
        
        # Add reaction conditions
        markdown += self.format_reaction_conditions(row)
        
        # Add SMILES if available
        markdown += self.format_smiles(row)
        
        # Add reference
        markdown += self.format_reference(row)
        
        # Add separator
        markdown += "---\n\n"
        
        return markdown
    
    def generate_summary_statistics(self, rows: List[Dict[str, Any]]) -> str:
        """Generate summary statistics for the markdown report."""
        if not rows:
            return "## Summary\n\nNo reactions found.\n\n"
        
        # Count reaction types
        reaction_types = defaultdict(int)
        total_reactions = len(rows)
        reactions_with_yield = 0
        avg_yield = 0
        
        for row in rows:
            reaction_type = row.get('ReactionType', 'Unknown')
            reaction_types[reaction_type] += 1
            
            yield_pct = row.get('Yield_%', '')
            if yield_pct:
                try:
                    yield_val = float(yield_pct)
                    avg_yield += yield_val
                    reactions_with_yield += 1
                except (ValueError, TypeError):
                    pass
        
        if reactions_with_yield > 0:
            avg_yield /= reactions_with_yield
        
        markdown = f"## Summary\n\n"
        markdown += f"**Total Reactions:** {total_reactions}\n\n"
        
        markdown += "**Reaction Types:**\n"
        for reaction_type, count in sorted(reaction_types.items()):
            percentage = (count / total_reactions) * 100
            markdown += f"  - {reaction_type}: {count} ({percentage:.1f}%)\n"
        markdown += "\n"
        
        if reactions_with_yield > 0:
            markdown += f"**Yield Statistics:**\n"
            markdown += f"  - Reactions with yield data: {reactions_with_yield}/{total_reactions}\n"
            markdown += f"  - Average yield: {avg_yield:.1f}%\n\n"
        
        return markdown
    
    def process_folder(self, folder_path: str, output_path: str, progress_callback=None) -> bool:
        """Process all RDF/TXT pairs in a folder and generate markdown report."""
        try:
            if progress_callback:
                progress_callback("Scanning for RDF/TXT pairs...")
            
            pairs = self.find_rdf_txt_pairs(folder_path)
            if not pairs:
                raise ValueError("No matching RDF/TXT pairs found in the folder")
            
            if progress_callback:
                progress_callback(f"Found {len(pairs)} RDF/TXT pairs")
            
            # Load CAS mappings
            if progress_callback:
                progress_callback("Loading CAS mappings...")
            self.cas_map = self.load_cas_mappings(folder_path)
            
            # Process all pairs
            all_txt = {}
            all_rdf = {}
            
            for i, (rdf_path, txt_path) in enumerate(pairs):
                if progress_callback:
                    progress_callback(f"Processing pair {i+1}/{len(pairs)}: {os.path.basename(txt_path)}")
                
                try:
                    txt_data = parse_txt(txt_path)
                    rdf_data = parse_rdf(rdf_path)
                    all_txt.update(txt_data)
                    all_rdf.update(rdf_data)
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Error processing {txt_path}: {e}")
                    continue
            
            if progress_callback:
                progress_callback("Assembling reaction data...")
            
            # Assemble rows
            rows = assemble_rows(all_txt, all_rdf, self.cas_map)
            
            if progress_callback:
                progress_callback(f"Generating markdown report for {len(rows)} reactions...")
            
            # Generate markdown report
            self.generate_markdown_report(rows, output_path, folder_path)
            
            if progress_callback:
                progress_callback(f"Report generated successfully: {output_path}")
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False
    
    def generate_markdown_report(self, rows: List[Dict[str, Any]], output_path: str, source_folder: str):
        """Generate the complete markdown report."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Reaction Data Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Source Folder:** {source_folder}\n")
            f.write(f"**Total Reactions:** {len(rows)}\n\n")
            
            # Summary statistics
            f.write(self.generate_summary_statistics(rows))
            
            # Individual reactions
            f.write("# Individual Reactions\n\n")
            
            # Sort reactions by ID for consistent output
            sorted_rows = sorted(rows, key=lambda x: x.get('ReactionID', ''))
            
            for row in sorted_rows:
                f.write(self.generate_reaction_markdown(row))


class MarkdownGeneratorGUI(QtWidgets.QWidget):
    """GUI for the Reaction Markdown Generator."""
    
    def __init__(self):
        super().__init__()
        self.generator = ReactionMarkdownGenerator()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Reaction Markdown Generator")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Title
        title = QtWidgets.QLabel("Reaction Markdown Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QtWidgets.QLabel(
            "Select a folder containing RDF/TXT pairs to generate a centralized markdown report.\n"
            "The tool will automatically find matching pairs and extract reaction information."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(desc)
        
        # Folder selection
        folder_layout = QtWidgets.QHBoxLayout()
        self.folder_edit = QtWidgets.QLineEdit()
        self.folder_edit.setPlaceholderText("Select folder containing RDF/TXT pairs...")
        folder_btn = QtWidgets.QPushButton("Browse Folder")
        folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(QtWidgets.QLabel("Input Folder:"))
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)
        
        # Output file selection
        output_layout = QtWidgets.QHBoxLayout()
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Choose output markdown file...")
        output_btn = QtWidgets.QPushButton("Browse Output")
        output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(QtWidgets.QLabel("Output File:"))
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)
        
        # Progress display
        self.progress_text = QtWidgets.QPlainTextEdit()
        self.progress_text.setMaximumHeight(150)
        self.progress_text.setReadOnly(True)
        layout.addWidget(QtWidgets.QLabel("Progress:"))
        layout.addWidget(self.progress_text)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.generate_btn = QtWidgets.QPushButton("Generate Report")
        self.generate_btn.clicked.connect(self.generate_report)
        self.generate_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        
        quit_btn = QtWidgets.QPushButton("Quit")
        quit_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(quit_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Folder with RDF/TXT Pairs"
        )
        if folder:
            self.folder_edit.setText(folder)
            # Auto-suggest output file
            if not self.output_edit.text():
                output_file = os.path.join(folder, "reaction_report.md")
                self.output_edit.setText(output_file)
    
    def select_output(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Markdown Report", "", "Markdown files (*.md);;All files (*.*)"
        )
        if file_path:
            if not file_path.lower().endswith('.md'):
                file_path += '.md'
            self.output_edit.setText(file_path)
    
    def log_progress(self, message: str):
        self.progress_text.appendPlainText(message)
        QtWidgets.QApplication.processEvents()  # Update GUI
    
    def generate_report(self):
        folder = self.folder_edit.text().strip()
        output = self.output_edit.text().strip()
        
        if not folder:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select an input folder.")
            return
        
        if not output:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please specify an output file.")
            return
        
        if not os.path.isdir(folder):
            QtWidgets.QMessageBox.critical(self, "Error", "Input folder does not exist.")
            return
        
        # Clear progress
        self.progress_text.clear()
        self.generate_btn.setEnabled(False)
        
        try:
            success = self.generator.process_folder(folder, output, self.log_progress)
            
            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", f"Markdown report generated successfully!\n\nFile: {output}"
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", "Failed to generate report. Check the progress log for details."
                )
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        
        finally:
            self.generate_btn.setEnabled(True)


def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate markdown reports from RDF/TXT reaction pairs")
    parser.add_argument('--folder', '-f', help='Input folder containing RDF/TXT pairs')
    parser.add_argument('--output', '-o', help='Output markdown file path')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface (default if no args)')
    
    args = parser.parse_args()
    
    # If command line arguments provided, run in CLI mode
    if args.folder and args.output:
        print("Running in command-line mode...")
        generator = ReactionMarkdownGenerator()
        
        def print_progress(msg):
            print(f"[INFO] {msg}")
        
        success = generator.process_folder(args.folder, args.output, print_progress)
        if success:
            print(f"✓ Report generated successfully: {args.output}")
            sys.exit(0)
        else:
            print("✗ Failed to generate report")
            sys.exit(1)
    
    # Otherwise launch GUI
    else:
        if args.folder or args.output:
            print("Note: Both --folder and --output are required for CLI mode. Launching GUI...")
        
        app = QtWidgets.QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("Reaction Markdown Generator")
        app.setApplicationVersion("1.0")
        
        # Create and show the main window
        window = MarkdownGeneratorGUI()
        window.show()
        
        # Run the application
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
