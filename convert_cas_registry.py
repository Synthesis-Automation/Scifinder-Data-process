#!/usr/bin/env python3
"""
Convert CAS registry CSV files to JSONL format for better data structure handling.
"""

import csv
import json
import os
from typing import Dict, List, Any, Optional

def csv_to_jsonl(csv_path: str, jsonl_path: str, format_type: str = "detailed") -> None:
    """
    Convert CSV CAS registry to JSONL format.
    
    Args:
        csv_path: Path to input CSV file
        jsonl_path: Path to output JSONL file
        format_type: "detailed" for cas_dictionary.csv, "simple" for comprehensive_cas_registry.csv
    """
    with open(csv_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        with open(jsonl_path, 'w', encoding='utf-8') as jsonl_file:
            for row in reader:
                if format_type == "detailed":
                    # Format for cas_dictionary.csv
                    entry = {
                        "cas": row.get("CAS", "").strip(),
                        "name": row.get("Name", "").strip(),
                        "generic_core": row.get("GenericCore", "").strip() or None,
                        "role": row.get("Role", "").strip() or None,
                        "category_hint": row.get("CategoryHint", "").strip() or None,
                        "token": row.get("Token", "").strip() or None,
                        "source": "cas_dictionary"
                    }
                else:
                    # Format for comprehensive_cas_registry.csv
                    entry = {
                        "cas": row.get("cas_number", "").strip(),
                        "name": row.get("compound_name", "").strip(),
                        "compound_type": row.get("compound_type", "").strip(),
                        "source": "comprehensive_registry"
                    }
                
                # Only write non-empty entries
                if entry["cas"] and entry["name"]:
                    jsonl_file.write(json.dumps(entry, ensure_ascii=False) + '\n')

def merge_jsonl_files(detailed_jsonl: str, simple_jsonl: str, merged_jsonl: str) -> None:
    """
    Merge the detailed and simple JSONL files into a unified registry.
    """
    cas_registry: Dict[str, Dict[str, Any]] = {}
    
    # Load detailed entries first (cas_dictionary)
    if os.path.exists(detailed_jsonl):
        with open(detailed_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line.strip())
                cas = entry["cas"]
                cas_registry[cas] = {
                    "cas": cas,
                    "name": entry["name"],
                    "generic_core": entry.get("generic_core"),
                    "role": entry.get("role"),
                    "category_hint": entry.get("category_hint"),
                    "token": entry.get("token"),
                    "compound_type": None,  # Will be filled from comprehensive if available
                    "sources": ["cas_dictionary"]
                }
    
    # Merge with comprehensive registry
    if os.path.exists(simple_jsonl):
        with open(simple_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line.strip())
                cas = entry["cas"]
                
                if cas in cas_registry:
                    # Update existing entry
                    cas_registry[cas]["compound_type"] = entry["compound_type"]
                    if "comprehensive_registry" not in cas_registry[cas]["sources"]:
                        cas_registry[cas]["sources"].append("comprehensive_registry")
                else:
                    # Add new entry from comprehensive registry
                    cas_registry[cas] = {
                        "cas": cas,
                        "name": entry["name"],
                        "generic_core": None,
                        "role": None,
                        "category_hint": None,
                        "token": None,
                        "compound_type": entry["compound_type"],
                        "sources": ["comprehensive_registry"]
                    }
    
    # Write merged registry
    with open(merged_jsonl, 'w', encoding='utf-8') as f:
        for cas in sorted(cas_registry.keys()):
            f.write(json.dumps(cas_registry[cas], ensure_ascii=False) + '\n')

def load_cas_registry_jsonl(jsonl_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load CAS registry from JSONL format.
    Returns dictionary compatible with existing process_reactions.py format.
    """
    registry = {}
    
    if not os.path.exists(jsonl_path):
        return registry
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            cas = entry["cas"]
            
            # Convert to format expected by process_reactions.py
            registry[cas] = {
                "Name": entry["name"],
                "GenericCore": entry.get("generic_core") or "",
                "Role": entry.get("role") or "",
                "CategoryHint": entry.get("category_hint") or "",
                "Token": entry.get("token") or ""
            }
    
    return registry

def main():
    """Convert existing CSV files to JSONL format."""
    
    # Convert individual files
    if os.path.exists("cas_dictionary.csv"):
        print("Converting cas_dictionary.csv to JSONL...")
        csv_to_jsonl("cas_dictionary.csv", "cas_dictionary.jsonl", "detailed")
    
    if os.path.exists("comprehensive_cas_registry.csv"):
        print("Converting comprehensive_cas_registry.csv to JSONL...")
        csv_to_jsonl("comprehensive_cas_registry.csv", "comprehensive_cas_registry.jsonl", "simple")
    
    # Create merged registry
    print("Creating merged CAS registry...")
    merge_jsonl_files("cas_dictionary.jsonl", "comprehensive_cas_registry.jsonl", "cas_registry_merged.jsonl")
    
    # Test loading
    print("Testing JSONL loading...")
    registry = load_cas_registry_jsonl("cas_registry_merged.jsonl")
    print(f"Loaded {len(registry)} entries from merged JSONL")
    
    # Show sample entries
    print("\nSample entries:")
    for i, (cas, info) in enumerate(list(registry.items())[:5]):
        print(f"  {cas}: {info['Name']} ({info.get('Role', 'N/A')})")
    
    print("\nConversion complete!")
    print("Files created:")
    print("  - cas_dictionary.jsonl")
    print("  - comprehensive_cas_registry.jsonl")
    print("  - cas_registry_merged.jsonl (unified registry)")

if __name__ == "__main__":
    main()
