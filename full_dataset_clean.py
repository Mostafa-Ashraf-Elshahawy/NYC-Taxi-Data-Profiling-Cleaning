import pandas as pd
from profile_and_clean import clean

FILE_PATH = "yellow_tripdata_2021-01.csv.gz"
CHUNK_SIZE = 100000

total_raw_rows = 0
total_cleaned_rows = 0
cumulative_rules = {}

print("Running full dataset cleaning across all chunks...")

for chunk in pd.read_csv(FILE_PATH, chunksize=CHUNK_SIZE, low_memory=False):
    total_raw_rows += len(chunk)
    cleaned_chunk, rules = clean(chunk)
    total_cleaned_rows += len(cleaned_chunk)
    
    for r, count in rules.items():
        cumulative_rules[r] = cumulative_rules.get(r, 0) + count

print("\n" + "=" * 60)
print("FULL DATASET CLEANING RESULTS (1,369,765 ROWS)")
print("=" * 60)
print(f"Total Raw Rows:      {total_raw_rows:,}")
print(f"Total Cleaned Rows:  {total_cleaned_rows:,}")
print(f"Total Dropped Rows:  {total_raw_rows - total_cleaned_rows:,}")
print(f"Retention Rate:      {(total_cleaned_rows / total_raw_rows) * 100:.2f}%\n")

print("--- Rows Removed / Handled Per Rule ---")
rule_summary = pd.DataFrame([
    {"Rule": k, "Count": v, "Pct_of_Raw": f"{(v / total_raw_rows) * 100:.3f}%"}
    for k, v in cumulative_rules.items()
])
print(rule_summary.to_string(index=False))
