import json
import os
import requests
import sys

API_BASE = 'https://api.guildwars2.com'
API_KEY = None
CACHE_DIR = None

def fetch(path, cache=True):
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
