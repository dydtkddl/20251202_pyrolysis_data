# -*- coding: utf-8 -*-
"""
Auto-compatible GROBID abstract extractor
Works with ALL versions of grobid_client_python
"""

import os
import argparse
import xml.etree.ElementTree as ET
from grobid_client.grobid_client import GrobidClient

HTML_TEMPLATE = """
<html>
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #444; margin-top: 30px; }}
        pre {{ line-height: 1.6; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <h2>Abstract</h2>
    <pre>{abstract}</pre>
</body>
</html>
"""


def extract_title_abstract(xml_text):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = ET.fromstring(xml_text)

    # title
    t = root.find(".//tei:titleStmt/tei:title", ns)
    title = t.text.strip() if t is not None and t.text else "No Title"

    # abstract
    a = root.find(".//tei:abstract", ns)
    if a is None:
        abstract = "No Abstract"
    else:
        paras = a.findall(".//tei:p", ns)
        if paras:
            abstract = "\n".join([(p.text or "").strip() for p in paras])
        else:
            abstract = (a.text or "").strip() or "No Abstract"

    return title, abstract


def safe_process_pdf(client, pdf_path):
    """Handles 1-return, 2-return, and 3-return signatures safely."""
    res = client.process_pdf(
        "processHeaderDocument",
        os.path.abspath(pdf_path),
        True,   # generateIDs
        True,   # consolidate_header
        False,  # consolidate_citations
        False,  # include_raw_citations
        False,  # include_raw_affiliations
        False,  # tei_coordinates
        False   # segment_sentences
    )

    if isinstance(res, tuple):
        if len(res) == 1:
            # xml only
            return 200, res[0]
        elif len(res) == 2:
            # (status, xml)
            return res
        elif len(res) == 3:
            # (pdf_path, status, xml)
            return res[1], res[2]
        else:
            raise RuntimeError("Unexpected return tuple length")
    else:
        # xml only
        return 200, res


def process_pdf(pdf_path, output_html, config_path):
    client = GrobidClient(config_path=config_path)

    print("🚀 Processing:", pdf_path)

    status, xml_text = safe_process_pdf(client, pdf_path)

    if status != 200:
        raise RuntimeError(f"GROBID returned HTTP {status}")

    title, abstract = extract_title_abstract(xml_text)

    html = HTML_TEMPLATE.format(title=title, abstract=abstract)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    print("🎉 Saved:", output_html)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="./config.json")
    args = parser.parse_args()

    process_pdf(args.pdf, args.output, args.config)


if __name__ == "__main__":
    main()


