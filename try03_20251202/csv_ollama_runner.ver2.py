#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSV Batch Ollama Classifier
- CSV의 텍스트 컬럼(또는 title/abstract 컬럼)을 읽어 1 row씩 모델 호출
- prompt.txt의 <<<ABSTRACT>>> 부분에 입력 텍스트를 삽입
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
        logging.FileHandler("logs/all.log", mode="w", encoding="utf-8"),
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
def run_ollama(model: str, full_prompt: str) -> str:
    cmd = [
        "ollama",
        "run",
        model,
        "--format",
        "json",
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
        err_str = err.strip()
        if err_str:
            logging.warning(f"Ollama STDERR: {err_str}")

    return out.strip() if out else ""


# ------------------------------------------------------------
# Safe folder name
# ------------------------------------------------------------
def safe_folder_name(name: str) -> str:
    name = str(name)
    name = name.strip()
    # 위험 문자는 전부 _ 로 치환
    name = re.sub(r"[^\w\-.]", "_", name)
    return name


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CSV batch classification using Ollama")

    parser.add_argument("--csv", required=True, help="Input CSV file")
    parser.add_argument(
        "--text_col",
        default="QWEN_INPUT",
        help="Column containing full text (fallback if title/abstract not provided)",
    )
    parser.add_argument(
        "--title_col",
        default=None,
        help="Column containing paper title (optional, used with --abstract_col)",
    )
    parser.add_argument(
        "--abstract_col",
        default=None,
        help="Column containing paper abstract (optional, used with --title_col)",
    )
    parser.add_argument(
        "--sf_col",
        default="source_file",
        help="Column for folder naming (e.g., source_file)",
    )
    parser.add_argument("--prompt", required=True, help="Prompt template file")
    parser.add_argument(
        "--model",
        default="qwen3:30b-a3b-instruct-2507-q4_K_M",
        help="Ollama model name",
    )
    parser.add_argument(
        "--outdir",
        default="results_csv",
        help="Root output directory to store per-row results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N rows for testing (optional)",
    )

    args = parser.parse_args()

    # Load CSV
    logging.info(f"Loading CSV: {args.csv}")
    df = pd.read_csv(args.csv)

    # 기본 컬럼 체크
    if args.sf_col not in df.columns:
        logging.error(f"Column '{args.sf_col}' not found in CSV!")
        return

    # title/abstract 사용 여부 결정
    use_title_abstract = False
    if args.title_col and args.abstract_col:
        if args.title_col not in df.columns:
            logging.error(f"Column '{args.title_col}' not found in CSV!")
            return
        if args.abstract_col not in df.columns:
            logging.error(f"Column '{args.abstract_col}' not found in CSV!")
            return
        use_title_abstract = True
        logging.info(
            f"Using title/abstract columns: title_col='{args.title_col}', abstract_col='{args.abstract_col}'"
        )
    else:
        # fallback: text_col 사용
        if args.text_col not in df.columns:
            logging.error(
                f"Column '{args.text_col}' not found in CSV and no title/abstract columns provided!"
            )
            return
        logging.info(f"Using text column: text_col='{args.text_col}'")

    if args.limit:
        df = df.head(args.limit)
        logging.info(f"Row limit set: {args.limit}, processing first {len(df)} rows")

    os.makedirs(args.outdir, exist_ok=True)

    # Load prompt
    logging.info(f"Loading prompt: {args.prompt}")
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # placeholder 확인 및 추가
    if "<<<ABSTRACT>>>" not in prompt_template:
        logging.warning(
            "Prompt missing <<<ABSTRACT>>> placeholder. Appending placeholder at the bottom."
        )
        prompt_template = prompt_template.rstrip() + "\n\n<<<ABSTRACT>>>"

    # Process rows
    for idx, row in tqdm(
        df.iterrows(), total=len(df), desc="Processing rows", unit="row"
    ):
        # 입력 텍스트 구성
        if use_title_abstract:
            title = str(row[args.title_col]).strip()
            abstract = str(row[args.abstract_col]).strip()
            abstract_text = f"Title: {title}\nAbstract: {abstract}"
        else:
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
            result_path = os.path.join(run_dir, "result.json")
            with open(result_path, "w", encoding="utf-8") as f:
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

            # JSON 구조 sanity check (약식)
            if not result or "pyrolysis_related" not in result:
                fail_logger.info(f"{source_name_raw} | Missing 'pyrolysis_related' in JSON")

        except Exception as e:
            fail_logger.info(f"{source_name_raw} | ERROR: {str(e)}")
            logging.error(f"Failed: {source_name_raw} | {e}")

    logging.info("All rows processed.")


if __name__ == "__main__":
    main()

