from grobid_client.grobid_client import GrobidClient
from lxml import etree

def tei_to_html(tei_xml: str) -> str:
    """TEI XML → HTML 변환"""
    root = etree.fromstring(tei_xml.encode("utf-8"))
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    # Title
    title_list = root.xpath("//tei:titleStmt/tei:title/text()", namespaces=ns)
    title = title_list[0] if title_list else "No Title"

    # Abstract
    abs_list = root.xpath("//tei:abstract//text()", namespaces=ns)
    abstract = " ".join(abs_list) if abs_list else "No Abstract"

    # Body
    paras = root.xpath("//tei:body//tei:p//text()", namespaces=ns)
    body = "\n".join(paras)
    body_html = body.replace("\n", "<br>")

    # f-string 대신 .format() 사용 (역슬래시 안전)
    html = """
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #444; margin-top: 30px; }}
            p {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <h2>Abstract</h2>
        <p>{abstract}</p>
        <h2>Full Text</h2>
        <p>{body}</p>
    </body>
    </html>
    """.format(title=title, abstract=abstract, body=body_html)

    return html


def process_pdf_to_html(pdf_path: str, output_html: str):
    client = GrobidClient(config_path="./config.json")

    print("[INFO] Processing PDF with GROBID...")

    _, _, tei_xml = client.process_pdf(
        "processFulltextDocument",
        pdf_path,
        True, True, True, True, True, True, True
    )

    print("[INFO] Converting TEI XML → HTML...")
    html_out = tei_to_html(tei_xml)

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[DONE] Saved: {output_html}")


if __name__ == "__main__":
    process_pdf_to_html("B.pdf", "B.html")


