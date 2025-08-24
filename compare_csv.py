import sys
import csv
from itertools import islice

def head_rows(path, n=10):
    with open(path, newline='', encoding='utf-8') as f:
        return list(islice(csv.DictReader(f), n))

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_csv.py <csv_a> <csv_b> [n]")
        sys.exit(1)
    a_path, b_path = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    A = head_rows(a_path, n)
    B = head_rows(b_path, n)
    print(f"Comparing first {min(n, len(A), len(B))} rows for Ligand, CATName, Base, BASName\n")
    cols = ("Ligand","CATName","Base","BASName")
    for i, (a, b) in enumerate(zip(A, B), start=1):
        print(f"Row {i}:")
        for c in cols:
            av = a.get(c, '')
            bv = b.get(c, '')
            print(f"  {c}:")
            print(f"    no-map: {av}")
            print(f"    maps:   {bv}")
        print()

if __name__ == "__main__":
    main()
