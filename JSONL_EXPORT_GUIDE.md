# JSONL Export Format for Chemical Reaction Analysis

## Overview

The JSONL (JSON Lines) format provides an optimal structure for chemical reaction data analysis, machine learning, and data processing. Each line contains a complete JSON record representing one chemical reaction with structured, analyzable data.

## Why JSONL is Ideal for Chemical Reaction Data

### **1. Technical Advantages**
- **Streaming Processing**: Process large datasets without loading everything into memory
- **Tool Compatibility**: Works seamlessly with pandas, Apache Spark, jq, and ML frameworks
- **Schema Flexibility**: Accommodates varying reaction complexities without rigid columns
- **Parallel Processing**: Each line is independent, enabling easy parallelization

### **2. Data Science Benefits**
- **Nested Structures**: Preserves complex relationships (catalyst systems, reagent roles)
- **Type Safety**: Maintains data types (floats, arrays, objects) unlike CSV
- **Machine Learning Ready**: Direct input to ML pipelines and chemical informatics tools
- **Query Efficiency**: Fast filtering and aggregation with tools like jq or pandas

### **3. Analysis Use Cases**
- **Similarity Analysis**: Compare catalyst systems, reagent combinations, conditions
- **Machine Learning**: Train models on reaction outcomes, catalyst performance
- **Statistical Analysis**: Aggregate yields, reaction times, temperature distributions
- **Pattern Mining**: Discover trends in successful reaction conditions

## JSONL Record Structure

Each JSONL record contains the following structured fields:

### **Core Identifiers**
```json
{
  "reaction_id": "31-172-CAS-23065394",
  "reaction_type": "Buchwald"
}
```

### **Catalytic System (Structured)**
```json
{
  "catalyst": {
    "core": [
      {
        "name": "Tris(dibenzylideneacetone)dipalladium",
        "cas": ""
      }
    ],
    "generic": ["Pd"],
    "ligands": [
      {
        "name": "Tri-tert-butylphosphonium tetrafluoroborate",
        "cas": ""
      }
    ],
    "full_system": [...]
  }
}
```

### **Reagents with Roles**
```json
{
  "reagents": [
    {
      "name": "Sodium tert-butoxide",
      "cas": "865-48-5",
      "role": "BASE"
    }
  ]
}
```

### **Reaction Conditions**
```json
{
  "conditions": {
    "temperature_c": 105.0,
    "time_h": null,
    "yield_pct": 94.0
  }
}
```

### **Chemical Structures**
```json
{
  "smiles": {
    "reactants": "CC1(C)c2ccccc2Nc2ccccc21.CCCCCCCCc1ccc(Br)cc1",
    "products": "CCCCCCCCc1ccc(N2c3ccccc3C(C)(C)c3ccccc32)cc1"
  }
}
```

### **Reference Information**
```json
{
  "reference": {
    "title": "Angewandte Chemie, International Edition (2021), 60(5), 2455-2463.",
    "authors": "Liu, Xinrui; et al",
    "citation": "Angewandte Chemie, International Edition (2021), 60(5), 2455-2463.",
    "doi": "10.1002/anie.202011957",
    "raw": "Full|pipe|separated|format"
  }
}
```

### **Original Text Preservation**
```json
{
  "original_text": [
    "Steps: 1, Yield: 94%",
    "CAS Reaction Number: 31-172-CAS-23065394",
    "1.1|Reagents: Sodium tert-butoxide|",
    "|Catalysts: Tris(dibenzylideneacetone)dipalladium, Tri-tert-butylphosphonium tetrafluoroborate|",
    "|Solvents: Toluene; 105 °C|"
  ]
}
```

## Analysis Examples

### **1. Python with Pandas**
```python
import pandas as pd
import json

# Load JSONL data
reactions = []
with open('buchwald_report.jsonl', 'r') as f:
    for line in f:
        reactions.append(json.loads(line))

df = pd.json_normalize(reactions)

# Analyze yields by catalyst type
yield_analysis = df.groupby('catalyst.generic')['conditions.yield_pct'].describe()
print(yield_analysis)
```

### **2. Command Line with jq**
```bash
# Find reactions with yields > 90%
cat buchwald_report.jsonl | jq 'select(.conditions.yield_pct > 90)'

# Count reactions by temperature ranges
cat buchwald_report.jsonl | jq -r '.conditions.temperature_c' | sort -n

# Extract all DOIs
cat buchwald_report.jsonl | jq -r '.reference.doi' | grep -v ^null
```

### **3. Machine Learning Features**
```python
# Extract features for ML
features = []
for record in reactions:
    feature_row = {
        'catalyst_count': len(record['catalyst']['core']),
        'ligand_count': len(record['catalyst']['ligands']),
        'reagent_count': len(record['reagents']),
        'temperature': record['conditions']['temperature_c'],
        'time': record['conditions']['time_h'],
        'yield': record['conditions']['yield_pct']
    }
    features.append(feature_row)

# Convert to DataFrame for ML
feature_df = pd.DataFrame(features)
```

## File Size and Performance

### **Comparison with Other Formats**
- **Markdown**: 2.3MB (human-readable reports)
- **JSONL**: ~1.5MB (structured data, estimated)
- **CSV**: ~800KB (flattened, loses structure)

### **Performance Benefits**
- **Memory Efficient**: Stream processing without loading full dataset
- **Fast Queries**: JSON parsing is highly optimized
- **Parallel Processing**: Easy to split across multiple cores/machines
- **Tool Integration**: Native support in modern data tools

## Integration with Current Workflow

The JSONL export is automatically generated alongside markdown reports:

```python
# Both files are created automatically
generator.process_folder(folder_path, "report.md")
# Creates:
# - report.md (human-readable)
# - report.jsonl (analysis-ready)
```

## Advanced Analysis Possibilities

### **1. Catalyst Performance Analysis**
- Compare yields across different catalyst systems
- Identify optimal ligand-metal combinations
- Analyze catalyst loading effects

### **2. Reaction Condition Optimization**
- Temperature vs yield correlations
- Time vs conversion relationships
- Solvent effect studies

### **3. Literature Mining**
- Publication trend analysis by year
- Author collaboration networks
- Journal impact assessment

### **4. Chemical Space Exploration**
- SMILES similarity analysis
- Substrate scope mapping
- Product diversity assessment

## Future Extensions

The JSONL format is designed for extensibility:

1. **Computed Properties**: Add molecular descriptors, fingerprints
2. **Experimental Details**: Include additional conditions, purification methods
3. **Economic Data**: Cost analysis, atom economy calculations
4. **Safety Information**: Hazard classifications, safety scores

## Conclusion

JSONL format provides the optimal balance between:
- **Human Readability**: Still readable as structured JSON
- **Machine Processing**: Efficient for analysis and ML
- **Data Preservation**: Maintains all relationships and metadata
- **Tool Compatibility**: Works with modern data science ecosystems

This format transforms the chemical reaction database from a collection of text files into a structured, queryable, analysis-ready dataset perfect for modern chemical informatics and machine learning applications.
