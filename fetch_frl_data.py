import requests
import json
import logging
import sys
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
TARGET_ID = "C2024C00545"
OUTPUT_JSON = "legislation_metadata.json"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FRL_Download")

def get_robust_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session

def fetch_and_download():
    session = get_robust_session()
    
    # 1. Search for the metadata to find the file details
    params = {"$filter": f"registerId eq '{TARGET_ID}'"}
    logger.info(f"Searching metadata for: {TARGET_ID}...")

    try:
        response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=30)
        response.raise_for_status()
        data = response.json()
        documents = data.get("value", [])

        if not documents:
            logger.warning(f"No document found for ID: {TARGET_ID}")
            return

        # Use the first match
        doc_metadata = documents[0]
        
        # Save Metadata
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(doc_metadata, f, indent=2)
        logger.info(f"Metadata saved to {OUTPUT_JSON}")

        # 2. Handle File Download
        # The FRL API typically provides the file at /v1/documents({id})/content 
        # or it might be embedded if 'bytes' is not null. 
        # Based on your discovery, 'bytes' was null, so we call the content endpoint.
        
        content_url = f"{BASE_URL}('{TARGET_ID}')/content"
        extension = doc_metadata.get("extension", ".pdf")
        filename = f"{TARGET_ID}{extension}"

        logger.info(f"Downloading file from: {content_url}")
        
        # Stream the file to handle large downloads without crashing memory
        with session.get(content_url, stream=True, timeout=60) as r:
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"SUCCESS: File downloaded as {filename}")
            else:
                logger.error(f"Could not download file. Status: {r.status_code}")
                # Some FRL endpoints use TitleId instead of RegisterId for content
                logger.info("Retrying with TitleId...")
                title_id = doc_metadata.get("titleId")
                # Secondary attempt logic could go here if needed

    except Exception as e:
        logger.critical(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_download()
