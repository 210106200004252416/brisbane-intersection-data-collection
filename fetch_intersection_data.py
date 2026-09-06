import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API_URL = (
    "https://data.brisbane.qld.gov.au/api/explore/v2.1/"
    "catalog/datasets/traffic-data-at-intersection/records"
)

TSC_FILE = "Brisbane_CBD_TSC_list.csv"

# --------------------------------------------------
# 1. Read the 65 CBD TSC numbers
# --------------------------------------------------

with open(TSC_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    tsc_list = sorted(
        {row["tsc"].strip() for row in reader if row["tsc"].strip()},
        key=lambda x: int(x)
    )

print(f"Loaded {len(tsc_list)} unique TSCs.")
print(tsc_list)

# --------------------------------------------------
# 2. Query every TSC
# --------------------------------------------------

all_records = []
coverage_report = []

for i, tsc in enumerate(tsc_list, start=1):

    print(f"\n[{i}/{len(tsc_list)}] Testing TSC {tsc}...")

    params = {
        "where": f'tsc = "{tsc}"',
        "limit": 100,
        "timezone": "Australia/Brisbane",
    }

    url = API_URL + "?" + urlencode(params)

    try:
        with urlopen(url, timeout=30) as response:
            data = json.load(response)

        records = data.get("results", [])
        total_count = data.get("total_count", 0)

        print(f"  Records found: {total_count}")

        coverage_report.append({
            "tsc": tsc,
            "status": "OK" if total_count > 0 else "NO_DATA",
            "record_count": total_count
        })

        all_records.extend(records)

    except Exception as e:

        print(f"  ERROR: {e}")

        coverage_report.append({
            "tsc": tsc,
            "status": "ERROR",
            "record_count": 0
        })

    # Small pause to avoid hammering the API
    time.sleep(0.2)

# --------------------------------------------------
# 3. Create output folder
# --------------------------------------------------

output_dir = Path("data")
output_dir.mkdir(exist_ok=True)

# --------------------------------------------------
# 4. Save all traffic records
# --------------------------------------------------

if all_records:

    fieldnames = sorted(
        {key for record in all_records for key in record.keys()}
    )

    output_file = output_dir / "CBD_intersection_test.csv"

    with output_file.open(
        "w", newline="", encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nSaved {len(all_records)} traffic records.")
    print(f"Traffic data file: {output_file}")

# --------------------------------------------------
# 5. Save TSC coverage report
# --------------------------------------------------

coverage_file = output_dir / "TSC_coverage_report.csv"

with coverage_file.open(
    "w", newline="", encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=["tsc", "status", "record_count"]
    )

    writer.writeheader()
    writer.writerows(coverage_report)

# --------------------------------------------------
# 6. Final summary
# --------------------------------------------------

working = [
    x for x in coverage_report
    if x["status"] == "OK"
]

no_data = [
    x for x in coverage_report
    if x["status"] == "NO_DATA"
]

errors = [
    x for x in coverage_report
    if x["status"] == "ERROR"
]

print("\n==============================")
print("CBD TSC TEST COMPLETE")
print("==============================")
print(f"Total TSCs tested : {len(tsc_list)}")
print(f"Working           : {len(working)}")
print(f"No current data   : {len(no_data)}")
print(f"Errors            : {len(errors)}")

if no_data:
    print("\nTSCs with no data:")
    print([x["tsc"] for x in no_data])

if errors:
    print("\nTSCs with errors:")
    print([x["tsc"] for x in errors])
