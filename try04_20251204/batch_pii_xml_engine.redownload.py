#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import os
from tqdm import tqdm
import logging

LOG_FILE = "download_xml.log"
SAVE_DIR = "./xmls"
API_KEY = "3c271c9aec7337d30416c170817761ad"

os.makedirs(SAVE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -------------------------------------------------------
# 1. 로그에서 실패한 URL 추출
# -------------------------------------------------------
def extract_failed_urls(log_file):
    failed = []
    pat = re.compile(r"Requesting:\s+(https?://[^\s]+)")

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    last_url = None

    for line in lines:
        if "Requesting:" in line:
            # remember last request
            m = pat.search(line)
            if m:
                last_url = m.group(1)

        if "Failed to fetch" in line and last_url:
            failed.append(last_url)
            last_url = None

    return list(set(failed))  # unique


# -------------------------------------------------------
# 2. 다운로드 후 파일 저장
# -------------------------------------------------------
def download_and_save(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            logging.error(f"Status {r.status_code}: {url}")
            return False

        # PII 파일명 추출
        m = re.search(r"/pii/([^?]+)", url)
        if not m:
            logging.error(f"Cannot extract PII: {url}")
            return False

        pii = m.group(1)
        out = os.path.join(SAVE_DIR, f"{pii}__FULL.xml")

        with open(out, "w", encoding="utf-8") as f:
            f.write(r.text)

        logging.info(f"Saved XML → {out}")
        return True

    except Exception as e:
        logging.error(f"download failed: {url} | {e}")
        return False


# -------------------------------------------------------
# 3. Main
# -------------------------------------------------------
def main():
    failed_urls = extract_failed_urls(LOG_FILE)

    logging.info(f"Found failed URLs: {len(failed_urls)}")

    for url in tqdm(failed_urls, desc="Retry download"):
        # API key replacement if needed
        if "apiKey=" not in url:
            if "?" in url:
                url = url + f"&apiKey={APIKEY}&view=FULL"
            else:
                url = url + f"?apiKey={APIKEY}&view=FULL"

        download_and_save(url)


if __name__ == "__main__":
    main()
