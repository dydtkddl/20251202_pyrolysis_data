import requests

API_KEY = "3c271c9aec7337d30416c170817761ad"

url = "https://api.elsevier.com/content/metadata/article"

headers = {
    "X-ELS-APIKey": API_KEY,
    "Accept": "application/json"
}

params = {
    "query": "TITLE(plastic)",
    "count": 25
}

r = requests.get(url, headers=headers, params=params)
print(r.status_code)
print(r.json())


