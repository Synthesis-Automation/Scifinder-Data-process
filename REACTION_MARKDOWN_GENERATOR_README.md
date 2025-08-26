# Reaction Markdown Generator

A standalone application that combines RDF and TXT files from SciFinder to generate comprehensive markdown reports with detailed reaction information.

## Features

- **Automatic Pair Detection**: Scans folders for matching RDF/TXT files
- **Rich Markdown Output**: Generates well-formatted reports with reaction details
- **CAS Number Mapping**: Automatically loads and applies CAS number mappings
- **Reaction Classification**: Categorizes reactions as Buchwald, Ullmann, or Other
- **Summary Statistics**: Provides overview of reaction types and yields
- **Dual Interface**: Both GUI and command-line interfaces available

## Installation

### Requirements

- Python 3.8+
- PyQt6 or PySide6
- Required Python modules (from this project):
  - `process_reactions.py`

### Setup

1. Ensure you have Python installed
2. Install PyQt6: `pip install PyQt6`
3. Place `reaction_markdown_generator.py` in your SciFinder data processing folder

## Usage

### GUI Mode (Recommended)

Run the application with GUI:
```bash
python reaction_markdown_generator.py
```

Or use the batch script on Windows:
```bash
run_markdown_generator.bat
```

**GUI Steps:**
1. Click "Browse Folder" to select a folder containing RDF/TXT pairs
2. Choose an output location for the markdown report
3. Click "Generate Report"
4. Monitor progress in the text area
5. Open the generated markdown file when complete

### Command Line Mode

For batch processing or automation:
```bash
python reaction_markdown_generator.py --folder "path/to/rdf_txt_folder" --output "report.md"
```

**Examples:**
```bash
# Process Ullmann dataset
python reaction_markdown_generator.py --folder "dataset/Ullman/2020-2024" --output "ullmann_reactions.md"

# Process Buchwald dataset
python reaction_markdown_generator.py --folder "dataset/Buchwald/2021-2024" --output "buchwald_reactions.md"

# Process Amide formation dataset
python reaction_markdown_generator.py --folder "dataset/Amide formation/2021-2024" --output "amide_reactions.md"
```

### Windows Batch Script

The included `run_markdown_generator.bat` provides easy access:

**GUI Mode:**
```cmd
run_markdown_generator.bat
```

**CLI Mode:**
```cmd
run_markdown_generator.bat "dataset\Ullman\2020-2024" "ullmann_report.md"
```

## Output Format

The generated markdown report includes:

### Summary Section
- Total reaction count
- Reaction type distribution (Buchwald, Ullmann, Other)
- Yield statistics

### Individual Reactions
For each reaction:
- **Reaction ID and Type**
- **Full Catalytic System**: Complete list of catalysts/ligands with CAS numbers
- **Catalyst Core**: Metal precursors and core catalysts
- **Generic Catalyst**: Metal type classification (Cu, Pd, etc.)
- **Ligands**: Supporting ligands with CAS numbers
- **Reagents**: With roles (BASE, OX, NUC, etc.) and CAS numbers
- **Solvents**: With CAS numbers
- **Reaction Conditions**: Temperature, time, yield
- **SMILES**: Reactant and product structures (if available)
- **Reference**: Literature citation

### Example Output

```markdown
## Reaction 31-031-CAS-21678191

**Type:** Ullmann

**Full Catalytic System:**
  - N,N′-Dimethylethylenediamine (CAS: 110-70-3)
  - Cupric acetate (CAS: 142-71-2)

**Catalyst Core:**
  - Cupric acetate (CAS: 142-71-2)

**Generic Catalyst:** Cu(II)

**Ligands:**
  - N,N′-Dimethylethylenediamine (CAS: 110-70-3)

**Reagents:**
  - Tripotassium phosphate (CAS: 7778-53-2) - Role: BASE

**Solvents:**
  - Dimethylformamide (CAS: 68-12-2)

**Reaction Conditions:**
  - Temperature: 150.0°C
  - Time: 12.0 hours
  - Yield: 68%

**SMILES:**
  - Reactants: `C1CCNC1.O=C(Cc1c(C(F)(F)F)nc2ccc(Cl)nn12)Nc1cccc(F)c1`
  - Products: `O=C(Cc1c(C(F)(F)F)nc2ccc(-n3cccc3)nn12)Nc1cccc(F)c1`

**Reference:** Journal of Medicinal Chemistry (2021), 64(1), 234-261. | Smith, J.; et al | Journal of Medicinal Chemistry (2021), 64(1), 234-261.
```

## File Structure

After running the tool, you'll have:
- Input folder with RDF/TXT pairs
- Generated markdown report (`.md` file)
- Automatically loaded CAS mapping files (if present)

## CAS Mapping

The tool automatically loads CAS mapping files from:
- `Buchwald/cas_dictionary.csv`
- `Ullman/新建文件夹/ullmann_cas_to_name_mapping.csv` 
- Local files: `cas_dictionary.csv`, `cas_mapping.csv` in the input folder

## Troubleshooting

### Common Issues

1. **No RDF/TXT pairs found**
   - Ensure files have matching base names (e.g., `Reaction_2024-1.rdf` and `Reaction_2024-1.txt`)
   - Check file extensions are exactly `.rdf` and `.txt`

2. **Missing dependencies**
   - Install PyQt6: `pip install PyQt6`
   - Ensure `process_reactions.py` is in the same folder

3. **Empty report**
   - Check that RDF/TXT files contain valid reaction data
   - Verify file encoding (should be UTF-8)

4. **SMILES warnings**
   - RDKit warnings about molecule structures are normal
   - They don't affect the report generation

### Performance Notes

- Large datasets (1000+ reactions) may take several minutes to process
- Progress is displayed in real-time
- Memory usage scales with dataset size

## Integration

This tool integrates with the existing SciFinder data processing pipeline:
- Uses the same parsing logic as `process_reactions.py`
- Compatible with existing CAS mapping files
- Can be used alongside `Scifinder_data_processer.py`

## License

Part of the SciFinder Data Processing toolkit.
