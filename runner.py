import requests

BASE = "https://api.prod.legislation.gov.au/v1"
ACT_ID = "C2004A04969"

# 1. Get latest compilation
meta = requests.get(
    f"{BASE}/Content('{ACT_ID}')",
    params={"$expand": "LatestCompilation"},
    headers={"Accept": "application/json"},
    timeout=60,
)
meta.raise_for_status()

comp_id = meta.json()["LatestCompilation"]["Id"]

# 2. Download XML snapshot
xml = requests.get(
    f"{BASE}/Compilations('{comp_id}')/Xml/$value",
    headers={"Accept": "application/xml"},
    timeout=120,
)
xml.raise_for_status()

with open("Trade_Marks_Act_latest.xml", "wb") as f:
    f.write(xml.content)

print(f"Downloaded compilation {comp_id}")
