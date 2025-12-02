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


def save_json(obj, path):
    Path(path).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def try_json_load(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Ollama experiment extraction pipeline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--step1", required=True)
    parser.add_argument("--step2", required=True)
    parser.add_argument("--step3", required=True)
    parser.add_argument("--step4", required=True)
    args = parser.parse_args()

    # Load base texts
    paper_text = load_text(args.input)
    prompt1 = load_text(args.step1)
    prompt2 = load_text(args.step2)
    prompt3 = load_text(args.step3)
    prompt4 = load_text(args.step4)

    # ======================================================
    # STEP 1 — Extract groups
    # ======================================================
    print("\n==============================")
    print(" [STEP 1] Extract experiment groups")
    print("==============================\n")

    step1_prompt = prompt1 + "\n" + paper_text
    step1_output = run_ollama(step1_prompt)
    print(step1_output)

    Path("step1_output.json").write_text(step1_output, encoding="utf-8")

    groups_json = try_json_load(step1_output)
    if groups_json is None:
        print("❌ STEP1 FAIL: Output is not valid JSON.")
        return

    # ======================================================
    # STEP 2 — Verify RAW groups
    # ======================================================
    print("\n==============================")
    print(" [STEP 2] Verify RAW extracted groups")
    print("==============================\n")

    step2_prompt = (
        prompt2
            .replace("{{PAPER_TEXT}}", paper_text)
            .replace("{{EXTRACTION_JSON}}", json.dumps(groups_json, indent=2))
    )

    step2_output = run_ollama(step2_prompt)
    print(step2_output)

    Path("step2_output.json").write_text(step2_output, encoding="utf-8")

    verified_json = try_json_load(step2_output)
    if verified_json is None:
        print("❌ STEP2 FAIL: Output invalid JSON.")
        return

    verified_groups = verified_json["verified_experiment_groups"]

    # ======================================================
    # STEP 3 — Per-group variable/constants extraction
    # ======================================================
    print("\n==============================")
    print(" [STEP 3] Extract variable/constants per group")
    print("==============================\n")

    step3_results = []

    for idx, group in enumerate(verified_groups):
        print(f"\n--- STEP3 GROUP {idx+1}/{len(verified_groups)} ---\n")

        step3_prompt = (
            prompt3
                .replace("{{PAPER_TEXT}}", paper_text)
                .replace("{{GROUP_JSON}}", json.dumps(group, indent=2))
        )

        step3_out = run_ollama(step3_prompt)
        print(step3_out)

        Path(f"step3_group_{idx+1}.json").write_text(step3_out, encoding="utf-8")

        parsed = try_json_load(step3_out)
        if parsed:
            step3_results.append(parsed)
        else:
            print(f"❌ STEP3 group {idx+1} invalid JSON, skipping…")

    # ======================================================
    # STEP 4 — Per-group verification
    # ======================================================
    print("\n==============================")
    print(" [STEP 4] Verify variable/constants per group")
    print("==============================\n")

    final_groups = []

    for idx, group3 in enumerate(step3_results):
        print(f"\n--- STEP4 GROUP {idx+1}/{len(step3_results)} ---\n")

        step4_prompt = (
            prompt4
                .replace("{{PAPER_TEXT}}", paper_text)
                .replace("{{GROUP_JSON}}", json.dumps(group3, indent=2))
        )

        step4_out = run_ollama(step4_prompt)
        print(step4_out)

        Path(f"step4_group_{idx+1}.json").write_text(step4_out, encoding="utf-8")

        parsed4 = try_json_load(step4_out)
        if parsed4:
            if parsed4.get("removed") is True:
                print(f"Group {idx+1} removed by verifier")
                continue
            final_groups.append(parsed4)
        else:
            print(f"❌ STEP4 group {idx+1} invalid JSON, skipping…")

    # ======================================================
    # FINAL MERGE
    # ======================================================
    print("\n==============================")
    print(" [FINAL] Save merged verified groups")
    print("==============================\n")

    final_output = {
        "final_verified_groups": final_groups,
        "num_groups": len(final_groups)
    }

    save_json(final_output, "final_verified_groups.json")

    print("\n🎉 DONE! Final output saved in final_verified_groups.json\n")


if __name__ == "__main__":
    main()

