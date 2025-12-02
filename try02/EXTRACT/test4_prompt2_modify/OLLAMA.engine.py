import subprocess
import json
import argparse
from pathlib import Path

MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"


def run_ollama(prompt_text: str):
    """Run Ollama model and return output."""

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
        print(f"[Error] {err.strip()}")

    return out


def load_text(path):
    return Path(path).read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Ollama experiment extraction pipeline")
    parser.add_argument("--input", required=True, help="Path to cleaned experiment text")
    parser.add_argument("--step1", required=True, help="Path to prompt1.txt")
    parser.add_argument("--step2", required=True, help="Path to prompt2.txt")

    args = parser.parse_args()

    # Load files
    paper_text = load_text(args.input)
    prompt1 = load_text(args.step1)
    prompt2_template = load_text(args.step2)

    # ---------------------------------------------------
    # STEP 1
    # ---------------------------------------------------
    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    step1_prompt = (
        f"{prompt1}\n\n"
        "==== PAPER_TEXT ====\n"
        f"{paper_text}\n"
    )

    step1_output = run_ollama(step1_prompt)

    print(step1_output)

    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    # JSON parse validation
    try:
        extracted_json = json.loads(step1_output)
    except json.JSONDecodeError:
        print("\n❌ ERROR: Step1 output is NOT valid JSON.")
        print("   Review step1_output.json manually.\n")
        return

    # ---------------------------------------------------
    # STEP 2 (Self-check)
    # ---------------------------------------------------
    print("\n==============================")
    print(" [STEP 2] Self-check verification")
    print("==============================\n")

    replacement_json = json.dumps(extracted_json, indent=2)

    step2_prompt = (
        prompt2_template
            .replace("{{EXTRACTION_JSON}}", replacement_json)
            .replace("{{PAPER_TEXT}}", paper_text)
            .strip() + "\n\n"
    )

    step2_output = run_ollama(step2_prompt)

    print(step2_output)

    Path("step2_output.json").write_text(step2_output, encoding="utf-8")

    # Final JSON validation
    try:
        json.loads(step2_output)
    except json.JSONDecodeError:
        print("\n❌ ERROR: Step2 output is NOT valid JSON.")
        print("   Review step2_output.json manually.\n")
        return

    print("\n🎉 DONE. Results saved as step1_output.json and step2_output.json.\n")


if __name__ == "__main__":
    main()


