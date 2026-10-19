import pandas as pd
import numpy as np

FILE_PATH = 'yellow_tripdata_2021-01.csv.gz'

print('========================================================')
print('STEP 1: LOOK AT THE FIRST 100 ROWS')
print('========================================================')

df_100 = pd.read_csv(FILE_PATH, nrows=100)
print('\n--- df.head() ---')
print(df_100.head())

print('\n--- df.dtypes ---')
print(df_100.dtypes)

print('\n--- Missing values in first 100 rows ---')
print(df_100.isnull().sum())

print('\n========================================================')
print('STEP 2: PROFILE DATA IN CHUNKS OF 100,000 ROWS')
print('========================================================')

chunksize = 100000
total_rows = 0
dtypes_dict = {}
null_counts = {}
min_vals = {}
max_vals = {}

# We specify parse_dates so pickup and dropoff can be checked accurately
for chunk_idx, chunk in enumerate(pd.read_csv(FILE_PATH, chunksize=chunksize, parse_dates=['tpep_pickup_datetime', 'tpep_dropoff_datetime'])):
    chunk_len = len(chunk)
    total_rows += chunk_len
    
    if chunk_idx == 0:
        for col in chunk.columns:
            dtypes_dict[col] = str(chunk[col].dtype)
            null_counts[col] = 0
            min_vals[col] = None
            max_vals[col] = None

    for col in chunk.columns:
        null_counts[col] += int(chunk[col].isnull().sum())
        
        valid_vals = chunk[col].dropna()
        if len(valid_vals) > 0:
            c_min = valid_vals.min()
            c_max = valid_vals.max()
            if min_vals[col] is None or c_min < min_vals[col]:
                min_vals[col] = c_min
            if max_vals[col] is None or c_max > max_vals[col]:
                max_vals[col] = c_max

profile_records = []
for col in dtypes_dict.keys():
    cnt_null = null_counts[col]
    pct_null = (cnt_null / total_rows) * 100
    profile_records.append({
        'column': col,
        'dtype': dtypes_dict[col],
        'null_count': cnt_null,
        'null_pct': f'{pct_null:.2f}%',
        'min_val': str(min_vals[col]),
        'max_val': str(max_vals[col])
    })

profile_df = pd.DataFrame(profile_records)
print(f'Total Rows Profiled: {total_rows}')
print(profile_df.to_string(index=False))

print('\n========================================================')
print('STEP 3: FIND PROBLEMS ACROSS THE FULL DATASET')
print('========================================================')

outside_jan_count = 0
neg_zero_fare_count = 0
neg_zero_distance_count = 0
zero_passenger_count = 0
null_passenger_count = 0

# Check duplicate keys across chunks or within chunks
# Since exact duplicates across 1.3M rows might require a hash set of keys:
import hashlib

seen_trip_hashes = set()
duplicate_rows_count = 0

for chunk in pd.read_csv(FILE_PATH, chunksize=chunksize, parse_dates=['tpep_pickup_datetime', 'tpep_dropoff_datetime']):
    # 1. Pickups outside January 2021
    bad_pickups = (chunk['tpep_pickup_datetime'] < '2021-01-01') | (chunk['tpep_pickup_datetime'] >= '2021-02-01')
    outside_jan_count += int(bad_pickups.sum())
    
    # 2. Negative or zero fares and distances
    bad_fares = chunk['fare_amount'] <= 0
    neg_zero_fare_count += int(bad_fares.sum())
    
    bad_distances = chunk['trip_distance'] <= 0
    neg_zero_distance_count += int(bad_distances.sum())
    
    # 3. Passenger count == 0 and null passenger_count
    zero_passengers = chunk['passenger_count'] == 0
    zero_passenger_count += int(zero_passengers.sum())
    null_passenger_count += int(chunk['passenger_count'].isnull().sum())
    
    # 4. Duplicate rows
    # Compute row hashes
    str_repr = chunk.astype(str).apply(lambda row: '|'.join(row), axis=1)
    for r in str_repr:
        h = hash(r)
        if h in seen_trip_hashes:
            duplicate_rows_count += 1
        else:
            seen_trip_hashes.add(h)

problems_summary = pd.DataFrame([
    {'Problem': 'Pickups outside Jan 2021', 'Count': outside_jan_count, 'Pct_of_Total': f'{(outside_jan_count/total_rows)*100:.2f}%'},
    {'Problem': 'Fare amount <= 0', 'Count': neg_zero_fare_count, 'Pct_of_Total': f'{(neg_zero_fare_count/total_rows)*100:.2f}%'},
    {'Problem': 'Trip distance <= 0', 'Count': neg_zero_distance_count, 'Pct_of_Total': f'{(neg_zero_distance_count/total_rows)*100:.2f}%'},
    {'Problem': 'Passenger count == 0', 'Count': zero_passenger_count, 'Pct_of_Total': f'{(zero_passenger_count/total_rows)*100:.2f}%'},
    {'Problem': 'Passenger count is NULL', 'Count': null_passenger_count, 'Pct_of_Total': f'{(null_passenger_count/total_rows)*100:.2f}%'},
    {'Problem': 'Duplicate Rows', 'Count': duplicate_rows_count, 'Pct_of_Total': f'{(duplicate_rows_count/total_rows)*100:.4f}%'},
])

print(problems_summary.to_string(index=False))

