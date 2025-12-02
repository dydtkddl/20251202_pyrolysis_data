# -*- coding: utf-8 -*-
"""
CSV Batch Ollama Classifier
- CSV의 QWEN_INPUT 텍스트를 읽어 1 row씩 모델 호출
- prompt.txt의 <<<ABSTRACT>>> 부분에 삽입
- 결과는 source_file 이름으로 폴더 생성 후 저장
- all.log + fail.log 동시에 기록
- tqdm + logging
"""

import argparse
import logging
import subprocess
from datetime import datetime
from tqdm import tqdm
import os
import sys
import shutil
import pandas as pd
import re


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/all.log", mode="w", encoding="utf-8")
    ],
)

# fail 전용 로거
fail_logger = logging.getLogger("fail_logger")
fail_handler = logging.FileHandler("logs/fail.log", mode="w", encoding="utf-8")
fail_logger.addHandler(fail_handler)
fail_logger.setLevel(logging.INFO)


# ------------------------------------------------------------
# Ollama runner
# ------------------------------------------------------------
def run_ollama(model: str, full_prompt: str):
    cmd = [
        "ollama", "run",
        model,
        "--format", "json"
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out, err = process.communicate(full_prompt)

    if err:
        logging.warning(f"Ollama STDERR: {err.strip()}")

    return out.strip()


# ------------------------------------------------------------
# Safe folder name
# ------------------------------------------------------------
def safe_folder_name(name: str):
    name = str(name)
    name = name.strip()
    name = re.sub(r"[^\w\-.]", "_", name)   # 위험문자 → _
    return name


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CSV batch classification using Ollama")

    parser.add_argument("--csv", required=True, help="Input CSV file")
    parser.add_argument("--text_col", default="QWEN_INPUT", help="Column containing abstract/title")
    parser.add_argument("--sf_col", default="source_file", help="Column for folder naming")
    parser.add_argument("--prompt", required=True, help="Prompt template file")
    parser.add_argument("--model", default="qwen3:30b-a3b-instruct-2507-q4_K_M", help="Ollama model name")
    parser.add_argument("--outdir", default="results_csv", help="Root output directory")
    parser.add_argument("--limit", type=int, default=None, help="Process only N rows for testing")

    args = parser.parse_args()

    # Load CSV
    df = pd.read_csv(args.csv)

    if args.text_col not in df.columns:
        logging.error(f"Column '{args.text_col}' not found!")
        return

    if args.sf_col not in df.columns:
        logging.error(f"Column '{args.sf_col}' not found!")
        return

    if args.limit:
        df = df.head(args.limit)

    os.makedirs(args.outdir, exist_ok=True)

    # Load prompt
    logging.info(f"Loading prompt: {args.prompt}")
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    if "<<<ABSTRACT>>>" not in prompt_template:
        logging.warning("Prompt missing <<<ABSTRACT>>> placeholder. Adding at bottom.")
        prompt_template += "\n<<<ABSTRACT>>>"

    # Process rows
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing rows"):

        abstract_text = str(row[args.text_col]).strip()
        source_name_raw = str(row[args.sf_col])
        source_name = safe_folder_name(source_name_raw)

        # Use source_file as folder name
        run_dir = os.path.join(args.outdir, source_name)
        os.makedirs(run_dir, exist_ok=True)

        # Build prompt
        full_prompt = prompt_template.replace("<<<ABSTRACT>>>", abstract_text)

        try:
            result = run_ollama(args.model, full_prompt)

            # Save result.json
            with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
                f.write(result)

            # Save used prompt
            with open(os.path.join(run_dir, "prompt_used.txt"), "w", encoding="utf-8") as f:
                f.write(full_prompt)

            # Save abstract input
            with open(os.path.join(run_dir, "input.txt"), "w", encoding="utf-8") as f:
                f.write(abstract_text)

            # Save original prompt copy
            shutil.copy(args.prompt, os.path.join(run_dir, "prompt_template.txt"))

            logging.info(f"[Row {idx}] OK → {run_dir}")

            # If JSON contains an error → log to fail
            if not result or "pyrolysis_related" not in result:
                fail_logger.info(f"{source_name_raw} | Missing JSON field")

        except Exception as e:
            fail_logger.info(f"{source_name_raw} | ERROR: {str(e)}")
            logging.error(f"Failed: {source_name_raw} | {e}")


    logging.info("All rows processed.")


if __name__ == "__main__":
    main()


