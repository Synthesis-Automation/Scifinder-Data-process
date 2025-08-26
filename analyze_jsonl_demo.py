#!/usr/bin/env python3
"""
JSONL Analysis Demonstration
Shows practical examples of analyzing chemical reaction data in JSONL format
"""

import json
import pandas as pd
from collections import Counter, defaultdict
import os

def analyze_jsonl_reactions(jsonl_file):
    """Demonstrate various analysis techniques on JSONL reaction data."""
    
    if not os.path.exists(jsonl_file):
        print(f"JSONL file not found: {jsonl_file}")
        return
    
    print(f"🔬 Analyzing reaction data from: {jsonl_file}")
    
    # Load data
    reactions = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            reactions.append(json.loads(line))
    
    print(f"📊 Loaded {len(reactions)} reactions")
    
    # 1. Basic Statistics
    print(f"\n📈 Basic Statistics:")
    reaction_types = Counter(r['reaction_type'] for r in reactions)
    for rtype, count in reaction_types.items():
        percentage = (count / len(reactions)) * 100
        print(f"  - {rtype}: {count} reactions ({percentage:.1f}%)")
    
    # 2. Yield Analysis
    yields = [r['conditions']['yield_pct'] for r in reactions if r['conditions']['yield_pct'] is not None]
    if yields:
        print(f"\n📊 Yield Analysis:")
        print(f"  - Average yield: {sum(yields)/len(yields):.1f}%")
        print(f"  - Median yield: {sorted(yields)[len(yields)//2]:.1f}%")
        print(f"  - Best yield: {max(yields):.1f}%")
        print(f"  - Worst yield: {min(yields):.1f}%")
        print(f"  - Reactions with yield data: {len(yields)}/{len(reactions)}")
    
    # 3. Catalyst Analysis
    print(f"\n⚗️ Catalyst Analysis:")
    catalyst_metals = Counter()
    catalyst_counts = []
    
    for reaction in reactions:
        # Count catalyst cores per reaction
        cores = reaction['catalyst']['core']
        catalyst_counts.append(len(cores))
        
        # Count metal types
        for metal in reaction['catalyst']['generic']:
            catalyst_metals[metal] += 1
    
    print(f"  - Average catalysts per reaction: {sum(catalyst_counts)/len(catalyst_counts):.1f}")
    print(f"  - Most common metals:")
    for metal, count in catalyst_metals.most_common(5):
        print(f"    {metal}: {count} reactions")
    
    # 4. Temperature Analysis
    temperatures = [r['conditions']['temperature_c'] for r in reactions if r['conditions']['temperature_c'] is not None]
    if temperatures:
        print(f"\n🌡️ Temperature Analysis:")
        print(f"  - Average temperature: {sum(temperatures)/len(temperatures):.1f}°C")
        print(f"  - Temperature range: {min(temperatures):.1f}°C - {max(temperatures):.1f}°C")
        print(f"  - Reactions with temperature data: {len(temperatures)}/{len(reactions)}")
    
    # 5. Solvent Analysis
    print(f"\n🧪 Solvent Analysis:")
    solvent_counter = Counter()
    for reaction in reactions:
        for solvent in reaction['solvents']:
            solvent_name = solvent['name']
            solvent_counter[solvent_name] += 1
    
    print(f"  - Most common solvents:")
    for solvent, count in solvent_counter.most_common(10):
        percentage = (count / len(reactions)) * 100
        print(f"    {solvent}: {count} reactions ({percentage:.1f}%)")
    
    # 6. Reagent Role Analysis
    print(f"\n🧬 Reagent Role Analysis:")
    role_counter = Counter()
    for reaction in reactions:
        for reagent in reaction['reagents']:
            role_counter[reagent['role']] += 1
    
    print(f"  - Reagent roles distribution:")
    for role, count in role_counter.most_common():
        print(f"    {role}: {count} occurrences")
    
    # 7. DOI and Reference Analysis
    print(f"\n📚 Reference Analysis:")
    reactions_with_doi = sum(1 for r in reactions if r['reference']['doi'])
    unique_dois = len(set(r['reference']['doi'] for r in reactions if r['reference']['doi']))
    
    print(f"  - Reactions with DOI: {reactions_with_doi}/{len(reactions)} ({(reactions_with_doi/len(reactions)*100):.1f}%)")
    print(f"  - Unique publications: {unique_dois}")
    
    # Year analysis from DOI/citation
    years = []
    for reaction in reactions:
        citation = reaction['reference']['citation']
        # Simple year extraction from citation
        import re
        year_match = re.search(r'\((\d{4})\)', citation)
        if year_match:
            years.append(int(year_match.group(1)))
    
    if years:
        year_counter = Counter(years)
        print(f"  - Publication years:")
        for year in sorted(year_counter.keys())[-5:]:  # Last 5 years
            print(f"    {year}: {year_counter[year]} reactions")
    
    # 8. Original Text Preservation Analysis
    print(f"\n📝 Original Text Analysis:")
    text_lengths = [len(r['original_text']) for r in reactions]
    reactions_with_text = sum(1 for length in text_lengths if length > 0)
    
    print(f"  - Reactions with original text: {reactions_with_text}/{len(reactions)}")
    if text_lengths:
        print(f"  - Average original text lines: {sum(text_lengths)/len(text_lengths):.1f}")
        print(f"  - Max original text lines: {max(text_lengths)}")
    
    # 9. Data Quality Metrics
    print(f"\n✅ Data Quality Metrics:")
    complete_reactions = 0
    for reaction in reactions:
        has_catalyst = len(reaction['catalyst']['core']) > 0
        has_reagents = len(reaction['reagents']) > 0
        has_conditions = any([
            reaction['conditions']['temperature_c'] is not None,
            reaction['conditions']['time_h'] is not None,
            reaction['conditions']['yield_pct'] is not None
        ])
        has_smiles = bool(reaction['smiles']['reactants'] and reaction['smiles']['products'])
        
        if has_catalyst and has_reagents and has_conditions and has_smiles:
            complete_reactions += 1
    
    print(f"  - Complete reactions (catalyst + reagents + conditions + SMILES): {complete_reactions}/{len(reactions)} ({(complete_reactions/len(reactions)*100):.1f}%)")
    
    return reactions

