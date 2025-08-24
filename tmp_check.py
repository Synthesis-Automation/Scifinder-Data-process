import csv, json
from pathlib import Path
for fn in ['out_variants.tsv','out_core_enriched.tsv']:
    p=Path(fn)
    if not p.exists():
        continue
    with p.open('r', encoding='utf-8', newline='') as f:
        r=csv.DictReader(f)
        total=0; hits=0; filled=0
        for row in r:
            total+=1
            core=(row.get('CatalystCoreDetail','') or '')
            if 'dibenzylideneacetone' in core.lower() or ' dba' in core.lower() or 'dba)' in core.lower():
                hits+=1
                try:
                    arr=json.loads(core)
                    if any(('|' in e) and (e.strip().split('|')[-1].strip()) for e in arr):
                        filled+=1
                except Exception:
                    pass
        print(f"{fn}: total={total} dba_like_rows={hits} rows_with_any_cas_among_those={filled}")