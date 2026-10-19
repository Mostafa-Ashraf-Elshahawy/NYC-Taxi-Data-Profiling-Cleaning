import pandas as pd
import numpy as np

FILE_PATH = "yellow_tripdata_2021-01.csv.gz"
CHUNK_SIZE = 100000

def step1_look():
    print("=" * 70)
    print("STEP 1: LOOK AT FIRST 100 ROWS")
    print("=" * 70)
    df_100 = pd.read_csv(FILE_PATH, nrows=100)
    
    print("\n--- df.head() ---")
    print(df_100.head())
    
    print("\n--- df.dtypes ---")
    print(df_100.dtypes)
    
    print("\n--- Missing values in first 100 rows ---")
    print(df_100.isnull().sum())
    
    return df_100

def step2_profile():
    print("\n" + "=" * 70)
    print("STEP 2: PROFILE ENTIRE FILE IN CHUNKS OF 100,000 ROWS")
    print("=" * 70)
    
    total_rows = 0
    dtypes_dict = {}
    null_counts = {}
    min_vals = {}
    max_vals = {}
    
    for chunk_idx, chunk in enumerate(pd.read_csv(FILE_PATH, chunksize=CHUNK_SIZE, parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"], low_memory=False)):
        total_rows += len(chunk)
        if chunk_idx == 0:
            for col in chunk.columns:
                dtypes_dict[col] = str(chunk[col].dtype)
                null_counts[col] = 0
                min_vals[col] = None
                max_vals[col] = None
                
        for col in chunk.columns:
            null_counts[col] += int(chunk[col].isnull().sum())
            valid = chunk[col].dropna()
            if len(valid) > 0:
                c_min = valid.min()
                c_max = valid.max()
                if min_vals[col] is None or c_min < min_vals[col]:
                    min_vals[col] = c_min
                if max_vals[col] is None or c_max > max_vals[col]:
                    max_vals[col] = c_max

    profile_records = []
    for col in dtypes_dict.keys():
        n_count = null_counts[col]
        n_pct = (n_count / total_rows) * 100
        profile_records.append({
            "column": col,
            "dtype": dtypes_dict[col],
            "null_count": n_count,
            "null_pct": f"{n_pct:.2f}%",
            "min_val": str(min_vals[col]),
            "max_val": str(max_vals[col])
        })
    profile_df = pd.DataFrame(profile_records)
    print(f"Total Rows Profiled: {total_rows}")
    print(profile_df.to_string(index=False))
    return profile_df, total_rows

def step3_find_problems(total_rows):
    print("\n" + "=" * 70)
    print("STEP 3: FIND PROBLEMS ACROSS FULL DATASET")
    print("=" * 70)
    
    outside_jan_count = 0
    fare_le_zero_count = 0
    dist_le_zero_count = 0
    both_fare_dist_zero_count = 0
    passenger_zero_count = 0
    passenger_null_count = 0
    duplicate_rows_count = 0
    
    seen_rows = set()
    
    for chunk in pd.read_csv(FILE_PATH, chunksize=CHUNK_SIZE, parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"], low_memory=False):
        # 1. Dates outside Jan 2021
        bad_dates = (chunk["tpep_pickup_datetime"] < "2021-01-01") | (chunk["tpep_pickup_datetime"] >= "2021-02-01")
        outside_jan_count += int(bad_dates.sum())
        
        # 2. Fare and distance <= 0
        fare_bad = chunk["fare_amount"] <= 0
        fare_le_zero_count += int(fare_bad.sum())
        
        dist_bad = chunk["trip_distance"] <= 0
        dist_le_zero_count += int(dist_bad.sum())
        
        both_bad = (chunk["fare_amount"] <= 0) & (chunk["trip_distance"] <= 0)
        both_fare_dist_zero_count += int(both_bad.sum())
        
        # 3. Passenger count == 0 and null
        p_zero = chunk["passenger_count"] == 0
        passenger_zero_count += int(p_zero.sum())
        passenger_null_count += int(chunk["passenger_count"].isnull().sum())
        
        # 4. Duplicate rows
        for row in chunk.itertuples(index=False, name=None):
            if row in seen_rows:
                duplicate_rows_count += 1
            else:
                seen_rows.add(row)

    problems_df = pd.DataFrame([
        {"Problem": "Pickups outside January 2021", "Count": outside_jan_count, "Pct_of_Total": f"{(outside_jan_count/total_rows)*100:.3f}%"},
        {"Problem": "Negative or zero fare (fare_amount <= 0)", "Count": fare_le_zero_count, "Pct_of_Total": f"{(fare_le_zero_count/total_rows)*100:.3f}%"},
        {"Problem": "Negative or zero trip distance (trip_distance <= 0)", "Count": dist_le_zero_count, "Pct_of_Total": f"{(dist_le_zero_count/total_rows)*100:.3f}%"},
        {"Problem": "Both fare <= 0 and trip distance <= 0", "Count": both_fare_dist_zero_count, "Pct_of_Total": f"{(both_fare_dist_zero_count/total_rows)*100:.3f}%"},
        {"Problem": "Passenger count == 0", "Count": passenger_zero_count, "Pct_of_Total": f"{(passenger_zero_count/total_rows)*100:.3f}%"},
        {"Problem": "Passenger count is NULL (missing)", "Count": passenger_null_count, "Pct_of_Total": f"{(passenger_null_count/total_rows)*100:.3f}%"},
        {"Problem": "Exact duplicate rows", "Count": duplicate_rows_count, "Pct_of_Total": f"{(duplicate_rows_count/total_rows)*100:.5f}%"},
    ])
    print(problems_df.to_string(index=False))
    return problems_df

def step4_decide_table():
    print("\n" + "=" * 70)
    print("STEP 4: DECISION MATRIX (DROP, FIX, OR FLAG)")
    print("=" * 70)
    
    decision_matrix = pd.DataFrame([
        {
            "Problem": "Pickups outside Jan 2021",
            "Decision": "Drop / Route",
            "Why": "Belongs to different month/year; corrupts Jan 2021 analytical partition.",
            "Owner": "Data Engineering"
        },
        {
            "Problem": "Negative / zero fare (fare <= 0)",
            "Decision": "Drop (or Flag for dispute audit)",
            "Why": "Negative fares indicate voids/disputes/cancellations; zero fares indicate unmetered or test rides.",
            "Owner": "Finance / Revenue Analytics"
        },
        {
            "Problem": "Negative / zero distance (dist <= 0)",
            "Decision": "Drop (or Flag)",
            "Why": "Taxi trip cannot be 0 miles; indicates meter activated mistakenly or immediate cancellation.",
            "Owner": "Operations / Fleet Telemetry"
        },
        {
            "Problem": "Passenger count == 0",
            "Decision": "Fix (Impute to 1) or Flag",
            "Why": "A completed trip must have at least 1 passenger; driver omitted passenger count; TLC default is 1.",
            "Owner": "Driver Mobile App / Product"
        },
        {
            "Problem": "Passenger count is NULL",
            "Decision": "Fix (Impute to 1) and Flag",
            "Why": "Missing metadata from dispatch records (7.18% of dataset); default to 1 passenger.",
            "Owner": "Data Engineering & Partner Integration"
        },
        {
            "Problem": "Exact duplicate rows",
            "Decision": "Drop",
            "Why": "Duplicated telemetry logs caused by pipeline network retries.",
            "Owner": "Data Engineering"
        }
    ])
    print(decision_matrix.to_string(index=False))
    return decision_matrix

def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Cleans the NYC yellow taxi DataFrame according to defined business rules.
    
    Requirements:
    - Never drop rows silently (returns dict of rows removed per rule).
    - Do not modify original dataframe (uses copy).
    - Returns: (cleaned_df, rows_removed_dict)
    """
    cleaned = df.copy()
    rows_removed = {}
    
    # Ensure datetime types
    cleaned["tpep_pickup_datetime"] = pd.to_datetime(cleaned["tpep_pickup_datetime"])
    cleaned["tpep_dropoff_datetime"] = pd.to_datetime(cleaned["tpep_dropoff_datetime"])
    
    initial_rows = len(cleaned)
    
    # Rule 1: Drop exact duplicates
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    rows_removed["rule_drop_duplicates"] = before - len(cleaned)
    
    # Rule 2: Drop pickups outside January 2021
    before = len(cleaned)
    valid_dates = (cleaned["tpep_pickup_datetime"] >= "2021-01-01") & (cleaned["tpep_pickup_datetime"] < "2021-02-01")
    cleaned = cleaned[valid_dates]
    rows_removed["rule_drop_outside_jan_2021"] = before - len(cleaned)
    
    # Rule 3: Drop negative or zero fares
    before = len(cleaned)
    valid_fares = cleaned["fare_amount"] > 0
    cleaned = cleaned[valid_fares]
    rows_removed["rule_drop_invalid_fare"] = before - len(cleaned)
    
    # Rule 4: Drop zero or negative trip distance
    before = len(cleaned)
    valid_distance = cleaned["trip_distance"] > 0
    cleaned = cleaned[valid_distance]
    rows_removed["rule_drop_invalid_distance"] = before - len(cleaned)
    
    # Rule 5: Fix / Impute passenger count (0 or null -> 1)
    before_fix_0 = int((cleaned["passenger_count"] == 0).sum())
    before_fix_null = int(cleaned["passenger_count"].isnull().sum())
    cleaned["passenger_count"] = cleaned["passenger_count"].fillna(1)
    cleaned.loc[cleaned["passenger_count"] == 0, "passenger_count"] = 1
    rows_removed["rule_fix_passenger_count_0_or_null"] = before_fix_0 + before_fix_null  # fixed, not dropped
    
    return cleaned, rows_removed

def step5_clean_demo():
    print("\n" + "=" * 70)
    print("STEP 5: DEMONSTRATE clean(df) FUNCTION")
    print("=" * 70)
    
    # Let's run clean on first 200,000 rows as a demonstration chunk
    sample_df = pd.read_csv(FILE_PATH, nrows=200000, low_memory=False)
    print(f"Sample initial rows: {len(sample_df)}")
    
    cleaned_df, removed_dict = clean(sample_df)
    
    print("\n--- Rows Removed per Rule Dict ---")
    print(removed_dict)
    
    summary_df = pd.DataFrame([
        {"Metric": "Rows Before", "Count": len(sample_df)},
        {"Metric": "Rows After", "Count": len(cleaned_df)},
        {"Metric": "Total Rows Dropped", "Count": len(sample_df) - len(cleaned_df)},
        {"Metric": "Retention Rate", "Count": f"{(len(cleaned_df) / len(sample_df)) * 100:.2f}%"}
    ])
    print("\n--- Cleaning Summary Table ---")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    step1_look()
    profile_df, total_rows = step2_profile()
    problems_df = step3_find_problems(total_rows)
    step4_decide_table()
    step5_clean_demo()
