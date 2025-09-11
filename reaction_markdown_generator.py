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
            "bis(1,5 cyclooctadiene)nickel": "244261-66-3",
            "bis(cyclooctadiene)nickel": "244261-66-3",
            # Nickel chloride common forms
            "nickel dichloride": "7718-54-9",
            "nickel(ii) chloride": "7718-54-9",
            "nickel chloride": "7718-54-9",
            "nicl2": "7718-54-9",
            "ni cl2": "7718-54-9",
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

    @staticmethod
    def _role_from_compound_type(compound_type: Optional[str]) -> Optional[str]:
        """Map registry compound_type to normalized role tokens used in output.

        Mapping:
        - catalyst_core -> CAT_CORE
        - ligand        -> CAT_LIG
        - base          -> BASE
        - solvent       -> SOLVENT
        """
        if not compound_type:
            return None
        ct = str(compound_type).strip().lower()
        if ct == 'catalyst_core':
            return 'CAT_CORE'
        if ct == 'ligand':
            return 'CAT_LIG'
        if ct == 'base':
            return 'BASE'
        if ct == 'solvent':
            return 'SOLVENT'
        return None
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
    
    def format_compound_list(self, compound_list: List[str], title: str, allow_name_only: bool = False) -> str:
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

                # If still missing or invalid CAS, optionally keep name-only when allowed
                if (not corrected_cas) or (not self.cas_registry.validate_cas_format(corrected_cas)):
                    if allow_name_only and name:
                        norm_name = self._norm(name)
                        if norm_name not in seen_names:
                            seen_names.add(norm_name)
                            lines.append(f"  - {name} (CAS: unknown)")
                            self.validation_warnings.append(f"{title}: No valid CAS for '{name}' — kept as name-only")
                    continue

                norm_name = self._norm(corrected_name)
                if corrected_cas:
                    if corrected_cas in seen_cas:
                        continue  # duplicate by CAS
                    seen_cas.add(corrected_cas)
                    # Prefer registry abbreviation, then registry name, then corrected_name
                    display_name = self.cas_registry.get_display_name(corrected_name, corrected_cas)
                    seen_names.add(self._norm(display_name))
                    # Role conflict warning: prefer compound_type over legacy Role
                    ctype = self.cas_registry.get_compound_type(corrected_cas)
                    rr = self._role_from_compound_type(ctype) or 'UNK'
                    if rr != 'UNK':
                        # Heuristics: title determines expected role family
                        tl = title.lower()
                        expected = ''
                        if 'solvent' in tl:
                            expected = 'SOLVENT'
                        elif 'ligand' in tl:
                            expected = 'CAT_LIG'
                        elif 'catalyst core' in tl or ('catalytic' in tl and 'system' in tl):
                            expected = 'CAT_CORE'
                        elif 'reagent' in tl:
                            # reagents handled in format_reagents
                            expected = ''
                        if expected and rr != expected:
                            self.validation_warnings.append(
                                f"{title}: Role conflict for '{display_name}' (CAS {corrected_cas}): registry compound_type -> {rr}"
                            )
                    if display_name != corrected_cas:
                        lines.append(f"  - {display_name} (CAS: {corrected_cas})")
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
                    display_name = self.cas_registry.get_display_name(name, cas_resolved)
                    norm_reg_name = self._norm(display_name)
                    if cas_resolved in seen_cas or norm_reg_name in seen_names:
                        continue
                    seen_cas.add(cas_resolved)
                    seen_names.add(norm_reg_name)
                    lines.append(f"  - {display_name} (CAS: {cas_resolved})")
                else:
                    # Cannot resolve to CAS; keep name-only if allowed
                    if allow_name_only and name:
                        if norm_name not in seen_names:
                            seen_names.add(norm_name)
                            lines.append(f"  - {name} (CAS: unknown)")
                            self.validation_warnings.append(f"{title}: No CAS for '{name}' — kept as name-only")
                    # otherwise drop entry
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
            provided_role = self._norm_role(reagent_roles[i] if i < len(reagent_roles) else "UNK")
            role = provided_role
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

            # If we have a CAS, prefer the registry compound_type → role mapping
            reg_role = ""
            if cas:
                ctype = self.cas_registry.get_compound_type(cas)
                mapped = self._role_from_compound_type(ctype)
                if mapped:
                    reg_role = mapped
                elif cas in self.cas_map:
                    reg_role = (self.cas_map[cas].get('Role') or '').strip()
            # Normalize and choose role: prefer registry role when available
            if reg_role:
                role = self._norm_role(reg_role)
                # Warn if the original provided role conflicts significantly
                prov = provided_role
                if prov != 'UNK' and role != prov:
                    self.validation_warnings.append(
                        f"Reagents: Role conflict for '{name}' (CAS {cas}): TXT role {prov}, registry role {role}"
                    )

            # Prefer registry abbreviation/name if CAS known
            display_name = name
            if cas:
                display_name = self.cas_registry.get_display_name(name, cas)

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
            markdown += self.format_compound_list(full_catalytic, "Full Catalytic System", allow_name_only=True)

        # Compute and render ConditionCore (replaces "Catalyst Core")
        cc_label = self._compute_condition_core_label(
            catalyst_core=catalyst_core,
            ligands=ligands,
            full_catalytic=full_catalytic,
            catalyst_generic=catalyst_generic,
        )
        if cc_label:
            markdown += f"**ConditionCore:** {cc_label}\n\n"

        if catalyst_generic:
            markdown += f"**Generic Catalyst:** {', '.join(catalyst_generic)}\n\n"
        
        if ligands:
            markdown += self.format_compound_list(ligands, "Ligands", allow_name_only=True)
        
        # Format reagents with roles and validation
        if reagents:
            markdown += self.format_reagents(reagents, reagent_roles)
        
        # Always show solvents; if empty, formatter will print None
        markdown += self.format_compound_list(solvents, "Solvents", allow_name_only=False)
        
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

    def _compute_condition_core_label(
        self,
        catalyst_core: List[str],
        ligands: List[str],
        full_catalytic: List[str],
        catalyst_generic: List[str],
    ) -> str:
        """Derive a concise ConditionCore label like 'Pd/XPhos' or 'HATU/DMAP'.

        Heuristics:
        - Prefer using the Full Catalytic System list; fallback to CatalystCore + Ligands.
        - Determine roles via CAS registry compound_type: metal/catalyst_core vs ligand vs activator.
        - Prefer a generic metal symbol from 'catalyst_generic' or registry entry 'generic_core'.
                - NEW: If any entry is a preformed metal complex (compound_type == 'preformed metal complex'),
                    use the complex name(s) directly (e.g., 'PdCl2(dppf)') and do not add extra ligands.
        - If metal and ligand present: 'Metal/Ligand'. If only metal: 'Metal'.
          If activator + ligand present (no metal): 'Activator/Ligand'.
        - As a last resort, join the first two components with '/'.
        """

        def parse_compounds(items: List[str]) -> List[Dict[str, str]]:
            out = []
            for it in items or []:
                if '|' in it:
                    name, cas = it.split('|', 1)
                    cas = cas.strip()
                    disp = self.cas_registry.get_display_name(name.strip(), cas)
                    ctype = self.cas_registry.get_compound_type(cas) or ''
                    entry = self.cas_registry.get_registry_entry(cas) or {}
                    gen = (entry.get('generic_core') or '').strip()
                    out.append({'name': disp, 'cas': cas, 'type': ctype, 'generic': gen})
                else:
                    # No CAS: keep name and empty cas/type; may still help as fallback
                    out.append({'name': it.strip(), 'cas': '', 'type': '', 'generic': ''})
            return out

        # Build candidate pool
        pool = parse_compounds(full_catalytic) if full_catalytic else (
            parse_compounds(catalyst_core) + parse_compounds(ligands)
        )

        if not pool and not catalyst_generic:
            return ""

        # Partition by role
        def is_metal(t: str) -> bool:
            t2 = (t or '').lower()
            return t2 in {"metal", "catalyst_core", "cat_core"}

        def is_ligand(t: str) -> bool:
            t2 = (t or '').lower()
            return t2 in {"ligand", "cat_lig"}

        def is_activator(t: str) -> bool:
            t2 = (t or '').lower()
            return t2 in {"activator", "activator_system", "activator_cat", "activator/core", "activator/core?", "activator?", "activator_core", "activator-core", "activatorbase", "activator/base", "activator/base?", "activatoradditive", "activator_additive", "activator/additive"}

        def is_preformed_complex(t: str) -> bool:
            # Normalize various hyphens/dashes and whitespace; compare loosely
            t2 = (t or '').lower().replace('\u2013', '-').replace('\u2014', '-').strip()
            return t2 == 'preformed metal complex' or t2 == 'preformed metal-ligand catalyst' or (
                'preformed' in t2 and 'metal' in t2 and ('complex' in t2 or 'catalyst' in t2)
            )

        metals = [c for c in pool if is_metal(c.get('type', ''))]
        ligs = [c for c in pool if is_ligand(c.get('type', ''))]
        acts = [c for c in pool if is_activator(c.get('type', ''))]
        preformed = [c for c in pool if is_preformed_complex(c.get('type', ''))]

        # If there are any preformed metal complexes, prefer using them directly
        if preformed:
            labels = [c.get('name', '') for c in preformed if c.get('name')]
            # If no names found (unlikely), fall back to CAS or empty-safe strings
            if not labels:
                labels = [c.get('cas', '') for c in preformed if c.get('cas')]
            # Join multiple complexes with ' + '
            return ' + '.join([lbl for lbl in labels if lbl])

        # Pick labels
        def pick_metal_label() -> str:
            # 1) Prefer explicit generic catalyst symbol if provided
            if catalyst_generic:
                return catalyst_generic[0]
            # 2) Prefer registry-provided generic_core
            for m in metals:
                if m.get('generic'):
                    return m['generic']
            # 3) Derive simple symbol from name (e.g., 'Pd(OAc)2' -> 'Pd')
            for m in metals:
                nm = m.get('name', '')
                m2 = re.search(r"\b(Pd|Ni|Cu|Pt|Rh|Ru|Ir|Co|Fe|Ag|Au|Mn|Cr|Mo|W|V|Ti|Zr|Hf|Sc|Y|La|Zn)\b", nm)
                if m2:
                    return m2.group(1)
            # 4) Fallback to first metal name
            if metals:
                return metals[0].get('name', '')
            return ""

        def pick_label(items: List[Dict[str, str]]) -> str:
            return items[0].get('name', '') if items else ''

        metal_label = pick_metal_label()
        ligand_label = pick_label(ligs)
        activator_label = pick_label(acts)

        if metal_label and ligand_label:
            return f"{metal_label}/{ligand_label}"
        if metal_label:
            # Enhancement: if multiple distinct metals present and no ligand, join them with '+' before placeholder.
            if len(metals) > 1:
                metal_syms: List[str] = []
                seen = set()
                metal_regex = re.compile(r"\b(Pd|Ni|Cu|Pt|Rh|Ru|Ir|Co|Fe|Ag|Au|Mn|Cr|Mo|W|V|Ti|Zr|Hf|Sc|Y|La|Zn)\b")
                for m in metals:
                    sym = ''
                    # Prefer generic field
                    if m.get('generic'):
                        sym = m['generic']
                    else:
                        nm = m.get('name','')
                        mr = metal_regex.search(nm)
                        if mr:
                            sym = mr.group(1)
                        else:
                            # fallback: first token up to space or punctuation (trim long names)
                            tok = re.split(r"[\s,;/]", nm.strip())[0]
                            sym = tok[:3] if tok else ''
                    if sym and sym not in seen:
                        seen.add(sym)
                        metal_syms.append(sym)
                    if len(metal_syms) >= 3:  # cap to avoid excessively long labels
                        break
                if metal_syms and '+'.join(metal_syms) != metal_label:
                    metal_label = '+'.join(metal_syms)
            # Requirement: when a metal is identified but no ligand resolved, emit a canonical placeholder '/*'.
            return f"{metal_label}/*"
        if activator_label and ligand_label:
            return f"{activator_label}/{ligand_label}"
        # Last resort: join the first two components of pool
        if len(pool) >= 2:
            return f"{pool[0]['name']}/{pool[1]['name']}"
        return pool[0]['name'] if pool else ""
    
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
                    cas = cas.strip()
                    disp = self.cas_registry.get_display_name(name.strip(), cas)
                    compounds.append({
                        'name': disp,
                        'cas': cas
                    })
                else:
                    compounds.append({
                        'name': item.strip(),
                        'cas': ''
                    })
            return compounds
        
        # Combine reagents with roles (prefer registry compound_type mapping)
        reagent_data = []
        for i, reagent in enumerate(reagents):
            provided_role = reagent_roles[i] if i < len(reagent_roles) else 'UNK'
            role = provided_role
            if '|' in reagent:
                name, cas = reagent.split('|', 1)
                cas = cas.strip()
                ctype = self.cas_registry.get_compound_type(cas)
                mapped = self._role_from_compound_type(ctype)
                if mapped:
                    role = mapped
                disp = self.cas_registry.get_display_name(name.strip(), cas)
                reagent_data.append({
                    'name': disp,
                    'cas': cas,
                    'role': self._norm_role(role)
                })
            else:
                reagent_data.append({
                    'name': reagent.strip(),
                    'cas': '',
                    'role': self._norm_role(role)
                })
        
        # Parse numerical values safely
        def safe_float(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Compute ConditionCore label for analysis
        condition_core_label = self._compute_condition_core_label(
            catalyst_core=catalyst_core,
            ligands=ligands,
            full_catalytic=full_catalytic,
            catalyst_generic=catalyst_generic,
        )

        # Build analysis-optimized record
        analysis_record = {
            # Basic identifiers
            'reaction_id': row.get('ReactionID', ''),
            'reaction_type': row.get('ReactionType', ''),
            'condition_core': condition_core_label,
            
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
