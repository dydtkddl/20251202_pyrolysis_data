import subprocess
import json
import argparse
from pathlib import Path
import re

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

    if err and err.strip():
        print("[Error]", err)

    return out


def clean_json_output(raw_text):
    """
    Extract first valid JSON block from model output.
    Removes extra text before/after JSON.
    """
    # Find first '{' and last '}'
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        return match.group(0)
    return raw_text  # fallback


def load_text(path):
    return Path(path).read_text(encoding="utf-8")


def save_json(path, content):
    Path(path).write_text(content, encoding="utf-8")


def try_parse_json(text, step_name):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"\n❌ JSON ERROR in {step_name}. Output is not valid JSON.")
        print("--------------------------------------------------------")
        print(text)
        print("--------------------------------------------------------")
        return None


def main():
    parser = argparse.ArgumentParser(description="Ollama full 4-step extraction pipeline")
    parser.add_argument("--input", required=True, help="Path to Experiment_Results.md")
    parser.add_argument("--step1", required=True)
    parser.add_argument("--step2", required=True)
    parser.add_argument("--step3", required=True)
    parser.add_argument("--step4", required=True)
    args = parser.parse_args()

    paper_text = load_text(args.input)

    # -----------------------------
    # STEP 1
    # -----------------------------
    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    prompt1 = load_text(args.step1)
    step1_raw = run_ollama(prompt1 + "\n" + paper_text)
    print(step1_raw)

    step1_clean = clean_json_output(step1_raw)
    save_json("step1_output.json", step1_clean)

    step1_json = try_parse_json(step1_clean, "STEP1")
    if step1_json is None:
        return

    # -----------------------------
    # STEP 2
    # -----------------------------
    print("\n==============================")
    print(" [STEP 2] Verification (Self-check)")
    print("==============================\n")

    prompt2 = load_text(args.step2)
    step2_prompt = (
        prompt2.replace("{{PAPER_TEXT}}", paper_text)
              .replace("{{EXTRACTION_JSON}}", json.dumps(step1_json, indent=2))
    )

    step2_raw = run_ollama(step2_prompt)
    print(step2_raw)

    step2_clean = clean_json_output(step2_raw)
    save_json("step2_output.json", step2_clean)

    step2_json = try_parse_json(step2_clean, "STEP2")
    if step2_json is None:
        return

    # -----------------------------
    # STEP 3
    # -----------------------------
    print("\n==============================")
    print(" [STEP 3] Extract variables & constants")
    print("==============================\n")

    prompt3 = load_text(args.step3)
    step3_prompt = (
        prompt3.replace("{{PAPER_TEXT}}", paper_text)
               .replace("{{EXTRACTION_JSON}}", json.dumps(step2_json, indent=2))
    )

    step3_raw = run_ollama(step3_prompt)
    print(step3_raw)

    step3_clean = clean_json_output(step3_raw)
    save_json("step3_output.json", step3_clean)

    step3_json = try_parse_json(step3_clean, "STEP3")
    if step3_json is None:
        return

    # -----------------------------
    # STEP 4
    # -----------------------------
    print("\n==============================")
    print(" [STEP 4] Verify Step3 (Self-check)")
    print("==============================\n")

    prompt4 = load_text(args.step4)
    step4_prompt = (
        prompt4.replace("{{PAPER_TEXT}}", paper_text)
               .replace("{{STEP3_JSON}}", json.dumps(step3_json, indent=2))
    )

    step4_raw = run_ollama(step4_prompt)
    print(step4_raw)

    step4_clean = clean_json_output(step4_raw)
    save_json("step4_output.json", step4_clean)

    step4_json = try_parse_json(step4_clean, "STEP4")
    if step4_json is None:
        return

    print("\n==============================")
    print("  All steps completed!")
    print("==============================\n")


if __name__ == "__main__":
    main()

