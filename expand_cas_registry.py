#!/usr/bin/env python3
"""
Expand CAS Registry with Common Synthesis Chemicals

This script adds common chemicals used in organic synthesis by:
1. Loading existing registry to avoid duplicates
2. Adding curated lists of common chemicals with verified CAS numbers
3. Categorizing them by compound type
4. Adding appropriate abbreviations
5. Validating CAS number format and checksums

Sources: Common chemicals from synthetic organic chemistry literature,
Merck/Sigma-Aldrich catalogs, and standard reference works.
"""

import json
import re
import os
from typing import Dict, List, Optional, Set
from collections import defaultdict

class CASRegistryExpander:
    """Expand the CAS registry with common synthesis chemicals."""
    
    def __init__(self, registry_file: str = 'cas_registry_merged.jsonl'):
        self.registry_file = registry_file
        self.existing_cas: Set[str] = set()
        self.existing_names: Set[str] = set()
        self.registry_entries: List[Dict] = []
        
        # Load existing registry
        self.load_existing_registry()
        
        # Common chemicals database with verified CAS numbers
        self.common_chemicals = self.build_common_chemicals_database()
    
    def load_existing_registry(self):
        """Load the existing registry to avoid duplicates."""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        self.registry_entries.append(entry)
                        
                        cas = entry.get('cas', '')
                        name = entry.get('name', '')
                        
                        if cas:
                            self.existing_cas.add(cas)
                        if name:
                            self.existing_names.add(name.lower().strip())
                            
                    except json.JSONDecodeError:
                        continue
        
        print(f"Loaded {len(self.registry_entries)} existing entries")
        print(f"Existing CAS numbers: {len(self.existing_cas)}")
        print(f"Existing names: {len(self.existing_names)}")
    
    def validate_cas_format(self, cas: str) -> bool:
        """Validate CAS number format."""
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
    
    def build_common_chemicals_database(self) -> Dict[str, List[Dict]]:
        """Build a comprehensive database of common synthesis chemicals."""
        
        # Organized by compound type for better categorization
        chemicals = {
            'catalyst_core': [
                # Palladium catalysts
                {'cas': '7440-05-3', 'name': 'Palladium', 'abbreviation': 'Pd'},
                {'cas': '14221-01-3', 'name': 'Tetrakis(triphenylphosphine)palladium(0)', 'abbreviation': 'Pd(PPh3)4'},
                {'cas': '31277-98-2', 'name': 'Bis(triphenylphosphine)palladium(II) dichloride', 'abbreviation': 'PdCl2(PPh3)2'},
                {'cas': '28068-96-6', 'name': 'Bis(triphenylphosphine)palladium(II) acetate', 'abbreviation': 'Pd(OAc)2(PPh3)2'},
                {'cas': '3375-31-3', 'name': 'Palladium(II) acetate', 'abbreviation': 'Pd(OAc)2'},
                {'cas': '7647-10-1', 'name': 'Palladium(II) chloride', 'abbreviation': 'PdCl2'},
                {'cas': '51364-51-3', 'name': 'Tris(dibenzylideneacetone)dipalladium(0)', 'abbreviation': 'Pd2(dba)3'},
                
                # Copper catalysts
                {'cas': '7440-50-8', 'name': 'Copper', 'abbreviation': 'Cu'},
                {'cas': '142-71-2', 'name': 'Copper(II) acetate', 'abbreviation': 'Cu(OAc)2'},
                {'cas': '7758-89-6', 'name': 'Copper(I) chloride', 'abbreviation': 'CuCl'},
                {'cas': '7681-65-4', 'name': 'Copper(I) iodide', 'abbreviation': 'CuI'},
                {'cas': '7787-70-4', 'name': 'Copper(I) bromide', 'abbreviation': 'CuBr'},
                {'cas': '7447-39-4', 'name': 'Copper(II) chloride', 'abbreviation': 'CuCl2'},
                {'cas': '10125-13-0', 'name': 'Copper(II) chloride dihydrate', 'abbreviation': 'CuCl2·2H2O'},
                {'cas': '1317-39-1', 'name': 'Copper(I) oxide', 'abbreviation': 'Cu2O'},
                {'cas': '1317-38-0', 'name': 'Copper(II) oxide', 'abbreviation': 'CuO'},
                {'cas': '598-54-9', 'name': 'Copper(II) sulfate', 'abbreviation': 'CuSO4'},
                
                # Other metal catalysts
                {'cas': '7440-33-7', 'name': 'Tungsten', 'abbreviation': 'W'},
                {'cas': '7440-02-0', 'name': 'Nickel', 'abbreviation': 'Ni'},
                {'cas': '7429-90-5', 'name': 'Aluminum', 'abbreviation': 'Al'},
                {'cas': '7440-66-6', 'name': 'Zinc', 'abbreviation': 'Zn'},
                {'cas': '7439-92-1', 'name': 'Lead', 'abbreviation': 'Pb'},
                {'cas': '7440-31-5', 'name': 'Tin', 'abbreviation': 'Sn'},
                {'cas': '7440-22-4', 'name': 'Silver', 'abbreviation': 'Ag'},
                {'cas': '10377-60-3', 'name': 'Magnesium nitrate hexahydrate', 'abbreviation': 'Mg(NO3)2·6H2O'},
            ],
            
            'ligand': [
                # Phosphine ligands
                {'cas': '603-35-0', 'name': 'Triphenylphosphine', 'abbreviation': 'PPh3'},
                {'cas': '6737-42-4', 'name': '1,3-Bis(diphenylphosphino)propane', 'abbreviation': 'dppp'},
                {'cas': '1663-45-2', 'name': '1,1-Bis(diphenylphosphino)ferrocene', 'abbreviation': 'dppf'},
                {'cas': '13991-08-7', 'name': '1,2-Bis(diphenylphosphino)ethane', 'abbreviation': 'dppe'},
                {'cas': '14221-02-4', 'name': '1,3-Bis(diphenylphosphino)propane', 'abbreviation': 'dppp'},
                {'cas': '23582-02-7', 'name': '1,4-Bis(diphenylphosphino)butane', 'abbreviation': 'dppb'},
                {'cas': '1028206-60-1', 'name': 'BrettPhos', 'abbreviation': 'BrettPhos'},
                {'cas': '887919-35-9', 'name': 'RuPhos', 'abbreviation': 'RuPhos'},
                {'cas': '564483-18-7', 'name': 'XPhos', 'abbreviation': 'XPhos'},
                {'cas': '787618-22-8', 'name': 'SPhos', 'abbreviation': 'SPhos'},
                {'cas': '1038-95-5', 'name': 'Tri(p-tolyl)phosphine', 'abbreviation': 'P(p-tol)3'},
                {'cas': '1116-01-4', 'name': 'Tri(2-furyl)phosphine', 'abbreviation': 'P(2-furyl)3'},
                
                # Nitrogen ligands
                {'cas': '366-18-7', 'name': '2,2\'-Bipyridine', 'abbreviation': '2,2\'-bipy'},
                {'cas': '66-71-7', 'name': '1,10-Phenanthroline', 'abbreviation': 'phen'},
                {'cas': '110-70-3', 'name': 'N,N\'-Dimethylethylenediamine', 'abbreviation': 'DMEDA'},
                {'cas': '1928-37-6', 'name': 'N,N,N\',N\'-Tetramethylethylenediamine', 'abbreviation': 'TMEDA'},
                {'cas': '1122-58-3', 'name': '4-(Dimethylamino)pyridine', 'abbreviation': 'DMAP'},
                {'cas': '100-76-5', 'name': '1,4-Diazabicyclo[2.2.2]octane', 'abbreviation': 'DABCO'},
                {'cas': '5807-14-7', 'name': 'trans-1,2-Diaminocyclohexane', 'abbreviation': 'DACH'},
                {'cas': '111-40-0', 'name': 'Diethylenetriamine', 'abbreviation': 'DETA'},
                
                # Other ligands
                {'cas': '108-47-4', 'name': '2,4-Dimethylpyridine', 'abbreviation': '2,4-lutidine'},
                {'cas': '108-48-5', 'name': '2,6-Dimethylpyridine', 'abbreviation': '2,6-lutidine'},
                {'cas': '583-61-9', 'name': '2,4,6-Trimethylpyridine', 'abbreviation': 'collidine'},
            ],
            
            'base': [
                # Inorganic bases
                {'cas': '1310-73-2', 'name': 'Sodium hydroxide', 'abbreviation': 'NaOH'},
                {'cas': '1310-58-3', 'name': 'Potassium hydroxide', 'abbreviation': 'KOH'},
                {'cas': '17194-00-2', 'name': 'Barium hydroxide', 'abbreviation': 'Ba(OH)2'},
                {'cas': '1305-62-0', 'name': 'Calcium hydroxide', 'abbreviation': 'Ca(OH)2'},
                {'cas': '497-19-8', 'name': 'Sodium carbonate', 'abbreviation': 'Na2CO3'},
                {'cas': '584-08-7', 'name': 'Potassium carbonate', 'abbreviation': 'K2CO3'},
                {'cas': '534-17-8', 'name': 'Cesium carbonate', 'abbreviation': 'Cs2CO3'},
                {'cas': '7778-53-2', 'name': 'Tripotassium phosphate', 'abbreviation': 'K3PO4'},
                {'cas': '865-48-5', 'name': 'Sodium tert-butoxide', 'abbreviation': 'NaOtBu'},
                {'cas': '865-47-4', 'name': 'Potassium tert-butoxide', 'abbreviation': 'KOtBu'},
                {'cas': '21564-17-0', 'name': 'Sodium bis(trimethylsilyl)amide', 'abbreviation': 'NaHMDS'},
                {'cas': '1722-73-8', 'name': 'Potassium bis(trimethylsilyl)amide', 'abbreviation': 'KHMDS'},
                
                # Organic bases
                {'cas': '121-44-8', 'name': 'Triethylamine', 'abbreviation': 'TEA'},
                {'cas': '100-97-0', 'name': 'N,N-Diisopropylethylamine', 'abbreviation': 'DIPEA'},
                {'cas': '75-50-3', 'name': 'Trimethylamine', 'abbreviation': 'TMA'},
                {'cas': '110-89-4', 'name': 'Piperidine', 'abbreviation': 'piperidine'},
                {'cas': '109-89-7', 'name': 'Diethylamine', 'abbreviation': 'DEA'},
                {'cas': '108-18-9', 'name': 'Diisopropylamine', 'abbreviation': 'DIPA'},
                {'cas': '7664-41-7', 'name': 'Ammonia', 'abbreviation': 'NH3'},
                {'cas': '1489-57-2', 'name': '2,6-Di-tert-butylpyridine', 'abbreviation': 'DTBP'},
            ],
            
            'solvent': [
                # Polar protic solvents
                {'cas': '64-17-5', 'name': 'Ethanol', 'abbreviation': 'EtOH'},
                {'cas': '67-56-1', 'name': 'Methanol', 'abbreviation': 'MeOH'},
                {'cas': '71-23-8', 'name': '1-Propanol', 'abbreviation': 'PrOH'},
                {'cas': '78-83-1', 'name': '2-Propanol', 'abbreviation': 'iPrOH'},
                {'cas': '71-36-3', 'name': '1-Butanol', 'abbreviation': 'BuOH'},
                {'cas': '75-65-0', 'name': '2-Methyl-2-propanol', 'abbreviation': 'tBuOH'},
                {'cas': '7732-18-5', 'name': 'Water', 'abbreviation': 'H2O'},
                
                # Polar aprotic solvents
                {'cas': '68-12-2', 'name': 'N,N-Dimethylformamide', 'abbreviation': 'DMF'},
                {'cas': '127-19-5', 'name': 'N,N-Dimethylacetamide', 'abbreviation': 'DMAc'},
                {'cas': '872-50-4', 'name': 'N-Methyl-2-pyrrolidinone', 'abbreviation': 'NMP'},
                {'cas': '67-68-5', 'name': 'Dimethyl sulfoxide', 'abbreviation': 'DMSO'},
                {'cas': '75-09-2', 'name': 'Dichloromethane', 'abbreviation': 'DCM'},
                {'cas': '67-66-3', 'name': 'Chloroform', 'abbreviation': 'CHCl3'},
                {'cas': '56-23-5', 'name': 'Carbon tetrachloride', 'abbreviation': 'CCl4'},
                {'cas': '79-01-6', 'name': 'Trichloroethylene', 'abbreviation': 'TCE'},
                {'cas': '107-06-2', 'name': '1,2-Dichloroethane', 'abbreviation': 'DCE'},
                
                # Nonpolar solvents
                {'cas': '110-54-3', 'name': 'n-Hexane', 'abbreviation': 'hexane'},
                {'cas': '142-82-5', 'name': 'n-Heptane', 'abbreviation': 'heptane'},
                {'cas': '111-65-9', 'name': 'n-Octane', 'abbreviation': 'octane'},
                {'cas': '71-43-2', 'name': 'Benzene', 'abbreviation': 'benzene'},
                {'cas': '108-88-3', 'name': 'Toluene', 'abbreviation': 'toluene'},
                {'cas': '100-41-4', 'name': 'Ethylbenzene', 'abbreviation': 'ethylbenzene'},
                {'cas': '106-42-3', 'name': 'p-Xylene', 'abbreviation': 'p-xylene'},
                {'cas': '108-38-3', 'name': 'm-Xylene', 'abbreviation': 'm-xylene'},
                {'cas': '95-47-6', 'name': 'o-Xylene', 'abbreviation': 'o-xylene'},
                
                # Ethers
                {'cas': '60-29-7', 'name': 'Diethyl ether', 'abbreviation': 'Et2O'},
                {'cas': '109-99-9', 'name': 'Tetrahydrofuran', 'abbreviation': 'THF'},
                {'cas': '71-24-9', 'name': '1,2-Dimethoxyethane', 'abbreviation': 'DME'},
                {'cas': '110-71-4', 'name': '1,2-Dimethoxyethane', 'abbreviation': 'DME'},
                {'cas': '629-14-1', 'name': 'Diethylene glycol dimethyl ether', 'abbreviation': 'diglyme'},
                {'cas': '100-66-3', 'name': 'Anisole', 'abbreviation': 'anisole'},
                {'cas': '123-91-1', 'name': '1,4-Dioxane', 'abbreviation': 'dioxane'},
                
                # Other useful solvents
                {'cas': '64-19-7', 'name': 'Acetic acid', 'abbreviation': 'AcOH'},
                {'cas': '79-09-4', 'name': 'Propionic acid', 'abbreviation': 'PrCOOH'},
                {'cas': '75-05-8', 'name': 'Acetonitrile', 'abbreviation': 'MeCN'},
                {'cas': '107-12-0', 'name': 'Propionitrile', 'abbreviation': 'EtCN'},
                {'cas': '109-74-0', 'name': 'Butyronitrile', 'abbreviation': 'PrCN'},
            ],
            
            'activator': [
                # Carbodiimides
                {'cas': '538-75-0', 'name': 'N,N\'-Dicyclohexylcarbodiimide', 'abbreviation': 'DCC'},
                {'cas': '1892-57-5', 'name': '1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide', 'abbreviation': 'EDC'},
                {'cas': '2491-17-0', 'name': 'N,N\'-Diisopropylcarbodiimide', 'abbreviation': 'DIC'},
                {'cas': '148893-10-1', 'name': 'O-(7-Azabenzotriazol-1-yl)-N,N,N\',N\'-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HATU'},
                {'cas': '148893-13-4', 'name': 'O-(1H-6-Chlorobenzotriazole-1-yl)-1,1,3,3-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HCTU'},
                {'cas': '94790-37-1', 'name': 'O-Benzotriazole-N,N,N\',N\'-tetramethyl-uronium-hexafluoro-phosphate', 'abbreviation': 'HBTU'},
                
                # Other activators
                {'cas': '7440-74-6', 'name': 'Indium', 'abbreviation': 'In'},
                {'cas': '78-11-5', 'name': 'Pentaerythritol tetranitrate', 'abbreviation': 'PETN'},
            ],
            
            'amide_additive': [
                {'cas': '2592-95-2', 'name': '1-Hydroxybenzotriazole', 'abbreviation': 'HOBt'},
                {'cas': '123333-53-9', 'name': '1-Hydroxy-7-azabenzotriazole', 'abbreviation': 'HOAt'},
                {'cas': '39968-33-7', 'name': 'N-Hydroxysuccinimide', 'abbreviation': 'NHS'},
                {'cas': '6066-82-6', 'name': '1-Hydroxybenzotriazole hydrate', 'abbreviation': 'HOBt·H2O'},
            ],
            
            'acid': [
                {'cas': '7647-01-0', 'name': 'Hydrochloric acid', 'abbreviation': 'HCl'},
                {'cas': '7664-93-9', 'name': 'Sulfuric acid', 'abbreviation': 'H2SO4'},
                {'cas': '7697-37-2', 'name': 'Nitric acid', 'abbreviation': 'HNO3'},
                {'cas': '7664-38-2', 'name': 'Phosphoric acid', 'abbreviation': 'H3PO4'},
                {'cas': '64-19-7', 'name': 'Acetic acid', 'abbreviation': 'AcOH'},
                {'cas': '79-09-4', 'name': 'Propionic acid', 'abbreviation': 'PrCOOH'},
                {'cas': '144-62-7', 'name': 'Oxalic acid', 'abbreviation': 'oxalic acid'},
                {'cas': '65-85-0', 'name': 'Benzoic acid', 'abbreviation': 'PhCOOH'},
                {'cas': '121-91-5', 'name': 'Isophthalic acid', 'abbreviation': 'isophthalic acid'},
                {'cas': '76-05-1', 'name': 'Trifluoroacetic acid', 'abbreviation': 'TFA'},
                {'cas': '1493-13-6', 'name': 'Trifluoromethanesulfonic acid', 'abbreviation': 'TfOH'},
                {'cas': '7681-57-4', 'name': 'Sodium metabisulfite', 'abbreviation': 'Na2S2O5'},
            ],
            
            'oxidant': [
                {'cas': '7782-44-7', 'name': 'Oxygen', 'abbreviation': 'O2'},
                {'cas': '7722-84-1', 'name': 'Hydrogen peroxide', 'abbreviation': 'H2O2'},
                {'cas': '10049-04-4', 'name': 'Chlorine dioxide', 'abbreviation': 'ClO2'},
                {'cas': '7778-50-9', 'name': 'Potassium dichromate', 'abbreviation': 'K2Cr2O7'},
                {'cas': '10294-33-4', 'name': 'Boron tribromide', 'abbreviation': 'BBr3'},
                {'cas': '865-44-1', 'name': 'tert-Butyl hydroperoxide', 'abbreviation': 'TBHP'},
                {'cas': '94-36-0', 'name': 'Benzoyl peroxide', 'abbreviation': 'BPO'},
                {'cas': '614-45-9', 'name': 'tert-Butyl peroxybenzoate', 'abbreviation': 'TBPB'},
            ],
            
            'reductant': [
                {'cas': '16940-66-2', 'name': 'Sodium borohydride', 'abbreviation': 'NaBH4'},
                {'cas': '25895-60-7', 'name': 'Lithium aluminum hydride', 'abbreviation': 'LiAlH4'},
                {'cas': '7440-66-6', 'name': 'Zinc', 'abbreviation': 'Zn'},
                {'cas': '7439-89-6', 'name': 'Iron', 'abbreviation': 'Fe'},
                {'cas': '7440-50-8', 'name': 'Copper', 'abbreviation': 'Cu'},
                {'cas': '7439-92-1', 'name': 'Lead', 'abbreviation': 'Pb'},
                {'cas': '10102-43-9', 'name': 'Nitric oxide', 'abbreviation': 'NO'},
            ]
        }
        
        return chemicals
    
    def add_chemical(self, cas: str, name: str, abbreviation: str, compound_type: str) -> bool:
        """Add a chemical to the registry if it doesn't already exist."""
        
        # Validate CAS format
        if not self.validate_cas_format(cas):
            print(f"Invalid CAS format: {cas}")
            return False
        
        # Validate CAS checksum
        if not self.calculate_cas_checksum(cas):
            print(f"Invalid CAS checksum: {cas}")
            return False
        
        # Check for duplicates
        if cas in self.existing_cas:
            print(f"CAS {cas} already exists, skipping")
            return False
        
        if name.lower().strip() in self.existing_names:
            print(f"Name '{name}' already exists, skipping")
            return False
        
        # Create entry
        entry = {
            'cas': cas,
            'name': name,
            'abbreviation': abbreviation,
            'generic_core': None,
            'category_hint': None,
            'token': None,
            'compound_type': compound_type,
            'sources': ['web_expansion']
        }
        
        # Add to registry
        self.registry_entries.append(entry)
        self.existing_cas.add(cas)
        self.existing_names.add(name.lower().strip())
        
        return True
    
    def expand_registry(self) -> int:
        """Expand the registry with common chemicals."""
        added_count = 0
        
        for compound_type, chemicals in self.common_chemicals.items():
            print(f"\nAdding {compound_type} compounds...")
            type_count = 0
            
            for chemical in chemicals:
                cas = chemical['cas']
                name = chemical['name']
                abbreviation = chemical['abbreviation']
                
                if self.add_chemical(cas, name, abbreviation, compound_type):
                    added_count += 1
                    type_count += 1
                    print(f"  Added: {name} ({cas}) -> {abbreviation}")
            
            print(f"  Added {type_count} {compound_type} compounds")
        
        return added_count
    
    def save_expanded_registry(self, output_file: Optional[str] = None):
        """Save the expanded registry to file."""
        if output_file is None:
            output_file = self.registry_file
        
        # Create backup
        backup_file = output_file.replace('.jsonl', '_backup.jsonl')
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"Created backup: {backup_file}")
        
        # Write expanded registry
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in self.registry_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"Saved expanded registry to: {output_file}")
    
    def generate_statistics(self):
        """Generate statistics about the expanded registry."""
        type_counts = defaultdict(int)
        total_with_abbreviations = 0
        
        for entry in self.registry_entries:
            compound_type = entry.get('compound_type', 'unknown')
            # Handle None values
            if compound_type is None:
                compound_type = 'unknown'
            type_counts[compound_type] += 1
            
            abbreviation = entry.get('abbreviation', '')
            if abbreviation and abbreviation.strip():
                total_with_abbreviations += 1
        
        print(f"\n=== Registry Statistics ===")
        print(f"Total entries: {len(self.registry_entries)}")
        print(f"Entries with abbreviations: {total_with_abbreviations}")
        
        print(f"\nBy compound type:")
        for compound_type, count in sorted(type_counts.items()):
            print(f"  {compound_type}: {count}")
        
        return type_counts


def main():
    """Main function to expand the CAS registry."""
    print("=== CAS Registry Expansion Tool ===")
    print("Adding common synthesis chemicals from curated sources...")
    
    expander = CASRegistryExpander()
    
    print(f"\nStarting with {len(expander.registry_entries)} existing entries")
    
    # Expand the registry
    added_count = expander.expand_registry()
    
    print(f"\n=== Expansion Complete ===")
    print(f"Added {added_count} new compounds")
    print(f"Total registry size: {len(expander.registry_entries)} entries")
    
    # Generate statistics
    expander.generate_statistics()
    
    # Save the expanded registry
    expander.save_expanded_registry()
    
    print(f"\nRegistry expansion completed successfully!")
    print(f"Backup created and expanded registry saved.")


if __name__ == "__main__":
    main()
