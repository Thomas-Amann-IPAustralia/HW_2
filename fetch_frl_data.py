import requests
import json
import sys

# API Configuration
BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"
OUTPUT_FILE = "legislation_data.json"
# The API usually defaults to a specific page size; we'll use a standard batch
PAGE_SIZE = 1000 

def fetch_wholesale_data():
    all_documents = []
    skip = 0
    
    print("Starting wholesale fetch from FRL API...")
    
    while True:
        # FRL typically uses OData-style pagination ($top and $skip)
        params = {
            "$top": PAGE_SIZE,
            "$skip": skip
        }
        
        try:
            response = requests.get(BASE_URL, params=params, headers={"accept": "application/json"})
            response.raise_for_status()
            
            data = response.json()
            
            # The API might return a list directly or a wrapper object
            batch = data if isinstance(data, list) else data.get("items", [])
            
            if not batch:
                print("No more records found.")
                break
                
            all_documents.extend(batch)
            print(f"Fetched {len(all_documents)} records so far...")
            
            # If we received fewer records than requested, we've reached the end
            if len(batch) < PAGE_SIZE:
                break
                
            skip += PAGE_SIZE
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            sys.exit(1)

    # Save as a single JSON object
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, indent=2)
    
    print(f"Success! Total records saved: {len(all_documents)}")

if __name__ == "__main__":
    fetch_wholesale_data()
