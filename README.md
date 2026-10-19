# NYC Taxi Data Profiling & Cleaning

## Overview & Instructions Followed
- Analyzed and profiled `yellow_tripdata_2021-01.csv.gz` in chunks of 100,000 rows.
- Handled missing values, invalid trip dates, negative/zero fares, and duplicates.
- Applied custom `clean(df)` logic returning cleaned data and removed-row metrics.
- Pipeline stopped at the cleaning stage without loading into PostgreSQL.
- No data files or `.venv` directory are tracked in this repository.

---

## Repository Structure
```text
├── README.md                 # Project overview and summary
├── lab3_clean_nyc_taxi.ipynb  # Executed notebook (Steps 1–5 + verification)
├── profile_and_clean.py      # Standalone Python script with clean(df)
├── LAB3_REPORT.md            # Comprehensive assignment report
└── .gitignore                # Excludes data files, .venv, and caches
```

---

## Cleaning Rules & Results

### Initial vs Cleaned Row Counts:
- **Total Initial Rows**: 1,369,765
- **Total Rows Dropped**: 26,402
- **Total Cleaned Rows**: 1,343,363
- **Retention Rate**: 98.07%

### Metrics per Rule:
| Rule | Action | Count Handled | % of Total | Rationale |
| :--- | :---: | :---: | :---: | :--- |
| `rule_drop_duplicates` | Drop | 0 | 0.00% | Exact duplicate records |
| `rule_drop_outside_jan_2021` | Drop | 24 | 0.002% | Pickups before 2021-01-01 or after 2021-01-31 |
| `rule_drop_invalid_fare` | Drop | 7,410 | 0.541% | Fare amount $\le 0$ (voids, disputes, cancellations) |
| `rule_drop_invalid_distance` | Drop | 18,968 | 1.385% | Trip distance $\le 0$ with positive fare |
| `rule_fix_passenger_count_0_or_null` | Fix | 123,259 | 8.999% | Imputed to 1 passenger (default TLC occupancy) |

---

## Usage

### 1. Run the Standalone Script
```bash
python profile_and_clean.py
```

### 2. Run the Notebook in VS Code / Jupyter
Open `lab3_clean_nyc_taxi.ipynb` to view the step-by-step code, profiling tables, and validation tests.