def demonstrate_pandas_analysis(jsonl_file):
    """Show how to use pandas for more advanced analysis."""
    
    if not os.path.exists(jsonl_file):
        print(f"JSONL file not found: {jsonl_file}")
        return
    
    print(f"\n🐼 Pandas Analysis Demonstration:")
    
    # Load into pandas
    reactions = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            reactions.append(json.loads(line))
    
    # Normalize to DataFrame
    df = pd.json_normalize(reactions)
    
    print(f"📊 DataFrame shape: {df.shape}")
    print(f"📋 Columns: {len(df.columns)}")
    
    # Example analysis: Yield vs Temperature correlation
    if 'conditions.yield_pct' in df.columns and 'conditions.temperature_c' in df.columns:
        temp_yield_df = df[['conditions.temperature_c', 'conditions.yield_pct']].dropna()
        if len(temp_yield_df) > 10:
            correlation = temp_yield_df['conditions.temperature_c'].corr(temp_yield_df['conditions.yield_pct'])
            print(f"🔗 Temperature-Yield correlation: {correlation:.3f}")
    
    # Group by reaction type and analyze yields
    if 'reaction_type' in df.columns and 'conditions.yield_pct' in df.columns:
        yield_by_type = df.groupby('reaction_type')['conditions.yield_pct'].agg(['count', 'mean', 'std', 'min', 'max'])
        print(f"\n📈 Yield statistics by reaction type:")
        print(yield_by_type.round(1))

if __name__ == "__main__":
    # Test with the manual JSONL file we created
    test_file = "test_manual.jsonl"
    
    if os.path.exists(test_file):
        print("🧪 Running analysis on test JSONL data...")
        reactions_data = analyze_jsonl_reactions(test_file)
        demonstrate_pandas_analysis(test_file)
    else:
        print(f"❌ Test file {test_file} not found!")
        print("💡 Run the test_manual_jsonl.py script first to generate test data.")
        
    # Look for larger JSONL files
    jsonl_files = [f for f in os.listdir('.') if f.endswith('.jsonl') and os.path.getsize(f) > 100]
    if jsonl_files:
        print(f"\n📁 Found larger JSONL files for analysis:")
        for file in jsonl_files:
            size = os.path.getsize(file)
            print(f"  - {file}: {size:,} bytes")
            
        # Offer to analyze the largest one
        largest_file = max(jsonl_files, key=os.path.getsize)
        print(f"\n🎯 Could analyze: {largest_file}")
        print(f"💡 To analyze: python {__file__} # then modify to use {largest_file}")
    else:
        print(f"\n💡 No large JSONL files found. Generate full reports first.")
