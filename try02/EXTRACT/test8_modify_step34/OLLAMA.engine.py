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


def parse_json_safe(output_text, step_name):
    """Try to parse model output JSON safely."""
    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        print(f"\n❌ JSON ERROR in {step_name}. Output is not valid JSON.")
        print("--------------------------------------------------------")
        print(output_text)
        print("--------------------------------------------------------\n")
        return None


def main():
    parser = argparse.ArgumentParser(description="Ollama experiment extraction pipeline")
    parser.add_argument("--input", required=True, help="Experiment_Results.md")
    parser.add_argument("--step1", required=True)
    parser.add_argument("--step2", required=True)
    parser.add_argument("--step3", required=True)
    parser.add_argument("--step4", required=True)
    args = parser.parse_args()

    paper_text = load_text(args.input)

    #
    # STEP 1 — Extract experiment groups
    #
    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    prompt1 = load_text(args.step1)
    step1_prompt = prompt1 + "\n" + paper_text
    step1_output = run_ollama(step1_prompt)

    Path("step1_output.json").write_text(step1_output, encoding="utf-8")
    extracted_json = parse_json_safe(step1_output, "STEP1")
    if extracted_json is None:
        return

    #
    # STEP 2 — Verification (Self-check)
    #
    print("\n==============================")
    print(" [STEP 2] Verification (Self-check)")
    print("==============================\n")

    template2 = load_text(args.step2)
    step2_prompt = (
        template2.replace("{{PAPER_TEXT}}", paper_text)
                 .replace("{{EXTRACTION_JSON}}", json.dumps(extracted_json, indent=2))
    )
    step2_output = run_ollama(step2_prompt)

    Path("step2_output.json").write_text(step2_output, encoding="utf-8")
    verified_step2 = parse_json_safe(step2_output, "STEP2")
    if verified_step2 is None:
        return

    #
    # STEP 3 — Extract variable + constants (STRICT)
    #
    print("\n==============================")
    print(" [STEP 3] Extract variables & constants")
    print("==============================\n")

    template3 = load_text(args.step3)
    step3_prompt = (
        template3.replace("{{PAPER_TEXT}}", paper_text)
                 .replace("{{EXTRACTION_JSON}}", json.dumps(verified_step2, indent=2))
    )
    step3_output = run_ollama(step3_prompt)

    Path("step3_output.json").write_text(step3_output, encoding="utf-8")
    step3_json = parse_json_safe(step3_output, "STEP3")
    if step3_json is None:
        return

    #
    # STEP 4 — Strict verification of variable/constants
    #
    print("\n==============================")
    print(" [STEP 4] Verification of variable/constants")
    print("==============================\n")

    template4 = load_text(args.step4)
    step4_prompt = (
        template4.replace("{{PAPER_TEXT}}", paper_text)
                 .replace("{{EXTRACTION_JSON}}", json.dumps(step3_json, indent=2))
    )
    step4_output = run_ollama(step4_prompt)

    Path("step4_output.json").write_text(step4_output, encoding="utf-8")
    step4_json = parse_json_safe(step4_output, "STEP4")
    if step4_json is None:
        return

    print("\nDone. All steps completed successfully.\n")


if __name__ == "__main__":
    main()

