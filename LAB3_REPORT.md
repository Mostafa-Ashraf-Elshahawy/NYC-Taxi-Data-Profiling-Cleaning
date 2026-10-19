# Lab 3 Report — NYC Taxi Data Profiling & Cleaning Pipeline

**Course**: INF4058 Data Engineering  
**Due Date**: October 19, 2026, 11:59 PM  
**Submission**: One PDF Report + GitHub Repository Link  

---

## 1. Cover
- **Student Name**: mostafa ashraf oahmed
- **Student ID**: 692300252
- **Date**: October 19, 2026
- **GitHub Repository Link**: [https://github.com/mostafaashraf/NYC-Taxi-Data-Profiling-Cleaning](https://github.com/mostafaashraf/NYC-Taxi-Data-Profiling-Cleaning)

---

## 2. The Flow (In Your Words)

### Pipeline Architecture:
$$\text{Source (NYC TLC Storage)} \longrightarrow \text{Extract (Chunked HTTP Stream)} \longrightarrow \text{Transform (clean(df) Quality Rules)} \longrightarrow \text{Load (PostgreSQL)} \longrightarrow \text{Serve (pgAdmin / Analytics)}$$

### Stage Explanations:
1. **Source**: The raw NYC TLC Yellow Taxi trip dataset hosted as a gzip-compressed CSV (`yellow_tripdata_2021-01.csv.gz`) on remote GitHub storage.
2. **Extract**: Streaming the compressed dataset into memory in batches of 100,000 rows (`chunksize=100000`). This avoids loading all 1.37 million rows simultaneously, keeping RAM consumption constant and preventing Out-Of-Memory (OOM) fatal errors.
3. **Transform**: Applying business data quality filters via `clean(df)`: dropping invalid dates, dropping non-positive fares and distances, fixing missing passenger counts, and stripping duplicate records.
4. **Load**: Writing the sanitized chunks into a PostgreSQL table (`yellow_taxi_data`) via SQLAlchemy.
5. **Serve**: The structured relational database is made queryable for downstream consumers, SQL analytical workloads, and database exploration in pgAdmin.

### What Each Component Does and Why:
- **`ingest_data.py`**: A parameterized CLI ingestion script built with `click`. It downloads the dataset, streams chunks, transforms dates, and ingests into PostgreSQL.
  - *Why Chunks*: Avoids loading gigabytes into RAM at once; allows continuous ingestion even on low-spec nodes.
  - *Why `Int64`*: Standard Pandas `int64` cannot store `NaN` values and automatically casts columns with missing entries to `float64` (e.g., `VendorID` becomes `1.0`). Specifying Pandas nullable integer type (`Int64`) preserves integer semantics while safely allowing nulls.
  - *Why `replace` on the first chunk only*: On chunk 0, `df.head(0).to_sql(..., if_exists='replace')` writes an empty schema table. All subsequent chunks use `if_exists='append'`. If `replace` were used on all chunks, each batch would overwrite the previous one, leaving only the final 69,765 rows.
- **`docker-compose.yaml`**: An orchestration manifest that defines multi-container architecture (PostgreSQL service + pgAdmin service + bridge network). It ensures persistent volume storage so database tables persist across container restarts.
- **`Dockerfile`**: A blueprint that packages the Python runtime, dependencies (`pandas`, `psycopg`, `click`, `tqdm`), and `ingest_data.py` into a containerized, reproducible execution unit that runs consistently across Linux, Windows, or Cloud environments without host dependency conflicts.

---

## 3. What We Ran in Class

1. **`docker compose up -d`**: Started the background multi-container environment containing the PostgreSQL database (`pgdatabase`) and pgAdmin Web UI on a shared Docker bridge network with persistent volume storage.
2. **`docker build -t taxi_ingest:v001 .`**: Packaged our Python ingestion script, dependencies, and environment configuration into a standalone Docker image.
3. **`docker run --network=pipeline_default taxi_ingest:v001 ...`**: Executed the ingestion container inside the shared Docker network, downloading the dataset and ingesting **1,369,765 rows** into the `yellow_taxi_data` Postgres table.
4. **Verification via pgAdmin**: Queried `SELECT count(1) FROM yellow_taxi_data;` which returned exactly `1,369,765`.

> **[REQUIRED EVIDENCE - SCREENSHOTS TAKEN IN CLASS]**  
> *(Insert your screenshot taken during class showing the command, its output, and your terminal prompt. Do not re-run class steps at home.)*  
>  
> `[PASTE IN-CLASS TERMINAL SCREENSHOT OF DOCKER COMPOSE UP HERE]`  
> `[PASTE IN-CLASS TERMINAL SCREENSHOT OF DOCKER BUILD HERE]`  
> `[PASTE IN-CLASS TERMINAL SCREENSHOT OF CONTAINER RUN & INGEST COUNT = 1,369,765 HERE]`  

---

## 4. What You Found in the Data (Profiling Results)

The dataset was profiled in chunks of 100,000 rows across all **1,369,765 rows**.

### Evidence: Printed Profiling Table (`print(profile_df)`)
*(Per Rule: Printed with print() and screenshotted from terminal / notebook)*

```text
               column          dtype  null_count null_pct             min_val             max_val
             VendorID          int64       98352    7.18%                   1                   2
 tpep_pickup_datetime datetime64[us]           0    0.00% 2008-12-31 23:05:14 2021-02-22 16:52:16
tpep_dropoff_datetime datetime64[us]           0    0.00% 2008-12-31 23:07:22 2021-02-22 16:56:15
      passenger_count          int64       98352    7.18%                   0                   8
        trip_distance        float64           0    0.00%                 0.0           263163.28
           RatecodeID          int64       98352    7.18%                   1                  99
   store_and_fwd_flag            str       98352    7.18%                   N                   Y
         PULocationID          int64           0    0.00%                   1                 265
         DOLocationID          int64           0    0.00%                   1                 265
         payment_type          int64       98352    7.18%                   1                   4
          fare_amount        float64           0    0.00%              -490.0              6960.5
                extra        float64           0    0.00%                -5.5                8.25
              mta_tax        float64           0    0.00%                -0.5                 0.5
           tip_amount        float64           0    0.00%              -100.0             1140.44
         tolls_amount        float64           0    0.00%              -31.12              811.75
improvement_surcharge        float64           0    0.00%                -0.3                 0.3
         total_amount        float64           0    0.00%              -492.8             7661.28
 congestion_surcharge        float64           0    0.00%                -2.5                 3.0
```

> **[REQUIRED EVIDENCE - SCREENSHOT OF OUTPUT]**  
> `[PASTE SCREENSHOT OF TERMINAL / JUPYTER OUTPUT OF print(profile_df) HERE]`

---

### Evidence: Printed Problems Table (`print(problems_df)`)

```text
                                            Problem  Count Pct_of_Total
                       Pickups outside January 2021     24       0.002%
           Negative or zero fare (fare_amount <= 0)   7411       0.541%
Negative or zero trip distance (trip_distance <= 0)  19952       1.457%
              Both fare <= 0 and trip distance <= 0    984       0.072%
                               Passenger count == 0  26726       1.951%
                  Passenger count is NULL (missing)  98352       7.180%
                               Exact duplicate rows      0     0.00000%
```

> **[REQUIRED EVIDENCE - SCREENSHOT OF OUTPUT]**  
> `[PASTE SCREENSHOT OF TERMINAL / JUPYTER OUTPUT OF print(problems_df) HERE]`

### Analysis of Anomalies:
1. **Bad Timestamps**: 24 records have pickup dates outside January 2021 (ranging from 2008 to late February 2021), caused by misconfigured taximeter clocks.
2. **Negative/Zero Fares**: 7,411 trips have `fare_amount <= 0` (minimum is `-$490.00`), representing payment disputes, voids, reversed charges, or system testing.
3. **Zero Distances**: 19,952 trips recorded `0.0` miles (with 984 also having zero fare), representing meter start-and-stops, passenger cancellations, or GPS sensor dropouts.
4. **Passenger Count Anomalies**: 26,726 rows explicitly record 0 passengers, and 98,352 rows (7.18%) have null passenger counts. Since a taxi cannot legally or physically carry 0 passengers on a fare-earning trip, these are omitted driver inputs.

---

## 5. How You Cleaned It

### Cleaning Decisions Matrix:
| Problem | Decision | Why | Rule Owner |
| :--- | :--- | :--- | :--- |
| **Pickups outside Jan 2021** | **Drop** | Belongs to separate monthly partition; corrupts January 2021 metrics. | Data Engineering |
| **Negative/Zero Fare** | **Drop** | Distorts revenue aggregation and unit economics; represents voided transactions. | Finance / Revenue Analytics |
| **Zero/Negative Distance** | **Drop** | Impossible physical trip; invalidates speed and distance analytics. | Fleet Telemetry / Ops |
| **Passenger Count = 0 or NULL** | **Fix (Impute to 1)** | Default taxi occupancy is 1 passenger; dropping 9% of rows would lose valid revenue data. | Driver App / Product |
| **Duplicate Rows** | **Drop** | Prevents double-counting trips caused by upstream network retries. | Data Engineering |

### The `clean(df)` Implementation:
```python
def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Cleans the NYC yellow taxi DataFrame according to defined business rules.
    
    Requirements followed:
    - Never drop rows silently (returns dict of rows removed per rule).
    - Do not modify original dataframe (uses copy).
    - Returns: (cleaned_df, rows_removed_dict)
    """
    cleaned = df.copy()
    rows_removed = {}
    
    cleaned['tpep_pickup_datetime'] = pd.to_datetime(cleaned['tpep_pickup_datetime'])
    cleaned['tpep_dropoff_datetime'] = pd.to_datetime(cleaned['tpep_dropoff_datetime'])
    
    # 1. Duplicates
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    rows_removed['rule_drop_duplicates'] = before - len(cleaned)
    
    # 2. Date filtering
    before = len(cleaned)
    valid_dates = (cleaned['tpep_pickup_datetime'] >= '2021-01-01') & (cleaned['tpep_pickup_datetime'] < '2021-02-01')
    cleaned = cleaned[valid_dates]
    rows_removed['rule_drop_outside_jan_2021'] = before - len(cleaned)
    
    # 3. Valid fare
    before = len(cleaned)
    cleaned = cleaned[cleaned['fare_amount'] > 0]
    rows_removed['rule_drop_invalid_fare'] = before - len(cleaned)
    
    # 4. Valid distance
    before = len(cleaned)
    cleaned = cleaned[cleaned['trip_distance'] > 0]
    rows_removed['rule_drop_invalid_distance'] = before - len(cleaned)
    
    # 5. Fix passenger count (0 or null -> 1)
    p_zero = int((cleaned['passenger_count'] == 0).sum())
    p_null = int(cleaned['passenger_count'].isnull().sum())
    cleaned['passenger_count'] = cleaned['passenger_count'].fillna(1)
    cleaned.loc[cleaned['passenger_count'] == 0, 'passenger_count'] = 1
    rows_removed['rule_fix_passenger_count_0_or_null'] = p_zero + p_null
    
    return cleaned, rows_removed
```

### Evidence: Full Dataset Cleaning Results Table:
```text
============================================================
FULL DATASET CLEANING RESULTS (1,369,765 ROWS)
============================================================
Total Raw Rows:      1,369,765
Total Cleaned Rows:  1,343,363
Total Dropped Rows:  26,402
Retention Rate:      98.07%

--- Rows Removed / Handled Per Rule ---
                              Rule  Count Pct_of_Raw
              rule_drop_duplicates      0     0.000%
        rule_drop_outside_jan_2021     24     0.002%
            rule_drop_invalid_fare   7410     0.541%
        rule_drop_invalid_distance  18968     1.385%
rule_fix_passenger_count_0_or_null 123259     8.999%
```

> **[REQUIRED EVIDENCE - SCREENSHOT OF OUTPUT]**  
> `[PASTE SCREENSHOT OF TERMINAL / JUPYTER OUTPUT OF {rule: rows_removed} AND SUMMARY HERE]`

---

## 6. Answers to Core Questions

### Q1: Why does the container reach the DB as `pgdatabase`, not `localhost`?
**Answer**: Each Docker container runs inside its own isolated Linux network namespace with its own loopback interface. If a script inside a container requests `localhost`, it talks only to itself, not to the host machine or other containers.  
When containers join a user-defined bridge network (created by Docker Compose), Docker runs an internal DNS server. Containers automatically resolve other services by their compose service name (e.g., `pgdatabase`). Therefore, the database host must be `pgdatabase`.

### Q2: Why chunks, and what was wrong with `replace` for many months?
**Answer**:
1. **Why chunks**: The raw uncompressed CSV expands to hundreds of megabytes in memory, and multi-month taxi datasets reach tens of gigabytes. Loading all data at once causes memory spikes, container thrashing, and OS Out-of-Memory (OOM) kills. Processing in chunks of 100,000 bounds memory consumption to a predictable, minimal footprint (~50MB RAM).
2. **What was wrong with `replace`**: If `if_exists='replace'` is applied across chunks or multiple monthly files, each batch drops the table and recreates it from scratch. All previous data is deleted, leaving only the very last ingested batch. The proper pattern is to execute `replace` only on the initial header batch (`df.head(0).to_sql(..., if_exists='replace')`) to set up schema types, followed strictly by `if_exists='append'` for every subsequent chunk.

### Q3: How did you verify your results?
**Answer**:
1. **Row Count Conservation**: Verified that Initial Rows (1,369,765) minus Total Dropped Rows (26,402) equals Final Cleaned Rows (1,343,363).
2. **Zero Defect Assertion**: Executed post-cleaning assertions across the cleaned output to confirm:
   - 0 records with pickup dates outside Jan 2021.
   - 0 records with `fare_amount <= 0`.
   - 0 records with `trip_distance <= 0`.
   - 0 records with `passenger_count <= 0` or missing (`NaN`).
   - 0 exact duplicate rows.

---

## 7. What Broke & How It Was Fixed

### Error Hit:
`DtypeWarning: Columns (6: store_and_fwd_flag) have mixed types. Specify dtype option on import or set low_memory=False.`  
Followed by integer parsing errors when converting columns with `NaN` values to integer datatypes (`ValueError: Cannot convert non-finite values (NA or inf) to integer`).

### Cause:
In Pandas, the standard NumPy integer type `int64` does not support null (`NaN`) values. When Pandas encounters mixed types or missing values in a column containing integers (like `VendorID`, `passenger_count`, `payment_type`), it automatically casts the entire column to `float64` or fails if an explicit `int` type cast is requested.

### Fix:
1. Specified `low_memory=False` on the chunk reader.
2. Utilized Pandas nullable integer types (`"Int64"` with a capital `I`) and nullable string types (`"string"`) in the schema dictionary:
```python
dtype = {
    "VendorID": "Int64",
    "passenger_count": "Int64",
    "RatecodeID": "Int64",
    "payment_type": "Int64",
    "store_and_fwd_flag": "string"
}
```
This allowed missing values to be represented as `<NA>` without forcing integer columns to become floating-point numbers.

> **[REQUIRED EVIDENCE - SCREENSHOT OF ERROR & FIX]**  
> `[PASTE SCREENSHOT OF THE TERMINAL DTYPE WARNING / ERROR AND THE CODE FIX HERE]`
