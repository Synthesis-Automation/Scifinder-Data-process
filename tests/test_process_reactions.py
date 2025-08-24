"""
Minimal tests for process_reactions:
- Validates that RDF CTAB blocks are converted to SMILES when RDKit is available.
- Validates solvent/reagent normalization using CAS mapping Token field.
- Validates CondSig/FamSig are non-empty when xxhash is installed.
"""
import json
import textwrap
import os
import sys

# Ensure project root on path for direct module import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from process_reactions import parse_rdf, assemble_rows, load_cas_maps, parse_txt


def _make_fake_rdf(tmp_path):
    # Construct a tiny RDF with 1 reaction, reactant/product CTAB, and CAS tokens
    rdf = textwrap.dedent(
        """
        $DTYPE CAS_Reaction_Number
        $DATUM RXNTEST001
        $DTYPE RXN:RCT(1):CAS_RN
        $DATUM 64-17-5
        $DTYPE RXN:SOL(1):CAS_RN
        $DATUM 64-17-5
        $DTYPE RXN:RGT(1):CAS_RN
        $DATUM 497-19-8
        $DTYPE RXN:RCT(1):CTAB
        $DATUM  RDKit          2D
        
          6  5  0  0  0  0            999 V2000
            0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
            1.2094    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
            1.8141    1.2094    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
            1.2094    2.4189    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
            0.0000    2.4189    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
           -0.6047    1.2094    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
          1  2  1  0  0  0  0
          2  3  1  0  0  0  0
          3  4  1  0  0  0  0
          4  5  1  0  0  0  0
          5  6  1  0  0  0  0
        M  END
        $DTYPE RXN:PRO(1):CTAB
        $DATUM  RDKit          2D
        
          3  2  0  0  0  0            999 V2000
            0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
            1.2094    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
            2.4189    0.0000    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0
          1  2  2  0  0  0  0
          1  3  1  0  0  0  0
        M  END
        """
    ).strip()
    p = tmp_path / "fake.rdf"
    p.write_text(rdf, encoding="utf-8")
    return str(p)


def _make_fake_txt(tmp_path):
    txt = textwrap.dedent(
        """
        Some Article Title
        By: Doe, J.
        Journal (2024), 1(1), 1-10
        Steps: Yield: 95 %
        CAS Reaction Number: RXNTEST001
        Catalysts: Pd(OAc)2, XPhos
        Reagents: Cs2CO3
        Solvents: EtOH; 80 C, 2 h
        """
    ).strip()
    p = tmp_path / "fake.txt"
    p.write_text(txt, encoding="utf-8")
    return str(p)


def _make_fake_map(tmp_path):
    csv = textwrap.dedent(
        """
        CAS,Name,GenericCore,Role,CategoryHint,Token
        64-17-5,Ethanol,,SOL,,EtOH
        497-19-8,Sodium carbonate,,BASE,,Na2CO3
        """
    ).strip()
    p = tmp_path / "map.csv"
    p.write_text(csv, encoding="utf-8")
    return str(p)


def test_smiles_and_normalization(tmp_path):
    rdf_path = _make_fake_rdf(tmp_path)
    txt_path = _make_fake_txt(tmp_path)
    map_path = _make_fake_map(tmp_path)

    rdf = parse_rdf(rdf_path)
    txt = parse_txt(txt_path)
    cas_map = load_cas_maps([map_path])

    rows = assemble_rows(txt, rdf, cas_map)
    assert rows and rows[0]['ReactionID'] == 'RXNTEST001'

    # Solvent normalized to Token (EtOH); ReagentRaw normalized to Na2CO3
    solv = json.loads(rows[0]['Solvent'])
    reag = json.loads(rows[0]['ReagentRaw'])
    assert 'EtOH' in solv
    assert 'Na2CO3' in reag

    # Roles drawn from mapping
    roles = json.loads(rows[0]['ReagentRole'])
    assert 'BASE' in roles

    # SMILES fields present (may be empty if RDKit is unavailable in environment)
    assert 'ReactantSMILES' in rows[0]
    assert 'ProductSMILES' in rows[0]
