# -*- coding: utf-8 -*-
"""
Split 'marker_commands.2.sh' into 3 equal parts.
Creates:
 - marker_commands.2.part1.sh
 - marker_commands.2.part2.sh
 - marker_commands.2.part3.sh
"""

import os
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("split_marker_commands.log"),
        logging.StreamHandler()
    ]
)


def split_into_three(file_path):
    if not os.path.isfile(file_path):
        logging.error(f"File not found: {file_path}")
        return

    logging.info(f"Loading file: {file_path}")

    # Read lines
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    logging.info(f"Total lines: {total}")

    # Determine chunk sizes
    size = total // 3
    remain = total % 3

    # Compute exact split indices
    part_sizes = [size, size, size]
    for i in range(remain):
        part_sizes[i] += 1

    logging.info(f"Part sizes: {part_sizes}")

    parts = []
    start = 0
    for p_size in part_sizes:
        end = start + p_size
        parts.append(lines[start:end])
        start = end

    # Save parts
    base = os.path.splitext(file_path)[0]

    for idx, content in enumerate(tqdm(parts, desc="Writing parts")):
        out_name = f"{base}.part{idx+1}.sh"
        with open(out_name, "w", encoding="utf-8") as f:
            f.writelines(content)
        logging.info(f"Created: {out_name} ({len(content)} lines)")


if __name__ == "__main__":
    split_into_three("marker_commands.2.sh")
    logging.info("Done.")

