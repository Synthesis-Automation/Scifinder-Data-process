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

Registry Coverage:
- 159 total compounds with CAS numbers
- 22 bases (including K2CO3, Cs2CO3, Et3N, DBU, etc.)
- 64 ligands (including PPh3, SPhos, XPhos, BINAP, DPPF, etc.)
- 64 solvents (including DMF, THF, toluene, acetonitrile, etc.)
- 9 catalyst cores (including PdCl2, CuI, Pd2(dba)3, etc.)

Data Sources:
- Comprehensive mapping from reagents JSON files
- Common organometallic chemistry reagents
- Cross-coupling reaction components
- Literature-validated CAS numbers

Usage:
    python cas_registry_tool.py --validate "123-45-6"
    python cas_registry_tool.py --lookup "6737-42-4"
    python cas_registry_tool.py --batch-validate input.csv
    python cas_registry_tool.py --build-registry folder_with_cas_maps
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple, Any, Iterable, Callable
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
        """Load comprehensive CAS registry for chemical compounds."""
        return {
            # Bases from JSON
            "584-08-7": "K2CO3",
            "534-17-8": "Cs2CO3",
            "7778-53-2": "K3PO4", 
            "865-47-4": "KOtBu",
            "865-48-5": "NaOtBu",
            "121-44-8": "Et3N",
            "7087-68-5": "DIPEA",
            "6674-22-2": "DBU",
            "3001-72-7": "DBN",
            "1310-58-3": "KOH",
            "497-19-8": "Na2CO3",
            "110-86-1": "Pyridine",
            "7646-69-7": "NaH",
            "1310-73-2": "NaOH",
            "144-55-8": "NaHCO3",
            "109-72-8": "n-BuLi",
            "1310-66-3": "LiOH",
            "110-89-4": "Piperidine",
            "109-02-4": "4-Methylmorpholine",
            "1122-58-3": "DMAP",
            "124-41-4": "NaOMe",
            "1336-21-6": "NH4OH",
            "4039-32-1": "LiHMDS",
            "108-48-5": "2,6-Lutidine",
            
            # Ligands from JSON - Phosphines
            "603-35-0": "PPh3",
            "2622-14-2": "PCy3",
            "13716-12-6": "PtBu3",
            "6163-58-2": "P(o-tol)3",
            "1038-95-5": "P(p-tol)3",
            "18437-78-2": "P(p-F-Ph)3",
            "1159-54-2": "P(p-Cl-Ph)3",
            "1160-71-4": "P(p-CF3-Ph)3",
            "1486-28-8": "PMePh2",
            "672-66-2": "PMe2Ph",
            "594-09-2": "PMe3",
            "554-70-1": "PEt3",
            "998-40-3": "P(nBu)3",
            "6476-36-4": "P(iPr)3",
            "5518-52-5": "P(2-furyl)3",
            "1757-50-8": "P(C6F5)3",
            "855-38-9": "P(p-MeO-Ph)3",
            "4731-65-1": "P(o-MeO-Ph)3",
            "23897-15-6": "P(mes)3",
            
            # Buchwald ligands
            "657408-07-6": "SPhos",
            "564483-18-7": "XPhos",
            "787618-22-8": "RuPhos",
            "1028206-60-1": "BrettPhos",
            "564483-19-8": "tBuXPhos",
            "145052-34-0": "JohnPhos",
            "213697-53-1": "DavePhos",
            "173219-46-8": "MePhos",
            "1374640-42-8": "AmplPhos",
            "384347-21-1": "QPhos",
            "200001-74-9": "CyJohnPhos",
            "1447953-76-7": "AlPhos",
            "1429311-55-2": "Me4tBuXPhos",
            "1447977-56-7": "AdBrettPhos",
            "1447977-55-6": "tBuBrettPhos",
            "1185098-04-7": "Ph-XPhos",
            "1447952-32-2": "MorDalPhos",
            
            # Bidentate ligands
            "2250-01-3": "BINAP",
            "99646-27-4": "Tol-BINAP",
            "117016-01-8": "H8-BINAP",
            "58467-99-1": "BIPHEP",
            "52364-71-3": "MeO-BIPHEP",
            "145854-69-9": "SEGPHOS",
            "196868-63-0": "DM-SEGPHOS",
            "243984-11-4": "DTBM-SEGPHOS",
            "150992-96-0": "C3-TunePhos",
            "156707-92-7": "DifluorPhos",
            "205319-91-7": "SynPhos",
            "1663-45-2": "DPPE",
            "6737-42-4": "DPPP",
            "7688-25-7": "DPPB",
            "12150-46-8": "DPPF",
            "161265-03-8": "XantPhos",
            "166330-10-5": "DPEPhos",
            
            # N-heterocyclic carbenes
            "246047-72-3": "IPr",
            "141556-45-8": "IMes",
            "343970-73-8": "SIPr",
            "141556-44-7": "SIMes",
            "250285-32-6": "IPrCl",
            
            # Nitrogen ligands
            "110-18-9": "TMEDA",
            "110-86-1": "Pyridine",
            "66-71-7": "Phenanthroline",
            "366-18-7": "Bipyridine",
            "1122-58-3": "4-DMAP",
            "6674-22-2": "DBU",
            "280-57-9": "DABCO",
            
            # Solvents from JSON
            "64-19-7": "Acetic Acid",
            "67-64-1": "Acetone",
            "75-05-8": "Acetonitrile",
            "71-43-2": "Benzene",
            "71-36-3": "1-Butanol",
            "78-92-2": "2-Butanol",
            "75-65-0": "tert-Butanol",
            "56-23-5": "Carbon Tetrachloride",
            "67-66-3": "Chloroform",
            "110-82-7": "Cyclohexane",
            "75-09-2": "Dichloromethane",
            "60-29-7": "Diethyl Ether",
            "68-12-2": "Dimethylformamide",
            "67-68-5": "Dimethyl Sulfoxide",
            "64-17-5": "Ethanol",
            "141-78-6": "Ethyl Acetate",
            "110-54-3": "Hexane",
            "67-56-1": "Methanol",
            "71-23-8": "1-Propanol",
            "67-63-0": "2-Propanol",
            "110-86-1": "Pyridine",
            "109-99-9": "THF",
            "108-88-3": "Toluene",
            "7732-18-5": "Water",
            "108-38-3": "m-Xylene",
            "95-47-6": "o-Xylene",
            "106-42-3": "p-Xylene",
            "107-06-2": "1,2-Dichloroethane",
            "123-91-1": "1,4-Dioxane",
            "108-90-7": "Chlorobenzene",
            "108-94-1": "Cyclohexanone",
            "142-96-1": "Dibutyl Ether",
            "108-20-3": "Diisopropyl Ether",
            "107-21-1": "Ethylene Glycol",
            "142-82-5": "Heptane",
            "78-83-1": "Isobutanol",
            "108-21-4": "Isopropyl Acetate",
            "78-93-3": "Methyl Ethyl Ketone",
            "872-50-4": "N-Methyl-2-pyrrolidone",
            "75-52-5": "Nitromethane",
            "109-66-0": "Pentane",
            "79-09-4": "Propionic Acid",
            "127-18-4": "Tetrachloroethylene",
            "121-44-8": "Triethylamine",
            "109-86-4": "2-Methoxyethanol",
            "123-86-4": "Butyl Acetate",
            "111-46-6": "Diethylene Glycol",
            "920-66-1": "Hexafluoroisopropanol",
            "96-47-9": "MeTHF",
            "5614-37-9": "Cyclopentyl methyl ether",
            "108-10-1": "Methyl isobutyl ketone",
            "75-85-4": "t-Amyl-OH",
            "127-19-5": "Dimethylacetamide",
            "110-71-4": "1,2-Dimethoxyethane",
            "75-89-8": "2,2,2-Trifluoroethanol",
            "95-50-1": "1,2-Dichlorobenzene",
            "1634-04-4": "tert-Butyl methyl ether",
            "108-24-7": "Acetic anhydride",
            "25322-68-3": "Polyethylene glycol (PEG-400)",
            "110-80-5": "2-Ethoxyethanol",
            "76-05-1": "Trifluoroacetic acid",
            "1076-43-3": "Benzene-d6",
            "98-08-8": "(Trifluoromethyl)benzene",
            "98-95-3": "Nitrobenzene",
            "108-67-8": "Mesitylene",
            "1330-20-7": "Xylene (mixed isomers)",
            "109-99-9": "Tetrahydrofuran",
            "67-63-0": "Isopropanol",
            "96-47-9": "2-Methyltetrahydrofuran",
            "109-86-4": "Glycol monoethyl ether",
            "920-66-1": "1,1,1,3,3,3-Hexafluoro-2-propanol",
            "75-85-4": "2-Methyl-2-butanol",
            
            # Additional catalyst cores
            "7647-10-1": "PdCl2",
            "32005-36-0": "Pd(dba)2",
            "51364-51-3": "Pd2(dba)3",
            "142-71-2": "Cu(OAc)2",
            "7681-65-4": "CuI",
            "7758-89-6": "CuCl",
            "1317-39-1": "Cu2O",
            "7447-39-4": "CuCl2",
            "7787-70-4": "CuBr",
        }
    
    def _load_compound_types(self) -> Dict[str, str]:
        """Load comprehensive compound type classifications."""
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
            
            # Phosphine ligands - monodentate
            "603-35-0": "ligand",          # PPh3
            "2622-14-2": "ligand",         # PCy3
            "13716-12-6": "ligand",        # PtBu3
            "6163-58-2": "ligand",         # P(o-tol)3
            "1038-95-5": "ligand",         # P(p-tol)3
            "18437-78-2": "ligand",        # P(p-F-Ph)3
            "1159-54-2": "ligand",         # P(p-Cl-Ph)3
            "1160-71-4": "ligand",         # P(p-CF3-Ph)3
            "1486-28-8": "ligand",         # PMePh2
            "672-66-2": "ligand",          # PMe2Ph
            "594-09-2": "ligand",          # PMe3
            "554-70-1": "ligand",          # PEt3
            "998-40-3": "ligand",          # P(nBu)3
            "6476-36-4": "ligand",         # P(iPr)3
            "5518-52-5": "ligand",         # P(2-furyl)3
            "1757-50-8": "ligand",         # P(C6F5)3
            "855-38-9": "ligand",          # P(p-MeO-Ph)3
            "4731-65-1": "ligand",         # P(o-MeO-Ph)3
            "23897-15-6": "ligand",        # P(mes)3
            
            # Buchwald ligands
            "657408-07-6": "ligand",       # SPhos
            "564483-18-7": "ligand",       # XPhos
            "787618-22-8": "ligand",       # RuPhos
            "1028206-60-1": "ligand",      # BrettPhos
            "564483-19-8": "ligand",       # tBuXPhos
            "145052-34-0": "ligand",       # JohnPhos
            "213697-53-1": "ligand",       # DavePhos
            "173219-46-8": "ligand",       # MePhos
            "1374640-42-8": "ligand",      # AmplPhos
            "384347-21-1": "ligand",       # QPhos
            "200001-74-9": "ligand",       # CyJohnPhos
            "1447953-76-7": "ligand",      # AlPhos
            "1429311-55-2": "ligand",      # Me4tBuXPhos
            "1447977-56-7": "ligand",      # AdBrettPhos
            "1447977-55-6": "ligand",      # tBuBrettPhos
            "1185098-04-7": "ligand",      # Ph-XPhos
            "1447952-32-2": "ligand",      # MorDalPhos
            
            # Bidentate phosphine ligands
            "2250-01-3": "ligand",         # BINAP
            "99646-27-4": "ligand",        # Tol-BINAP
            "117016-01-8": "ligand",       # H8-BINAP
            "58467-99-1": "ligand",        # BIPHEP
            "52364-71-3": "ligand",        # MeO-BIPHEP
            "145854-69-9": "ligand",       # SEGPHOS
            "196868-63-0": "ligand",       # DM-SEGPHOS
            "243984-11-4": "ligand",       # DTBM-SEGPHOS
            "150992-96-0": "ligand",       # C3-TunePhos
            "156707-92-7": "ligand",       # DifluorPhos
            "205319-91-7": "ligand",       # SynPhos
            "1663-45-2": "ligand",         # DPPE
            "6737-42-4": "ligand",         # DPPP
            "7688-25-7": "ligand",         # DPPB
            "12150-46-8": "ligand",        # DPPF
            "161265-03-8": "ligand",       # XantPhos
            "166330-10-5": "ligand",       # DPEPhos
            
            # N-heterocyclic carbenes
            "246047-72-3": "ligand",       # IPr
            "141556-45-8": "ligand",       # IMes
            "343970-73-8": "ligand",       # SIPr
            "141556-44-7": "ligand",       # SIMes
            "250285-32-6": "ligand",       # IPrCl
            
            # Nitrogen ligands
            "110-18-9": "ligand",          # TMEDA
            "110-86-1": "ligand",          # Pyridine (can be ligand or base)
            "66-71-7": "ligand",           # Phenanthroline
            "366-18-7": "ligand",          # Bipyridine
            "1122-58-3": "ligand",         # DMAP (can be ligand or base)
            "6674-22-2": "ligand",         # DBU (can be ligand or base)
            "280-57-9": "ligand",          # DABCO
            
            # Bases
            "584-08-7": "base",            # K2CO3
            "534-17-8": "base",            # Cs2CO3
            "7778-53-2": "base",           # K3PO4
            "865-47-4": "base",            # KOtBu
            "865-48-5": "base",            # NaOtBu
            "121-44-8": "base",            # Et3N
            "7087-68-5": "base",           # DIPEA
            "6674-22-2": "base",           # DBU
            "3001-72-7": "base",           # DBN
            "1310-58-3": "base",           # KOH
            "497-19-8": "base",            # Na2CO3
            "7646-69-7": "base",           # NaH
            "1310-73-2": "base",           # NaOH
            "144-55-8": "base",            # NaHCO3
            "109-72-8": "base",            # n-BuLi
            "1310-66-3": "base",           # LiOH
            "110-89-4": "base",            # Piperidine
            "109-02-4": "base",            # 4-Methylmorpholine
            "124-41-4": "base",            # NaOMe
            "1336-21-6": "base",           # NH4OH
            "4039-32-1": "base",           # LiHMDS
            "108-48-5": "base",            # 2,6-Lutidine
            
            # Solvents
            "64-19-7": "solvent",          # Acetic Acid
            "67-64-1": "solvent",          # Acetone
            "75-05-8": "solvent",          # Acetonitrile
            "71-43-2": "solvent",          # Benzene
            "71-36-3": "solvent",          # 1-Butanol
            "78-92-2": "solvent",          # 2-Butanol
            "75-65-0": "solvent",          # tert-Butanol
            "56-23-5": "solvent",          # Carbon Tetrachloride
            "67-66-3": "solvent",          # Chloroform
            "110-82-7": "solvent",         # Cyclohexane
            "75-09-2": "solvent",          # Dichloromethane
            "60-29-7": "solvent",          # Diethyl Ether
            "68-12-2": "solvent",          # Dimethylformamide
            "67-68-5": "solvent",          # Dimethyl Sulfoxide
            "64-17-5": "solvent",          # Ethanol
            "141-78-6": "solvent",         # Ethyl Acetate
            "110-54-3": "solvent",         # Hexane
            "67-56-1": "solvent",          # Methanol
            "71-23-8": "solvent",          # 1-Propanol
            "67-63-0": "solvent",          # 2-Propanol
            "109-99-9": "solvent",         # THF
            "108-88-3": "solvent",         # Toluene
            "7732-18-5": "solvent",        # Water
            "108-38-3": "solvent",         # m-Xylene
            "95-47-6": "solvent",          # o-Xylene
            "106-42-3": "solvent",         # p-Xylene
            "107-06-2": "solvent",         # 1,2-Dichloroethane
            "123-91-1": "solvent",         # 1,4-Dioxane
            "108-90-7": "solvent",         # Chlorobenzene
            "108-94-1": "solvent",         # Cyclohexanone
            "142-96-1": "solvent",         # Dibutyl Ether
            "108-20-3": "solvent",         # Diisopropyl Ether
            "107-21-1": "solvent",         # Ethylene Glycol
            "142-82-5": "solvent",         # Heptane
            "78-83-1": "solvent",          # Isobutanol
            "108-21-4": "solvent",         # Isopropyl Acetate
            "78-93-3": "solvent",          # Methyl Ethyl Ketone
            "872-50-4": "solvent",         # N-Methyl-2-pyrrolidone
            "75-52-5": "solvent",          # Nitromethane
            "109-66-0": "solvent",         # Pentane
            "79-09-4": "solvent",          # Propionic Acid
            "127-18-4": "solvent",         # Tetrachloroethylene
            "109-86-4": "solvent",         # 2-Methoxyethanol
            "123-86-4": "solvent",         # Butyl Acetate
            "111-46-6": "solvent",         # Diethylene Glycol
            "920-66-1": "solvent",         # Hexafluoroisopropanol
            "96-47-9": "solvent",          # MeTHF
            "5614-37-9": "solvent",        # Cyclopentyl methyl ether
            "108-10-1": "solvent",         # Methyl isobutyl ketone
            "75-85-4": "solvent",          # t-Amyl-OH
            "127-19-5": "solvent",         # Dimethylacetamide
            "110-71-4": "solvent",         # 1,2-Dimethoxyethane
            "75-89-8": "solvent",          # 2,2,2-Trifluoroethanol
            "95-50-1": "solvent",          # 1,2-Dichlorobenzene
            "1634-04-4": "solvent",        # tert-Butyl methyl ether
            "108-24-7": "solvent",         # Acetic anhydride
            "25322-68-3": "solvent",       # Polyethylene glycol (PEG-400)
            "110-80-5": "solvent",         # 2-Ethoxyethanol
            "76-05-1": "solvent",          # Trifluoroacetic acid
            "1076-43-3": "solvent",        # Benzene-d6
            "98-08-8": "solvent",          # (Trifluoromethyl)benzene
            "98-95-3": "solvent",          # Nitrobenzene
            "108-67-8": "solvent",         # Mesitylene
            "1330-20-7": "solvent",        # Xylene (mixed isomers)
            "75-85-4": "solvent",          # 2-Methyl-2-butanol
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
        """Look up compound information via PubChem API using CAS RN cross-reference.

        Returns a dict with keys: name, iupac_name, formula, molecular_weight, smiles,
        synonyms (List[str]), source.
        """
        if not REQUESTS_AVAILABLE:
            return None

        user_agent = "Scifinder-Data-Process/1.0 (+https://github.com/Synthesis-Automation)"
        headers = {"User-Agent": user_agent, "Accept": "application/json"}

        # Simple retry logic (network hiccups)
        last_err: Optional[str] = None
        for attempt in range(2):
            try:
                props_url = (
                    f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/RN/{cas}/"
                    "property/Title,IUPACName,MolecularFormula,MolecularWeight,IsomericSMILES/JSON"
                )
                resp = requests.get(props_url, timeout=12, headers=headers)
                title = iupac = formula = smiles = ""
                mw: Optional[Any] = None
                if resp.status_code == 200:
                    data = resp.json() or {}
                    props_list = (data.get('PropertyTable') or {}).get('Properties') or []
                    if props_list:
                        props = props_list[0]
                        title = (props.get('Title') or '').strip()
                        iupac = (props.get('IUPACName') or '').strip()
                        formula = (props.get('MolecularFormula') or '').strip()
                        mw = props.get('MolecularWeight')
                        # Try both SMILES field names
                        smiles = (props.get('IsomericSMILES') or props.get('SMILES') or '').strip()
                else:
                    last_err = f"status {resp.status_code}"

                # Synonyms
                syns: List[str] = []
                try:
                    syns_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/RN/{cas}/synonyms/JSON"
                    r2 = requests.get(syns_url, timeout=10, headers=headers)
                    if r2.status_code == 200:
                        d2 = r2.json() or {}
                        infos = (d2.get('InformationList') or {}).get('Information') or []
                        if infos and 'Synonym' in infos[0]:
                            syns = [s for s in infos[0]['Synonym'] if isinstance(s, str)]
                except Exception as se:  # noqa: F841
                    pass

                if any([title, iupac, formula, smiles]) or syns:
                    return {
                        'name': title or iupac or (syns[0] if syns else ''),
                        'iupac_name': iupac,
                        'formula': formula,
                        'molecular_weight': mw,
                        'smiles': smiles,
                        'synonyms': syns,
                        'source': 'PubChem',
                    }
            except Exception as e:
                last_err = str(e)
            # brief backoff only if first attempt failed and second to retry
        if last_err and os.environ.get('CAS_DEBUG'):
            print(f"[DEBUG] PubChem lookup failed for {cas}: {last_err}")
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
            if online_result and online_result.get('name'):
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

    # --- New: Append CAS entries into a JSONL registry ---
    def _load_jsonl_registry(self, jsonl_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Load a JSONL registry into a dict keyed by CAS (string). Keeps all variants per CAS."""
        reg: Dict[str, List[Dict[str, Any]]] = {}
        if not os.path.exists(jsonl_path):
            return reg
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    cas = (obj.get('cas') or obj.get('CAS') or '').strip()
                    if not cas:
                        continue
                    reg.setdefault(cas, []).append(obj)
                except Exception:
                    # Skip bad lines
                    continue
        return reg

    def _append_jsonl(self, jsonl_path: str, obj: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(jsonl_path) or '.', exist_ok=True)
        with open(jsonl_path, 'a', encoding='utf-8', newline='') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _choose_abbreviation(self, cas: str, name: str, synonyms: Optional[List[str]]) -> str:
        """Choose a suitable chemical abbreviation, avoiding code-like IDs.

        Rule:
        - Prefer a curated mapping for very common solvents/bases.
        - Otherwise, only accept from a conservative allowlist of known chemical abbreviations.
        - Reject code-like IDs (e.g., NSC-xxxx, DBxxxxx, UNxxxx, FDxxxxx, etc.).
        - If nothing suitable, return empty string.
        """
        known = {
            # solvents/bases
            '67-56-1': 'MeOH', '67-63-0': 'iPrOH', '64-17-5': 'EtOH', '68-12-2': 'DMF',
            '67-68-5': 'DMSO', '109-99-9': 'THF', '75-05-8': 'MeCN', '75-09-2': 'DCM',
            '121-44-8': 'TEA', '7087-68-5': 'DIPEA', '1122-58-3': 'DMAP',
        }
        if cas in known:
            return known[cas]

        allowlist = {
            # Solvents
            'MeOH','EtOH','iPrOH','tBuOH','tAmylOH','THF','MeTHF','MeCN','DCM','DCE','DMF','DMSO','NMP','EtOAc',
            # Bases / reagents
            'TEA','DIPEA','DMAP','DBU','DBN','KOtBu','NaOtBu','NaOMe','NaOEt','NaHCO3','K2CO3','Cs2CO3','Na2CO3',
            # Ligands / catalysts
            'BINAP','DPPF','XantPhos','DPEPhos','DPPP','DPPB','PPh3','PCy3','PMe3','PEt3','TMEDA','IPr','IMes','SIPr','SIMes',
            'SPhos','XPhos','RuPhos','JohnPhos','MePhos','CyJohnPhos','QPhos','AlPhos','Me4tBuXPhos',
            # Misc
            'PEG-400','tBuOMe','TFA','PhMe'
        }

        banned_prefixes = (
            'NSC','DB','UN','INS','FD','AS','SY','MB','SH','NA','FC','SB','STR'
        )
        def looks_banned(s: str) -> bool:
            ss = s.strip()
            if not ss:
                return True
            up = ss.upper()
            for pref in banned_prefixes:
                # forms like NSC12345, NSC-12345
                if up.startswith(pref) and re.search(r"\d", up):
                    return True
            # Overly numeric codes: >= 3 digits and no lowercase letters
            if re.fullmatch(r"[A-Z\-]*\d{3,}[A-Z\-]*", up):
                return True
            return False

        if synonyms:
            for s in synonyms:
                if s in allowlist:
                    return s
            for s in synonyms:
                if looks_banned(s):
                    continue
                # Very conservative acceptance: short alpha tokens like DMF, THF, NMP
                if re.fullmatch(r"[A-Za-z]{2,6}(?:-[0-9]{2,4})?", s):
                    if s.isupper() or s in allowlist:
                        return s

        # Do not fall back to using the proper name as abbreviation
        return ''

    def _build_jsonl_entry(self, cas: str, base_name: str = '') -> Tuple[Dict[str, Any], List[str]]:
        """Build a JSONL registry entry for a CAS using manual maps and web lookups.

        Returns (entry, warnings).
        """
        warnings: List[str] = []

        # Validate
        if not self.validate_cas_format(cas):
            warnings.append(f"Invalid CAS format: {cas}")
            return {}, warnings
        if not self.calculate_cas_checksum(cas):
            warnings.append(f"Invalid CAS checksum: {cas}")

        name = base_name.strip() if base_name else ''

        # Manual correction name if known (still allow enrichment from PubChem)
        manual_used = False
        if cas in self.manual_corrections:
            name = self.manual_corrections[cas]
            manual_used = True
            warnings.append("Name from manual corrections")

        # Always attempt PubChem lookup for enrichment (unless requests unavailable)
        online = self.lookup_pubchem(cas)
        syns: List[str] = []
        formula: Optional[str] = None
        mw: Optional[Any] = None
        smiles: Optional[str] = None
        if online:
            syns = list(online.get('synonyms') or [])
            formula = online.get('formula') or None
            mw = online.get('molecular_weight') or None
            smiles = online.get('smiles') or None
            if not manual_used and online.get('name') and (not name or name.lower() == cas.lower()):
                name = online['name']
                warnings.append("Name from PubChem")
            # If manual name used but differs from PubChem primary name, keep manual but note availability
            elif manual_used and online.get('name') and online['name'].lower() != name.lower():
                warnings.append("PubChem name differs (kept manual)")
        
        # If no manual correction and no PubChem data, reject the compound
        if not manual_used and not online:
            warnings.append("No PubChem data found; compound rejected")
            return {}, warnings

        ctype = self.get_compound_type(cas)
        abbreviation = self._choose_abbreviation(cas, name, syns)

        entry: Dict[str, Any] = {
            'cas': cas,
            'name': name or cas,
            'abbreviation': abbreviation,
            'generic_core': None,
            'category_hint': None,
            'token': None,
            'compound_type': ctype,
            'formula': formula,
            'molecular_weight': mw,
            'smile': smiles,
        }
        return entry, warnings

    def add_to_jsonl_registry(self, registry_path: str, cas_items: Iterable[str], dry_run: bool = False, progress_cb: Optional[Callable[[str], None]] = None) -> Tuple[int, int]:
        """Add new CAS entries to a JSONL registry if missing.

        Returns (added_count, skipped_existing_count).
        """
        reg = self._load_jsonl_registry(registry_path)
        added = 0
        skipped = 0
        for raw in cas_items:
            cas = (raw or '').strip()
            if not cas:
                continue
            if cas in reg and reg[cas]:
                skipped += 1
                msg = f"Skip (exists): {cas}"
                (progress_cb or print)(msg)
                continue
            entry, warns = self._build_jsonl_entry(cas)
            if not entry:
                msg = f"Skip (invalid): {cas} | {'; '.join(warns)}"
                (progress_cb or print)(msg)
                continue
            (progress_cb or print)(f"Add: {cas} → {entry.get('name','')} {'| ' + '; '.join(warns) if warns else ''}")
            if not dry_run:
                self._append_jsonl(registry_path, entry)
            added += 1
        return added, skipped

    # --- New: Text scanning utilities ---
    def extract_cas_from_text(self, file_path: str) -> List[str]:
        """Extract likely CAS RNs from any text-based file using regex and checksum.

        - Accepts any text file; opens with utf-8 and errors='ignore'.
        - Returns unique, order-preserving list of valid CAS (format + checksum).
        """
        cas_re = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")
        seen = set()
        result: List[str] = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    for match in cas_re.findall(line):
                        cas = match.strip()
                        if cas in seen:
                            continue
                        if self.validate_cas_format(cas) and self.calculate_cas_checksum(cas):
                            seen.add(cas)
                            result.append(cas)
        except Exception as e:
            print(f"Failed to read text file '{file_path}': {e}")
        return result

    # --- New: Update existing entries in a JSONL registry ---
    def update_jsonl_registry(
        self,
        registry_path: str,
        cas_items: Optional[Iterable[str]] = None,
        dry_run: bool = False,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Tuple[int, int]:
        """Update existing JSONL entries with missing fields filled from lookups.

        Conservative merge rules:
        - Never change 'cas'.
        - Only fill fields that are missing/empty in existing entry: name, abbreviation,
          generic_core, category_hint, token, compound_type.

        Returns (updated_count, not_found_count).
        """
        if not os.path.exists(registry_path):
            print(f"Registry not found: {registry_path}")
            return 0, 0

        # Load all lines to preserve order
        lines: List[str] = []
        entries: List[Optional[Dict[str, Any]]] = []
        with open(registry_path, 'r', encoding='utf-8') as f:
            for line in f:
                lines.append(line.rstrip('\n'))
                try:
                    entries.append(json.loads(line))
                except Exception:
                    entries.append(None)

        # Determine target CAS set
        target_set = set()
        if cas_items:
            for raw in cas_items:
                c = (raw or '').strip()
                if c:
                    target_set.add(c)
        else:
            # If none provided, update all CAS present
            for obj in entries:
                if isinstance(obj, dict):
                    c = (obj.get('cas') or obj.get('CAS') or '').strip()
                    if c:
                        target_set.add(c)

        updated = 0
        not_found = 0
        # Map CAS to first index for update
        cas_to_index: Dict[str, int] = {}
        for idx, obj in enumerate(entries):
            if not isinstance(obj, dict):
                continue
            c = (obj.get('cas') or obj.get('CAS') or '').strip()
            if c and c not in cas_to_index:
                cas_to_index[c] = idx

        for cas in sorted(target_set):
            if cas not in cas_to_index:
                not_found += 1
                (progress_cb or print)(f"Skip (not found): {cas}")
                continue
            idx = cas_to_index[cas]
            obj = entries[idx]
            if not isinstance(obj, dict):
                (progress_cb or print)(f"Skip (corrupt line) at {idx+1}")
                continue

            # Build a candidate entry from lookups
            candidate, warns = self._build_jsonl_entry(cas)
            if not candidate:
                # Nothing to merge
                continue

            # Merge conservatively (extended with new chemical properties)
            updatable_keys = ['name','abbreviation','generic_core','category_hint','token','compound_type','formula','molecular_weight','smile']
            diffs: List[Tuple[str, Any, Any]] = []
            for k in updatable_keys:
                old = obj.get(k)
                new = candidate.get(k)
                # Treat None/''/missing as empty
                empty_old = (old is None) or (isinstance(old, str) and old.strip() == '') or (k not in obj)
                if empty_old and new not in (None, ''):
                    diffs.append((k, old, new))
                    obj[k] = new

            if diffs:
                # Report diff
                (progress_cb or print)(f"Update: {cas}")
                for k, old, new in diffs:
                    (progress_cb or print)(f"  - {k}: {old!r} -> {new!r}")
                if not dry_run:
                    # Persist the updated object back into the line buffer
                    lines[idx] = json.dumps(obj, ensure_ascii=False)
                updated += 1

        if updated and not dry_run:
            # Rewrite the registry file
            with open(registry_path, 'w', encoding='utf-8', newline='') as f:
                for line in lines:
                    f.write((line or '') + "\n")

        return updated, not_found


def main():
    parser = argparse.ArgumentParser(description="CAS Number Validation and Registry Tool")
    parser.add_argument('--validate', help='Validate a single CAS number')
    parser.add_argument('--lookup', help='Look up information for a CAS number')
    parser.add_argument('--batch-validate', help='Validate and correct a CSV file')
    parser.add_argument('--output', help='Output file for batch operations')
    parser.add_argument('--build-registry', help='Build registry from folder of CAS mapping files')
    # New CLI for JSONL registry augmentation
    parser.add_argument('--add-cas', help='Add a single CAS to JSONL registry (if missing)')
    parser.add_argument('--add-csv', help='CSV with one CAS per line/column to add to JSONL registry')
    parser.add_argument('--add-text', help='Text file to scan for CAS RNs and add to JSONL registry')
    parser.add_argument('--registry', help='Path to cas_registry_merged.jsonl (default: ./cas_registry_merged.jsonl)')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without writing JSONL')
    parser.add_argument('--update-existing', action='store_true', help='Update existing entries (fill missing fields) instead of adding new ones. If used without inputs, updates all entries in the registry.')
    
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
    elif args.add_cas or args.add_csv or args.add_text or args.update_existing:
        reg_path = args.registry or os.path.join(os.getcwd(), 'cas_registry_merged.jsonl')
        todo: List[str] = []
        if args.add_cas:
            todo.append(args.add_cas.strip())
        if args.add_csv:
            p = Path(args.add_csv)
            if not p.exists():
                print(f"CSV not found: {p}")
                sys.exit(1)
            with open(p, 'r', encoding='utf-8') as f:
                # Accept either raw single-column CSV or headerless lines
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    todo.append(row[0].strip())
        if args.add_text:
            p = Path(args.add_text)
            if not p.exists():
                print(f"Text file not found: {p}")
                sys.exit(1)
            extracted = registry.extract_cas_from_text(str(p))
            print(f"Extracted {len(extracted)} CAS from text file")
            todo.extend(extracted)
        print(f"Target JSONL: {reg_path}")
        if args.update_existing:
            updated, not_found = registry.update_jsonl_registry(reg_path, todo or None, dry_run=args.dry_run)
            print(f"Done. Updated: {updated}; Not found: {not_found}")
        else:
            added, skipped = registry.add_to_jsonl_registry(reg_path, todo, dry_run=args.dry_run)
            print(f"Done. Added: {added}; Skipped existing: {skipped}")
    
    else:
        # Launch GUI (PyQt6) when no CLI args. Falls back to text mode on import failure.
        try:
            launch_gui(registry)
        except Exception as e:  # Broad catch to provide simple fallback
            print(f"GUI failed ({e}). Falling back to minimal interactive mode.")
            try:
                user_inp = input("Enter a CAS (blank to exit): ").strip()
            except Exception:
                return
            if not user_inp:
                return
            if registry.validate_cas_format(user_inp) and registry.calculate_cas_checksum(user_inp):
                reg_path = os.path.join(os.getcwd(), 'cas_registry_merged.jsonl')
                added, skipped = registry.add_to_jsonl_registry(reg_path, [user_inp], dry_run=False)
                print(f"Done. Added: {added}; Skipped existing: {skipped}")
            else:
                print("Invalid CAS.")


# ---------------- GUI IMPLEMENTATION (PyQt6) ---------------- #
def launch_gui(registry: Optional['ComprehensiveCASRegistry'] = None) -> None:
    """Launch a PyQt6 GUI for adding / updating CAS entries from text or markdown.

    Features:
    - Select a .txt/.md file; extract CAS RNs (with checksum) using existing logic.
    - Display unique CAS list with counts.
    - Choose registry JSONL path (defaults to ./cas_registry_merged.jsonl).
    - Mode: Add new entries OR Update existing (fill missing fields).
    - Dry run option.
    - Progress / log panel.
    - Non-blocking worker thread to avoid UI freeze.

    PyQt6 is imported lazily to avoid import cost headless (tests/CI).
    """
    if registry is None:
        registry = ComprehensiveCASRegistry()

    try:
        from PyQt6 import QtWidgets, QtCore
    except ImportError as ie:  # pragma: no cover
        raise RuntimeError("PyQt6 not installed; cannot start GUI") from ie

    class Worker(QtCore.QThread):
        progress = QtCore.pyqtSignal(str)
        finished = QtCore.pyqtSignal(int, int, str)  # (countA, countB, mode)

        def __init__(self, mode: str, reg_path: str, cas_list: list[str], dry: bool, parent=None):
            super().__init__(parent)
            self.mode = mode
            self.reg_path = reg_path
            self.cas_list = cas_list
            self.dry = dry

        def run(self):  # noqa: D401
            try:
                if self.mode == 'add':
                    added, skipped = registry.add_to_jsonl_registry(
                        self.reg_path,
                        self.cas_list,
                        dry_run=self.dry,
                        progress_cb=lambda m: self.progress.emit(m)
                    )
                    self.finished.emit(added, skipped, self.mode)
                else:
                    updated, not_found = registry.update_jsonl_registry(
                        self.reg_path,
                        self.cas_list,
                        dry_run=self.dry,
                        progress_cb=lambda m: self.progress.emit(m)
                    )
                    self.finished.emit(updated, not_found, self.mode)
            except Exception as e:  # pragma: no cover - runtime safety
                self.progress.emit(f"Error: {e}")

    class MainWin(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("CAS Registry Generator")
            self.resize(820, 600)
            self.worker: Worker | None = None
            self._build_ui()

        def _build_ui(self):
            lay = QtWidgets.QVBoxLayout(self)

            # File selection row
            file_row = QtWidgets.QHBoxLayout()
            self.file_edit = QtWidgets.QLineEdit()
            self.file_btn = QtWidgets.QPushButton("Select Text/Markdown…")
            self.file_btn.clicked.connect(self.select_file)
            file_row.addWidget(QtWidgets.QLabel("Source File:"))
            file_row.addWidget(self.file_edit, 1)
            file_row.addWidget(self.file_btn)
            lay.addLayout(file_row)

            # Registry selection
            reg_row = QtWidgets.QHBoxLayout()
            self.registry_edit = QtWidgets.QLineEdit(os.path.join(os.getcwd(), 'cas_registry_merged.jsonl'))
            self.registry_btn = QtWidgets.QPushButton("Select Registry…")
            self.registry_btn.clicked.connect(self.select_registry)
            reg_row.addWidget(QtWidgets.QLabel("Registry JSONL:"))
            reg_row.addWidget(self.registry_edit, 1)
            reg_row.addWidget(self.registry_btn)
            lay.addLayout(reg_row)

            # Mode + options
            opt_row = QtWidgets.QHBoxLayout()
            self.mode_add = QtWidgets.QRadioButton("Add New")
            self.mode_update = QtWidgets.QRadioButton("Update Existing")
            self.mode_add.setChecked(True)
            opt_row.addWidget(self.mode_add)
            opt_row.addWidget(self.mode_update)
            self.dry_check = QtWidgets.QCheckBox("Dry Run")
            opt_row.addWidget(self.dry_check)
            opt_row.addStretch(1)
            lay.addLayout(opt_row)

            # CAS list (auto-extracted on file selection)
            cas_group = QtWidgets.QGroupBox("CAS Numbers (auto-extracted on file selection)")
            v2 = QtWidgets.QVBoxLayout(cas_group)
            self.cas_list = QtWidgets.QListWidget()
            self.cas_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            v2.addWidget(self.cas_list)
            lay.addWidget(cas_group, 1)

            # Log panel
            log_group = QtWidgets.QGroupBox("Log / Progress")
            v3 = QtWidgets.QVBoxLayout(log_group)
            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            v3.addWidget(self.log)
            lay.addWidget(log_group, 2)

            # Action buttons
            act_row = QtWidgets.QHBoxLayout()
            self.run_btn = QtWidgets.QPushButton("Run")
            self.run_btn.clicked.connect(self.run_action)
            self.stop_btn = QtWidgets.QPushButton("Stop")
            self.stop_btn.setEnabled(False)
            self.stop_btn.clicked.connect(self.stop_worker)
            act_row.addStretch(1)
            act_row.addWidget(self.run_btn)
            act_row.addWidget(self.stop_btn)
            lay.addLayout(act_row)

        # --- Slots ---
        def select_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select text/markdown file", "", "Text/Markdown (*.txt *.md *.markdown);;All Files (*)")
            if path:
                self.file_edit.setText(path)
                # Auto extract CAS immediately
                self.extract_cas()

        def select_registry(self):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select / Create registry JSONL", self.registry_edit.text(), "JSONL (*.jsonl);;All Files (*)")
            if path:
                self.registry_edit.setText(path)

        def extract_cas(self):
            path = self.file_edit.text().strip()
            if not path or not os.path.isfile(path):
                self._log("No valid file selected.")
                return
            cas_list = registry.extract_cas_from_text(path)
            self.cas_list.clear()
            for cas in cas_list:
                self.cas_list.addItem(cas)
            self._log(f"Extracted {len(cas_list)} CAS numbers.")

        def run_action(self):
            if self.worker and self.worker.isRunning():
                self._log("Worker already running.")
                return
            cas_items = [self.cas_list.item(i).text() for i in range(self.cas_list.count())]
            if not cas_items:
                self._log("No CAS to process.")
                return
            mode = 'add' if self.mode_add.isChecked() else 'update'
            reg_path = self.registry_edit.text().strip()
            dry = self.dry_check.isChecked()
            self._log(f"Starting {mode} on {len(cas_items)} CAS | dry={dry}")
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.worker = Worker(mode, reg_path, cas_items, dry)
            self.worker.progress.connect(self._log)
            self.worker.finished.connect(self._on_finished)
            self.worker.start()

        def stop_worker(self):  # pragma: no cover
            if self.worker and self.worker.isRunning():
                self.worker.terminate()
                self._log("Worker terminated.")
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

        def _on_finished(self, a: int, b: int, mode: str):
            if mode == 'add':
                self._log(f"Done. Added: {a}; Skipped existing: {b}")
            else:
                self._log(f"Done. Updated: {a}; Not found: {b}")
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

        def _log(self, msg: str):
            self.log.appendPlainText(msg)
            self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = MainWin()
    win.show()
    app.exec()


if __name__ == '__main__':  # Placed at end so launch_gui is defined
    main()
