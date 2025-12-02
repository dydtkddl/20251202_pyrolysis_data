# -*- coding: utf-8 -*-
"""
CSV Batch Ollama Classifier
- CSV의 특정 텍스트 컬럼(QWEN_INPUT 등)을 읽어 1 row씩 모델 호출
- prompt.txt의 <<<ABSTRACT>>> 부분에 각 row의 텍스트를 삽입
- 각 row마다 개별 run 폴더 생성 후 result.json, prompt_used.txt, input.txt 저장
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

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


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
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CSV batch classification using Ollama")

    parser.add_argument("--csv", required=True, help="Input CSV file")
    parser.add_argument("--text_col", default="QWEN_INPUT", help="Column name containing the text")
    parser.add_argument("--prompt", required=True, help="Prompt template file (with <<<ABSTRACT>>>)")
    parser.add_argument("--model", default="qwen3:30b-a3b-instruct-2507-q4_K_M", help="Ollama model name")
    parser.add_argument("--outdir", default="results_csv", help="Root output directory")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N rows for test")

    args = parser.parse_args()

    # -----------------------------------
    # Load CSV
    # -----------------------------------
    df = pd.read_csv(args.csv)
    if args.text_col not in df.columns:
        logging.error(f"Column '{args.text_col}' not found in CSV!")
        return

    # limit test
    if args.limit:
        df = df.head(args.limit)

    os.makedirs(args.outdir, exist_ok=True)

    # -----------------------------------
    # Load prompt template
    # -----------------------------------
    logging.info(f"Loading prompt template: {args.prompt}")
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    if "<<<ABSTRACT>>>" not in prompt_template:
        logging.warning("Prompt missing <<<ABSTRACT>>> placeholder. Adding at bottom.")
        prompt_template += "\n<<<ABSTRACT>>>"

    # -----------------------------------
    # Processing rows with tqdm
    # -----------------------------------
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing rows"):
        abstract_text = str(row[args.text_col]).strip()

        # Substitute prompt
        full_prompt = prompt_template.replace("<<<ABSTRACT>>>", abstract_text)

        # Create per-run folder
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(args.outdir, f"run_{ts}_{idx}")
        os.makedirs(run_dir, exist_ok=True)

        # Run model
        result = run_ollama(args.model, full_prompt)

        # Save result.json
        with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
            f.write(result)

        # Save prompt used
        with open(os.path.join(run_dir, "prompt_used.txt"), "w", encoding="utf-8") as f:
            f.write(full_prompt)

        # Save input text
        with open(os.path.join(run_dir, "input.txt"), "w", encoding="utf-8") as f:
            f.write(abstract_text)

        # Save prompt template
        shutil.copy(args.prompt, os.path.join(run_dir, "prompt_template.txt"))

        logging.info(f"[Row {idx}] Saved → {run_dir}")

    logging.info("All rows processed successfully.")


if __name__ == "__main__":
    main()


