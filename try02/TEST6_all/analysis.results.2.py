# -*- coding: utf-8 -*-
"""
Scan qwen_results_test folder directly.
Extract YES items (input.txt + reason) into a CSV.
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
    """
    data = []

    # 모든 서브폴더 리스트
    subfolders = [
        os.path.join(root_folder, d)
        for d in os.listdir(root_folder)
        if os.path.isdir(os.path.join(root_folder, d))
    ]

    for folder in tqdm(subfolders, desc="Scanning result folders"):
        input_path = os.path.join(folder, "input.txt")
        result_path = os.path.join(folder, "result.json")

        # input.txt 없는 폴더는 스킵
        if not os.path.exists(input_path) or not os.path.exists(result_path):
            continue

        try:
            # input.txt = title + abstract
            with open(input_path, "r", encoding="utf-8") as f:
                abstract = f.read().strip()

            # result.json = pyrolysis_related, reason
            with open(result_path, "r", encoding="utf-8") as f:
                result = json.load(f)

            pyro = result.get("pyrolysis_related", "")
            reason = result.get("reason", "")

            data.append({
                "abstract": abstract,
                "pyrolysis_related": pyro,
                "reason": reason
            })

        except Exception as e:
            logging.error(f"Error reading {folder}: {e}")
            continue

    return data


def save_yes_to_csv(data, csv_path="yes_results.csv"):
    yes_items = [d for d in data if d["pyrolysis_related"] == "YES"]

    logging.info(f"Saving YES entries to CSV: {csv_path}")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["abstract", "reason"])

        for d in yes_items:
            writer.writerow([d["abstract"], d["reason"]])

    logging.info(f"Saved {len(yes_items)} YES rows to {csv_path}")


def count_yes_no(data):
    yes = sum(1 for d in data if d["pyrolysis_related"] == "YES")
    no  = sum(1 for d in data if d["pyrolysis_related"] == "NO")
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

    save_yes_to_csv(parsed, "yes_results.csv")
    print("\nCSV saved: yes_results.csv")


