import requests
import json
import time
from datetime import datetime, timedelta

# This is the hostname that we see in the grafana URL
GRAFANA_URL = "https://grafana.e6data.cloud"

# Paste your full cookie: "grafana_session=xxx; grafana_session_expiry=xxx", get it by opening developer tools, netwrok tab, open any succeeded query... request, get cookie in request headers 
BROWSER_COOKIE = "grafana_session=e1e1609f063f32569506d65e15756fd6; grafana_session_expiry=1773895576"

# Get UID from grafana link, there will be one field called datasource in URL, paste the value below.
LOKI_UID = "b9831d5e-622d-4a07-acf3-e7b91edf6116"

# Your LogQL query
LOGQL_QUERY = '{alias="freshworks",component="planner",workspace="analytics-us-pre-prod",cluster="soak-test-web-cs"}'

# --- TIME RANGE SETUP ---
# Add start time here, format is: (Start: 2026-03-18 16:51:50)
start_dt = datetime(2026, 3, 18, 16, 51, 50)

# Add end time here, format is: (End: 2026-03-19 1:35:59)
end_dt = datetime(2026, 3, 19, 1, 35, 59)

# Since grafana allows only 5000 rows at max, try to fetch logs for smaller window, reduce it if limit of 5000 lines is reached
WINDOW_SIZE_MINUTES = 5 # Smaller windows prevent hitting result limits

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