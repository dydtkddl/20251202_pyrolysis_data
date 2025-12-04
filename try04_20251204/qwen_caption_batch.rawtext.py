#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure & Table Caption Detector for Elsevier rawtext XML
-------------------------------------------------------

규칙:
- Figure:
    - Elsevier 규칙: "Fig. x." 패턴이 나오면 Figure 캡션 시작으로 간주.
    - 해당 문장이 포함된 문장부터, 그 뒤 최대 2문장까지 (총 최대 3문장)을 캡션으로 취급.
    - LLM 사용 안 함. 순수 규칙 기반.

- Table:
    - "Table" 키워드가 포함된 문장이 있을 때만 후보로 삼음.
    - 그 문장(S0) + 뒤 두 문장(S1, S2)까지 최대 3문장을 LLM에 전달.
    - LLM(QWEN via Ollama)은:
        LABEL=TABLE_CAPTION or NOT_CAPTION
        END_INDEX=-1/0/1/2 (캡션이 어디까지인지, -1이면 캡션 아님)
        REASON=간단한 이유
      형식으로 한 줄을 출력.
    - 배치 처리 없이, candidate마다 한 번씩만 LLM 호출.

출력:
- per-XML JSON: output_json_dir/<file>.json
    각 엔트리:
        {
          "file": ...,
          "type": "FIGURE" or "TABLE",
          "id": "<번호 문자열 또는 null>",
          "start_sent_idx": int,
          "end_sent_idx": int,
          "caption_text": "...",
          "source": "RULE_FIG_PATTERN" or "LLM_TABLE",
          "raw_window": [S0, S1, S2],
          "table_label": ...,
          "table_end_in_window": ...,
          "table_reason": ...
        }

- 전체 CSV (out_csv): 위 필드를 컬럼으로 모아서 저장.

사용 예:
    python detect_captions_fig_table.py --xml_dir ./xmls_with_rawtext \
        --out_csv captions_all.csv \
        --out_json_dir ./output_captions
