import requests
import json
import logging
import sys
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
KEYWORDS = ["trade marks", "patents"]
PAGE_SIZE = 1000

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FRL_Sync")

def get_robust_session():
    """Configures a requests session with retries for 429, 500, 502, 503, 504 errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2, # Waits 2s, 4s, 8s, 16s, 32s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session

def contains_keywords(obj):
    """Recursively checks if any string value in a JSON object contains keywords."""
    # Convert to lowercase string for a "catch-all" text search
    obj_str = json.dumps(obj).lower()
    return any(word.lower() in obj_str for word in KEYWORDS)

def fetch_frl_data():
    session = get_robust_session()
    all_filtered_docs = []
    skip = 0
    
    logger.info("Initiating FRL API wholesale fetch...")

    while True:
        params = {"$top": PAGE_SIZE, "$skip": skip}
        logger.info(f"Fetching batch: skip={skip}, limit={PAGE_SIZE}")

        try:
            response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=30)
            
            # If request fails after retries, log everything
            if not response.ok:
                logger.error(f"Request Failed! Status: {response.status_code}")
                logger.error(f"URL: {response.url}")
                logger.error(f"Headers: {dict(response.headers)}")
                logger.error(f"Sample Body: {response.text[:500]}")
                break

            data = response.json()
            batch = data if isinstance(data, list) else data.get("items", [])

            if not batch:
                logger.info("No more documents found in the Register.")
                break

            # Filtering logic
            initial_count = len(batch)
            filtered_batch = [doc for doc in batch if contains_keywords(doc)]
            all_filtered_docs.extend(filtered_batch)

            logger.info(f"Batch Processed: Found {len(filtered_batch)} matches out of {initial_count} items.")

            # Stop if we didn't get a full page (end of data)
            if len(batch) < PAGE_SIZE:
                break
                
            skip += PAGE_SIZE
            
        except Exception as e:
            logger.critical(f"A non-recoverable error occurred: {str(e)}", exc_info=True)
            sys.exit(1)

    # Final Save
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_filtered_docs, f, indent=2)
        logger.info(f"SUCCESS: Saved {len(all_filtered_docs)} total documents to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")

if __name__ == "__main__":
    fetch_frl_data()
