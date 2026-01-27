import requests
import json
import logging
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
TARGET_COUNT = 50  # Stop once we hit this number

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FRL_Sync")

def get_robust_session():
    """Configures session with retries for stability."""
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

def fetch_frl_data():
    session = get_robust_session()
    
    # Filter for authorized documents only
    params = {
        "$top": TARGET_COUNT,
        "$filter": "isAuthorised eq true"
    }
    
    logger.info(f"Requesting {TARGET_COUNT} authorised documents from FRL API...")

    try:
        # 60-second timeout to give the server plenty of time to process the filter
        response = session.get(BASE_URL, params=params, headers={"accept": "application/json"}, timeout=60)
        
        if not response.ok:
            logger.error(f"API Request Failed! Status: {response.status_code}")
            logger.error(f"Headers: {dict(response.headers)}")
            logger.error(f"Body snippet: {response.text[:500]}")
            sys.exit(1)

        data = response.json()
        
        # OData standard puts results in the 'value' key
        documents = data.get("value", [])

        if not documents:
            logger.warning("No authorised documents were returned by the API.")
            return

        # Double-check count and save
        count = len(documents)
        logger.info(f"Successfully retrieved {count} authorised documents.")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)
            
        logger.info(f"SUCCESS: Data saved to {OUTPUT_FILE}.")

    except Exception as e:
        logger.critical(f"A non-recoverable error occurred: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    fetch_frl_data()