"""

import os
import re
import json
import logging
import argparse
from typing import List, Dict, Optional

from lxml import etree
from tqdm import tqdm
import pandas as pd
import ollama


# =========================================================
# CONFIG
# =========================================================
DEFAULT_XML_DIR = "./xmls"
DEFAULT_OUT_CSV = "captions_all.csv"
DEFAULT_OUT_JSON_DIR = "./output_captions"

QWEN_MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"   # 너 환경에 맞게 수정

# 문장 분할 시 Fig. 잘리는 문제 방지용 치환 토큰
FIG_TOKEN = "FIGSPECIALTOKEN"
FIGS_TOKEN = "FIGSSPECIALTOKEN"


# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# =========================================================
# XML → rawtext 추출
# =========================================================
def extract_rawtext_from_xml(path: str) -> Optional[str]:
    """
    XML 파일에서 <rawtext> (또는 <xocs:rawtext>) 태그 내부 텍스트만 추출.
    여러 노드가 있을 경우 모두 이어붙임.
    """
    try:
        tree = etree.parse(path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"XML parse error: {path} | {e}")
        return None

    nodes = root.xpath("//*[local-name()='rawtext']//text()")
    if not nodes:
        return None

    text = " ".join(nodes)
    text = text.replace("\r", " ")
    text = " ".join(text.split())
    return text.strip()


# =========================================================
# 문장 분할 (마침표 기준) + Fig. 보정
# =========================================================
_SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

def split_sentences(text: str) -> List[str]:
    """
    아주 단순한 영문 문장 분할.
    - 'Fig.'에서 잘려나가지 않도록 사전 치환 후 분할, 이후 복원.
    """
    # Fig. → FIGSPECIALTOKEN, Figs. → FIGSSPECIALTOKEN
    tmp = text.replace("Fig.", FIG_TOKEN).replace("Figs.", FIGS_TOKEN)

    sents = _SENT_SPLIT_RE.split(tmp)
    sents = [s.strip() for s in sents if s and len(s.strip()) > 0]

    # 토큰 복원
    restored = []
    for s in sents:
        s = s.replace(FIG_TOKEN, "Fig.").replace(FIGS_TOKEN, "Figs.")
        restored.append(s.strip())
    return restored


# =========================================================
# Figure 캡션 검출 (규칙 기반)
# =========================================================
FIG_PATTERN = re.compile(r"\bFig\.\s*\d+", re.IGNORECASE)

def detect_figure_captions(sentences: List[str]) -> List[Dict]:
    """
    문장 리스트에서 Fig. x. 패턴을 찾아 Figure 캡션 구간을 검출.
    - Fig. x. 포함 문장 = 캡션 시작
    - 그 뒤 최대 2문장까지 포함 (총 3문장)
    - 이미 사용된 문장은 중복 사용하지 않도록 관리
    """
    used = [False] * len(sentences)
    results: List[Dict] = []

    for i, s in enumerate(sentences):
        if used[i]:
            continue

        if FIG_PATTERN.search(s):
            # Figure 번호 추출
            m = FIG_PATTERN.search(s)
            fig_no = None
            if m:
                # m.group() 예: "Fig. 1" → 숫자만 추출
                tail = s[m.start():]
                m_num = re.search(r"Fig\.\s*([0-9]+[a-zA-Z]?)", tail)
                if m_num:
                    fig_no = m_num.group(1)

            start_idx = i
            end_idx = min(i + 2, len(sentences) - 1)

            for k in range(start_idx, end_idx + 1):
                used[k] = True

            caption_text = " ".join(sentences[start_idx:end_idx + 1])

            results.append({
                "type": "FIGURE",
                "id": fig_no,
                "start_sent_idx": start_idx,
                "end_sent_idx": end_idx,
                "caption_text": caption_text,
                "source": "RULE_FIG_PATTERN",
                "raw_window": sentences[start_idx:end_idx + 1],
                "table_label": None,
                "table_end_in_window": None,
                "table_reason": None,
            })

    return results


# =========================================================
# Table 캡션 판별용 QWEN 호출
# =========================================================
def build_table_prompt(s0: str, s1: str, s2: str) -> str:
    """
    Table 후보 3문장(S0, S1, S2)에 대해 QWEN에게 판별을 요청하는 프롬프트.
    출력 포맷:
        LABEL=<TABLE_CAPTION or NOT_CAPTION>;
        END_INDEX=< -1, 0, 1, 2 >;
        REASON=<짧은 이유>
    한 줄로만 출력하도록 강하게 요구.
    """
    prompt = f"""
You are helping to detect TABLE captions in Elsevier-style scientific articles.

You are given up to three sentences, S0, S1, S2. S0 contains the word "Table" or "Tables".
In Elsevier articles, a table caption is usually a short block of text describing the content of the table.

Your task:
1) Decide if these sentences form a TABLE CAPTION or NOT.
2) If it is a TABLE CAPTION, determine up to which sentence the caption extends:
   - 0: only S0 is the caption.
   - 1: S0 and S1 together form the caption.
   - 2: S0, S1, and S2 together form the caption.
3) If it is NOT a caption, use -1.

Respond in EXACTLY ONE LINE with the following format:

LABEL=<TABLE_CAPTION or NOT_CAPTION>; END_INDEX=< -1 or 0 or 1 or 2 >; REASON=<very short explanation in English>

Do NOT add anything before 'LABEL='. Do NOT add extra lines.

Here are the sentences:

