# -*- coding: utf-8 -*-
"""
QWEN2.5 Step1 Extraction Engine
- Based on your NUEXTRACT engine structure
- Uses qwen2.5:14b-instruct
- Safe JSON validation + auto-repair
"""

import subprocess
import json
import argparse
from pathlib import Path
import re


MODEL = "qwen2.5:14b-instruct"


# ------------------------------------------------------
# Ollama run
# ------------------------------------------------------
def run_ollama(prompt_text: str):
    """Run the model via subprocess and return output string."""
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
        print("[Model Error]", err)

    return out


# ------------------------------------------------------
# JSON auto-repair
# ------------------------------------------------------
def try_parse_json(output: str):
    """Try multiple strategies to load JSON."""
    try:
        return json.loads(output)
    except Exception:
        pass

    # Remove Markdown fences
    cleaned = re.sub(r"```json|```", "", output).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Remove trailing characters
    cleaned = cleaned.replace("\n", " ")
    cleaned = cleaned.replace("\t", " ")

    # Attempt to cut after last closing brace
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        try:
            return json.loads(cleaned[:last_brace + 1])
        except Exception:
            pass

    raise ValueError("Failed to parse JSON after auto-repair.")


# ------------------------------------------------------
# File loader
# ------------------------------------------------------
def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ------------------------------------------------------
# Main
# ------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="QWEN2.5 Step1 Extraction Engine")
    parser.add_argument("--input", required=True, help="Path to full paper markdown/text")
    parser.add_argument("--prompt1", required=True, help="Path to prompt1 template")
    args = parser.parse_args()

    # Load source texts
    fulltext = load_text(args.input)
    prompt_template = load_text(args.prompt1)

    # Insert FULLTEXT into prompt
    final_prompt = prompt_template.replace("{{FULLTEXT}}", fulltext)

    print("\n=============================================")
    print("   [STEP 1] QWEN 2.5 – STRICT EXTRACTION")
    print("=============================================\n")

    # Run model
    raw_output = run_ollama(final_prompt)

    print("\n--- RAW MODEL OUTPUT ---\n")
    print(raw_output)

    # Save raw output
    Path("step1_output_raw.txt").write_text(raw_output, encoding="utf-8")

    print("\n>>> Validating and repairing JSON...\n")

    try:
        parsed = try_parse_json(raw_output)
    except Exception as e:
        print("❌ JSON parsing failed!")
        print("   Error:", e)
        print("   Check step1_output_raw.txt manually.")
        return

    # Save valid JSON
    Path("step1_output.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("✔ JSON successfully parsed and saved to step1_output.json\n")


if __name__ == "__main__":
    main()

