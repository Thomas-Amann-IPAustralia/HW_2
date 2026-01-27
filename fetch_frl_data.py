import requests
import json
import logging
import sys
import os
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
CONTENT_DIR = "legislative_text"

# List your Register IDs here
TARGET_IDS = [
    "C2024C00545",
    "C2024C00455", 
    "F2026C00009"
]

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FRL_Sync")

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

def get_filename_from_cd(cd_header, default_name):
    """
    Extracts filename from Content-Disposition header.
    """
    if not cd_header:
        return default_name
    fname = re.findall('filename=(.+)', cd_header)
    if len(fname) == 0:
        return default_name
    return fname[0].strip().strip('"')

def download_content(session, register_id):
    """
    Downloads the binary content (bytes) for a given register ID.
    Uses the /find endpoint which returns bytes by default.
    """
    # Using the 'find' endpoint as per API docs 
    # This endpoint returns the document bytes by default.
    download_url = f"{BASE_URL}/find(registerId='{register_id}')"
    
    try:
        logger.info(f"Downloading content for {register_id}...")
        response = session.get(download_url, stream=True, timeout=60)
        
        if response.status_code == 404:
            logger.warning(f"No downloadable content found for {register_id}.")
            return
        
        response.raise_for_status()

        # Determine filename from headers or fallback to ID + extension guess
        content_type = response.headers.get("Content-Type", "")
        content_disp = response.headers.get("Content-Disposition")
        
        # Default extension guess
        ext = ".pdf" if "pdf" in content_type else ".docx"
        filename = get_filename_from_cd(content_disp, f"{register_id}{ext}")
        
        filepath = os.path.join(CONTENT_DIR, filename)

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Saved: {filename}")

    except Exception as e:
        logger.error(f"Failed to download text for {register_id}: {e}")

def fetch_documents():
    session = get_robust_session()
    
    # Ensure output directory exists
    if not os.path.exists(CONTENT_DIR):
        os.makedirs(CONTENT_DIR)

    # 1. Fetch Metadata
    # Construct the OData filter
    filter_query = " or ".join([f"registerId eq '{tid}'" for tid in TARGET_IDS])
    params = {"$filter": filter_query}
    
    logger.info(f"Searching for metadata matches...")

    try:
        response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        documents = data.get("value", [])

        # --- MISSING ID CHECK ---
        found_ids = [doc.get("registerId") for doc in documents]
        missing_ids = [tid for tid in TARGET_IDS if tid not in found_ids]
        
        if missing_ids:
            logger.warning(f"The following IDs were NOT found: {', '.join(missing_ids)}")
        
        if not documents:
            logger.error("No documents found at all.")
            return

        logger.info(f"SUCCESS: Found {len(documents)} matching metadata records.")

        # Save Metadata
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)

        # 2. Fetch Content Snapshots
        logger.info("Starting content downloads...")
        for doc in documents:
            reg_id = doc.get("registerId")
            if reg_id:
                download_content(session, reg_id)
            
    except Exception as e:
        logger.critical(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_documents()