[S0] {s0}
[S1] {s1}
[S2] {s2}
""".strip()
    return prompt


def parse_table_response(text: str) -> Dict:
    """
    QWEN 응답에서 LABEL, END_INDEX, REASON 파싱.
    LABEL=<...>; END_INDEX=<...>; REASON=<...>
    형태를 정규식으로 추출.
    """
    # 첫 번째로 'LABEL='이 등장하는 위치부터 이후만 사용
    idx = text.find("LABEL=")
    if idx >= 0:
        text = text[idx:]

    # 멀티라인일 경우 한 줄로
    text_one = " ".join(text.splitlines())
    # 공백 정리
    text_one = " ".join(text_one.split())

    # LABEL, END_INDEX, REASON 추출
    m = re.search(
        r"LABEL\s*=\s*([A-Z_]+)\s*;\s*END_INDEX\s*=\s*(-?\d+)\s*;\s*REASON\s*=\s*(.+)",
        text_one
    )
    if not m:
        return {
            "label": "PARSE_ERROR",
            "end_index": -1,
            "reason": f"raw: {text_one[:200]}"
        }

    label = m.group(1).upper()
    try:
        end_idx = int(m.group(2))
    except ValueError:
        end_idx = -1
    reason = m.group(3).strip()

    # sanity check
    if label not in ("TABLE_CAPTION", "NOT_CAPTION"):
        label = "PARSE_ERROR"

    if end_idx not in (-1, 0, 1, 2):
        end_idx = -1

    return {
        "label": label,
        "end_index": end_idx,
        "reason": reason,
    }


def call_qwen_table(s0: str, s1: str, s2: str) -> Dict:
    """
    Table 캡션 여부를 QWEN(Qwen via Ollama)에 물어봄.
    배치 없이 한 번에 하나만 요청.
    """
    prompt = build_table_prompt(s0, s1, s2)

    try:
        resp = ollama.chat(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Qwen call failed (Table): {e}")
        return {
            "label": "ERROR",
            "end_index": -1,
            "reason": f"Qwen call error: {e}"
        }

    parsed = parse_table_response(content)
    return parsed


# =========================================================
# Table 캡션 검출 (LLM 기반)
# =========================================================
TABLE_KEYWORD_PAT = re.compile(r"\bTable[s]?\b", re.IGNORECASE)

def detect_table_captions(sentences: List[str]) -> List[Dict]:
    """
    문장 리스트에서 'Table' 키워드가 들어간 문장을 후보로 잡고,
    S0(해당 문장) + S1, S2까지를 QWEN에 넘겨서 캡션 여부와 범위를 판별.
    """
    used = [False] * len(sentences)
    results: List[Dict] = []

    i = 0
    n = len(sentences)
    while i < n:
        if used[i]:
            i += 1
            continue

        s = sentences[i]
        if not TABLE_KEYWORD_PAT.search(s):
            i += 1
            continue

        # 후보 window 구성
        s0 = s
        s1 = sentences[i+1] if i+1 < n else ""
        s2 = sentences[i+2] if i+2 < n else ""

        q_res = call_qwen_table(s0, s1, s2)
        label = q_res["label"]
        end_in_win = q_res["end_index"]
        reason = q_res["reason"]

        if label == "TABLE_CAPTION" and end_in_win >= 0:
            # 캡션 범위: i ~ i + end_in_win
            end_idx = min(i + end_in_win, n - 1)
            start_idx = i

            for k in range(start_idx, end_idx + 1):
                used[k] = True

            # Table 번호 추출 시도
            text_window = " ".join(sentences[start_idx:end_idx + 1])
            table_id = None
            m = re.search(r"\bTable\s*([0-9]+[a-zA-Z]?)", text_window, re.IGNORECASE)
            if m:
                table_id = m.group(1)

            caption_text = " ".join(sentences[start_idx:end_idx + 1])

            results.append({
                "type": "TABLE",
                "id": table_id,
                "start_sent_idx": start_idx,
                "end_sent_idx": end_idx,
                "caption_text": caption_text,
                "source": "LLM_TABLE",
                "raw_window": [s0, s1, s2],
                "table_label": label,
                "table_end_in_window": end_in_win,
                "table_reason": reason,
            })

            # 이미 이 범위는 사용되었으니 end_idx+1 부터 다시 탐색
            i = end_idx + 1
        else:
            # 캡션 아님 혹은 파싱 에러 → 문장만 넘기고 i+1에서 계속
            results.append({
                "type": "TABLE",
                "id": None,
                "start_sent_idx": i,
                "end_sent_idx": i,
                "caption_text": s0,
                "source": "LLM_TABLE",
                "raw_window": [s0, s1, s2],
                "table_label": label,
                "table_end_in_window": end_in_win,
                "table_reason": reason,
            })
            i += 1

    return results


# =========================================================
# 단일 XML 파일 처리
# =========================================================
def process_single_xml(path: str, out_json_dir: str) -> List[Dict]:
    """
    한 XML 파일에 대해:
      - rawtext 추출
      - 문장 분할
      - Figure 캡션(규칙 기반) 탐지
      - Table 캡션(LLM 기반) 탐지
      - 결과를 JSON(+리스트)로 반환 & per-XML JSON 저장
    """
    fname = os.path.basename(path)

    rawtext = extract_rawtext_from_xml(path)
    if not rawtext:
        logger.info(f"[{fname}] No rawtext found.")
        return []

    sentences = split_sentences(rawtext)
    if not sentences:
        logger.info(f"[{fname}] No sentences parsed.")
        return []

    fig_caps = detect_figure_captions(sentences)
    tab_caps = detect_table_captions(sentences)

    logger.info(
        f"[{fname}] Figure captions: {len(fig_caps)}, Table records: {len(tab_caps)}"
    )

    # file / 문장 리스트를 추가 필드로 합치기
    all_records: List[Dict] = []
    for r in fig_caps + tab_caps:
        rec = dict(r)
        rec["file"] = fname
        all_records.append(rec)

    if all_records:
        os.makedirs(out_json_dir, exist_ok=True)
        out_path = os.path.join(out_json_dir, fname.replace(".xml", ".json"))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)
        logger.info(f"[{fname}] Saved JSON → {out_path}")

    return all_records


# =========================================================
# 전체 배치 처리
# =========================================================
def run_batch(xml_dir: str, out_csv: str, out_json_dir: str):
    xml_files = [
        os.path.join(xml_dir, f)
        for f in os.listdir(xml_dir)
        if f.lower().endswith(".xml")
    ]
    xml_files.sort()

    logger.info(f"XML files found: {len(xml_files)}")

    all_rows: List[Dict] = []

    for path in tqdm(xml_files, desc="Processing XML"):
        rows = process_single_xml(path, out_json_dir)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        logger.warning("No captions detected in any file.")
        return

    df = pd.DataFrame(all_rows)

    # JSON 필드(raw_window 등)는 CSV에 그냥 문자열로 들어가게 둠
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Saved aggregated CSV → {out_csv}")

    # 간단 통계
    logger.info("Type counts:\n%s", df["type"].value_counts())
    if "table_label" in df.columns:
        logger.info("Table label counts:\n%s", df["table_label"].value_counts())


# =========================================================
# CLI
# =========================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Figure/Table caption detector (Elsevier rawtext)."
    )
    parser.add_argument(
        "--xml_dir",
        type=str,
        default=DEFAULT_XML_DIR,
        help=f"XML 폴더 경로 (default: {DEFAULT_XML_DIR})"
    )
    parser.add_argument(
        "--out_csv",
        type=str,
        default=DEFAULT_OUT_CSV,
        help=f"최종 종합 결과 CSV 파일 경로 (default: {DEFAULT_OUT_CSV})"
    )
    parser.add_argument(
        "--out_json_dir",
        type=str,
        default=DEFAULT_OUT_JSON_DIR,
        help=f"XML별 JSON 결과 저장 폴더 (default: {DEFAULT_OUT_JSON_DIR})"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not os.path.isdir(args.xml_dir):
        logger.error(f"XML dir not found: {args.xml_dir}")
        raise SystemExit(1)

    logger.info(f"XML dir: {args.xml_dir}")
    logger.info(f"Output CSV: {args.out_csv}")
    logger.info(f"Per-file JSON dir: {args.out_json_dir}")
    logger.info(f"Qwen model: {QWEN_MODEL}")

    run_batch(args.xml_dir, args.out_csv, args.out_json_dir)
