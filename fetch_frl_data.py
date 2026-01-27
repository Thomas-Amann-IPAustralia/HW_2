import requests
import json
import logging
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
TARGET_ID = "C2024C00545"

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

def fetch_specific_document():
    session = get_robust_session()
    
    # Filter for the exact Register ID
    # Note: Strings in OData filters must be wrapped in single quotes
    params = {
        "$filter": f"registerId eq '{TARGET_ID}'"
    }
    
    logger.info(f"Searching for Document ID: {TARGET_ID}...")

    try:
        response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=30)
        
        if not response.ok:
            logger.error(f"Request failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return

        data = response.json()
        documents = data.get("value", [])

        if not documents:
            logger.warning(f"No document found with Register ID: {TARGET_ID}")
            return

        # Log the name of what we found
        doc_name = documents[0].get("titleId", "Unknown Title")
        logger.info(f"Found: {doc_name} (Items returned: {len(documents)})")

        # Save to JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)
            
        logger.info(f"SUCCESS: Result saved to {OUTPUT_FILE}")

    except Exception as e:
        logger.critical(f"Error during API call: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_specific_document()
