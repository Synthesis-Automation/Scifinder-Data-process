#!/usr/bin/env python3
import json

# Quick JSONL verification
with open('test_dual_format_report.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"JSONL Records: {len(lines)}")

if lines:
    rec = json.loads(lines[0])
    print(f"First reaction: {rec['reaction_id']}")
    print(f"Type: {rec['reaction_type']}")
    print(f"Original text lines: {len(rec['original_text'])}")
    print("✅ JSONL format verified!")
