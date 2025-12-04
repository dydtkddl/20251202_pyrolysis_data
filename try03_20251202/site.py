#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streamlit viewer for QWEN plastic pyrolysis classification results
==================================================================

- Reads: all_results.csv
- Shows one paper at a time with navigation (prev/next/random/index)
- Filters by:
    - pyrolysis_related (YES/NO)
    - include_in_oil_db (YES/NO)
    - flags (any-of)
    - text search in abstract
    - "only rows without manual review"
- Displays:
    - source_file
    - model outputs (pyrolysis_related, include_in_oil_db, reason, flags)
    - abstract text
    - manual review form:
        - pyrolysis_related_gold (YES/NO/blank)
        - include_in_oil_db_gold (YES/NO/blank)
        - review_comment
- Saves manual reviews to: review_results.csv
"""

import os
import logging
from datetime import datetime
from collections import Counter

import pandas as pd
from tqdm import tqdm
import streamlit as st


# ============================================================
# Paths
# ============================================================
ALL_RESULTS_CSV = "all_results.csv"
REVIEW_RESULTS_CSV = "review_results.csv"
LOG_FILE = "streamlit_qwen_review.log"


# ============================================================
# Logging setup
# ============================================================
os.makedirs("logs", exist_ok=True)
log_path = os.path.join("logs", LOG_FILE)

logger = logging.getLogger("qwen_review_app")
logger.setLevel(logging.INFO)
logger.handlers.clear()

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)

logger.info("=== Streamlit QWEN Review App started ===")


# ============================================================
# Data loading
# ============================================================
@st.cache_data
def load_all_results(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} not found in current directory.")
    df = pd.read_csv(csv_path)

    # Ensure required cols exist; others can be extra
    required_cols = [
        "source_file",
        "abstract",
        "pyrolysis_related",
        "include_in_oil_db",
        "reason",
        "flags",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in all_results.csv: {missing}")

    # Normalize flags text and parse into list
    df["flags"] = df["flags"].fillna("").astype(str)
    df["flags_list"] = df["flags"].apply(
        lambda x: [f.strip() for f in x.split(";") if f.strip()]
    )

    return df


def load_review_results(csv_path: str) -> pd.DataFrame:
    """Load or initialize review_results.csv (not cached; small file)."""
    if not os.path.exists(csv_path):
        cols = [
            "source_file",
            "pyrolysis_related_gold",
            "include_in_oil_db_gold",
            "review_comment",
            "review_timestamp",
        ]
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(csv_path)
    # Ensure all expected columns exist
    for col in [
        "source_file",
        "pyrolysis_related_gold",
        "include_in_oil_db_gold",
        "review_comment",
        "review_timestamp",
    ]:
        if col not in df.columns:
            df[col] = ""
    return df


def save_review_result(
    source_file: str,
    pyro_gold: str,
    include_gold: str,
    comment: str,
    csv_path: str = REVIEW_RESULTS_CSV,
):
    """Insert or update a review row in review_results.csv."""
    df_rev = load_review_results(csv_path)

    timestamp = datetime.now().isoformat(timespec="seconds")

    if source_file in df_rev["source_file"].values:
        # Update existing row
        idx = df_rev.index[df_rev["source_file"] == source_file][0]
        df_rev.loc[idx, "pyrolysis_related_gold"] = pyro_gold
        df_rev.loc[idx, "include_in_oil_db_gold"] = include_gold
        df_rev.loc[idx, "review_comment"] = comment
        df_rev.loc[idx, "review_timestamp"] = timestamp
        logger.info(f"Updated review for {source_file}")
    else:
        # Append new row
        new_row = {
            "source_file": source_file,
            "pyrolysis_related_gold": pyro_gold,
            "include_in_oil_db_gold": include_gold,
            "review_comment": comment,
            "review_timestamp": timestamp,
        }
        df_rev = pd.concat([df_rev, pd.DataFrame([new_row])], ignore_index=True)
        logger.info(f"Added new review for {source_file}")

    df_rev.to_csv(csv_path, index=False, encoding="utf-8-sig")


def build_flag_universe(df: pd.DataFrame) -> list[str]:
    """Collect all unique flags across dataset (with tqdm for logging)."""
    counter = Counter()
    for text in tqdm(df["flags"], desc="Scanning flags for UI"):
        parts = str(text).split(";")
        for p in parts:
            f = p.strip()
            if f:
                counter[f] += 1
    # Sort by frequency (desc) then alphabetically
    sorted_flags = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [f for f, _ in sorted_flags]


# ============================================================
# UI helpers
# ============================================================
def init_session_state():
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "last_filtered_count" not in st.session_state:
        st.session_state.last_filtered_count = 0


def badge(label: str, color: str) -> str:
    """HTML badge for small status tags."""
    return f"""
    <span style="
        display:inline-block;
        padding:2px 8px;
        margin-right:4px;
        border-radius:10px;
        background-color:{color};
        color:white;
        font-size:0.8rem;
    ">{label}</span>
    """


# ============================================================
# Main Streamlit app
# ============================================================
def main():
    st.set_page_config(
        page_title="QWEN Plastic Pyrolysis Review",
        layout="wide",
    )

    init_session_state()

    st.title("QWEN Plastic Pyrolysis – Paper Review Interface")

    # Load main data
    try:
        df_all = load_all_results(ALL_RESULTS_CSV)
    except Exception as e:
        st.error(f"Failed to load {ALL_RESULTS_CSV}: {e}")
        logger.exception("Failed to load all_results.csv")
        return

    df_review = load_review_results(REVIEW_RESULTS_CSV)

    # Merge review info into main DataFrame (left join by source_file)
    df = df_all.merge(
        df_review[
            [
                "source_file",
                "pyrolysis_related_gold",
                "include_in_oil_db_gold",
                "review_comment",
            ]
        ],
        on="source_file",
        how="left",
    )

    # Sidebar: dataset summary and filters
    with st.sidebar:
        st.header("Dataset Summary")

        total_n = len(df)
        pyro_counts = df["pyrolysis_related"].value_counts(dropna=False)
        include_counts = df["include_in_oil_db"].value_counts(dropna=False)

        st.write(f"**Total rows:** {total_n}")
        st.write("**pyrolysis_related:**")
        for k, v in pyro_counts.items():
            st.write(f"- {k}: {v} ({v/total_n:.1%})")

        st.write("**include_in_oil_db:**")
        for k, v in include_counts.items():
            st.write(f"- {k}: {v} ({v/total_n:.1%})")

        reviewed_count = df["pyrolysis_related_gold"].notna().sum()
        st.write(f"**Rows with manual review:** {reviewed_count}")

        st.markdown("---")
        st.header("Filters")

        # Filter: pyrolysis_related
        pyro_options = sorted(df["pyrolysis_related"].dropna().unique().tolist())
        pyro_selected = st.multiselect(
            "pyrolysis_related",
            options=pyro_options,
            default=pyro_options,
        )

        # Filter: include_in_oil_db
        include_options = sorted(df["include_in_oil_db"].dropna().unique().tolist())
        include_selected = st.multiselect(
            "include_in_oil_db",
            options=include_options,
            default=include_options,
        )

        # Flags filter: build universe once
        all_flags = build_flag_universe(df)
        if all_flags:
            flags_selected = st.multiselect(
                "Filter by flags (ANY of selected)",
                options=all_flags,
                default=[],
            )
        else:
            flags_selected = []

        # Text search in abstract
        search_text = st.text_input(
            "Search text in abstract (case-insensitive)",
            value="",
            placeholder="e.g., polypropylene, zeolite, TGA, GC-MS ...",
        )

        # Only rows without manual review
        only_without_review = st.checkbox(
            "Show only rows without manual review", value=False
        )

    # Apply filters
    df_filtered = df.copy()

    if pyro_selected:
        df_filtered = df_filtered[df_filtered["pyrolysis_related"].isin(pyro_selected)]

    if include_selected:
        df_filtered = df_filtered[df_filtered["include_in_oil_db"].isin(include_selected)]

    if flags_selected:
        # Keep rows that contain ANY of the selected flags
        df_filtered = df_filtered[
            df_filtered["flags_list"].apply(
                lambda flist: any(f in flist for f in flags_selected)
            )
        ]

    if search_text.strip():
        pattern = search_text.strip()
        df_filtered = df_filtered[
            df_filtered["abstract"].str.contains(pattern, case=False, na=False)
        ]

    if only_without_review:
        mask = (
            df_filtered["pyrolysis_related_gold"].isna()
            & df_filtered["include_in_oil_db_gold"].isna()
            & df_filtered["review_comment"].isna()
        )
        df_filtered = df_filtered[mask]

    filtered_count = len(df_filtered)

    if filtered_count == 0:
        st.warning("No rows match the current filters.")
        st.stop()

    # Adjust current_index if filtered count changed (e.g. after filter change)
    if st.session_state.current_index >= filtered_count:
        st.session_state.current_index = max(0, filtered_count - 1)

    st.subheader("Filtered set overview")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total rows", total_n)
    with col_b:
        st.metric("Filtered rows", filtered_count)
    with col_c:
        st.metric("Manual review rows (overall)", reviewed_count)

    st.markdown("---")

    # Navigation controls
    st.subheader("Navigation")

    nav_cols = st.columns([1, 1, 1, 3])
    with nav_cols[0]:
        if st.button("◀ Prev"):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1

    with nav_cols[1]:
        if st.button("Next ▶"):
            if st.session_state.current_index < filtered_count - 1:
                st.session_state.current_index += 1

    with nav_cols[2]:
        import random

        if st.button("🎲 Random"):
            st.session_state.current_index = random.randint(0, filtered_count - 1)

    with nav_cols[3]:
        idx_input = st.number_input(
            "Go to index (0-based in filtered set)",
            min_value=0,
            max_value=filtered_count - 1,
            value=int(st.session_state.current_index),
            step=1,
        )
        # If user changed the number input, update current_index
        if idx_input != st.session_state.current_index:
            st.session_state.current_index = int(idx_input)

    st.write(f"Current index in filtered set: **{st.session_state.current_index} / {filtered_count - 1}**")

    # Current row
    row = df_filtered.iloc[st.session_state.current_index]

    st.markdown("---")
    st.subheader("Current paper")

    # Top summary row
    col_left, col_right = st.columns([2, 2])

    with col_left:
        st.markdown(f"**source_file:** `{row['source_file']}`")

        # Model outputs as badges
        pyro = str(row["pyrolysis_related"])
        include = str(row["include_in_oil_db"])

        pyro_color = "#2ecc71" if pyro == "YES" else "#e74c3c"
        include_color = "#3498db" if include == "YES" else "#95a5a6"

        badge_html = (
            badge(f"pyrolysis_related: {pyro}", pyro_color)
            + badge(f"include_in_oil_db: {include}", include_color)
        )
        st.markdown(badge_html, unsafe_allow_html=True)

    with col_right:
        flags_str = row.get("flags", "")
        st.markdown("**flags (model):**")
        if flags_str.strip():
            flag_tokens = [f.strip() for f in flags_str.split(";") if f.strip()]
            if flag_tokens:
                st.write(", ".join(flag_tokens))
            else:
                st.write("(none)")
        else:
            st.write("(none)")

        st.markdown("**Model reason:**")
        st.write(str(row.get("reason", "")))

    st.markdown("---")

    # Abstract
    st.subheader("Abstract (model input)")
    st.text_area(
        "Abstract",
        value=str(row["abstract"]),
        height=300,
        key=f"abstract_{row['source_file']}",
    )

    st.markdown("---")

    # Manual review section
    st.subheader("Manual review (gold labels)")

    # Determine default values from existing review
    pyro_gold_existing = str(row.get("pyrolysis_related_gold", ""))
    include_gold_existing = str(row.get("include_in_oil_db_gold", ""))
    comment_existing = str(row.get("review_comment", "")) if not pd.isna(row.get("review_comment", "")) else ""

    options_gold = ["", "YES", "NO"]

    def get_index_for_option(value: str) -> int:
        if value not in options_gold:
            return 0
        return options_gold.index(value)

    with st.form(key=f"review_form_{row['source_file']}"):
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            pyro_gold = st.selectbox(
                "pyrolysis_related_gold (human)",
                options=options_gold,
                index=get_index_for_option(pyro_gold_existing),
                help="Leave blank if not decided yet.",
            )
        with col_f2:
            include_gold = st.selectbox(
                "include_in_oil_db_gold (human)",
                options=options_gold,
                index=get_index_for_option(include_gold_existing),
                help="Leave blank if not decided yet.",
            )

        comment = st.text_area(
            "Reviewer comment / notes",
            value=comment_existing,
            height=120,
        )

        submitted = st.form_submit_button("💾 Save review")

        if submitted:
            save_review_result(
                source_file=row["source_file"],
                pyro_gold=pyro_gold,
                include_gold=include_gold,
                comment=comment,
            )
            st.success("Review saved.")
            logger.info(
                f"Review saved for {row['source_file']} | pyro_gold={pyro_gold}, include_gold={include_gold}"
            )
            # Re-run to refresh merged DataFrame with updated review info
            st.experimental_rerun()


if __name__ == "__main__":
    main()
