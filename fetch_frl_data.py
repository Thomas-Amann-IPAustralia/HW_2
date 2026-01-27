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
PAGE_SIZE = 500  # Confirmed server limit
START_DATE = "1989-01-01T00:00:00"

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
    """
    Checks if keywords exist in any string value within the object.
    We convert the whole object to a string to catch keywords in any field.
    """
    obj_str = json.dumps(obj).lower()
    return any(word.lower() in obj_str for word in KEYWORDS)

def fetch_frl_data():
    session = get_robust_session()
    all_filtered_docs = []
    skip = 0
    
    # Using the 'start' field discovered in your logs
    odata_filter = f"start ge {START_DATE}"

    logger.info(f"Starting wholesale fetch for documents since {START_DATE}...")

    while True:
        params = {
            "$top": PAGE_SIZE, 
            "$skip": skip,
            "$filter": odata_filter
        }
        
        try:
            response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=60)
            
            if not response.ok:
                logger.error(f"API Error {response.status_code} at skip={skip}")
                logger.error(f"Details: {response.text}")
                break

            data = response.json()
            # As seen in discovery, items are inside the 'value' key
            batch = data.get("value", [])

            if not batch:
                logger.info("Reached the end of the data stream.")
                break

            # Local keyword filtering
            filtered_batch = [doc for doc in batch if contains_keywords(doc)]
            all_filtered_docs.extend(filtered_batch)

            logger.info(f"Fetched {skip + len(batch)} items total... found {len(all_filtered_docs)} matches.")

            # If we got fewer items than the page size, we're done
            if len(batch) < PAGE_SIZE:
                break
                
            skip += PAGE_SIZE
            
        except Exception as e:
            logger.critical(f"Connection error: {str(e)}")
            break

    # Final save to your repo
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_filtered_docs, f, indent=2)
    
    logger.info(f"DONE. Total matching documents saved: {len(all_filtered_docs)}")

if __name__ == "__main__":
    fetch_frl_data()
