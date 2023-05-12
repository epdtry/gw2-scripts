import json
import requests
import sys
import time

API_BASE = 'https://www.gw2bltc.com/api/tp/chart/'

def _fetch_req(item_id):
    headers = {
            'accept': 'application/json',
            }
    url = API_BASE + str(item_id)
    print('fetch ' + url, file=sys.stderr)
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r

def fetch(item_id):
    data = _fetch_req(item_id).json()
    return data

def fetch_with_retries(item_id, retry_count=2, seconds_between_retries=1):
    retries=0
    while retries < retry_count:
        try:
            response = fetch(item_id)
            break
        except requests.HTTPError as e:
            if e.response.status_code >= 400 and e.response.status_code < 500:
                print(f"HTTP {e.response.status_code} Error On Client Side for item_id: {item_id}")
                return None
            retries += 1
            time.sleep(seconds_between_retries)
            print('Error fetching path. Retry: ', retries)
    if retries >= retry_count:
        raise Exception('FetchWithRetryFailure')

    return response