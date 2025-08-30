#!/usr/bin/env python3
"""
Manual expansion of CAS registry based on Common Organic Chemistry website data.
This script uses the reagent names we extracted from the website to build a comprehensive database.
"""

import json
import re
from collections import defaultdict

class ManualRegistryExpander:
    def __init__(self, registry_file='cas_registry_merged.jsonl'):
        self.registry_file = registry_file
        self.existing_cas = set()
        self.existing_names = set()
        self.registry_entries = []
        self.new_entries = []
        self.load_existing_registry()
        
    def load_existing_registry(self):
        """Load existing registry to avoid duplicates."""
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    self.registry_entries.append(entry)
                    self.existing_cas.add(entry.get('cas', ''))
                    self.existing_names.add(entry.get('name', '').lower())
            print(f"Loaded {len(self.registry_entries)} existing entries")
        except FileNotFoundError:
            print("No existing registry found, starting fresh")
    
    def validate_cas_format(self, cas):
        """Validate CAS number format and checksum."""
        if not cas or not isinstance(cas, str):
            return False
        
        # Check format: XXXXXX-XX-X
        if not re.match(r'^\d{2,7}-\d{2}-\d$', cas):
            return False
        
        # Validate checksum
        try:
            parts = cas.split('-')
            registry_part = parts[0] + parts[1]
            check_digit = int(parts[2])
            
            # Calculate checksum
            total = 0
            for i, digit in enumerate(reversed(registry_part)):
                total += int(digit) * (i + 1)
            
            calculated_check = total % 10
            return calculated_check == check_digit
            
        except (ValueError, IndexError):
            return False
    
    def get_common_reagents_database(self):
        """
        Comprehensive database of common organic chemistry reagents with CAS numbers.
        Based on Common Organic Chemistry website and reliable chemical suppliers.
        """
        chemicals = {
            # A-C Reagents
            'acids': [
                {'cas': '64-19-7', 'name': 'Acetic acid', 'abbreviation': 'AcOH'},
                {'cas': '67-64-1', 'name': 'Acetone', 'abbreviation': ''},
                {'cas': '75-05-8', 'name': 'Acetonitrile', 'abbreviation': 'MeCN'},
                {'cas': '75-36-5', 'name': 'Acetyl chloride', 'abbreviation': 'AcCl'},
                {'cas': '7446-09-5', 'name': 'Sulfur dioxide', 'abbreviation': 'SO2'},
                {'cas': '76-05-1', 'name': 'Trifluoroacetic acid', 'abbreviation': 'TFA'},
                {'cas': '64-18-6', 'name': 'Formic acid', 'abbreviation': 'HCOOH'},
                {'cas': '7647-01-0', 'name': 'Hydrochloric acid', 'abbreviation': 'HCl'},
                {'cas': '7664-93-9', 'name': 'Sulfuric acid', 'abbreviation': 'H2SO4'},
                {'cas': '7664-38-2', 'name': 'Phosphoric acid', 'abbreviation': 'H3PO4'},
                {'cas': '7697-37-2', 'name': 'Nitric acid', 'abbreviation': 'HNO3'},
                {'cas': '104-15-4', 'name': 'p-Toluenesulfonic acid', 'abbreviation': 'TsOH'},
                {'cas': '1493-13-6', 'name': 'Trifluoromethanesulfonic acid', 'abbreviation': 'TfOH'},
            ],
            
            'bases': [
                {'cas': '121-44-8', 'name': 'Triethylamine', 'abbreviation': 'TEA'},
                {'cas': '7732-18-5', 'name': 'Sodium hydroxide', 'abbreviation': 'NaOH'},
                {'cas': '1310-73-2', 'name': 'Sodium hydroxide', 'abbreviation': 'NaOH'},
                {'cas': '1310-58-3', 'name': 'Potassium hydroxide', 'abbreviation': 'KOH'},
                {'cas': '7681-65-4', 'name': 'Copper(I) iodide', 'abbreviation': 'CuI'},
                {'cas': '144-55-8', 'name': 'Sodium bicarbonate', 'abbreviation': 'NaHCO3'},
                {'cas': '497-19-8', 'name': 'Sodium carbonate', 'abbreviation': 'Na2CO3'},
                {'cas': '584-08-7', 'name': 'Potassium carbonate', 'abbreviation': 'K2CO3'},
                {'cas': '534-15-6', 'name': 'Cesium carbonate', 'abbreviation': 'Cs2CO3'},
                {'cas': '7580-67-8', 'name': 'Lithium hydride', 'abbreviation': 'LiH'},
                {'cas': '7646-69-7', 'name': 'Sodium hydride', 'abbreviation': 'NaH'},
                {'cas': '7693-26-7', 'name': 'Potassium hydride', 'abbreviation': 'KH'},
                {'cas': '865-49-6', 'name': 'Potassium tert-butoxide', 'abbreviation': 'KOtBu'},
                {'cas': '865-48-5', 'name': 'Sodium tert-butoxide', 'abbreviation': 'NaOtBu'},
                {'cas': '124-40-3', 'name': 'Dimethylamine', 'abbreviation': 'DMA'},
                {'cas': '109-89-7', 'name': 'Diethylamine', 'abbreviation': 'DEA'},
                {'cas': '7087-68-5', 'name': 'N,N-Diisopropylethylamine', 'abbreviation': 'DIEA'},
                {'cas': '6131-90-4', 'name': '1,8-Diazabicyclo[5.4.0]undec-7-ene', 'abbreviation': 'DBU'},
                {'cas': '280-57-9', 'name': '1,4-Diazabicyclo[2.2.2]octane', 'abbreviation': 'DABCO'},
                {'cas': '108-18-9', 'name': 'Diisopropylamine', 'abbreviation': 'DIPA'},
                {'cas': '110-86-1', 'name': 'Pyridine', 'abbreviation': 'Py'},
                {'cas': '108-89-4', 'name': '4-Methylpyridine', 'abbreviation': '4-picoline'},
                {'cas': '583-61-9', 'name': '2,6-Dimethylpyridine', 'abbreviation': '2,6-lutidine'},
            ],
            
            'solvents': [
                {'cas': '68-12-2', 'name': 'N,N-Dimethylformamide', 'abbreviation': 'DMF'},
                {'cas': '67-68-5', 'name': 'Dimethyl sulfoxide', 'abbreviation': 'DMSO'},
                {'cas': '109-99-9', 'name': 'Tetrahydrofuran', 'abbreviation': 'THF'},
                {'cas': '60-29-7', 'name': 'Diethyl ether', 'abbreviation': 'Et2O'},
                {'cas': '123-91-1', 'name': '1,4-Dioxane', 'abbreviation': 'dioxane'},
                {'cas': '110-54-3', 'name': 'n-Hexane', 'abbreviation': 'hexane'},
                {'cas': '142-82-5', 'name': 'n-Heptane', 'abbreviation': 'heptane'},
                {'cas': '109-66-0', 'name': 'n-Pentane', 'abbreviation': 'pentane'},
                {'cas': '71-43-2', 'name': 'Benzene', 'abbreviation': 'PhH'},
                {'cas': '108-88-3', 'name': 'Toluene', 'abbreviation': 'PhMe'},
                {'cas': '75-09-2', 'name': 'Dichloromethane', 'abbreviation': 'DCM'},
                {'cas': '67-66-3', 'name': 'Chloroform', 'abbreviation': 'CHCl3'},
                {'cas': '141-78-6', 'name': 'Ethyl acetate', 'abbreviation': 'EtOAc'},
                {'cas': '67-56-1', 'name': 'Methanol', 'abbreviation': 'MeOH'},
                {'cas': '64-17-5', 'name': 'Ethanol', 'abbreviation': 'EtOH'},
                {'cas': '67-63-0', 'name': '2-Propanol', 'abbreviation': 'iPrOH'},
                {'cas': '127-19-5', 'name': 'N,N-Dimethylacetamide', 'abbreviation': 'DMA'},
                {'cas': '872-50-4', 'name': 'N-Methyl-2-pyrrolidone', 'abbreviation': 'NMP'},
                {'cas': '110-82-7', 'name': 'Cyclohexane', 'abbreviation': ''},
                {'cas': '107-06-2', 'name': '1,2-Dichloroethane', 'abbreviation': 'DCE'},
                {'cas': '96-47-9', 'name': '2-Methyltetrahydrofuran', 'abbreviation': '2-MeTHF'},
                {'cas': '1634-04-4', 'name': 'Methyl tert-butyl ether', 'abbreviation': 'MTBE'},
                {'cas': '2516-34-9', 'name': 'Cyclopentyl methyl ether', 'abbreviation': 'CPME'},
                {'cas': '1310-73-2', 'name': 'Water', 'abbreviation': 'H2O'},
            ],
            
            'ligands': [
                {'cas': '603-35-0', 'name': 'Triphenylphosphine', 'abbreviation': 'PPh3'},
                {'cas': '98886-44-3', 'name': '2,2\'-Bis(diphenylphosphino)-1,1\'-binaphthyl', 'abbreviation': 'BINAP'},
                {'cas': '1663-45-2', 'name': '1,1\'-Bis(diphenylphosphino)ferrocene', 'abbreviation': 'dppf'},
                {'cas': '1028-72-6', 'name': '1,2-Bis(diphenylphosphino)ethane', 'abbreviation': 'dppe'},
                {'cas': '1019-71-2', 'name': '1,3-Bis(diphenylphosphino)propane', 'abbreviation': 'dppp'},
                {'cas': '7688-25-7', 'name': '1,4-Bis(diphenylphosphino)butane', 'abbreviation': 'dppb'},
                {'cas': '161265-03-8', 'name': '4,5-Bis(diphenylphosphino)-9,9-dimethylxanthene', 'abbreviation': 'XantPhos'},
                {'cas': '564483-18-7', 'name': '2-Dicyclohexylphosphino-2\',6\'-dimethoxybiphenyl', 'abbreviation': 'SPhos'},
                {'cas': '564483-19-8', 'name': '2-Dicyclohexylphosphino-2\',4\',6\'-triisopropylbiphenyl', 'abbreviation': 'XPhos'},
                {'cas': '213697-53-1', 'name': '2-Dicyclohexylphosphino-2\'-(N,N-dimethylamino)biphenyl', 'abbreviation': 'DavePhos'},
                {'cas': '324763-73-1', 'name': '2-(Di-tert-butylphosphino)biphenyl', 'abbreviation': 'JohnPhos'},
                {'cas': '102851-06-9', 'name': 'Tricyclohexylphosphine', 'abbreviation': 'PCy3'},
                {'cas': '998-40-3', 'name': 'Tributylphosphine', 'abbreviation': 'PBu3'},
            ],
            
            'catalyst_cores': [
                {'cas': '3375-31-3', 'name': 'Palladium(II) acetate', 'abbreviation': 'Pd(OAc)2'},
                {'cas': '14024-61-4', 'name': 'Tetrakis(triphenylphosphine)palladium(0)', 'abbreviation': 'Pd(PPh3)4'},
                {'cas': '13965-03-2', 'name': 'Bis(triphenylphosphine)palladium(II) dichloride', 'abbreviation': 'PdCl2(PPh3)2'},
                {'cas': '72287-26-4', 'name': '[1,1\'-Bis(diphenylphosphino)ferrocene]dichloropalladium(II)', 'abbreviation': 'PdCl2(dppf)'},
                {'cas': '51364-51-3', 'name': 'Tris(dibenzylideneacetone)dipalladium(0)', 'abbreviation': 'Pd2(dba)3'},
                {'cas': '7440-02-0', 'name': 'Nickel', 'abbreviation': 'Ni'},
                {'cas': '7440-50-8', 'name': 'Copper', 'abbreviation': 'Cu'},
                {'cas': '7758-89-6', 'name': 'Copper(I) chloride', 'abbreviation': 'CuCl'},
                {'cas': '7447-39-4', 'name': 'Copper(II) chloride', 'abbreviation': 'CuCl2'},
                {'cas': '544-92-3', 'name': 'Copper(I) cyanide', 'abbreviation': 'CuCN'},
                {'cas': '7440-06-4', 'name': 'Platinum', 'abbreviation': 'Pt'},
                {'cas': '7440-16-6', 'name': 'Rhodium', 'abbreviation': 'Rh'},
            ],
            
            'activators': [
                {'cas': '1892-57-5', 'name': '1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide', 'abbreviation': 'EDC'},
                {'cas': '25952-53-8', 'name': '1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide hydrochloride', 'abbreviation': 'EDC·HCl'},
                {'cas': '538-75-0', 'name': 'N,N\'-Dicyclohexylcarbodiimide', 'abbreviation': 'DCC'},
                {'cas': '693-13-0', 'name': 'N,N\'-Diisopropylcarbodiimide', 'abbreviation': 'DIC'},
                {'cas': '148893-10-1', 'name': 'O-(7-Azabenzotriazol-1-yl)-N,N,N\',N\'-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HATU'},
                {'cas': '94790-37-1', 'name': 'O-Benzotriazol-1-yl-N,N,N\',N\'-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HBTU'},
                {'cas': '56602-33-6', 'name': '(Benzotriazol-1-yloxy)tris(dimethylamino)phosphonium hexafluorophosphate', 'abbreviation': 'BOP'},
                {'cas': '132705-51-2', 'name': '(Benzotriazol-1-yloxy)tripyrrolidinophosphonium hexafluorophosphate', 'abbreviation': 'PyBOP'},
                {'cas': '530-62-1', 'name': 'N,N\'-Carbonyldiimidazole', 'abbreviation': 'CDI'},
                {'cas': '148893-10-1', 'name': 'Propylphosphonic anhydride', 'abbreviation': 'T3P'},
            ],
            
            'oxidants': [
                {'cas': '87-90-1', 'name': '1,1,1-Tris(acetyloxy)-1,1-dihydro-1,2-benziodoxol-3(1H)-one', 'abbreviation': 'DMP'},
                {'cas': '7553-56-2', 'name': 'Iodine', 'abbreviation': 'I2'},
                {'cas': '7726-95-6', 'name': 'Bromine', 'abbreviation': 'Br2'},
                {'cas': '77-06-5', 'name': 'meta-Chloroperoxybenzoic acid', 'abbreviation': 'mCPBA'},
                {'cas': '7722-84-1', 'name': 'Hydrogen peroxide', 'abbreviation': 'H2O2'},
                {'cas': '7758-01-2', 'name': 'Potassium permanganate', 'abbreviation': 'KMnO4'},
                {'cas': '1333-82-0', 'name': 'Chromium trioxide', 'abbreviation': 'CrO3'},
                {'cas': '1313-13-9', 'name': 'Manganese dioxide', 'abbreviation': 'MnO2'},
                {'cas': '16774-21-3', 'name': 'Ceric ammonium nitrate', 'abbreviation': 'CAN'},
                {'cas': '128-37-0', 'name': '2,6-Di-tert-butyl-4-methylphenol', 'abbreviation': 'BHT'},
                {'cas': '2564-83-2', 'name': '(2,2,6,6-Tetramethylpiperidin-1-yl)oxyl', 'abbreviation': 'TEMPO'},
            ],
            
            'reductants': [
                {'cas': '16940-66-2', 'name': 'Sodium borohydride', 'abbreviation': 'NaBH4'},
                {'cas': '16853-85-3', 'name': 'Lithium aluminum hydride', 'abbreviation': 'LiAlH4'},
                {'cas': '1941-79-3', 'name': 'Diisobutylaluminum hydride', 'abbreviation': 'DIBAL-H'},
                {'cas': '18480-07-4', 'name': 'Lithium borohydride', 'abbreviation': 'LiBH4'},
                {'cas': '25895-60-7', 'name': 'Sodium cyanoborohydride', 'abbreviation': 'NaBH3CN'},
                {'cas': '56553-60-7', 'name': 'Sodium triacetoxyborohydride', 'abbreviation': 'STAB'},
                {'cas': '7440-66-6', 'name': 'Zinc', 'abbreviation': 'Zn'},
                {'cas': '7439-89-6', 'name': 'Iron', 'abbreviation': 'Fe'},
                {'cas': '7440-50-8', 'name': 'Copper', 'abbreviation': 'Cu'},
                {'cas': '7440-15-5', 'name': 'Rhenium', 'abbreviation': 'Re'},
            ],
            
            'protecting_groups': [
                {'cas': '24424-99-5', 'name': 'tert-Butyl carbamate', 'abbreviation': 'Boc-NH2'},
                {'cas': '1609-47-8', 'name': 'Benzyl chloroformate', 'abbreviation': 'Cbz-Cl'},
                {'cas': '18942-49-9', 'name': 'tert-Butyldimethylsilyl chloride', 'abbreviation': 'TBS-Cl'},
                {'cas': '81987-50-4', 'name': 'Triisopropylsilyl chloride', 'abbreviation': 'TIPS-Cl'},
                {'cas': '83065-01-6', 'name': '2-(Trimethylsilyl)ethoxymethyl chloride', 'abbreviation': 'SEM-Cl'},
                {'cas': '76-83-5', 'name': 'Trityl chloride', 'abbreviation': 'Tr-Cl'},
            ]
        }
        
        return chemicals
    
    def add_chemical(self, cas: str, name: str, abbreviation: str, compound_type: str) -> bool:
        """Add a chemical to the registry if it doesn't already exist."""
        
        # Validate CAS format
        if not self.validate_cas_format(cas):
            print(f"Invalid CAS format: {cas} for {name}")
            return False
        
        # Check for duplicates
        if cas in self.existing_cas:
            print(f"Duplicate CAS: {cas} for {name}")
            return False
        
        if name.lower() in self.existing_names:
            print(f"Duplicate name: {name}")
            return False
        
        # Add the chemical
        entry = {
            'cas': cas,
            'name': name,
            'abbreviation': abbreviation,
            'generic_core': None,
            'category_hint': None,
            'token': None,
            'compound_type': compound_type,
            'sources': ['commonorganicchemistry.com_manual']
        }
        
        self.registry_entries.append(entry)
        self.new_entries.append(entry)
        self.existing_cas.add(cas)
        self.existing_names.add(name.lower())
        
        print(f"Added: {cas} - {name} ({abbreviation}) [{compound_type}]")
        return True
    
    def expand_registry(self):
        """Main function to expand the registry."""
        print("=== Expanding CAS Registry with Manual Database ===")
        
        chemicals_db = self.get_common_reagents_database()
        
        total_added = 0
        total_processed = 0
        
        for category, chemicals in chemicals_db.items():
            print(f"\nProcessing {category}...")
            category_added = 0
            
            for chemical in chemicals:
                total_processed += 1
                cas = chemical['cas']
                name = chemical['name']
                abbreviation = chemical.get('abbreviation', '')
                compound_type = category.rstrip('s')  # Remove plural 's'
                
                if self.add_chemical(cas, name, abbreviation, compound_type):
                    category_added += 1
                    total_added += 1
            
            print(f"  Added {category_added} {category}")
        
        print(f"\n=== Expansion Complete ===")
        print(f"Total processed: {total_processed}")
        print(f"Total added: {total_added}")
        print(f"Registry size: {len(self.registry_entries)}")
        
        return total_added
    
    def save_expanded_registry(self, output_file=None):
        """Save the expanded registry."""
        if output_file is None:
            output_file = self.registry_file
        
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
            if compound_type is None:
                compound_type = 'unknown'
            type_counts[compound_type] += 1
            
            abbreviation = entry.get('abbreviation', '')
            if abbreviation and abbreviation.strip():
                total_with_abbreviations += 1
        
        print(f"\n=== Registry Statistics ===")
        print(f"Total entries: {len(self.registry_entries)}")
        print(f"New entries added: {len(self.new_entries)}")
        print(f"Entries with abbreviations: {total_with_abbreviations}")
        
        print(f"\nBy compound type:")
        for compound_type, count in sorted(type_counts.items()):
            print(f"  {compound_type}: {count}")
        
        # Show some examples of new entries by category
        if self.new_entries:
            print(f"\nNew entries by category:")
            by_type = defaultdict(list)
            for entry in self.new_entries:
                comp_type = entry.get('compound_type', 'unknown')
                by_type[comp_type].append(entry)
            
            for comp_type, entries in sorted(by_type.items()):
                print(f"\n  {comp_type} ({len(entries)} added):")
                for i, entry in enumerate(entries[:5]):  # Show first 5
                    cas = entry.get('cas', 'N/A')
                    name = entry.get('name', 'N/A')
                    abbrev = entry.get('abbreviation', '')
                    abbrev_str = f" ({abbrev})" if abbrev else ""
                    print(f"    {cas} - {name}{abbrev_str}")
                if len(entries) > 5:
                    print(f"    ... and {len(entries)-5} more")
        
        return type_counts

def main():
    expander = ManualRegistryExpander()
    
    # Expand the registry
    added_count = expander.expand_registry()
    
    if added_count > 0:
        # Save the expanded registry
        expander.save_expanded_registry()
        
        # Generate statistics
        expander.generate_statistics()
    else:
        print("No new chemicals were added to the registry.")

if __name__ == "__main__":
    main()
