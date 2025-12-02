# -*- coding: utf-8 -*-
"""
NUEXTRACT Step1 Engine
- Uses the nuextract model for high-accuracy scientific experiment extraction.
- Input: PAPER_TEXT + prompt1
- Output: step1_output.json (strict JSON)
"""

import subprocess
import json
import argparse
from pathlib import Path


MODEL = "nuextract:latest"   # Ollama model for information extraction


def run_ollama(prompt_text: str):
    """Run the nuextract model and return output string."""
    cmd = ["ollama", "run", MODEL]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    out, err = process.communicate(input=prompt_text)

    if err and err.strip():
        print("[Error from model]", err)

    return out


def load_text(path: str) -> str:
    """Load text file content."""
    return Path(path).read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="NUEXTRACT Step1 Engine")
    parser.add_argument("--input", required=True, help="Path to full paper markdown/text")
    parser.add_argument("--prompt1", required=True, help="Path to prompt1.txt")
    args = parser.parse_args()

    # Load files
    paper_text = load_text(args.input)
    prompt1_template = load_text(args.prompt1)

    # Insert text into prompt
    step1_prompt = prompt1_template.replace("{{PAPER_TEXT}}", paper_text)

    print("\n==============================")
    print(" [STEP 1] NUEXTRACT — Experiment Extraction")
    print("==============================\n")

    # Run model
    step1_output = run_ollama(step1_prompt)

    print(step1_output)

    # Save raw model output
    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    print("\n>>> Validating JSON...\n")

    try:
        parsed = json.loads(step1_output)
        print("✔ JSON structure is valid.")
    except json.JSONDecodeError as e:
        print("❌ ERROR: Output is not valid JSON.")
        print("   Message:", e)
        print("   Check step1_output.json manually.")
        return

    print("\nDone. step1_output.json saved.\n")


if __name__ == "__main__":
    main()

