import subprocess
import json
import argparse
from pathlib import Path

MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"

def run_ollama(prompt_text: str):
    cmd = ["ollama", "run", MODEL]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = process.communicate(input=prompt_text)
    if err:
        print("[Error]", err)
    return out

def load_text(path):
    return Path(path).read_text(encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Ollama experiment extraction pipeline")
    parser.add_argument("--input", required=True, help="Path to Experiment_Results.md")
    parser.add_argument("--step1", required=True, help="Path to prompt1.txt")
    parser.add_argument("--step2", required=True, help="Path to prompt2.txt")
    args = parser.parse_args()

    paper_text = load_text(args.input)
    prompt1 = load_text(args.step1)

    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    step1_prompt = prompt1 + "\n\n" + paper_text
    step1_output = run_ollama(step1_prompt)
    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    try:
        extracted_json = json.loads(step1_output)
    except json.JSONDecodeError:
        print("❌ ERROR: Step1 output is not valid JSON.")
        print("   Check step1_output.json manually.")
        return

    prompt2 = load_text(args.step2)
    step2_prompt = prompt2.replace("{{EXTRACTION_JSON}}", json.dumps(extracted_json, indent=2))

    print("\n==============================")
    print(" [STEP 2] Verification")
    print("==============================\n")

    step2_output = run_ollama(step2_prompt)
    Path("step2_output.json").write_text(step2_output, encoding="utf-8")

    print("\nDone. Saved: step1_output.json, step2_output.json\n")

if __name__ == "__main__":
    main()

