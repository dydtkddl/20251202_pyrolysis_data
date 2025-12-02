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

    print("\n[STEP 1] Extracting experiment groups...\n")
    step1_prompt = prompt1 + "\n" + paper_text
    step1_output = run_ollama(step1_prompt)
    print(step1_output)

    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    # Parse JSON
    try:
        extracted_json = json.loads(step1_output)
    except json.JSONDecodeError:
        print("!! JSON parse error in step1_output.json !!")
        return

    # Step 2 (self-check)
    prompt2_template = load_text(args.step2)
    step2_prompt = (
        prompt2_template
        .replace("{{EXTRACTION_JSON}}", json.dumps(extracted_json, indent=2))
        .replace("{{PAPER_TEXT}}", paper_text)
    )

    print("\n[STEP 2] Running self-check verification...\n")
    step2_output = run_ollama(step2_prompt)
    print(step2_output)

    Path("step2_output.json").write_text(step2_output, encoding="utf-8")

    print("\nDone. Results saved in step1_output.json and step2_output.json.\n")


if __name__ == "__main__":
    main()
