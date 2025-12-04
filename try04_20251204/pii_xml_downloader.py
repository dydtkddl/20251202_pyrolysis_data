# -*- coding: utf-8 -*-
"""
Stage 1: Elsevier PII XML Downloader
- PII & view만 argparse로 받고
- XML을 xmls/<pii>__<view>.xml 로 저장
"""

import argparse
import requests
import logging
import os

API_KEY = "3c271c9aec7337d30416c170817761ad"
BASE = "https://api.elsevier.com/content/article/pii"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("download_xml.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)

def save_xml(content, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    logging.info(f"Saved XML → {path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pii", type=str, required=True)
    parser.add_argument("--view", type=str, default="META_ABS")
    args = parser.parse_args()

    pii = args.pii.strip()
    view = args.view.strip()

    url = f"{BASE}/{pii}?apiKey={API_KEY}&view={view}"
    logging.info(f"Requesting: {url}")

    try:
        r = requests.get(url, timeout=10)
        content = r.content  # RAW XML
    except Exception as e:
        logging.error(f"Failed to fetch: {e}")
        return

    filename = f"{pii}__{view}.xml"
    save_xml(content, f"xmls/{filename}")

if __name__ == "__main__":
    main()
