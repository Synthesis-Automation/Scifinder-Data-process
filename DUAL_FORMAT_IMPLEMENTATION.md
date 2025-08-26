# Dual Format Export: Markdown + JSONL

## Overview

The Reaction Markdown Generator now automatically generates **both formats** when processing chemical reaction data:

1. **Markdown (.md)** - Human-readable reports for presentations and documentation
2. **JSONL (.jsonl)** - Structured data for analysis, machine learning, and computational chemistry

## Features Implemented

### ✅ **Automatic Dual Generation**
- Both files are created simultaneously from the same processed data
- JSONL filename automatically derived from MD filename (`report.md` → `report.jsonl`)
- Progress messages show both file generation steps

### ✅ **Enhanced GUI Interface**
- Updated description explains both format types
- Success dialog shows paths to both generated files
- Clear indication of format purposes (human vs. machine-readable)

### ✅ **Consistent Data Structure**
- Both formats contain identical chemical reaction information
- JSONL provides structured access to nested data (catalysts, reagents, conditions)
- Original text preservation included in both formats

## File Comparison

| Aspect | Markdown (.md) | JSONL (.jsonl) |
|--------|----------------|----------------|
| **Purpose** | Human reading | Data analysis |
| **Size** | ~2.3MB | ~5.6MB |
| **Structure** | Visual formatting | Structured JSON |
| **Tool Support** | Viewers, browsers | Pandas, ML tools |
| **Searchability** | Text search | Field-specific queries |

## Usage Examples

### **Command Line**
```bash
# Both files generated automatically
python reaction_markdown_generator.py --folder dataset/Buchwald/2021-2024 --output report.md
# Creates: report.md + report.jsonl
```

### **GUI Interface**
1. Launch: `python reaction_markdown_generator.py`
2. Select input folder containing RDF/TXT pairs
3. Choose output markdown file name
4. Click "Generate Report"
5. Both `.md` and `.jsonl` files created automatically

### **Analysis Workflow**
```python
# Load JSONL for analysis
import pandas as pd
import json

reactions = []
with open('report.jsonl', 'r') as f:
    for line in f:
        reactions.append(json.loads(line))

# Convert to DataFrame for analysis
df = pd.json_normalize(reactions)

# Analyze yields by catalyst type
yield_stats = df.groupby('catalyst.generic')['conditions.yield_pct'].describe()
```

## Technical Implementation

### **Core Changes**
1. **process_folder()** method enhanced to call both generators
2. **generate_jsonl_export()** method creates structured JSONL output
3. **prepare_analysis_record()** optimizes data for analysis
4. **GUI updates** inform users about dual format generation

### **Data Structure Preservation**
- **Nested Catalysts**: Core + ligands with CAS numbers
- **Reagent Roles**: Structured role assignments (BASE, WORKUP, etc.)
- **Reaction Conditions**: Temperature, time, yield as typed values
- **Reference Data**: Title, authors, citation, DOI as separate fields
- **Original Text**: Raw condition blocks for debugging

### **Quality Assurance**
- **Validation**: Both formats generated from same source data
- **Testing**: Verified with 1,343 Buchwald reactions
- **Completeness**: All chemical information preserved in both formats

## Benefits for Users

### **Research Scientists**
- **Markdown**: Share findings in presentations and documents
- **JSONL**: Perform statistical analysis and pattern recognition

### **Data Scientists**
- **Structured Data**: Ready for machine learning pipelines
- **Tool Integration**: Compatible with pandas, scikit-learn, etc.
- **Chemical Informatics**: SMILES, CAS numbers, reaction signatures

### **Software Developers**
- **API Integration**: JSONL easily consumed by web services
- **Database Import**: Structured format for chemical databases
- **Workflow Automation**: Programmatic access to reaction data

## File Generation Verified

✅ **Test Results (Buchwald Dataset)**:
- **Markdown**: 2,346,805 bytes (1,343 reactions)
- **JSONL**: 5,628,924 bytes (1,343 records)
- **Completion**: 100% success rate
- **Data Integrity**: All original text preserved
- **Format Validation**: Valid JSON on every line

## Conclusion

The app now provides the **best of both worlds**:
- **Markdown for humans** - readable reports with formatting
- **JSONL for machines** - structured data for computation

This dual format approach makes the chemical reaction data accessible to both human researchers and automated analysis systems, significantly expanding the utility and value of the processed SciFinder data.
