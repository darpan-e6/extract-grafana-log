import os
import requests
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GRAFANA_URL = os.environ["GRAFANA_URL"]
BROWSER_COOKIE = os.environ["BROWSER_COOKIE"]
LOKI_UID = os.environ["LOKI_UID"]
LOGQL_QUERY = os.environ["LOGQL_QUERY"]

start_dt = datetime.strptime(os.environ["START_TIME"], "%Y-%m-%d %H:%M:%S")
end_dt = datetime.strptime(os.environ["END_TIME"], "%Y-%m-%d %H:%M:%S")

# Since grafana allows only 5000 rows at max, try to fetch logs for smaller window, reduce it if limit of 5000 lines is reached
WINDOW_SIZE_MINUTES = int(os.environ.get("WINDOW_SIZE_MINUTES", 5))

def fetch_all_logs():
    current_start = start_dt
    output_file = "output/logs_from_grafana.log"
    
    # Clear file if it exists
    with open(output_file, "w") as f: pass 

    print(f"Starting export to {output_file}...")

    while current_start < end_dt:
        current_end = min(current_start + timedelta(minutes=WINDOW_SIZE_MINUTES), end_dt)
        
        # Convert to nanoseconds for Loki API
        start_ns = str(int(current_start.timestamp() * 1e9))
        end_ns = str(int(current_end.timestamp() * 1e9))

        # Using the direct Loki proxy endpoint often found in browser dev tools
        # Adjust 'uid/loki' if your specific environment uses a different UID
        endpoint = f"{GRAFANA_URL}/api/datasources/proxy/uid/{LOKI_UID}/loki/api/v1/query_range"
        
        headers = {"Cookie": BROWSER_COOKIE,
                   "X-Grafana-Org-Id": "1"}
        params = {
            "query": LOGQL_QUERY,
            "start": start_ns,
            "end": end_ns,
            "limit": 5000, # Standard safe limit
            "direction": "forward"
        }

        try:
            response = requests.get(endpoint, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', {}).get('result', [])
                
                with open(output_file, "a", encoding="utf-8") as f:
                    count = 0
                    for stream in results:
                        for _, line in stream.get('values', []):
                            f.write(f"{line}\n")
                            count += 1
                
                print(f"Saved {count} lines for window: {current_start} to {current_end}")
            else:
                print(f"Failed at {current_start}: {response.status_code} - {response.text}")
                # Optional: break if 401 (expired cookie)
                if response.status_code == 401: break

        except Exception as e:
            print(f"Error at {current_start}: {e}")

        # Move to next time window
        current_start = current_end
        time.sleep(0.5) # Polite delay to avoid rate-limiting

    print("Export complete.")

if __name__ == "__main__":
    fetch_all_logs()