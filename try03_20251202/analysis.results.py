# -*- coding: utf-8 -*-
"""
YES/NO ratio counter for results.txt
Includes logging + tqdm
"""

import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def count_yes_no(filepath):
    yes = 0
    no = 0

    logging.info(f"Reading file: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="Processing lines"):
        line = line.strip()
        if '"pyrolysis_related": "YES"' in line:
            yes += 1
        elif '"pyrolysis_related": "NO"' in line:
            no += 1

    total = yes + no
    ratio_yes = yes / total * 100 if total > 0 else 0
    ratio_no  = no / total * 100 if total > 0 else 0

    logging.info("Done counting.")

    return {
        "YES": yes,
        "NO": no,
        "Total": total,
        "YES_ratio(%)": round(ratio_yes, 2),
        "NO_ratio(%)": round(ratio_no, 2),
    }


if __name__ == "__main__":
    result = count_yes_no("results.txt")
    print("\n===== SUMMARY =====")
    for k, v in result.items():
        print(f"{k}: {v}")

