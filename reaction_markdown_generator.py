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
- process_reactions module (for parsing             # Generate markdown report
            self.generate_markdown_report(rows, output_path, source_folder)
            
            # Also generate JSONL export for analysis
            jsonl_path = output_path.replace('.md', '.jsonl')
            self.generate_jsonl_export(rows, jsonl_path, source_folder)
            
            if progress_callback:
                progress_callback(f"Report generated successfully: {output_path}")
                progress_callback(f"JSONL export generated: {jsonl_path}")
            
            return True
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

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: 'requests' not available. Online CAS validation will be disabled.")


class CASRegistry:
    """Enhanced CAS number registry with validation and lookup capabilities."""
    
    def __init__(self):
        self.cas_cache = {}
        self.registry_data = {}  # Will store the full registry from JSONL
        self.manual_corrections = {
            # Known corrections from your example
            "6737-42-4": "1,3-Bis(diphenylphosphino)propane",
            "7787-70-4": "Copper(I) bromide",
            # Common catalyst CAS numbers
            "142-71-2": "Copper(II) acetate",
            "7681-65-4": "Copper(I) iodide", 
            "7758-89-6": "Copper(I) chloride",
            "1317-39-1": "Copper(I) oxide",
            "1122-58-3": "4-(Dimethylamino)pyridine",
            "7447-39-4": "Copper(II) chloride",
            # Common ligands
            "110-70-3": "N,N'-Dimethylethylenediamine",
            "366-18-7": "2,2'-Bipyridine",
            "66-71-7": "1,10-Phenanthroline",
            # Common solvents
            "68-12-2": "Dimethylformamide",
            "64-17-5": "Ethanol",
            "108-88-3": "Toluene",
            "107-06-2": "1,2-Dichloroethane",
            "67-68-5": "Dimethyl sulfoxide",
            "109-99-9": "Tetrahydrofuran",
            "75-09-2": "Dichloromethane",
            # Common reagents
            "584-08-7": "Potassium carbonate",
            "534-17-8": "Cesium carbonate", 
            "497-19-8": "Sodium carbonate",
            "7778-53-2": "Tripotassium phosphate",
            "121-44-8": "Triethylamine",
            "7782-44-7": "Oxygen",
            "7732-18-5": "Water",
        }
        self.compound_types = {
            # Catalyst cores (metal salts/precursors)
            "142-71-2": "catalyst_core",
            "7681-65-4": "catalyst_core", 
            "7758-89-6": "catalyst_core",
            "1317-39-1": "catalyst_core",
            "7447-39-4": "catalyst_core",
            "7787-70-4": "catalyst_core",  # CuBr
            # Ligands
            "6737-42-4": "ligand",  # dppp
            "110-70-3": "ligand",
            "366-18-7": "ligand",
            "66-71-7": "ligand",
            "1122-58-3": "ligand",  # DMAP can act as ligand
            # Bases
            "584-08-7": "base",
            "534-17-8": "base",
            "497-19-8": "base", 
            "7778-53-2": "base",
            "121-44-8": "base",
            # Solvents
            "68-12-2": "solvent",
            "64-17-5": "solvent",
            "108-88-3": "solvent",
            "107-06-2": "solvent",
            "67-68-5": "solvent",
            "109-99-9": "solvent",
            "75-09-2": "solvent",
        }
        
        # Load registry data from the updated JSONL file
        self.load_registry_data()
    
    def load_registry_data(self):
        """Load the updated CAS registry data from the JSONL file."""
        registry_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cas_registry_merged.jsonl')
        
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            entry = json.loads(line)
                            cas = entry.get('cas')
                            if cas:
                                self.registry_data[cas] = entry
                        except json.JSONDecodeError:
                            continue
                            
                print(f"[INFO] Loaded {len(self.registry_data)} entries from CAS registry")
            except Exception as e:
                print(f"[WARNING] Could not load CAS registry: {e}")
        else:
            print(f"[WARNING] CAS registry not found at {registry_path}")
    
    def get_registry_entry(self, cas: str) -> Optional[Dict[str, Any]]:
        """Get the full registry entry for a CAS number."""
        return self.registry_data.get(cas)
    
    def get_compound_abbreviation(self, cas: str) -> Optional[str]:
        """Get the abbreviation for a compound from the registry."""
        entry = self.get_registry_entry(cas)
        if entry:
            abbrev = entry.get('abbreviation', '')
            return abbrev if abbrev else None
        return None
    
    def validate_cas_format(self, cas: str) -> bool:
        """Validate CAS number format (XXXXX-XX-X)."""
        if not cas:
            return False
        import re
        pattern = r'^\d{2,7}-\d{2}-\d$'
        return bool(re.match(pattern, cas.strip()))
    
    def calculate_cas_checksum(self, cas: str) -> bool:
        """Validate CAS number checksum."""
        try:
            # Remove hyphens
            digits = cas.replace('-', '')
            if len(digits) < 3:
                return False
            
            check_digit = int(digits[-1])
            body_digits = [int(d) for d in digits[:-1]]
            
            # Calculate checksum (rightmost digit has weight 1, next has weight 2, etc.)
            total = 0
            weight = 1
            for digit in reversed(body_digits):
                total += digit * weight
                weight += 1
            
            return (total % 10) == check_digit
        except (ValueError, IndexError):
            return False
    
    def lookup_cas_online(self, cas: str) -> Optional[str]:
        """Look up CAS number using online services (placeholder for future implementation)."""
        # This would integrate with services like:
        # - PubChem API
        # - ChemSpider API  
        # - SciFinder-n API
        # For now, return None to use fallback methods
        return None
    
    def get_compound_name(self, cas: str) -> str:
        """Get the correct compound name for a CAS number."""
        if not cas or not self.validate_cas_format(cas):
            return cas or "Unknown"
        
        # Check registry first
        entry = self.get_registry_entry(cas)
        if entry:
            name = entry.get('name', '')
            if name:
                return name
        
        # Check manual corrections
        if cas in self.manual_corrections:
            return self.manual_corrections[cas]
        
        # Try online lookup if available
        if REQUESTS_AVAILABLE:
            online_result = self.lookup_cas_online(cas)
            if online_result:
                self.cas_cache[cas] = online_result
                return online_result
        
        # Validate checksum
        if not self.calculate_cas_checksum(cas):
            return f"{cas} (Invalid CAS)"
        
        # Return CAS as fallback
        return cas
    
    def get_compound_type(self, cas: str) -> Optional[str]:
        """Get the compound type (catalyst_core, ligand, base, solvent) for a CAS number."""
        # Check registry first
        entry = self.get_registry_entry(cas)
        if entry:
            compound_type = entry.get('compound_type')
            if compound_type:
                return compound_type
        
        # Fallback to manual mappings
        return self.compound_types.get(cas)
    
    def get_display_name(self, name: str, cas: str) -> str:
        """Get the best display name for a compound, using abbreviation if available."""
        if not cas:
            return name
        
        # Get abbreviation from registry
        abbreviation = self.get_compound_abbreviation(cas)
        registry_name = self.get_compound_name(cas)
        
        # Priority: 1) abbreviation, 2) registry name, 3) provided name
        if abbreviation and abbreviation != cas:
            return abbreviation
        elif registry_name and registry_name != cas:
            return registry_name
        else:
            return name if name else cas
    
    def validate_compound_pair(self, name: str, cas: str) -> Tuple[str, str, List[str]]:
        """Validate and correct a compound name/CAS pair.
        
        Returns:
            Tuple of (corrected_name, corrected_cas, list_of_warnings)
        """
        warnings = []
        corrected_name = name
        corrected_cas = cas
        
        if not cas or not self.validate_cas_format(cas):
            if cas:
                warnings.append(f"Invalid CAS format: {cas}")
            return corrected_name, corrected_cas, warnings
        
        # Check if CAS has valid checksum
        if not self.calculate_cas_checksum(cas):
            warnings.append(f"Invalid CAS checksum: {cas}")
        
        # Get the best display name using the new registry
        best_name = self.get_display_name(name, cas)
        
        # Get registry entry for additional validation
        entry = self.get_registry_entry(cas)
        if entry:
            registry_name = entry.get('name', '')
            abbreviation = entry.get('abbreviation', '')
            
            # Check for name mismatches
            if name and registry_name:
                # Allow for abbreviation matches
                name_lower = name.lower().strip()
                registry_name_lower = registry_name.lower().strip()
                abbrev_lower = abbreviation.lower().strip() if abbreviation else ""
                
                if (name_lower != registry_name_lower and 
                    name_lower != abbrev_lower and
                    name_lower != cas.lower()):
                    warnings.append(
                        f"Name mismatch: '{name}' vs registry '{registry_name}'"
                        + (f" (abbrev: '{abbreviation}')" if abbreviation else "")
                        + f" for CAS {cas}"
                    )
            
            # Use the best available name
            corrected_name = best_name
        else:
            # Check manual corrections if not in registry
            if cas in self.manual_corrections:
                correct_name = self.manual_corrections[cas]
                if name.lower() != correct_name.lower():
                    warnings.append(f"Name mismatch: '{name}' vs expected '{correct_name}' for CAS {cas}")
                    corrected_name = correct_name
        
        return corrected_name, corrected_cas, warnings


class ReactionMarkdownGenerator:
    """Main class for generating markdown reports from RDF/TXT pairs."""
    
    def __init__(self):
        self.cas_map = {}
        self.cas_registry = CASRegistry()
        self.validation_warnings = []
        # Reverse indices for lookups and de-duplication
        self.name_to_cas = {}
        self.token_to_cas = {}
        self.alias_to_cas = {}
        # Direct CAS-to-CAS alias map for canonicalization (e.g., precatalyst CAS -> ligand CAS)
        self.cas_alias_to_cas = {}

    @staticmethod
    def _norm(s: str) -> str:
        """Normalize names for matching: lowercase, strip, collapse spaces, remove certain punctuation."""
        if not s:
            return ""
        import re
        s2 = s.lower().strip()
        # Replace unicode primes and quotes with nothing
        s2 = s2.replace("′", "").replace("’", "").replace("'", "")
        # Remove brackets and commas
        s2 = re.sub(r"[\[\]\(\),]", " ", s2)
        # Collapse hyphens to spaces
        s2 = s2.replace("-", " ")
        # Collapse multiple spaces
        s2 = re.sub(r"\s+", " ", s2)
        return s2

    def _build_reverse_indices(self):
        """Build reverse indices from the loaded CAS map and manual aliases."""
        self.name_to_cas.clear()
        self.token_to_cas.clear()
        self.alias_to_cas.clear()
        self.cas_alias_to_cas.clear()

        # From CAS map
        for cas, data in (self.cas_map or {}).items():
            name = (data.get('Name') or '').strip()
            token = (data.get('Token') or '').strip()
            if name:
                self.name_to_cas[self._norm(name)] = cas
            if token:
                self.token_to_cas[self._norm(token)] = cas

        # Manual aliases (common synonyms/expanded names)
        manual = {
            # Bases and salts
            "sodium tert butoxide": "865-48-5",  # NaOtBu
            "sodium t butoxide": "865-48-5",
            "naotbu": "865-48-5",
            # Cu(I) iodide common token
            "cui": "7681-65-4",
            # Potassium tert-butoxide
            "potassium tert butoxide": "865-47-4",  # KOtBu
            "potassium t butoxide": "865-47-4",
            "kotbu": "865-47-4",
            "sodium hydroxide": "1310-73-2",   # NaOH
            "naoh": "1310-73-2",
            "ammonium chloride": "12125-02-9",
            "triethylamine": "121-44-8",
            "diisopropylethylamine": "7087-68-5",  # DIPEA
            "n n diisopropylethylamine": "7087-68-5",
            "dicyclohexylcarbodiimide": "538-75-0",  # DCC / DIC? (DCC is 538-75-0)
            "edc": "1892-57-5",  # EDCI free base
            "edci": "25952-53-8", # EDCI·HCl
            # Tripotassium phosphate
            "k3po4": "7778-53-2",
            "tripotassium phosphate": "7778-53-2",

            # Biaryl phosphines (common systematic spellings -> abbreviations)
            # RuPhos
            "[2,6 bis 1 methylethoxy 1,1 biphenyl 2 yl]dicyclohexylphosphine": "787618-22-8",
            "2 6 bis 1 methylethoxy 1 1 biphenyl 2 yl dicyclohexylphosphine": "787618-22-8",
            "ruphos": "787618-22-8",
            # Occasionally the palladium precatalyst CAS appears where the ligand is intended; canonicalize to RuPhos
            "1445085-77-7": "787618-22-8",
            # XPhos, SPhos, tBuXPhos and BrettPhos common forms
            "xphos": "564483-18-7",
            "sphos": "657408-07-6",
            "tbu xphos": "564483-19-8",
            "brettphos": "1028206-60-1",
            # Oxidants/common reagents
            "ddq": "84-58-2",
            # Nickel sources
            "ni(cod)2": "244261-66-3",
            "ni cod 2": "244261-66-3",
        }

        # Normalize keys into alias_to_cas
        for k, v in manual.items():
            self.alias_to_cas[self._norm(k)] = v

        # CAS-to-CAS canonicalization (ensure report uses canonical ligand CAS)
        # RuPhos Pd-precatalyst CAS -> RuPhos ligand CAS
        self.cas_alias_to_cas["1445085-77-7"] = "787618-22-8"

    def canonicalize_cas(self, cas: Optional[str]) -> Optional[str]:
        """Return canonical CAS if an alias mapping exists; otherwise return the input."""
        if not cas:
            return cas
        return self.cas_alias_to_cas.get(cas, cas)

    @staticmethod
    def _norm_role(role: str) -> str:
        """Normalize reagent role labels; keep only clean tokens like BASE, CAT_LIG, etc."""
        if not role:
            return "UNK"
        import re
        r = str(role).strip().upper()
        # unify separators to underscore
        r = re.sub(r"[^A-Z0-9]+", "_", r)
        r = r.strip("_")
        # allow only letters, digits and underscores; otherwise UNK
        if not re.match(r"^[A-Z0-9_]{2,}$", r):
            return "UNK"
        # common normalizations
        if r in {"CATLIG", "CAT-LIG", "CAT__LIG"}:
            r = "CAT_LIG"
        return r
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
        
        # Use only the unified registry if available, otherwise fall back to individual files
        here = os.path.dirname(os.path.abspath(__file__))
        merged_path = os.path.join(here, 'cas_registry_merged.jsonl')
        if os.path.exists(merged_path):
            cas_map_paths.append(merged_path)
        else:
            # Fallback to individual JSONL files if merged doesn't exist
            maybe_paths = [
                os.path.join(here, 'cas_dictionary.jsonl'),
                os.path.join(here, 'comprehensive_cas_registry.jsonl'),
                os.path.join(folder_path, 'cas_dictionary.jsonl'),
                os.path.join(folder_path, 'cas_mapping.jsonl'),
            ]
            for path in maybe_paths:
                if os.path.exists(path):
                    cas_map_paths.append(path)
        
        self.cas_map = load_cas_maps(cas_map_paths) if cas_map_paths else {}
        # Rebuild reverse indices for name resolution and de-duplication
        self._build_reverse_indices()
        return self.cas_map

    def resolve_name_to_cas(self, name: str) -> Optional[str]:
        """Resolve a plain compound name to a CAS using registry and aliases."""
        if not name:
            return None
        n = self._norm(name)
        # Direct name match from registry
        cas = self.name_to_cas.get(n)
        if cas:
            return cas
        # Token/abbreviation match
        cas = self.token_to_cas.get(n)
        if cas:
            return cas
        # Manual alias match
        cas = self.alias_to_cas.get(n)
        if cas:
            return cas
        return None
    
    def format_compound_list(self, compound_list: List[str], title: str) -> str:
        """Format a list of compounds for markdown output with CAS validation and de-duplication.
        Rules:
        - Prefer entries with CAS over name-only duplicates.
        - Resolve name-only entries to CAS using registry/aliases when possible.
        - De-duplicate by CAS; if no CAS, de-duplicate by normalized name.
        """
        if not compound_list:
            return f"**{title}:** None\n"

        seen_cas: set[str] = set()
        seen_names: set[str] = set()
        lines: List[str] = []

        for compound in compound_list:
            compound = compound.strip()
            if not compound:
                continue

            if '|' in compound:
                # Explicit name|CAS entry
                name, cas = compound.split('|', 1)
                name = name.strip()
                cas = cas.strip()

                corrected_name, corrected_cas, warnings = self.cas_registry.validate_compound_pair(name, cas)
                # Filter out name-mismatch warnings when the provided name is a known alias for the same CAS
                for warning in warnings:
                    if "Name mismatch:" in warning:
                        try:
                            resolved = self.resolve_name_to_cas(name)
                        except Exception:
                            resolved = None
                        if resolved and (self.canonicalize_cas(resolved) == self.canonicalize_cas(corrected_cas)):
                            continue  # suppress benign alias mismatch
                    self.validation_warnings.append(f"{title}: {warning}")

                # Canonicalize CAS by name alias resolution when possible
                canonical_cas = self.resolve_name_to_cas(corrected_name)
                if canonical_cas:
                    corrected_cas = canonical_cas

                # Also canonicalize by direct CAS alias mapping
                corrected_cas = self.canonicalize_cas(corrected_cas)

                # If still missing or invalid CAS, drop this entry (enforce CAS-only policy)
                if (not corrected_cas) or (not self.cas_registry.validate_cas_format(corrected_cas)):
                    continue

                norm_name = self._norm(corrected_name)
                if corrected_cas:
                    if corrected_cas in seen_cas:
                        continue  # duplicate by CAS
                    seen_cas.add(corrected_cas)
                    # Prefer registry canonical display name when available
                    reg_name = (self.cas_map.get(corrected_cas, {}) or {}).get('Name') or corrected_name
                    seen_names.add(self._norm(reg_name))
                    if reg_name != corrected_cas:
                        lines.append(f"  - {reg_name} (CAS: {corrected_cas})")
                    else:
                        lines.append(f"  - CAS: {corrected_cas}")
            else:
                # Name-only; try resolve to CAS
                name = compound
                norm_name = self._norm(name)
                cas_resolved = self.resolve_name_to_cas(name)
                if cas_resolved:
                    # Prefer the canonical registry name if available
                    cas_resolved = self.canonicalize_cas(cas_resolved) or cas_resolved
                    if not self.cas_registry.validate_cas_format(cas_resolved):
                        continue
                    reg_name = (self.cas_map.get(cas_resolved, {}) or {}).get('Name') or name
                    norm_reg_name = self._norm(reg_name)
                    if cas_resolved in seen_cas or norm_reg_name in seen_names:
                        continue
                    seen_cas.add(cas_resolved)
                    seen_names.add(norm_reg_name)
                    lines.append(f"  - {reg_name} (CAS: {cas_resolved})")
                else:
                    # Cannot resolve to CAS; drop per CAS-only policy
                    continue

        if not lines:
            return f"**{title}:** None\n"
        result = f"**{title}:**\n" + "\n".join(lines) + "\n\n"
        return result
    
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

    def format_reagents(self, reagents: List[str], reagent_roles: List[str]) -> str:
        """Format reagents with roles using CAS/alias resolution and de-duplication.
        - Resolve names to CAS when possible
        - Deduplicate by CAS first; otherwise by normalized name
        - Merge roles for duplicates (sorted, unique)
        """
        if not reagents:
            return ""

        # Maps and sets for dedup
        cas_to_entry: Dict[str, Dict[str, Any]] = {}
        name_to_entry: Dict[str, Dict[str, Any]] = {}

        for i, reagent in enumerate(reagents):
            role = self._norm_role(reagent_roles[i] if i < len(reagent_roles) else "UNK")
            name: str = reagent
            cas: Optional[str] = None
            if '|' in reagent:
                n, c = reagent.split('|', 1)
                name = n.strip()
                cas = c.strip()

            # Try to resolve CAS if missing or invalid
            if not cas or not self.cas_registry.validate_cas_format(cas):
                resolved = self.resolve_name_to_cas(name)
                cas = resolved or cas or ""

            # Canonicalize CAS using name alias even if CAS present
            if name:
                canonical = self.resolve_name_to_cas(name)
                if canonical:
                    cas = canonical

            # Canonicalize CAS using direct CAS alias mapping
            cas = self.canonicalize_cas(cas) or cas

            # If we have a CAS, prefer the registry-declared role to fix misalignment issues
            reg_role = ""
            if cas and cas in self.cas_map:
                reg_role = (self.cas_map[cas].get('Role') or '').strip()
            # Normalize and choose role: prefer registry role when available
            if reg_role:
                role = self._norm_role(reg_role)

            # Prefer registry canonical name if CAS known
            display_name = name
            if cas and cas in self.cas_map:
                display_name = (self.cas_map[cas].get('Name') or name).strip()

            # Deduplicate by CAS if we have it
            if cas:
                entry = cas_to_entry.get(cas)
                if not entry:
                    entry = {"name": display_name, "cas": cas, "roles": set()}
                    cas_to_entry[cas] = entry
                entry["roles"].add(role)
                continue

            # Otherwise deduplicate by normalized name
            key = self._norm(display_name)
            entry = name_to_entry.get(key)
            if not entry:
                entry = {"name": display_name, "cas": "", "roles": set()}
                name_to_entry[key] = entry
            entry["roles"].add(role)

        # Build lines
        lines: List[str] = ["**Reagents:**"]
        # Emit only CAS-specified entries; drop name-only reagents (no CAS)
        for cas, entry in sorted(cas_to_entry.items()):
            # Normalize roles for stable output; drop UNK if we also have a specific one
            norm_roles = sorted(self._norm_role(r) for r in entry["roles"])
            if any(r != "UNK" for r in norm_roles):
                norm_roles = [r for r in norm_roles if r != "UNK"]
            roles = ", ".join(norm_roles)
            lines.append(f"  - {entry['name']} (CAS: {entry['cas']}) - Role: {roles}")
        # Intentionally skip name-only entries to avoid duplicates and unmapped reagents
        return "\n".join(lines) + "\n\n"
    
    def format_reference(self, row: Dict[str, Any]) -> str:
        """Format reference information for markdown output."""
        reference = row.get('Reference', '').strip()
        if not reference:
            return ""
        
        # Parse reference format: title | authors | citation | doi
        parts = [part.strip() for part in reference.split('|')]
        
        result = "**Reference:**\n"
        
        if len(parts) >= 1 and parts[0]:
            # Title (first part)
            result += f"  - **Title:** {parts[0]}\n"
        
        if len(parts) >= 2 and parts[1]:
            # Authors (second part)
            result += f"  - **Authors:** {parts[1]}\n"
        
        if len(parts) >= 3 and parts[2]:
            # Citation (third part)
            result += f"  - **Citation:** {parts[2]}\n"
        
        if len(parts) >= 4 and parts[3]:
            # DOI (fourth part)
            doi = parts[3].strip()
            if doi:
                # Format DOI as a clickable link
                result += f"  - **DOI:** [https://doi.org/{doi}](https://doi.org/{doi})\n"
        
        # If only one part or doesn't follow expected format, show as-is
        if len(parts) == 1 or not any(parts[1:]):
            result = f"**Reference:** {reference}\n"
        
        return result + "\n"
    
    def clean_original_line(self, line: str) -> str:
        """Clean up SciFinder formatting artifacts from original text lines."""
        cleaned = line.strip()
        
        # Skip empty lines or lines with only pipes and spaces
        if not cleaned or set(cleaned) <= {' ', '|'}:
            return ""
        
        # Remove leading and trailing pipes
        cleaned = cleaned.strip('|').strip()
        
        # Clean up multiple consecutive spaces
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Filter out scheme headers (e.g., "164. Scheme 164 (1 Reaction)")
        scheme_pattern = r'^\d+\.\s*Scheme\s+\d+\s*\(\d+\s*Reactions?\)$'
        if re.match(scheme_pattern, cleaned, re.IGNORECASE):
            return ""
        
        # Filter out the standard SciFinder footer
        if cleaned == "View All Sources in CAS SciFinder":
            return ""
        
        # If after cleaning we only have empty content, return empty
        if not cleaned:
            return ""
        
        return cleaned

    def format_original_text(self, row: Dict[str, Any]) -> str:
        """Format original text information for markdown output with cleaned formatting."""
        original_text = row.get('original_text', [])
        if not original_text:
            return ""
        
        result = "**Original Text:**\n"
        result += "```\n"
        
        for line in original_text:
            cleaned_line = self.clean_original_line(line)
            if cleaned_line:  # Only add non-empty lines
                result += cleaned_line + "\n"
        
        result += "```\n"
        
        return result + "\n"
    
    def generate_reaction_markdown(self, row: Dict[str, Any]) -> str:
        """Generate markdown content for a single reaction with validation."""
        reaction_id = row.get('ReactionID', 'Unknown')
        reaction_type = row.get('ReactionType', 'Unknown')
        
        # Clear warnings for this reaction
        self.validation_warnings = []
        
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
        
        # Format catalytic system with validation
        if full_catalytic:
            markdown += self.format_compound_list(full_catalytic, "Full Catalytic System")
        
        if catalyst_core:
            markdown += self.format_compound_list(catalyst_core, "Catalyst Core")
        
        if catalyst_generic:
            markdown += f"**Generic Catalyst:** {', '.join(catalyst_generic)}\n\n"
        
        if ligands:
            markdown += self.format_compound_list(ligands, "Ligands")
        
        # Format reagents with roles and validation
        if reagents:
            markdown += self.format_reagents(reagents, reagent_roles)
        
        if solvents:
            markdown += self.format_compound_list(solvents, "Solvents")
        
        # Add reaction conditions
        markdown += self.format_reaction_conditions(row)
        
        # Add SMILES if available
        markdown += self.format_smiles(row)
        
        # Add reference
        markdown += self.format_reference(row)
        
        # Add original text if available
        markdown += self.format_original_text(row)
        
        # Add validation warnings if any
        if self.validation_warnings:
            markdown += "**Data Quality Warnings:**\n"
            for warning in self.validation_warnings:
                markdown += f"  - ⚠️ {warning}\n"
            markdown += "\n"
        
        # Add separator
        markdown += "---\n\n"
        
        return markdown
    
    def generate_summary_statistics(self, rows: List[Dict[str, Any]]) -> str:
        """Generate summary statistics for the markdown report with data quality metrics."""
        if not rows:
            return "## Summary\n\nNo reactions found.\n\n"
        
        # Count reaction types
        reaction_types = defaultdict(int)
        total_reactions = len(rows)
        reactions_with_yield = 0
        avg_yield = 0
        total_warnings = 0
        reactions_with_warnings = 0
        
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
        
        # Add data quality section
        markdown += "**Data Quality Notes:**\n"
        markdown += "  - CAS number validation and correction enabled\n"
        markdown += "  - Compound name/CAS mismatches are automatically flagged\n"
        markdown += "  - Manual corrections applied for known common compounds\n"
        markdown += "  - Look for ⚠️ warnings in individual reactions for data quality issues\n\n"
        
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
            
            # Also generate JSONL export for analysis
            jsonl_path = output_path.replace('.md', '.jsonl')
            self.generate_jsonl_export(rows, jsonl_path, folder_path)
            
            if progress_callback:
                progress_callback(f"Report generated successfully: {output_path}")
                progress_callback(f"JSONL export generated: {jsonl_path}")
            
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
    
    def generate_jsonl_export(self, rows: List[Dict[str, Any]], output_path: str, source_folder: str):
        """Generate JSONL export for data analysis and machine learning."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for row in rows:
                # Create analysis-optimized record
                analysis_record = self.prepare_analysis_record(row)
                
                # Write as single line JSON
                f.write(json.dumps(analysis_record, ensure_ascii=False) + '\n')
    
    def prepare_analysis_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a reaction record optimized for analysis and ML."""
        
        # Parse JSON fields safely
        def safe_json_parse(value, default=None):
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default if default is not None else []
            return value if value is not None else (default if default is not None else [])
        
        # Extract and clean data
        catalyst_core = safe_json_parse(row.get('CatalystCoreDetail', '[]'))
        catalyst_generic = safe_json_parse(row.get('CatalystCoreGeneric', '[]'))
        ligands = safe_json_parse(row.get('Ligand', '[]'))
        full_catalytic = safe_json_parse(row.get('FullCatalyticSystem', '[]'))
        reagents = safe_json_parse(row.get('Reagent', '[]'))
        reagent_roles = safe_json_parse(row.get('ReagentRole', '[]'))
        solvents = safe_json_parse(row.get('Solvent', '[]'))
        original_text_raw = row.get('original_text', [])
        
        # Clean original text for better readability
        original_text = []
        for line in original_text_raw:
            cleaned_line = self.clean_original_line(line)
            if cleaned_line:  # Only add non-empty lines
                original_text.append(cleaned_line)
        
        # Parse reference
        reference_raw = row.get('Reference', '')
        reference_parts = [part.strip() for part in reference_raw.split('|')] if reference_raw else []
        
        reference = {
            'title': reference_parts[0] if len(reference_parts) > 0 else '',
            'authors': reference_parts[1] if len(reference_parts) > 1 else '',
            'citation': reference_parts[2] if len(reference_parts) > 2 else '',
            'doi': reference_parts[3] if len(reference_parts) > 3 else '',
            'raw': reference_raw
        }
        
        # Extract compound information with CAS numbers
        def extract_compounds(compound_list):
            compounds = []
            for item in compound_list:
                if '|' in item:
                    name, cas = item.split('|', 1)
                    compounds.append({
                        'name': name.strip(),
                        'cas': cas.strip()
                    })
                else:
                    compounds.append({
                        'name': item.strip(),
                        'cas': ''
                    })
            return compounds
        
        # Combine reagents with roles
        reagent_data = []
        for i, reagent in enumerate(reagents):
            role = reagent_roles[i] if i < len(reagent_roles) else 'UNK'
            if '|' in reagent:
                name, cas = reagent.split('|', 1)
                reagent_data.append({
                    'name': name.strip(),
                    'cas': cas.strip(),
                    'role': role
                })
            else:
                reagent_data.append({
                    'name': reagent.strip(),
                    'cas': '',
                    'role': role
                })
        
        # Parse numerical values safely
        def safe_float(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Build analysis-optimized record
        analysis_record = {
            # Basic identifiers
            'reaction_id': row.get('ReactionID', ''),
            'reaction_type': row.get('ReactionType', ''),
            
            # Catalytic system (structured)
            'catalyst': {
                'core': extract_compounds(catalyst_core),
                'generic': catalyst_generic,
                'ligands': extract_compounds(ligands),
                'full_system': extract_compounds(full_catalytic)
            },
            
            # Reagents (structured with roles)
            'reagents': reagent_data,
            
            # Solvents (structured)
            'solvents': extract_compounds(solvents),
            
            # Reaction conditions
            'conditions': {
                'temperature_c': safe_float(row.get('Temperature_C')),
                'time_h': safe_float(row.get('Time_h')),
                'yield_pct': safe_float(row.get('Yield_%'))
            },
            
            # Chemical structures
            'smiles': {
                'reactants': row.get('ReactantSMILES', ''),
                'products': row.get('ProductSMILES', '')
            },
            
            # Reference information (structured)
            'reference': reference,
            
            # Original text for debugging/analysis
            'original_text': original_text,
            
            # Computed signatures for similarity analysis
            'signatures': {
                'cond_key': row.get('CondKey', ''),
                'cond_sig': row.get('CondSig', ''),
                'fam_sig': row.get('FamSig', '')
            },
            
            # Raw data preservation
            'raw_data': {
                'raw_cas': row.get('RawCAS', ''),
                'raw_data_json': row.get('RawData', ''),
                'enriched_names': {
                    'reactants': safe_json_parse(row.get('RCTName', '[]')),
                    'products': safe_json_parse(row.get('PROName', '[]')),
                    'reagents': safe_json_parse(row.get('RGTName', '[]')),
                    'catalysts': safe_json_parse(row.get('CATName', '[]')),
                    'solvents': safe_json_parse(row.get('SOLName', '[]'))
                }
            },
            
            # Metadata
            'metadata': {
                'export_timestamp': datetime.now().isoformat(),
                'export_version': '1.0'
            }
        }
        
        return analysis_record


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
            "Select a folder containing RDF/TXT pairs to generate reports in two formats:\n"
            "• Markdown (.md) - Human-readable reports with reaction details\n"
            "• JSONL (.jsonl) - Structured data for analysis and machine learning\n"
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
                jsonl_output = output.replace('.md', '.jsonl')
                QtWidgets.QMessageBox.information(
                    self, "Success", 
                    f"Reports generated successfully!\n\n"
                    f"Markdown: {output}\n"
                    f"JSONL: {jsonl_output}\n\n"
                    f"The JSONL file is optimized for data analysis and machine learning."
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
