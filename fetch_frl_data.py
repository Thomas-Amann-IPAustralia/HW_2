import requests
import json
import logging
import sys

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
TARGET_ID = "C2024C00545"
OUTPUT_JSON = "legislation_metadata.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FRL_Download")

def fetch_and_download():
    session = requests.Session()
    
    # 1. Get Metadata
    params = {"$filter": f"registerId eq '{TARGET_ID}'"}
    try:
        response = session.get(BASE_URL, params=params, headers={"accept": "application/json"})
        response.raise_for_status()
        items = response.json().get("value", [])

        if not items:
            logger.error(f"No metadata found for {TARGET_ID}")
            return

        doc_metadata = items[0]
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(doc_metadata, f, indent=2)

        # 2. Download File using /$value (Standard OData Binary Endpoint)
        # Attempting the /$value route which is common for OData media streams
        download_url = f"{BASE_URL}('{TARGET_ID}')/$value"
        extension = doc_metadata.get("extension", ".pdf")
        filename = f"{TARGET_ID}{extension}"

        logger.info(f"Attempting download from: {download_url}")
        
        with session.get(download_url, stream=True, timeout=60) as r:
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"SUCCESS: Downloaded {filename}")
            else:
                logger.error(f"Download failed with status: {r.status_code}")
                # Create a placeholder file so GitHub Action doesn't crash on 'pathspec' error
                with open("download_failed.txt", "w") as f:
                    f.write(f"Failed to download {TARGET_ID}. API returned {r.status_code}")

    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_download()
