# -*- coding: utf-8 -*-
"""
Plastic Pyrolysis Classifier (prompt.txt + abs.txt → per-run folder)
- Saves: result.json + prompt_template.txt + prompt_used.txt + abstract.txt
- Logging + tqdm included
"""

import argparse
import logging
import subprocess
from datetime import datetime
from tqdm import tqdm
import os
import sys
import shutil

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
    logging.info("Running Ollama model...")

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
    parser = argparse.ArgumentParser(description="Ollama classifier with separated prompt/abstract + per-run dir")

    parser.add_argument("--prompt", required=True, help="Path to prompt.txt")
    parser.add_argument("--abs", required=True, help="Path to abstract abs.txt")
    parser.add_argument("--model", default="qwen3:30b-a3b-instruct-2507-q4_K_M", help="Ollama model name")
    parser.add_argument("--outdir", default="results", help="Root output directory")

    args = parser.parse_args()

    # Make root output directory
    os.makedirs(args.outdir, exist_ok=True)

    # Timestamp per-run folder
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(args.outdir, f"run_{ts}")
    os.makedirs(run_dir, exist_ok=True)

    # Load prompt template
    logging.info(f"Loading prompt template: {args.prompt}")
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Load abstract
    logging.info(f"Loading abstract: {args.abs}")
    with open(args.abs, "r", encoding="utf-8") as f:
        abstract = f.read().strip()

    # Ensure placeholder exists
    if "<<<ABSTRACT>>>" not in prompt_template:
        logging.warning("Prompt missing placeholder <<<ABSTRACT>>> — adding automatically.")
        prompt_template += "\n<<<\n<<<ABSTRACT>>>\n>>>"

    # Replace placeholder
    full_prompt = prompt_template.replace("<<<ABSTRACT>>>", abstract)

    # Run model with tqdm
    for _ in tqdm(range(1), desc="Classifying"):
        result = run_ollama(args.model, full_prompt)

    # Save result JSON
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(result)
    logging.info(f"Saved result → {result_path}")

    # Save used prompt (after replacement)
    prompt_used_path = os.path.join(run_dir, "prompt_used.txt")
    with open(prompt_used_path, "w", encoding="utf-8") as f:
        f.write(full_prompt)
    logging.info(f"Saved used prompt → {prompt_used_path}")

    # Save template copy
    prompt_template_path = os.path.join(run_dir, "prompt_template.txt")
    shutil.copy(args.prompt, prompt_template_path)
    logging.info(f"Copied prompt template → {prompt_template_path}")

    # Save abstract copy
    abs_copy_path = os.path.join(run_dir, "abstract.txt")
    shutil.copy(args.abs, abs_copy_path)
    logging.info(f"Copied abstract → {abs_copy_path}")

    logging.info(f"All artifacts saved in folder: {run_dir}")


if __name__ == "__main__":
    main()
