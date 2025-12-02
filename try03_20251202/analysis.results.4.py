# -*- coding: utf-8 -*-
"""
Scan qwen_results folders and export a CSV with:
source_file, abstract, pyrolysis_related, include_in_oil_db, reason, flags
"""

import os
import json
import csv
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def scan_results(root_folder):
    """
    Scan result folders such as:
      root/source_file_folder/
         - input.txt
         - result.json
    Return list of dict containing parsed info.
    """
    data = []

    subfolders = [
        os.path.join(root_folder, d)
        for d in os.listdir(root_folder)
        if os.path.isdir(os.path.join(root_folder, d))
    ]

    for folder in tqdm(subfolders, desc="Scanning result folders"):
        source_file = os.path.basename(folder)
        input_path = os.path.join(folder, "input.txt")
        result_path = os.path.join(folder, "result.json")

        if not (os.path.exists(input_path) and os.path.exists(result_path)):
            continue

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                abstract = f.read().strip()

            with open(result_path, "r", encoding="utf-8") as f:
                result = json.load(f)

            pyro = result.get("pyrolysis_related", "")
            include = result.get("include_in_oil_db", "")
            reason = result.get("reason", "")
            flags = result.get("flags", [])

            # flags must be list, convert safely
            if isinstance(flags, list):
                flags_str = ";".join(flags)
            else:
                flags_str = str(flags)

            data.append({
                "source_file": source_file,
                "abstract": abstract,
                "pyrolysis_related": pyro,
                "include_in_oil_db": include,
                "reason": reason,
                "flags": flags_str
            })

        except Exception as e:
            logging.error(f"Error reading {folder}: {e}")
            continue

    return data


def save_all_to_csv(data, csv_path="all_results.csv"):
    logging.info(f"Saving ALL entries (YES + NO) to CSV: {csv_path}")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "source_file",
            "abstract",
            "pyrolysis_related",
            "include_in_oil_db",
            "reason",
            "flags"
        ])

        for d in data:
            writer.writerow([
                d["source_file"],
                d["abstract"],
                d["pyrolysis_related"],
                d["include_in_oil_db"],
                d["reason"],
                d["flags"]
            ])

    logging.info(f"Saved {len(data)} rows to {csv_path}")


def count_yes_no(data):
    yes = sum(1 for d in data if d["pyrolysis_related"] == "YES")
    no = sum(1 for d in data if d["pyrolysis_related"] == "NO")
    total = yes + no
    return yes, no, total


if __name__ == "__main__":
    ROOT = "qwen_results_v2"

    logging.info("Starting scan...")
    parsed = scan_results(ROOT)

    yes, no, total = count_yes_no(parsed)

    print("\n===== SUMMARY =====")
    print(f"pyrolysis_related = YES: {yes}")
    print(f"pyrolysis_related = NO : {no}")
    print(f"TOTAL: {total}")

    save_all_to_csv(parsed, "all_results.csv")
    print("\nCSV saved: all_results.csv")

