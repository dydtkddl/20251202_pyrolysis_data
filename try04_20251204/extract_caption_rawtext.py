#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract sentences containing 'Fig.' / 'Figure' / 'Table' from Elsevier XMLs.

- For each XML in a directory:
  1) Extract text (prefer <rawtext>, else <body> all text)
  2) Split into sentences (nltk if available, else regex)
  3) Filter sentences containing figure/table keywords
  4) Write them to a .txt file (one sentence per line) under out_dir

Usage:
    python extract_fig_table_sentences.py --xml_dir ./xmls --out_dir fig_table_sentences
"""

import os
import re
import argparse
import logging

from typing import List, Optional

from lxml import etree
from tqdm import tqdm

import os
os.environ["NLTK_DATA"] = "/home/yongsang/nltk_data"
# -------------------------------------------------------
# Try nltk sentence tokenizer (preferred), else fallback
# -------------------------------------------------------
try:
    import nltk
    from nltk.tokenize import sent_tokenize
    _HAS_NLTK = True
except Exception:
    _HAS_NLTK = False

import textwrap


# =======================================================
# CONFIG & LOGGING
# =======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Figure/Table keyword 패턴
FIG_TABLE_PATTERN = re.compile(
    r"\b(Fig\.?|Figure|Figs\.?|Table|Tables?)\b",
    re.IGNORECASE,
)


# =======================================================
# Sentence Splitter
# =======================================================
_SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

def split_sentences(text: str) -> List[str]:
    """
    문장 단위로 텍스트를 나눔.
    - nltk가 설치되어 있으면 sent_tokenize 사용
    - 아니면 단순 regex로 fallback
    """
    text = text.strip()
    if not text:
        return []

    if _HAS_NLTK:
        try:
            # punkt 모델이 필요. 처음 한 번은 아래처럼 다운로드 해야 함.
            #   >>> import nltk
            #   >>> nltk.download("punkt")
            sents = sent_tokenize(text)
        except LookupError:
            # punkt 없으면 fallback
            logger.warning("nltk punkt not found; fallback to regex splitter.")
            sents = _SENT_SPLIT_RE.split(text)
    else:
        sents = _SENT_SPLIT_RE.split(text)

    sents = [s.strip() for s in sents if s and len(s.strip()) > 0]
    return sents


# =======================================================
# XML → 텍스트 추출
# =======================================================
def extract_text_from_xml(path: str) -> Optional[str]:
    """
    XML 파일에서 우선 <rawtext> 텍스트만 추출.
    - 없으면 <body> 안의 모든 텍스트를 join.
    - 그래도 없으면 None 반환.
    """
    try:
        tree = etree.parse(path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"XML parse error: {path} | {e}")
        return None

    # 1) rawtext 우선
    raw_nodes = root.xpath("//*[local-name()='rawtext']//text()")
    if raw_nodes:
        text = " ".join(raw_nodes)
        text = " ".join(text.split())
        return text

    # 2) fallback: body 전체 텍스트
    body_nodes = root.xpath("//*[local-name()='body']//text()")
    if body_nodes:
        text = " ".join(body_nodes)
        text = " ".join(text.split())
        return text

    # 3) 더이상 없으면 그냥 전체 문서 텍스트
    all_nodes = root.xpath("//text()")
    if all_nodes:
        text = " ".join(all_nodes)
        text = " ".join(text.split())
        return text

    return None


# =======================================================
# Filter sentences with Fig/Table
# =======================================================
def filter_fig_table_sentences(sentences: List[str]) -> List[str]:
    """
    문장 리스트에서 Fig./Figure/Table 키워드가 포함된 문장만 필터링.
    """
    hits = []
    for s in sentences:
        if FIG_TABLE_PATTERN.search(s):
            hits.append(s)
    return hits


# =======================================================
# Process single XML
# =======================================================
def process_single_xml(xml_path: str, out_dir: str) -> int:
    """
    단일 XML 파일 처리:
      - 텍스트 추출
      - 문장 분할
      - Fig/Table 포함 문장 필터
      - 결과를 out_dir/원파일이름.txt 로 저장
    반환값: 추출된 문장 개수
    """
    fname = os.path.basename(xml_path)
    base, _ = os.path.splitext(fname)
    out_path = os.path.join(out_dir, base + ".txt")

    text = extract_text_from_xml(xml_path)
    if not text:
        logger.info(f"[SKIP] No text extracted: {fname}")
        return 0

    sentences = split_sentences(text)
    if not sentences:
        logger.info(f"[SKIP] No sentences parsed: {fname}")
        return 0

    hit_sents = filter_fig_table_sentences(sentences)
    if not hit_sents:
        # 문장이 하나도 없으면 파일은 안쓰고 0 반환
        logger.info(f"[NO_FIG_TABLE] {fname}: 0 sentences")
        return 0

    # 한 줄에 한 문장씩 저장
    with open(out_path, "w", encoding="utf-8") as f:
        for s in hit_sents:
            # 너무 긴 문장은 원하는 대로 줄바꿈 해서 보기 좋게 할 수도 있음
            # 여기서는 그냥 한 줄에 통째로 기록
            f.write(s.strip() + "\n")

    logger.info(f"[OK] {fname}: {len(hit_sents)} sentences → {out_path}")
    return len(hit_sents)


# =======================================================
# Main batch
# =======================================================
def run(xml_dir: str, out_dir: str):
    if not os.path.isdir(xml_dir):
        logger.error(f"XML dir not found: {xml_dir}")
        raise SystemExit(1)

    os.makedirs(out_dir, exist_ok=True)

    xml_files = [
        os.path.join(xml_dir, f)
        for f in os.listdir(xml_dir)
        if f.lower().endswith(".xml")
    ]
    xml_files.sort()

    logger.info(f"XML files found: {len(xml_files)}")
    total_hits = 0
    files_with_hits = 0

    for path in tqdm(xml_files, desc="Processing XML"):
        n = process_single_xml(path, out_dir)
        total_hits += n
        if n > 0:
            files_with_hits += 1

    logger.info("=== Summary ===")
    logger.info(f"Total XML files: {len(xml_files)}")
    logger.info(f"Files with Fig/Table sentences: {files_with_hits}")
    logger.info(f"Total sentences extracted: {total_hits}")


# =======================================================
# CLI
# =======================================================
def parse_args():
    ap = argparse.ArgumentParser(
        description="Extract sentences containing Fig./Table from Elsevier XMLs."
    )
    ap.add_argument(
        "--xml_dir",
        type=str,
        default="./xmls",
        help="XML directory (default: ./xmls)"
    )
    ap.add_argument(
        "--out_dir",
        type=str,
        default="./fig_table_sentences",
        help="Output directory for .txt files (default: ./fig_table_sentences)"
    )
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info(f"XML dir : {args.xml_dir}")
    logger.info(f"Out dir : {args.out_dir}")

    if _HAS_NLTK:
        logger.info("Using nltk.sent_tokenize for sentence splitting.")
    else:
        logger.info("nltk not available → using regex-based sentence splitter.")

    run(args.xml_dir, args.out_dir)

