# -*- coding: utf-8 -*-
"""
QWEN2.5-14B Step1 Extraction Engine
- Uses Qwen2.5-14b-instruct via Ollama
- Enforces strict JSON-only output
- Auto-recovers malformed JSON
"""

import subprocess
import json
import argparse
from pathlib import Path
import re

MODEL = "qwen2.5:14b-instruct"


def run_ollama(prompt_text: str):
    """Run the Qwen model through Ollama and return raw text output."""
    cmd = ["ollama", "run", MODEL]
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )

    out, err = process.communicate(input=prompt_text)

    if err and err.strip():
        print("[Model STDERR]", err)

    return out


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def extract_json(raw: str):
    """
    Attempt to isolate and repair JSON from raw output.
    """
    # 1) Remove code fences if model added them
    raw = raw.strip()
    raw = raw.replace("```json", "").replace("```", "")

    # 2) Attempt direct parsing
    try:
        return json.loads(raw)
    except:
        pass

    # 3) Try to extract JSON substring using regex
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except:
            pass

    return None  # Failed


def main():
    parser = argparse.ArgumentParser(description="QWEN2.5 Step1 Engine")
    parser.add_argument("--input", required=True, help="Fulltext markdown or txt")
    parser.add_argument("--prompt1", required=True, help="Prompt1 template")
    args = parser.parse_args()

    # Load
    paper_text = load_text(args.input)
    prompt1 = load_text(args.prompt1)

    # Insert full text
    prompt = prompt1.replace("{{PAPER_TEXT}}", paper_text)

    print("\n=============================================")
    print("   [STEP 1] QWEN2.5–14B STRICT EXTRACTION")
    print("=============================================\n")

    # Run model
    raw_output = run_ollama(prompt)

    Path("step1_output_raw.txt").write_text(raw_output, encoding="utf-8")
    print("--- RAW MODEL OUTPUT SAVED TO step1_output_raw.txt ---\n")

    # Try repair
    print(">>> Validating and repairing JSON...\n")
    parsed = extract_json(raw_output)

    if parsed is None:
        print("❌ JSON parsing failed!")
        print("   Check step1_output_raw.txt manually.")
        return

    # Save final
    Path("step1_output.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("✔ JSON successfully extracted and saved to step1_output.json")


if __name__ == "__main__":
    main()

