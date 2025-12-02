# -*- coding: utf-8 -*-
"""
Add CUDA_VISIBLE_DEVICES=<N> to each command line
Example:
  CUDA_VISIBLE_DEVICES=0 marker_single "YES_ALL/..." ...
"""

import argparse
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("prepend_cuda_env.log"),
        logging.StreamHandler(),
    ],
)


def prepend_cuda(input_file, output_file, cuda_id):
    logging.info(f"Reading: {input_file}")
    logging.info(f"CUDA_VISIBLE_DEVICES={cuda_id}")

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in tqdm(lines, desc="Processing commands"):
        stripped = line.strip()
        if stripped == "":
            new_lines.append("\n")
            continue

        new_lines.append(f"CUDA_VISIBLE_DEVICES={cuda_id} {stripped}\n")

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logging.info(f"Saved updated script → {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Prepend CUDA_VISIBLE_DEVICES to each command line"
    )
    parser.add_argument("--cuda", type=int, required=True,
                        help="CUDA device index (e.g., 0 or 1)")
    parser.add_argument("--input", type=str, required=True,
                        help="original .sh file")
    parser.add_argument("--output", type=str, required=True,
                        help="new .sh file to write")

    args = parser.parse_args()
    prepend_cuda(args.input, args.output, args.cuda)


if __name__ == "__main__":
    main()

