# -*- coding: utf-8 -*-
import requests
import logging
import time
import json
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

HEADERS = {
    "User-Agent": "CrossrefHarvester/1.0 (mailto:your_email@example.com)"
}

def fetch_crossref(doi, max_retries=3):
    url = f"https://api.crossref.org/works/{doi}"

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)

            # 정상 응답
            if r.status_code == 200:
                return r.json()

            # 너무 많이 요청한 경우 → backoff
            if r.status_code == 429:
                wait = 1.5 * attempt
                logging.warning(f"Rate limited (429) → waiting {wait}s...")
                time.sleep(wait)
                continue

            # 기타 오류
            logging.error(f"HTTP {r.status_code} for DOI {doi} (attempt {attempt})")

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed ({doi}) attempt {attempt}: {e}")

        time.sleep(1.0 * attempt)

    return None


def extract_title(message):
    if "title" in message:
        t = message["title"]
        if isinstance(t, list) and len(t) > 0:
            return t[0]
        if isinstance(t, str):
            return t
    return None


def save_metadata(doi, data):
    safe = doi.replace("/", "_")
    with open(f"meta_{safe}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    dois = [
"10.1016/j.jaap.2012.06.009"
    ]

    for doi in tqdm(dois, desc="Fetching"):
        data = fetch_crossref(doi)

        if data is None:
            logging.error(f"❌ Failed metadata: {doi}")
            continue

        msg = data.get("message", {})
        title = extract_title(msg)

        logging.info(f"Title: {title}")

        # 🔥 전체 메타데이터 저장
        save_metadata(doi, msg)
        logging.info(f"Saved metadata → meta_{doi.replace('/', '_')}.json")


