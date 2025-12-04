# -*- coding: utf-8 -*-
"""
Batch PII XML Downloader Engine (with success/failure logs)
- CSV 입력 → URL에서 PII 추출 → subprocess 병렬 다운로드
- 성공/실패 전체 로그 + 실패 전용 로그 생성
"""

import argparse
import pandas as pd
import re
import subprocess
from multiprocessing import Pool
from tqdm import tqdm
import os
import logging
import sys
from datetime import datetime

# ------------------------------------------------------------
# Setup logging (main engine log)
# ------------------------------------------------------------
os.makedirs("engine_logs", exist_ok=True)

full_log_path = os.path.join("engine_logs", "engine_full.log")
fail_log_path = os.path.join("engine_logs", "engine_fail.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(full_log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ],
)

fail_logger = logging.getLogger("fail_logger")
fail_logger.setLevel(logging.WARNING)
fail_handler = logging.FileHandler(fail_log_path, encoding="utf-8")
fail_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
fail_logger.addHandler(fail_handler)


# ------------------------------------------------------------
# Extract PII from URL
# ------------------------------------------------------------
def extract_pii(url: str) -> str:
    match = re.search(r"/pii/([A-Za-z0-9().-]+)", url)
    if match:
        return match.group(1).strip()
    return None


# ------------------------------------------------------------
# subprocess runner for downloader
# ------------------------------------------------------------
def run_downloader(task):
    pii, view, script_path = task
    cmd = [
        sys.executable,
        script_path,
        "--pii", pii,
        "--view", view
    ]

    try:
        subprocess.run(cmd, check=True)
        return (pii, "OK")

    except Exception as e:
        return (pii, f"FAIL: {e}")


# ------------------------------------------------------------
# Main engine
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Batch PII XML Downloader Engine")
    parser.add_argument("--csv", required=True, help="CSV file containing URLs")
    parser.add_argument("--view", default="META_ABS", help="Elsevier API view type")
    parser.add_argument("--script", default="pii_xml_downloader.py", help="Downloader script path")
    parser.add_argument("--n_cpus", type=int, default=4, help="Number of parallel workers")

    args = parser.parse_args()

    logging.info(f"Loading CSV: {args.csv}")
    df = pd.read_csv(args.csv)

    # if "url" not in df.columns:
    #     raise ValueError("CSV must contain a 'url' column")

    # Extract PII
    # df["pii"] = df["url"].apply(extract_pii)
    df_valid = df[df["pii"].notna()].copy()

    logging.info(f"Valid PII count = {len(df_valid)}")

    tasks = [(row["pii"], args.view, args.script) for _, row in df_valid.iterrows()]

    # Parallel processing
    logging.info(f"Starting parallel downloads (n_cpus={args.n_cpus})")

    with Pool(args.n_cpus) as pool:
        results = list(tqdm(pool.imap(run_downloader, tasks), total=len(tasks)))

    # Save results
    out_csv = "download_results.csv"
    res_df = pd.DataFrame(results, columns=["pii", "status"])
    res_df.to_csv(out_csv, index=False)

    logging.info(f"Result CSV saved → {out_csv}")

    # Write failure-only log
    failures = [f"{pii} | {status}" for pii, status in results if status != "OK"]
    if failures:
        logging.warning(f"Failed downloads: {len(failures)} entries")
        for line in failures:
            fail_logger.warning(line)
    else:
        logging.info("No failed downloads.")

    logging.info(f"Engine full log → {full_log_path}")
    logging.info(f"Engine fail log → {fail_log_path}")
    logging.info("All tasks completed.")


if __name__ == "__main__":
    main()
