from Scifinder_rdf_processer import RDFWorker
import os, json
folder = r'dataset\\Buchwald\\2021-2024'
md_out = os.path.join(folder,'_test_out.md')
jsonl_out = os.path.join(folder,'_test_out.jsonl')
worker = RDFWorker(folder, md_out, jsonl_out)
worker.rdf_files = worker._find_rdf_files()
combined = worker._process_rdf_files()
print('combined size', len(combined))
txt_map = worker._create_minimal_txt_map(combined)
count_with = 0
examples = []
for rid, rec in list(txt_map.items()):
    if rec.get('temperature_c') is not None or rec.get('time_h') is not None:
        count_with +=1
        if len(examples)<5:
            examples.append((rid, rec.get('temperature_c'), rec.get('time_h'), rec.get('all_condition_lines')[:2]))
print('Total reactions', len(txt_map))
print('With parsed conditions', count_with)
print('Examples:', json.dumps(examples, ensure_ascii=False, indent=2))
