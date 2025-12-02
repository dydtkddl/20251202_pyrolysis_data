# -*- coding: utf-8 -*-
"""
Scan qwen_results_test folders.
Save all (YES + NO) into CSV with:
source_file, abstract, label, reason
Includes logging + tqdm.
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
    qwen_results_test 내부 폴더들을 순회하며
    input.txt + result.json 을 파싱.
    폴더 이름(~.xml)을 source_file 로 저장.
    """
    data = []

    subfolders = [
        os.path.join(root_folder, d)
        for d in os.listdir(root_folder)
        if os.path.isdir(os.path.join(root_folder, d))
    ]

    for folder in tqdm(subfolders, desc="Scanning result folders"):
        source_file = os.path.basename(folder)  # e.g., 000862159380027C__META_ABS.xml
        input_path = os.path.join(folder, "input.txt")
        result_path = os.path.join(folder, "result.json")

        if not os.path.exists(input_path) or not os.path.exists(result_path):
            continue

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                abstract = f.read().strip()

            with open(result_path, "r", encoding="utf-8") as f:
                result = json.load(f)

            label = result.get("pyrolysis_related", "")
            reason = result.get("reason", "")

            data.append({
                "source_file": source_file,
                "abstract": abstract,
                "label": label,
                "reason": reason
            })

        except Exception as e:
            logging.error(f"Error reading {folder}: {e}")
            continue

    return data


def save_all_to_csv(data, csv_path="all_results.csv"):
    logging.info(f"Saving ALL entries (YES + NO) to CSV: {csv_path}")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["source_file", "abstract", "label", "reason"])

        for d in data:
            writer.writerow([
                d["source_file"],
                d["abstract"],
                d["label"],
                d["reason"]
            ])

    logging.info(f"Saved {len(data)} rows to {csv_path}")


def count_yes_no(data):
    yes = sum(1 for d in data if d["label"] == "YES")
    no = sum(1 for d in data if d["label"] == "NO")
    total = yes + no
    return yes, no, total


if __name__ == "__main__":
    ROOT = "qwen_results_test"

    logging.info("Starting scan...")
    parsed = scan_results(ROOT)

    yes, no, total = count_yes_no(parsed)

    print("\n===== SUMMARY =====")
    print(f"YES: {yes}")
    print(f"NO: {no}")
    print(f"TOTAL: {total}")

    save_all_to_csv(parsed, "all_results.csv")
    print("\nCSV saved: all_results.csv")

