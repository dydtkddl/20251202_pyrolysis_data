import requests
import logging

logging.basicConfig(level=logging.INFO)

def fetch_semantic(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract,authors,year,venue"
    r = requests.get(url, timeout=10)

    if r.status_code != 200:
        logging.error(f"Failed: {doi}")
        return None

    return r.json()

doi = "10.1016/j.jaap.2012.06.009"

data = fetch_semantic(doi)

print("Title:", data.get("title"))
print("Abstract:", data.get("abstract"))


