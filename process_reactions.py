#!/usr/bin/env python3
"""
CLI to parse a SciFinder TXT export and a RXN/RDF export, merge by Reaction ID,
and write a flat CSV conforming to reaction_dataset_schema.md.

Assumptions and heuristics:
- TXT is the primary source for names of catalysts, ligands, reagents, solvents, time, temp.
- RXN/RDF is the authoritative source for ReactionID, CAS lists, and reported yield.
- Ligands are items listed under "Catalysts:" that do not look like metal salts/precursors.
- ReactionType is inferred from presence of metal: Cu -> "Ullmann", Pd -> "Buchwald", else "Other".
- Time_h = sum of all durations found across steps; Temperature_C = max numeric temperature found;
  "rt" -> 25 °C; "overnight" -> 16 h; "reflux" ignored (cannot infer solvent boiling point robustly).
- JSON arrays are stored as strings of JSON lists as per schema.

Usage:
    python process_reactions.py --rdf Reaction_2024-1.rdf --txt Reaction_2024-1.txt --out reactions.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional

try:
    import xxhash  # type: ignore
except Exception:  # pragma: no cover
    xxhash = None  # We'll check at runtime

# RDKit is optional; enable SMILES extraction when available
try:  # pragma: no cover - import tested in runtime
    from rdkit import Chem  # type: ignore
except Exception:  # pragma: no cover
    Chem = None  # type: ignore


# ------------------------------ Schema helpers ------------------------------

def _json_list(items: List[str]) -> str:
    # Keep stable ordering: unique preserving first-seen order
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip()
        if not key:
            continue
        if key not in seen:
            seen.add(key)
            out.append(key)
    return json.dumps(out, ensure_ascii=False)


def _hash32_hex(s: str) -> str:
    if xxhash is None:
        return ""
    return xxhash.xxh32_hexdigest(s)


def build_condkey(row: Dict[str, str]) -> str:
    def _join(col):
        try:
            return "+".join(sorted(json.loads(row.get(col, "[]")))) or "none"
        except Exception:
            return "none"

    cg = _join("CoreGeneric")
    lig = _join("Ligand")
    bas = _join("ReagentRaw")
    solv = _join("Solvent")
    return f"{cg}/{lig}/{bas}/{solv}"


def build_condsig(row: Dict[str, str]) -> str:
    parts = []
    for c in ["CoreGeneric", "Ligand", "ReagentRaw", "Solvent"]:
        try:
            parts.append("+".join(sorted(json.loads(row.get(c, "[]")))))
        except Exception:
            parts.append("")
    return _hash32_hex("|".join(parts))


def build_famsig(row: Dict[str, str]) -> str:
    # collapse metal detail: here CoreGeneric is already generic tokens
    try:
        core = json.loads(row.get("CoreGeneric", "[]"))
        lig = json.loads(row.get("Ligand", "[]"))
        reag = json.loads(row.get("ReagentRaw", "[]"))
        solv = json.loads(row.get("Solvent", "[]"))
    except Exception:
        return ""

    # collapse reagents by head token before '-' (very rough)
    reag_collapsed = [r.split("-")[0] for r in reag]
    key = "|".join([
        "+".join(sorted(core)),
        "+".join(sorted(lig)),
        "+".join(sorted(reag_collapsed)),
        "+".join(sorted(solv)),
    ])
    return _hash32_hex(key)


# --------------------------- Parsing the TXT file ---------------------------

_RE_TIME = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hrs|hour|hours|min|mins|minute|minutes)\b", re.I)
_RE_TEMP_C = re.compile(r"(?P<val>-?\d+(?:\.\d+)?)\s*[^A-Za-z0-9]{0,3}C\b")  # tolerate broken degree symbol


def _normalize_token_list(s: str) -> List[str]:
    # Split on commas
    toks = [t.strip().strip(';').strip() for t in s.split(',')]
    toks = [t for t in toks if t]
    return toks


def _is_condition_token(tok: str) -> bool:
    """Return True if the token looks like a condition fragment (time/temperature keywords)."""
    t = tok.strip()
    if not t:
        return False
    if _RE_TEMP_C.search(t):
        return True
    if _RE_TIME.search(t):
        return True
    tlo = t.lower()
    if tlo in {"rt", "room temperature", "reflux", "overnight"}:
        return True
    # simple catch: tokens like "120C" without space
    if re.search(r"\b\d+\s*(?:c|°c)\b", tlo):
        return True
    return False


def _classify_catalyst_or_ligand(name: str) -> Tuple[str, str]:
    """Return (kind, generic) where kind in {"core", "ligand"} and generic metal tag.
    generic may be "Pd", "Cu(I)", "Cu(II)", "Cu", "Ni", "Ir", "Rh", or "".
    """
    n = name.lower()
    metal = ""
    if any(x in n for x in ["palladium", "pd("]):
        metal = "Pd"
    if any(x in n for x in ["nickel", "ni("]):
        metal = "Ni"
    if any(x in n for x in ["iridium", "ir("]):
        metal = "Ir"
    if any(x in n for x in ["rhodium", "rh("]):
        metal = "Rh"
    if "cuprous" in n or "cu(i)" in n:
        metal = "Cu(I)"
    elif "cupric" in n or "cu(ii)" in n:
        metal = "Cu(II)"
    elif "copper" in n or n.startswith("cu ") or n.startswith("cu-") or n == "cu":
        metal = "Cu"

    # Decide if this entry is a metal precursor (core) vs ligand
    is_metal_precursor = bool(metal) or any(k in n for k in ["oxide", "bromide", "iodide", "chloride", "acetate", "triflate", "acac", "sulfate"]) and ("copper" in n or "palladium" in n or "nickel" in n)
    kind = "core" if is_metal_precursor else "ligand"
    return kind, metal


def _classify_reagent_role(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["carbonate", "methoxide", "tert-butoxide", "trimethylsilanolate", "triethylamine", "pyridine", "koh", "naoh", "hydroxide", "potassium tert-butoxide"]):
        return "BASE"
    if any(k in n for k in ["water", "h2o", "brine", "nh4cl", "ammonium chloride", "work-up"]):
        return "WORKUP"
    if any(k in n for k in ["oxygen", "air", "peroxide", "selenium", "nbs", "ncs", "silver fluoride"]):
        return "OX"
    if any(k in n for k in ["sodium azide", "azide", "amine", "morpholine", "aniline", "indole", "carbazole"]):
        return "NUC"
    return "UNK"


def parse_txt(path: str) -> Dict[str, Dict[str, Any]]:
    reactions: Dict[str, Dict[str, Any]] = {}
    current_title = ""
    current_authors = ""
    current_citation = ""

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Capture Title / Authors / Citation blocks
        if line and not line.startswith(('Steps:', 'CAS Reaction Number:', 'View All', 'Reactions (', 'Search', 'Filtered By:', 'Scheme')) and not line.startswith('By:') and not line.startswith('10.'):
            # Likely a title line (very heuristic)
            current_title = line
        if line.startswith('By:'):
            current_authors = line.replace('By:', '').strip()
        # Journal/citation line often contains a year in parentheses
        if re.search(r"\(20\d{2}\)", line):
            # Prefer the line that looks like Journal (year), vol, pages.
            current_citation = line.strip()

        # If we hit a reaction header, start collecting
        if line.startswith('Steps:'):
            # Parse the yield on same line if present
            m = re.search(r"Yield:\s*([0-9]{1,3})\s*%", line)
            pending_yield = int(m.group(1)) if m else None
            # The ID is within a few lines: look ahead up to +3 for CAS Reaction Number
            j = i
            rid = None
            while j < len(lines) and j <= i + 6:
                if lines[j].strip().startswith('CAS Reaction Number:'):
                    rid = lines[j].split(':', 1)[1].strip()
                    break
                j += 1
            if rid:
                # Init record
                rec = reactions.setdefault(rid, {
                    'title': current_title,
                    'authors': current_authors,
                    'citation': current_citation,
                    'txt_yield': pending_yield,
                    'reagents': [],
                    'catalysts': [],
                    'solvents': [],
                    'all_condition_lines': [],
                })

                # Collect step details until the next blank separator or next scheme/title block
                k = j + 1
                while k < len(lines):
                    s = lines[k].strip()
                    if not s:
                        k += 1
                        continue
                    # Stop if we hit the next top-level block: a title line (not starting with digit or label) followed by By:/Steps
                    if s.startswith('Steps:') or s.startswith('CAS Reaction Number:') or s.startswith('Scheme '):
                        break
                    # Many blocks end with a line that's just a '?'
                    if s == '?':
                        k += 1
                        break
                    # Collect content
                    rec['all_condition_lines'].append(s)
                    if s.lower().startswith('reagents:'):
                        rest = s.split(':', 1)[1].strip()
                        # Use content before first ';' to avoid trailing conditions
                        before = rest.split(';', 1)[0].strip()
                        toks = [t for t in _normalize_token_list(before) if not _is_condition_token(t)]
                        rec['reagents'].extend(toks)
                    elif s.lower().startswith('catalysts:'):
                        rest = s.split(':', 1)[1].strip()
                        before = rest.split(';', 1)[0].strip()
                        toks = [t for t in _normalize_token_list(before) if not _is_condition_token(t)]
                        rec['catalysts'].extend(toks)
                    elif s.lower().startswith('solvents:'):
                        rest = s.split(':', 1)[1].strip()
                        # Before first semicolon are solvents (may be comma-separated)
                        parts = [p.strip() for p in rest.split(';')]
                        if parts:
                            rec['solvents'].extend(_normalize_token_list(parts[0]))
                        # The rest of parts may contain time/temps
                    k += 1
                # advance
                i = k
                continue

        i += 1

    # Post-process: dedupe tokens and compute time/temp
    for rid, rec in reactions.items():
        # Dedupe
        rec['reagents'] = list(dict.fromkeys([x.strip() for x in rec['reagents'] if x.strip()]))
        rec['catalysts'] = list(dict.fromkeys([x.strip() for x in rec['catalysts'] if x.strip()]))
        rec['solvents'] = list(dict.fromkeys([x.strip() for x in rec['solvents'] if x.strip()]))

        # Parse time and temperature across all condition lines
        total_h = 0.0
        max_c = -math.inf
        had_rt = False
        for ln in rec.get('all_condition_lines', []):
            # time
            for m in _RE_TIME.finditer(ln):
                num = float(m.group('num'))
                unit = m.group('unit').lower()
                if unit.startswith('min'):
                    total_h += num / 60.0
                else:
                    total_h += num
            if re.search(r"\bovernight\b", ln, re.I):
                total_h += 16.0
            # temperature
            for m in _RE_TEMP_C.finditer(ln):
                val = float(m.group('val'))
                if val > max_c:
                    max_c = val
            if re.search(r"\brt\b|room temperature", ln, re.I):
                had_rt = True
        temperature_c = max_c if max_c != -math.inf else (25.0 if had_rt else None)

        rec['time_h'] = round(total_h, 3) if total_h > 0 else None
        rec['temperature_c'] = round(temperature_c, 1) if temperature_c is not None else None

    return reactions


# --------------------------- Parsing the RXN/RDF ----------------------------

def parse_rdf(path: str) -> Dict[str, Dict[str, Any]]:
    reactions: Dict[str, Dict[str, Any]] = {}
    pending_key = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]

    def _ensure(rid: str) -> Dict[str, Any]:
        return reactions.setdefault(rid, {
            'rct_cas': [],
            'pro_cas': [],
            'rgt_cas': [],
            'cat_cas': [],
            'sol_cas': [],
            # capture CTAB/MOL blocks for SMILES extraction
            'rct_mol': [],
            'pro_mol': [],
            'yield_pct': None,
            'title': None,
            'authors': None,
            'citation': None,
            'notes': [],
        })

    current_rid: str | None = None
    # queue pending RXN mol blocks (reactants/products) until we see the CAS Reaction Number
    pending_rxn_sets: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Capture RXN header + MOL blocks (V2000/V3000). Format:
        # $RXN ... [counts line with two ints] then $MOL blocks for reactants then products.
        if line.strip().startswith('$RXN'):
            i += 1
            # find counts line like "  2  1"
            rct_count = 0
            pro_count = 0
            counts_re = re.compile(r"^\s*(\d+)\s+(\d+)\s*$")
            while i < len(lines):
                if lines[i].strip().startswith('$MOL'):
                    # counts line missing; break to MOL parsing
                    break
                m = counts_re.match(lines[i])
                if m:
                    rct_count, pro_count = int(m.group(1)), int(m.group(2))
                    i += 1
                    break
                i += 1
            total_needed = (rct_count + pro_count) if (rct_count + pro_count) > 0 else None
            mol_blocks: List[str] = []
            # collect $MOL blocks until we have total_needed (if known), else until next $DTYPE/$RXN
            while i < len(lines):
                if lines[i].strip().startswith('$MOL'):
                    j = i + 1
                    block_lines: List[str] = []
                    while j < len(lines):
                        block_lines.append(lines[j])
                        if lines[j].strip() == 'M  END':
                            j += 1
                            break
                        # stop if another record starts unexpectedly
                        if lines[j].startswith('$') and not lines[j].startswith('M '):
                            break
                        j += 1
                    mol_blocks.append('\n'.join(block_lines).rstrip())
                    i = j
                    if total_needed is not None and len(mol_blocks) >= total_needed:
                        break
                    continue
                # stop at next rxn or dtype if no more mols
                if lines[i].strip().startswith('$RXN') or lines[i].strip().startswith('$DTYPE'):
                    break
                i += 1
            # push pending set; will be assigned to the next CAS Reaction Number encountered
            pending_rxn_sets.append({
                'rct_count': rct_count,
                'pro_count': pro_count,
                'mol_blocks': mol_blocks,
            })
            # do not increment i here further; continue loop
            continue
        if line.startswith('$DTYPE'):
            pending_key = line.split(' ', 1)[1].strip()
            # Prepare to read $DATUM
            i += 1
            # Expect $DATUM next, but handle robustness
            if i < len(lines) and lines[i].startswith('$DATUM'):
                # Capture $DATUM content including continuation lines until next '$'
                first = lines[i][len('$DATUM '):]
                datum_lines = [first]
                i += 1
                while i < len(lines) and not lines[i].startswith('$'):
                    datum_lines.append(lines[i])
                    i += 1
                key = pending_key or ''
                # For CTAB/MOL blocks, preserve newlines; for others, join with space
                if key.endswith(':CTAB') or key.endswith(':MOL'):
                    datum = '\n'.join(datum_lines).rstrip()
                else:
                    datum = ' '.join(p.strip() for p in datum_lines).strip()

                # Route datum into the appropriate bucket
                if 'CAS_Reaction_Number' in key:
                    current_rid = datum
                    _ensure(current_rid)
                    # attach earliest pending RXN set if present
                    if pending_rxn_sets:
                        rxnset = pending_rxn_sets.pop(0)
                        blocks: List[str] = rxnset.get('mol_blocks', []) or []
                        rct_n = int(rxnset.get('rct_count') or 0)
                        # if counts missing, split by heuristic: half reactants, rest products
                        if rct_n <= 0 and blocks:
                            rct_n = max(0, min(len(blocks), len(blocks) - 1))
                        _ensure(current_rid)['rct_mol'].extend(blocks[:rct_n])
                        _ensure(current_rid)['pro_mol'].extend(blocks[rct_n:])
                elif ':RCT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['rct_cas'].append(datum)
                elif ':PRO(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['pro_cas'].append(datum)
                elif ':RGT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['rgt_cas'].append(datum)
                elif ':CAT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['cat_cas'].append(datum)
                elif ':SOL(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['sol_cas'].append(datum)
                elif ':RCT(' in key and (key.endswith(':CTAB') or key.endswith(':MOL')):
                    if current_rid:
                        _ensure(current_rid)['rct_mol'].append(datum)
                elif ':PRO(' in key and (key.endswith(':CTAB') or key.endswith(':MOL')):
                    if current_rid:
                        _ensure(current_rid)['pro_mol'].append(datum)
                elif key.endswith(':PRO(1):YIELD'):
                    if current_rid:
                        try:
                            _ensure(current_rid)['yield_pct'] = int(float(datum))
                        except Exception:
                            _ensure(current_rid)['yield_pct'] = None
                elif key.endswith(':REFERENCE(1):TITLE'):
                    if current_rid:
                        _ensure(current_rid)['title'] = datum
                elif key.endswith(':REFERENCE(1):AUTHOR'):
                    if current_rid:
                        _ensure(current_rid)['authors'] = datum
                elif key.endswith(':REFERENCE(1):CITATION'):
                    if current_rid:
                        _ensure(current_rid)['citation'] = datum
                elif key.endswith(':NOTES'):
                    if current_rid:
                        _ensure(current_rid)['notes'].append(datum)
                # do not increment i here; we already moved to next line or stop
                continue
            else:
                # No $DATUM where expected; continue
                continue
        else:
            i += 1

    # Deduplicate lists
    for rid, rec in reactions.items():
        for k in ['rct_cas', 'pro_cas', 'rgt_cas', 'cat_cas', 'sol_cas', 'notes']:
            rec[k] = list(dict.fromkeys(rec.get(k, [])))
        # de-dupe mol blocks while preserving order
        for k in ['rct_mol', 'pro_mol']:
            seen: set[str] = set()
            uniq: List[str] = []
            for mb in rec.get(k, []) or []:
                if mb not in seen:
                    seen.add(mb)
                    uniq.append(mb)
            rec[k] = uniq
    return reactions


# ------------------------------- Row assembly -------------------------------

def infer_reaction_type(core_generic_tokens: List[str]) -> str:
    s = set(t.lower() for t in core_generic_tokens)
    if any(t.startswith('pd') for t in s):
        return 'Buchwald'
    if any(t.startswith('cu') for t in s):
        return 'Ullmann'
    if any(t.startswith('ni') for t in s):
        return 'Ullmann'  # generalized copper/nickel-mediated C–N
    return 'Other'

def load_cas_maps(paths: List[str]) -> Dict[str, Dict[str, str]]:
    """Load one or more CSV mapping files into a dict: CAS -> {Name, GenericCore, Role, CategoryHint, Token}.
    Accepts slightly different headers; missing fields are blank. CAS keys are normalized as plain strings.
    """
    import csv as _csv
    mapping: Dict[str, Dict[str, str]] = {}
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    cas = (row.get('CAS') or '').strip()
                    if not cas:
                        continue
                    entry = mapping.setdefault(cas, {})
                    # Copy known fields if present
                    for k in ['Name', 'GenericCore', 'Role', 'CategoryHint', 'Token']:
                        v = row.get(k)
                        if v:
                            entry[k] = v.strip()
        except Exception:
            # ignore file-specific issues
            pass
    return mapping


def _cas_to_names(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for cas in cases:
        name = cas_map.get(cas, {}).get('Name')
        out.append(name or cas)
    return out


def _generic_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for cas in cases:
        e = cas_map.get(cas) or {}
        gen = (e.get('GenericCore') or '').strip()
        if not gen and (e.get('CategoryHint') or '').lower().startswith('copper'):
            # crude inference
            gen = 'Cu'
        if gen:
            out.append(gen)
    return out


def _tokens_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    """Return normalized short tokens for CAS list using mapping: prefer Token, then Name, else CAS."""
    out: List[str] = []
    for cas in cases:
        e = cas_map.get(cas) or {}
        tok = (e.get('Token') or '').strip()
        if not tok:
            tok = (e.get('Name') or '').strip()
        if not tok:
            tok = cas
        out.append(tok)
    # stable de-dupe while preserving order
    seen = set()
    uniq: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _roles_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    roles: List[str] = []
    for cas in cases:
        role = (cas_map.get(cas, {}).get('Role') or '').strip().upper()
        roles.append(role if role else 'UNK')
    return roles


def _split_cat_vs_lig_from_cas(cat_cas: List[str], cas_map: Dict[str, Dict[str, str]]) -> Tuple[List[str], List[str], List[str]]:
    """Split catalyst CAS list into (core_catalyst_cas, ligand_cas, other_cas) using Role/Category/GenericCore hints."""
    core: List[str] = []
    lig: List[str] = []
    other: List[str] = []
    for cas in cat_cas or []:
        e = cas_map.get(cas) or {}
        role = (e.get('Role') or '').strip().upper()
        hint = (e.get('CategoryHint') or '').strip().lower()
        gen = (e.get('GenericCore') or '').strip()
        name = (e.get('Name') or '').strip().lower()
        if role.startswith('LIG') or 'ligand' in hint:
            lig.append(cas)
        elif role.startswith('CAT') or gen or any(m in name for m in ['palladium', 'copper', 'nickel', 'iridium', 'rhodium']):
            core.append(cas)
        else:
            other.append(cas)
    return core, lig, other


def _molblock_to_smiles(mb: str) -> str:
    """Convert a V2000/V3000 mol block to a canonical SMILES using RDKit if available."""
    if not Chem:
        return ''
    mol = None
    try:
        mol = Chem.MolFromMolBlock(mb, sanitize=True, removeHs=True)
    except Exception:
        mol = None
    if mol is None:
        try:
            mol = Chem.MolFromMolBlock(mb, sanitize=False, removeHs=True)
            if mol is not None:
                try:
                    Chem.SanitizeMol(mol)
                except Exception:
                    pass
        except Exception:
            mol = None
    if mol is None:
        return ''
    try:
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return ''


def assemble_rows(txt: Dict[str, Dict[str, Any]], rdf: Dict[str, Dict[str, Any]], cas_map: Optional[Dict[str, Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    ids = sorted(set(txt.keys()) | set(rdf.keys()))
    rows: List[Dict[str, Any]] = []
    for rid in ids:
        t = txt.get(rid, {})
        r = rdf.get(rid, {})

        # Catalysts split into core vs ligand, also gather generic tags
        core_detail: List[str] = []
        ligands: List[str] = []
        core_generic: List[str] = []

        # Prefer CAS-role-based split if mapping available
        cat_core_cas: List[str] = []
        cat_lig_cas: List[str] = []
        if cas_map and r.get('cat_cas'):
            cat_core_cas, cat_lig_cas, _ = _split_cat_vs_lig_from_cas(r.get('cat_cas', []), cas_map)
            # Names/tokens from CAS for ligands
            ligands.extend(_tokens_from_cas_list(cat_lig_cas, cas_map))
            # Core generic metal tags from catalyst CAS
            core_generic.extend(_generic_from_cas_list(cat_core_cas, cas_map))

        # Also include TXT catalysts; classify into core vs ligand and extract generic tags
        for item in t.get('catalysts', []):
            kind, gen = _classify_catalyst_or_ligand(item)
            if kind == 'core':
                core_detail.append(item)
            else:
                ligands.append(item)
            if gen:
                core_generic.append(gen)

        # If still no core_generic but copper-like catalyst present explicitly, infer
        if not core_generic and any('copper' in c.lower() for c in core_detail):
            core_generic.append('Cu')

        # Reagents and roles (normalize using CAS mapping tokens if present)
        reagents: List[str]
        roles: List[str]
        if cas_map and r.get('rgt_cas'):
            reagents = _tokens_from_cas_list(r.get('rgt_cas', []), cas_map)
            roles = _roles_from_cas_list(r.get('rgt_cas', []), cas_map)
        else:
            reagents = list(t.get('reagents', []))
            roles = [_classify_reagent_role(x) for x in reagents]

        # Derive Base list from roles and mapping (BASE)
        base_tokens: List[str] = []
        if cas_map and r.get('rgt_cas'):
            for cas in r.get('rgt_cas', []):
                role = (cas_map.get(cas, {}).get('Role') or '').strip().upper()
                if role == 'BASE':
                    tok = (cas_map.get(cas, {}).get('Token') or cas_map.get(cas, {}).get('Name') or cas).strip()
                    base_tokens.append(tok)
        else:
            # Heuristic: pick bases from reagent names
            for name in reagents:
                if _classify_reagent_role(name) == 'BASE':
                    base_tokens.append(name)
        # Stable de-dupe
        base_seen = set(); base_tokens = [x for x in base_tokens if not (x in base_seen or base_seen.add(x))]

        # Solvents (normalize using CAS mapping when available)
        if cas_map and r.get('sol_cas'):
            solvents: List[str] = _tokens_from_cas_list(r.get('sol_cas', []), cas_map)
        else:
            solvents = list(t.get('solvents', []))

        # Time / Temp / Yield
        temp_c = t.get('temperature_c')
        time_h = t.get('time_h')
        yield_pct = r.get('yield_pct') if r.get('yield_pct') is not None else t.get('txt_yield')

        # Reference priority: TXT-derived title/authors/citation; fallback to RDF
        title = t.get('title') or r.get('title') or ''
        authors = t.get('authors') or r.get('authors') or ''
        citation = t.get('citation') or r.get('citation') or ''
        reference = ' | '.join([x for x in [title, authors, citation] if x])

        # RawCAS trail
        def join_plus(lst):
            return ' + '.join(lst) if lst else ''
        rawcas_parts = []
        if r.get('rct_cas'):
            rawcas_parts.append(f"RCT: {join_plus(r['rct_cas'])}")
        if r.get('pro_cas'):
            rawcas_parts.append(f"PRO: {join_plus(r['pro_cas'])}")
        if r.get('rgt_cas'):
            rawcas_parts.append(f"RGT: {join_plus(r['rgt_cas'])}")
        if r.get('cat_cas'):
            rawcas_parts.append(f"CAT: {join_plus(r['cat_cas'])}")
        if r.get('sol_cas'):
            rawcas_parts.append(f"SOL: {join_plus(r['sol_cas'])}")
        raw_cas = ' | '.join(rawcas_parts)

        # Name arrays from CAS mapping (if provided)
        rct_names = _cas_to_names(r.get('rct_cas', []), cas_map or {})
        pro_names = _cas_to_names(r.get('pro_cas', []), cas_map or {})
        rgt_names = _cas_to_names(r.get('rgt_cas', []), cas_map or {})
        # Avoid ligand leakage into CATName by excluding cas tagged as ligand
        if cas_map and r.get('cat_cas'):
            cat_core_only = [c for c in r.get('cat_cas', []) if c not in (cat_lig_cas or [])]
        else:
            cat_core_only = r.get('cat_cas', [])
        cat_names = _cas_to_names(cat_core_only, cas_map or {})
        sol_names = _cas_to_names(r.get('sol_cas', []), cas_map or {})
        # Base names enrichment
        if cas_map and r.get('rgt_cas'):
            bas_names = []
            for cas in r.get('rgt_cas', []):
                role = (cas_map.get(cas, {}).get('Role') or '').strip().upper()
                if role == 'BASE':
                    bas_names.append((cas_map.get(cas, {}).get('Name') or cas).strip())
        else:
            bas_names = list(base_tokens)

        # Defaults for absent arrays
        if not ligands:
            ligands = ["none"]

        # SMILES from MOL blocks if RDKit is available
        rct_smiles_list: List[str] = []
        pro_smiles_list: List[str] = []
        for mb in r.get('rct_mol', []) or []:
            smi = _molblock_to_smiles(mb)
            if smi:
                rct_smiles_list.append(smi)
        for mb in r.get('pro_mol', []) or []:
            smi = _molblock_to_smiles(mb)
            if smi:
                pro_smiles_list.append(smi)

        row = {
            'ReactionID': rid,
            'ReactionType': infer_reaction_type(core_generic),
            'CoreDetail': _json_list(core_detail),
            'CoreGeneric': _json_list(core_generic),
            'Ligand': _json_list(ligands),
            'ReagentRaw': _json_list(reagents),
            'ReagentRole': _json_list(roles),
            'Base': _json_list(base_tokens),
            'Solvent': _json_list(solvents),
            'Temperature_C': temp_c if temp_c is not None else '',
            'Time_h': time_h if time_h is not None else '',
            'Yield_%': yield_pct if yield_pct is not None else '',
            'ReactantSMILES': ' . '.join(rct_smiles_list) if rct_smiles_list else '',
            'ProductSMILES': ' . '.join(pro_smiles_list) if pro_smiles_list else '',
            'Reference': reference,
            'CondKey': '',  # fill after
            'CondSig': '',  # fill after
            'FamSig': '',   # fill after
            'RawCAS': raw_cas,
            # Optional enrichment (JSON arrays of names; falls back to CAS when unknown)
            'RCTName': _json_list(rct_names),
            'PROName': _json_list(pro_names),
            'RGTName': _json_list(rgt_names),
            'CATName': _json_list(cat_names),
            'SOLName': _json_list(sol_names),
            'BASName': _json_list(bas_names),
        }

        # Build keys/hashes
        row['CondKey'] = build_condkey(row)
        row['CondSig'] = build_condsig(row)
        row['FamSig'] = build_famsig(row)

        rows.append(row)

    return rows


def write_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    # Ensure consistent column order per schema
    cols = [
        'ReactionID', 'ReactionType', 'CoreDetail', 'CoreGeneric', 'Ligand',
    'ReagentRaw', 'ReagentRole', 'Base', 'Solvent', 'Temperature_C', 'Time_h',
        'Yield_%', 'ReactantSMILES', 'ProductSMILES', 'Reference',
        'CondKey', 'CondSig', 'FamSig', 'RawCAS',
        # enrichment columns (optional)
    'RCTName', 'PROName', 'RGTName', 'CATName', 'SOLName', 'BASName',
    ]
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in cols})


def main():
    ap = argparse.ArgumentParser(description="Merge SciFinder TXT + RXN/RDF into schema CSV")
    ap.add_argument('--rdf', required=True, help='Path to Reaction_*.rdf file')
    ap.add_argument('--txt', required=True, help='Path to Reaction_*.txt file')
    ap.add_argument('--out', required=True, help='Output CSV path')
    ap.add_argument('--cas-map', action='append', help='Optional CAS->Name mapping CSV (can be used multiple times)')
    ap.add_argument('--no-auto-cas-maps', action='store_true', help='Disable auto-detection of built-in CAS maps')
    args = ap.parse_args()

    if xxhash is None:
        print("Warning: xxhash not installed; CondSig/FamSig will be blank. Install 'xxhash' for hashes.")

    txt_map = parse_txt(args.txt)
    rdf_map = parse_rdf(args.rdf)

    # Collect mapping files
    cas_map_paths: List[str] = []
    if args.cas_map:
        cas_map_paths.extend(args.cas_map)
    if not args.no_auto_cas_maps:
        # Try auto-known paths if present
        here = os.path.dirname(os.path.abspath(__file__))
        maybe = [
            os.path.join(here, 'Buchwald', 'cas_dictionary.csv'),
            os.path.join(here, 'Ullman', '新建文件夹', 'ullmann_cas_to_name_mapping.csv'),
        ]
        cas_map_paths.extend([p for p in maybe if os.path.exists(p)])
    cas_map = load_cas_maps(cas_map_paths) if cas_map_paths else {}

    rows = assemble_rows(txt_map, rdf_map, cas_map)
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == '__main__':
    main()
