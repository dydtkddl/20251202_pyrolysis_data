# step1_engine.py
import subprocess
import json
import argparse
from pathlib import Path

MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"


def run_ollama(prompt_text: str):
    """Run Ollama model and return output string."""
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
        print("[Error]", err)

    return out


def load_text(path):
    return Path(path).read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Step1: Single-Experiment Extraction Engine")
    parser.add_argument("--input", required=True, help="Path to Experiment_Results.md")
    parser.add_argument("--step1_prompt", required=True, help="Path to prompt_step1.txt")
    args = parser.parse_args()

    # Load files
    paper_text = load_text(args.input)
    prompt_template = load_text(args.step1_prompt)

    # Build prompt
    step1_prompt = prompt_template.replace("<<<INSERT_FULL_TEXT_HERE>>>", paper_text)

    print("\n==============================")
    print(" [STEP 1] Extract SINGLE Experiment + Outcome Groups")
    print("==============================\n")

    step1_output = run_ollama(step1_prompt)
    print(step1_output)

    # Save raw output
    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    # Validate JSON
    try:
        parsed = json.loads(step1_output)
        print("\n✅ JSON validated successfully.")
    except json.JSONDecodeError:
        print("\n❌ ERROR: Step1 output is not valid JSON.")
        print("   → Check step1_output.json manually.")
        return

    print("\n🎉 Done. Output saved to step1_output.json.\n")


if __name__ == "__main__":
    main()

