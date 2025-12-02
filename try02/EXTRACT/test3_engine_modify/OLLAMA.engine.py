# OLLAMA.engine.py
# -------------------------------------------------------
# Step1 : Extract experiment_groups
# Step2 : Self-check & verification
#
# Compatible with all Ollama versions (no --raw)
# -------------------------------------------------------

import subprocess
import json
import argparse
from pathlib import Path


MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"


# -------------------------------------------------------
# Run Ollama (standard mode)
# -------------------------------------------------------
def run_ollama(prompt_text: str):
    """Run Ollama and return model output."""

    cmd = ["ollama", "run", MODEL]   #  <-- --raw 제거됨

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    out, err = process.communicate(input=prompt_text)

    if err and err.strip():
        print(f"[Error] {err}")

    return out


# -------------------------------------------------------
# Load file content safely
# -------------------------------------------------------
def load_text(path):
    return Path(path).read_text(encoding="utf-8")


# -------------------------------------------------------
# Main execution pipeline
# -------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Ollama experiment extraction pipeline")
    parser.add_argument("--input", required=True, help="Path to Experiment_Results.md or parsed text file")
    parser.add_argument("--step1", required=True, help="Path to prompt1.txt")
    parser.add_argument("--step2", required=True, help="Path to prompt2.txt")

    args = parser.parse_args()

    # Load files
    paper_text = load_text(args.input)
    prompt1 = load_text(args.step1)
    prompt2_template = load_text(args.step2)

    # ---------------------------------------------------
    # STEP 1 : Extraction
    # ---------------------------------------------------
    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    step1_prompt = (
        f"{prompt1}\n\n"
        "====BEGIN_TEXT====\n"
        f"{paper_text}\n"
        "====END_TEXT====\n"
    )

    step1_output = run_ollama(step1_prompt)

    print(step1_output)

    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    # Parse extracted JSON
    try:
        extracted_json = json.loads(step1_output)
    except json.JSONDecodeError:
        print("\n❌ ERROR: Step1 output is not valid JSON.")
        print("   Check step1_output.json manually.\n")
        return

    # ---------------------------------------------------
    # STEP 2 : Verification
    # ---------------------------------------------------
    print("\n==============================")
    print(" [STEP 2] Self-check verification")
    print("==============================\n")

    step2_prompt = (
        f"{prompt2_template}\n\n"
        "====BEGIN_EXTRACTION_JSON====\n"
        f"{json.dumps(extracted_json, indent=2)}\n"
        "====END_EXTRACTION_JSON====\n\n"
        "====BEGIN_PAPER_TEXT====\n"
        f"{paper_text}\n"
        "====END_PAPER_TEXT====\n"
    )

    step2_output = run_ollama(step2_prompt)

    print(step2_output)

    Path("step2_output.json").write_text(step2_output, encoding="utf-8")

    print("\n🎉 Done. Results saved in step1_output.json and step2_output.json.\n")


if __name__ == "__main__":
    main()

