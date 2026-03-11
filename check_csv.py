import csv
with open('keyword_driven_tests.csv') as f:
    rows = list(csv.DictReader(f))
    for r in rows:
        print(f"{r['Test Case ID']} - {r['Operation']}")
