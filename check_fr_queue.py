import csv

print("=== FR Apply Queue ===")
with open('data/fr_apply_queue.csv', newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
print(f"Rows: {len(rows)}")
for r in rows:
    print(f"  [{r.get('recommended_action','?')}] {r.get('adjusted_priority_score','?')} | {r.get('title','?')[:50]} | {r.get('company','?')[:25]}")

print()
print("=== FR filtered_strict.csv row count ===")
with open('data/fr_adzuna_jobs_filtered_strict.csv', newline='', encoding='utf-8-sig') as f:
    rows2 = list(csv.DictReader(f))
print(f"Rows: {len(rows2)}")
if rows2:
    print("Columns:", rows2[0].keys())
    print("First row title:", rows2[0].get('title','?'))
    print("First row score:", rows2[0].get('adjusted_priority_score','?'))
