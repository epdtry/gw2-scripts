import json
import os
import requests
import sys
import time

API_BASE = 'https://api.guildwars2.com'
API_KEY = None
CACHE_DIR = None

def fetch(path, cache=False):
    if cache and CACHE_DIR is not None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_key = path.replace('/', '__')
        cache_path = os.path.join(CACHE_DIR, cache_key)
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return json.load(f)

    headers = {}
    if API_KEY is not None:
        headers['Authorization'] = 'Bearer ' + API_KEY
    url = API_BASE + path
    print('fetch ' + url, file=sys.stderr)
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    j = r.json()

    if cache and CACHE_DIR is not None:
        with open(cache_path, 'w') as f:
            json.dump(j, f)

    return j

def fetch_with_retries(path, retry_count=3, seconds_between_retries=2, cache=False):
    retries=0
    while retries < retry_count:
        try:
            response = fetch(path, cache)
            break
        except requests.HTTPError as e:
            retries += 1
            time.sleep(seconds_between_retries)
            print('Error fetching path. Retry: ', retries)
    if retries >= retry_count:
        raise Exception('FetchWithRetryFailure')

    return response
