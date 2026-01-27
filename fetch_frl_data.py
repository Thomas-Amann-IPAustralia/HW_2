import requests
import json
import logging
import sys

# --- CONFIGURATION ---
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
TARGET_ID = "C2024C00545"
OUTPUT_JSON = "legislation_metadata.json"
LOG_FILE = "download_log.txt"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FRL_Hunter")

def fetch_and_download():
    session = requests.Session()
    session.headers.update({"accept": "application/json"})
    
    log_entries = []

    try:
        # 1. Get Metadata
        params = {"$filter": f"registerId eq '{TARGET_ID}'"}
        response = session.get(BASE_URL, params=params)
        response.raise_for_status()
        items = response.json().get("value", [])

        if not items:
            msg = f"No metadata found for {TARGET_ID}"
            logger.error(msg)
            log_entries.append(msg)
        else:
            doc_metadata = items[0]
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(doc_metadata, f, indent=2)
            
            # 2. Try to find the file
            # If the ID C2024C00545 is a Register ID, the actual document ID 
            # might be different. Let's look for 'titleId'
            alt_id = doc_metadata.get("titleId", TARGET_ID)
            extension = doc_metadata.get("extension", ".pdf")
            
            # Try the three most common OData media patterns
            test_urls = [
                f"{BASE_URL}('{TARGET_ID}')/$value",
                f"{BASE_URL}('{alt_id}')/$value",
                f"https://api.prod.legislation.gov.au/v1/files('{TARGET_ID}')/content"
            ]

            success = False
            for url in test_urls:
                logger.info(f"Testing URL: {url}")
                try:
                    with session.get(url, stream=True, timeout=30) as r:
                        if r.status_code == 200:
                            filename = f"{TARGET_ID}{extension}"
                            with open(filename, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logger.info(f"SUCCESS: Downloaded {filename} from {url}")
                            log_entries.append(f"Successfully downloaded from {url}")
                            success = True
                            break
                        else:
                            log_entries.append(f"Failed {url} - Status {r.status_code}")
                except Exception as e:
                    log_entries.append(f"Error testing {url}: {str(e)}")

            if not success:
                logger.error("All download attempts failed.")

    except Exception as e:
        log_entries.append(f"Critical error: {str(e)}")

    # ALWAYS write a log file so the GitHub Action has something to commit
    with open(LOG_FILE, "w") as f:
        f.write("\n".join(log_entries))

if __name__ == "__main__":
    fetch_and_download()
