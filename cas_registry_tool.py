#!/usr/bin/env python3
"""
CAS Number Validation and Registry Tool

This tool provides comprehensive CAS number validation, correction, and lookup functionality.
It can be used to build and maintain a reliable CAS registry for chemical compounds.

Features:
- CAS number format validation
- Checksum verification
- Online lookup capabilities (when API keys are available)
- Manual correction database
- Compound type classification
- Batch validation and correction

Usage:
    python cas_registry_tool.py --validate "123-45-6"
    python cas_registry_tool.py --lookup "6737-42-4"
    python cas_registry_tool.py --batch-validate input.csv
    python cas_registry_tool.py --build-registry folder_with_cas_maps
"""

import argparse
import csv
import json
import re
import sys
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Try to import requests for online lookup
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: 'requests' not available. Online lookup disabled.")


class ComprehensiveCASRegistry:
    """Enhanced CAS registry with validation, correction, and online lookup."""
    
    def __init__(self):
        self.manual_corrections = self._load_manual_corrections()
        self.compound_types = self._load_compound_types()
        self.cas_cache = {}
        self.api_keys = {}  # For future API integration
        
    def _load_manual_corrections(self) -> Dict[str, str]:
        """Load manual CAS corrections from known issues."""
        return {
            # Your specific example
            "6737-42-4": "1,3-Bis(diphenylphosphino)propane",
            "7787-70-4": "Copper(I) bromide",
            
            # Common catalyst cores
            "142-71-2": "Copper(II) acetate",
            "7681-65-4": "Copper(I) iodide", 
            "7758-89-6": "Copper(I) chloride",
            "1317-39-1": "Copper(I) oxide",
            "7447-39-4": "Copper(II) chloride",
            "1122-58-3": "4-(Dimethylamino)pyridine",
            
            # Common phosphine ligands
            "2622-05-1": "Triphenylphosphine",
            "1663-45-2": "1,1'-Bis(diphenylphosphino)ferrocene",
            "13991-08-7": "1,2-Bis(diphenylphosphino)ethane",
            "1663-45-2": "dppf",
            
            # Common nitrogen ligands
            "110-70-3": "N,N'-Dimethylethylenediamine",
            "366-18-7": "2,2'-Bipyridine",
            "66-71-7": "1,10-Phenanthroline",
            "1484-13-5": "trans-N,N'-Dimethylcyclohexane-1,2-diamine",
            
            # Common solvents
            "68-12-2": "Dimethylformamide",
            "64-17-5": "Ethanol",
            "108-88-3": "Toluene",
            "107-06-2": "1,2-Dichloroethane",
            "67-68-5": "Dimethyl sulfoxide",
            "109-99-9": "Tetrahydrofuran",
            "75-09-2": "Dichloromethane",
            "71-43-2": "Benzene",
            "100-42-5": "Styrene",
            
            # Common bases and reagents
            "584-08-7": "Potassium carbonate",
            "534-17-8": "Cesium carbonate", 
            "497-19-8": "Sodium carbonate",
            "7778-53-2": "Tripotassium phosphate",
            "121-44-8": "Triethylamine",
            "7446-70-0": "Aluminum chloride",
            "7782-44-7": "Oxygen",
            "7732-18-5": "Water",
            
            # Common oxidants
            "128-09-6": "N-Chlorosuccinimide",
            "110-05-4": "tert-Butyl peroxide",
            "534-16-7": "Silver carbonate",
        }
    
    def _load_compound_types(self) -> Dict[str, str]:
        """Load compound type classifications."""
        return {
            # Palladium catalysts
            "7647-10-1": "catalyst_core",  # PdCl2
            "32005-36-0": "catalyst_core", # Pd(dba)2
            "51364-51-3": "catalyst_core", # Pd2(dba)3
            
            # Copper catalysts  
            "142-71-2": "catalyst_core",   # Cu(OAc)2
            "7681-65-4": "catalyst_core",  # CuI
            "7758-89-6": "catalyst_core",  # CuCl
            "1317-39-1": "catalyst_core",  # Cu2O
            "7447-39-4": "catalyst_core",  # CuCl2
            "7787-70-4": "catalyst_core",  # CuBr
            
            # Phosphine ligands
            "6737-42-4": "ligand",         # dppp
            "2622-05-1": "ligand",         # PPh3
            "1663-45-2": "ligand",         # dppf
            "13991-08-7": "ligand",        # dppe
            "1663-45-2": "ligand",         # dppf
            
            # Nitrogen ligands
            "110-70-3": "ligand",          # DMEDA
            "366-18-7": "ligand",          # bpy
            "66-71-7": "ligand",           # phen
            "1122-58-3": "ligand",         # DMAP (can be ligand or catalyst)
            
            # Bases
            "584-08-7": "base",            # K2CO3
            "534-17-8": "base",            # Cs2CO3
            "497-19-8": "base",            # Na2CO3
            "7778-53-2": "base",           # K3PO4
            "121-44-8": "base",            # Et3N
            
            # Solvents
            "68-12-2": "solvent",          # DMF
            "64-17-5": "solvent",          # EtOH
            "108-88-3": "solvent",         # Toluene
            "109-99-9": "solvent",         # THF
            "75-09-2": "solvent",          # DCM
            "67-68-5": "solvent",          # DMSO
        }
    
    def validate_cas_format(self, cas: str) -> bool:
        """Validate CAS number format (XXXXX-XX-X)."""
        if not cas:
            return False
        pattern = r'^\d{2,7}-\d{2}-\d$'
        return bool(re.match(pattern, cas.strip()))
    
    def calculate_cas_checksum(self, cas: str) -> bool:
        """Validate CAS number checksum."""
        try:
            digits = cas.replace('-', '')
            if len(digits) < 3:
                return False
            
            check_digit = int(digits[-1])
            body_digits = [int(d) for d in digits[:-1]]
            
            total = 0
            weight = 1
            for digit in reversed(body_digits):
                total += digit * weight
                weight += 1
            
            return (total % 10) == check_digit
        except (ValueError, IndexError):
            return False
    
    def lookup_pubchem(self, cas: str) -> Optional[Dict[str, Any]]:
        """Look up compound information via PubChem API."""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            # PubChem REST API
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                    props = data['PropertyTable']['Properties'][0]
                    return {
                        'name': props.get('IUPACName', ''),
                        'formula': props.get('MolecularFormula', ''),
                        'molecular_weight': props.get('MolecularWeight', ''),
                        'source': 'PubChem'
                    }
        except Exception as e:
            print(f"PubChem lookup failed for {cas}: {e}")
        
        return None
    
    def lookup_chemspider(self, cas: str) -> Optional[Dict[str, Any]]:
        """Look up compound via ChemSpider API (requires API key)."""
        # Placeholder for ChemSpider integration
        # Would require API key from RSC
        return None
    
    def validate_and_correct(self, name: str, cas: str) -> Tuple[str, str, List[str]]:
        """Validate and correct a compound name/CAS pair."""
        warnings = []
        corrected_name = name
        corrected_cas = cas
        
        # Basic CAS validation
        if not self.validate_cas_format(cas):
            if cas:
                warnings.append(f"Invalid CAS format: {cas}")
            return corrected_name, corrected_cas, warnings
        
        # Checksum validation
        if not self.calculate_cas_checksum(cas):
            warnings.append(f"Invalid CAS checksum: {cas}")
        
        # Manual correction lookup
        if cas in self.manual_corrections:
            correct_name = self.manual_corrections[cas]
            if name.lower() != correct_name.lower():
                warnings.append(f"Name correction: '{name}' → '{correct_name}' for CAS {cas}")
                corrected_name = correct_name
        
        # Online lookup for unknown compounds
        elif name == cas or not name:  # CAS-only entry
            online_result = self.lookup_pubchem(cas)
            if online_result and online_result['name']:
                corrected_name = online_result['name']
                warnings.append(f"Retrieved name from PubChem: {corrected_name}")
        
        return corrected_name, corrected_cas, warnings
    
    def get_compound_type(self, cas: str) -> Optional[str]:
        """Get the compound type classification."""
        return self.compound_types.get(cas)
    
    def batch_validate_csv(self, input_file: str, output_file: str) -> None:
        """Validate and correct a CSV file with CAS numbers."""
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        corrected_rows = []
        all_warnings = []
        
        for row in rows:
            cas = row.get('CAS', '').strip()
            name = row.get('Name', '').strip()
            
            corrected_name, corrected_cas, warnings = self.validate_and_correct(name, cas)
            
            # Update row
            row['Name'] = corrected_name
            row['CAS'] = corrected_cas
            row['CompoundType'] = self.get_compound_type(cas) or ''
            row['Warnings'] = '; '.join(warnings) if warnings else ''
            
            corrected_rows.append(row)
            all_warnings.extend(warnings)
        
        # Write corrected file
        if corrected_rows:
            fieldnames = list(corrected_rows[0].keys())
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(corrected_rows)
        
        print(f"Processed {len(corrected_rows)} compounds")
        print(f"Total warnings: {len(all_warnings)}")
        if all_warnings:
            print("\nSample warnings:")
            for warning in all_warnings[:10]:
                print(f"  - {warning}")
    
    def build_registry_from_folder(self, folder_path: str, output_file: str) -> None:
        """Build a comprehensive registry from CAS mapping files in a folder."""
        folder = Path(folder_path)
        all_compounds = {}
        
        # Find all CSV files
        csv_files = list(folder.glob('**/*.csv'))
        print(f"Found {len(csv_files)} CSV files")
        
        for csv_file in csv_files:
            print(f"Processing: {csv_file}")
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cas = row.get('CAS', '').strip()
                        name = row.get('Name', '').strip()
                        
                        if cas and self.validate_cas_format(cas):
                            corrected_name, corrected_cas, warnings = self.validate_and_correct(name, cas)
                            
                            all_compounds[cas] = {
                                'CAS': corrected_cas,
                                'Name': corrected_name,
                                'OriginalName': name,
                                'CompoundType': self.get_compound_type(cas) or '',
                                'Source': str(csv_file.name),
                                'Warnings': '; '.join(warnings) if warnings else '',
                                'HasChecksum': self.calculate_cas_checksum(cas)
                            }
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")
        
        # Write comprehensive registry
        if all_compounds:
            fieldnames = ['CAS', 'Name', 'OriginalName', 'CompoundType', 'Source', 'Warnings', 'HasChecksum']
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for compound in all_compounds.values():
                    writer.writerow(compound)
        
        print(f"Built registry with {len(all_compounds)} unique compounds")
        print(f"Registry saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="CAS Number Validation and Registry Tool")
    parser.add_argument('--validate', help='Validate a single CAS number')
    parser.add_argument('--lookup', help='Look up information for a CAS number')
    parser.add_argument('--batch-validate', help='Validate and correct a CSV file')
    parser.add_argument('--output', help='Output file for batch operations')
    parser.add_argument('--build-registry', help='Build registry from folder of CAS mapping files')
    
    args = parser.parse_args()
    
    registry = ComprehensiveCASRegistry()
    
    if args.validate:
        cas = args.validate.strip()
        print(f"Validating CAS: {cas}")
        
        format_valid = registry.validate_cas_format(cas)
        checksum_valid = registry.calculate_cas_checksum(cas) if format_valid else False
        
        print(f"  Format valid: {format_valid}")
        print(f"  Checksum valid: {checksum_valid}")
        
        if cas in registry.manual_corrections:
            print(f"  Corrected name: {registry.manual_corrections[cas]}")
        
        compound_type = registry.get_compound_type(cas)
        if compound_type:
            print(f"  Compound type: {compound_type}")
    
    elif args.lookup:
        cas = args.lookup.strip()
        print(f"Looking up CAS: {cas}")
        
        # Manual correction
        if cas in registry.manual_corrections:
            print(f"  Name (manual): {registry.manual_corrections[cas]}")
        
        # Online lookup
        online_result = registry.lookup_pubchem(cas)
        if online_result:
            print(f"  Name (PubChem): {online_result['name']}")
            print(f"  Formula: {online_result['formula']}")
            print(f"  MW: {online_result['molecular_weight']}")
        
        compound_type = registry.get_compound_type(cas)
        if compound_type:
            print(f"  Type: {compound_type}")
    
    elif args.batch_validate:
        if not args.output:
            args.output = args.batch_validate.replace('.csv', '_corrected.csv')
        
        print(f"Batch validating: {args.batch_validate}")
        registry.batch_validate_csv(args.batch_validate, args.output)
        print(f"Results saved to: {args.output}")
    
    elif args.build_registry:
        if not args.output:
            args.output = "comprehensive_cas_registry.csv"
        
        print(f"Building registry from: {args.build_registry}")
        registry.build_registry_from_folder(args.build_registry, args.output)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
