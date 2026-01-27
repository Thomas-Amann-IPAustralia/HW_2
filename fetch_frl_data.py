import requests
import json
import logging
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"

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

def fetch_documents():
    session = get_robust_session()
    
    # Construct the OData filter
    filter_query = " or ".join([f"registerId eq '{tid}'" for tid in TARGET_IDS])
    params = {"$filter": filter_query}
    
    logger.info(f"Searching for {len(TARGET_IDS)} documents...")

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

        logger.info(f"SUCCESS: Found {len(documents)} matching documents.")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)
            
    except Exception as e:
        logger.critical(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_documents()
