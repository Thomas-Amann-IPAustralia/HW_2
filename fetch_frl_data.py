import requests
import json
import logging
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
KEYWORDS = ["trade marks", "patents"]
PAGE_SIZE = 500  # Fixed: FRL limit is 500
START_DATE = "1989-01-01T00:00:00Z"

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

def contains_keywords(obj):
    """Recursively checks if any string value in a JSON object contains keywords."""
    obj_str = json.dumps(obj).lower()
    return any(word.lower() in obj_str for word in KEYWORDS)

def fetch_frl_data():
    session = get_robust_session()
    all_filtered_docs = []
    skip = 0
    
    # We apply the date filter directly in the API call to reduce the data we have to download
    # registrationDate is the standard field for FRL OData queries
    odata_filter = f"registrationDate ge {START_DATE}"

    logger.info(f"Initiating FRL API fetch (Documents since {START_DATE})...")

    while True:
        params = {
            "$top": PAGE_SIZE, 
            "$skip": skip,
            "$filter": odata_filter
        }
        
        try:
            response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=30)
            
            if not response.ok:
                logger.error(f"Request Failed! Status: {response.status_code}")
                logger.error(f"Body: {response.text}")
                break

            data = response.json()
            # FRL usually wraps results in a 'value' or 'items' key for OData
            batch = data.get("value", []) if isinstance(data, dict) else data

            if not batch:
                logger.info("Reached the end of the Register.")
                break

            # Filter locally for keywords
            filtered_batch = [doc for doc in batch if contains_keywords(doc)]
            all_filtered_docs.extend(filtered_batch)

            logger.info(f"Processed {skip + len(batch)} total items... (Found {len(all_filtered_docs)} matches)")

            # If we got less than the PAGE_SIZE, we've hit the end of the server's list
            if len(batch) < PAGE_SIZE:
                break
                
            skip += PAGE_SIZE
            
        except Exception as e:
            logger.critical(f"Fatal error: {str(e)}", exc_info=True)
            sys.exit(1)

    # Save to file
    if all_filtered_docs:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_filtered_docs, f, indent=2)
        logger.info(f"SUCCESS: {len(all_filtered_docs)} documents matching criteria saved to {OUTPUT_FILE}")
    else:
        logger.warning("No documents found matching those keywords since 1989.")

if __name__ == "__main__":
    fetch_frl_data()
