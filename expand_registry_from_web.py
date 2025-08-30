#!/usr/bin/env python3
"""
Comprehensive CAS Registry Expansion using Common Organic Chemistry website.
This script extracts reagents from commonorganicchemistry.com and adds them to our registry.
"""

import json
import re
import requests
from collections import defaultdict
from urllib.parse import urljoin
import time
import hashlib

class CommonOrganicChemistryExpander:
    def __init__(self, registry_file='cas_registry_merged.jsonl'):
        self.registry_file = registry_file
        self.existing_cas = set()
        self.existing_names = set()
        self.registry_entries = []
        self.new_entries = []
        self.load_existing_registry()
        
        # Base URL for common organic chemistry
        self.base_url = "https://commonorganicchemistry.com/"
        
        # Common reagent URLs from the three pages
        self.reagent_urls = []
        
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
    
    def extract_reagent_urls_from_content(self, content):
        """Extract reagent URLs from the webpage content."""
        urls = []
        # Look for links to Common_Reagents
        pattern = r'href="([^"]*Common_Reagents[^"]*\.htm)"'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # Convert relative URLs to absolute
            if match.startswith('/'):
                url = self.base_url.rstrip('/') + match
            elif match.startswith('http'):
                url = match
            else:
                url = urljoin(self.base_url, match)
            urls.append(url)
        
        return urls
    
    def get_all_reagent_urls(self):
        """Get all reagent URLs from the three main pages."""
        main_pages = [
            "https://commonorganicchemistry.com/Sidebar/Common_Reagents.htm",
            "https://commonorganicchemistry.com/Sidebar/Common_Reagents_2.htm", 
            "https://commonorganicchemistry.com/Sidebar/Common_Reagents_3.htm"
        ]
        
        all_urls = []
        
        for page_url in main_pages:
            try:
                print(f"Fetching reagent URLs from {page_url}")
                response = requests.get(page_url, timeout=10)
                response.raise_for_status()
                
                urls = self.extract_reagent_urls_from_content(response.text)
                all_urls.extend(urls)
                print(f"Found {len(urls)} reagent URLs on this page")
                
                time.sleep(1)  # Be respectful
                
            except Exception as e:
                print(f"Error fetching {page_url}: {e}")
        
        # Remove duplicates
        self.reagent_urls = list(set(all_urls))
        print(f"Total unique reagent URLs: {len(self.reagent_urls)}")
        
        return self.reagent_urls
    
    def extract_cas_from_reagent_page(self, url):
        """Extract CAS number, name, and abbreviation from individual reagent page."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            content = response.text
            
            # Extract name from URL - it's in the path
            name_match = re.search(r'/([^/]+)\.htm$', url)
            if name_match:
                url_name = name_match.group(1).replace('_', ' ').replace('%20', ' ')
            else:
                url_name = ""
            
            # Look for CAS number patterns in the content
            cas_patterns = [
                r'CAS[:\s]*(\d{2,7}-\d{2}-\d)',  # CAS: 123-45-6
                r'(\d{2,7}-\d{2}-\d)',  # Just the number 123-45-6
                r'Registry[:\s]*(\d{2,7}-\d{2}-\d)',  # Registry: 123-45-6
            ]
            
            cas_number = None
            for pattern in cas_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Take the first valid CAS number
                    for match in matches:
                        if self.validate_cas_format(match):
                            cas_number = match
                            break
                    if cas_number:
                        break
            
            # Extract chemical name from title or headers
            name_patterns = [
                r'<title>([^<]+)</title>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'<h2[^>]*>([^<]+)</h2>',
            ]
            
            chemical_name = url_name  # Default fallback
            for pattern in name_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    title = matches[0].strip()
                    # Clean up the title
                    title = re.sub(r'\s*-\s*Common\s+Organic\s+Chemistry.*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'\s*\|\s*Common\s+Organic\s+Chemistry.*', '', title, flags=re.IGNORECASE)
                    if title and len(title) > 3:
                        chemical_name = title
                        break
            
            # Try to extract abbreviation from content or name
            abbreviation = ""
            abbrev_patterns = [
                r'\(([A-Z]{2,8})\)',  # (DMF), (DMAP), etc.
                r'\[([A-Z]{2,8})\]',  # [DMF], [DMAP], etc.
            ]
            
            for pattern in abbrev_patterns:
                matches = re.findall(pattern, chemical_name)
                if matches:
                    abbreviation = matches[0]
                    break
            
            return {
                'cas': cas_number,
                'name': chemical_name,
                'abbreviation': abbreviation,
                'url': url
            }
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            return None
    
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
    
    def categorize_chemical(self, name, url):
        """Categorize chemical based on name and URL patterns."""
        name_lower = name.lower()
        url_lower = url.lower()
        
        # Solvents
        if any(word in name_lower for word in [
            'acetonitrile', 'dmf', 'dmso', 'thf', 'dioxane', 'ether', 'benzene', 
            'toluene', 'hexane', 'heptane', 'pentane', 'methanol', 'ethanol', 
            'isopropanol', 'dichloromethane', 'chloroform', 'acetone', 'dma',
            'dme', '2-methyltetrahydrofuran', 'cyclopentyl methyl ether', 'xylene'
        ]):
            return 'solvent'
        
        # Bases
        if any(word in name_lower for word in [
            'hydroxide', 'carbonate', 'bicarbonate', 'triethylamine', 'diisopropylethylamine',
            'pyrrolidine', 'piperidine', 'morpholine', 'dbu', 'dabco', 'lutidine',
            'lithium diisopropylamide', 'lda', 'sodium hydride', 'potassium hydride',
            'sodium methoxide', 'potassium t-butoxide', 'sodium t-butoxide',
            'lhmds', 'nahmds', 'khmds', 'cesium carbonate'
        ]):
            return 'base'
        
        # Ligands (phosphines, etc.)
        if any(word in name_lower for word in [
            'phosphine', 'binap', 'dppe', 'dppf', 'dppp', 'dppb', 'xantphos',
            'johnphos', 'sphos', 'xphos', 'davephos', 'triphenylphosphine',
            'tricyclohexylphosphine', 'tributylphosphine'
        ]):
            return 'ligand'
        
        # Catalysts
        if any(word in name_lower for word in [
            'palladium', 'platinum', 'nickel', 'copper', 'iron', 'rhodium',
            'ruthenium', 'pd/c', 'pd(oac)', 'pd(pph3)', 'raney'
        ]):
            return 'catalyst_core'
        
        # Activators/Coupling reagents
        if any(word in name_lower for word in [
            'carbodiimide', 'edc', 'dcc', 'dic', 'hatu', 'hbtu', 'bop', 'pybop',
            'cdi', 't3p', 'hobt', 'oxyma'
        ]):
            return 'activator'
        
        # Acids
        if any(word in name_lower for word in [
            'acid', 'triflic', 'mesylic', 'tosylic', 'tfa', 'acetic acid',
            'formic acid', 'hydrochloric', 'sulfuric', 'phosphoric'
        ]):
            return 'acid'
        
        # Oxidants
        if any(word in name_lower for word in [
            'periodinane', 'dmp', 'iodine', 'bromine', 'chlorine', 'peroxide',
            'permanganate', 'chromium', 'manganese dioxide', 'ceric ammonium',
            'oxone', 'mcpba', 'pcc', 'pdc', 'tempo'
        ]):
            return 'oxidant'
        
        # Reductants
        if any(word in name_lower for word in [
            'borohydride', 'aluminum hydride', 'lah', 'dibal', 'zinc', 'iron powder',
            'stannous', 'samarium', 'nabh4', 'lialh4'
        ]):
            return 'reductant'
        
        # Protecting group reagents
        if any(word in name_lower for word in [
            'boc', 'cbz', 'fmoc', 'tbs', 'tips', 'sem', 'trityl', 'silyl'
        ]):
            return 'protecting_group'
        
        # Default
        return 'reagent'
    
    def add_new_chemical(self, cas, name, abbreviation, compound_type, url):
        """Add a new chemical to the registry."""
        if cas in self.existing_cas or name.lower() in self.existing_names:
            return False
        
        entry = {
            'cas': cas,
            'name': name,
            'abbreviation': abbreviation,
            'generic_core': None,
            'category_hint': None,
            'token': None,
            'compound_type': compound_type,
            'sources': ['commonorganicchemistry.com']
        }
        
        self.registry_entries.append(entry)
        self.new_entries.append(entry)
        self.existing_cas.add(cas)
        self.existing_names.add(name.lower())
        
        return True
    
    def expand_registry(self):
        """Main function to expand the registry."""
        print("=== Expanding CAS Registry from Common Organic Chemistry ===")
        
        # Get all reagent URLs
        reagent_urls = self.get_all_reagent_urls()
        
        added_count = 0
        processed_count = 0
        
        print(f"\nProcessing {len(reagent_urls)} reagent pages...")
        
        for i, url in enumerate(reagent_urls):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(reagent_urls)} ({(i/len(reagent_urls)*100):.1f}%)")
            
            reagent_data = self.extract_cas_from_reagent_page(url)
            processed_count += 1
            
            if reagent_data and reagent_data['cas'] and reagent_data['name']:
                cas = reagent_data['cas']
                name = reagent_data['name']
                abbreviation = reagent_data['abbreviation']
                
                # Skip if we already have this chemical
                if cas in self.existing_cas or name.lower() in self.existing_names:
                    continue
                
                # Categorize the chemical
                compound_type = self.categorize_chemical(name, url)
                
                # Add to registry
                if self.add_new_chemical(cas, name, abbreviation, compound_type, url):
                    added_count += 1
                    print(f"Added: {cas} - {name} ({abbreviation}) [{compound_type}]")
            
            # Be respectful to the server
            time.sleep(0.5)
        
        print(f"\nProcessing complete!")
        print(f"Processed: {processed_count} reagent pages")
        print(f"Added: {added_count} new chemicals")
        
        return added_count
    
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
        
        # Show some examples of new entries
        if self.new_entries:
            print(f"\nSample new entries:")
            for i, entry in enumerate(self.new_entries[:10]):
                cas = entry.get('cas', 'N/A')
                name = entry.get('name', 'N/A')
                abbrev = entry.get('abbreviation', '')
                comp_type = entry.get('compound_type', 'unknown')
                
                abbrev_str = f" ({abbrev})" if abbrev else ""
                print(f"  {i+1:2d}. {cas} - {name}{abbrev_str} [{comp_type}]")
        
        return type_counts

def main():
    expander = CommonOrganicChemistryExpander()
    
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
