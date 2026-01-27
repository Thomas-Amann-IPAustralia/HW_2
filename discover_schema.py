import requests
import json
import sys

BASE_URL = "https://api.prod.legislation.gov.au/v1/documents"

def discover():
    print("--- STARTING SCHEMA DISCOVERY ---")
    params = {"$top": 3}  # Just 3 items to keep logs clean
    headers = {"accept": "application/json"}
    
    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Determine if it's a list or a dict with a 'value' key
        items = data.get("value", []) if isinstance(data, dict) else data
        
        if not items:
            print("CRITICAL: No items found in response.")
            print(f"Full Response: {json.dumps(data, indent=2)}")
            return

        print(f"SUCCESS: Retrieved {len(items)} items.")
        
        # 1. Show all keys
        print("\n[AVAILABLE FIELDS]")
        for key in sorted(items[0].keys()):
            print(f"- {key}")
            
        # 2. Show a full sample of one object
        print("\n[SAMPLE OBJECT DATA]")
        print(json.dumps(items[0], indent=2))
        
    except Exception as e:
        print(f"DISCOVERY FAILED: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Body: {e.response.text}")

if __name__ == "__main__":
    discover()
