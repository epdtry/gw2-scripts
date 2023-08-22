import json
import os
import requests
import sys
import time

API_BASE = 'https://api.guildwars2.com'
API_VERSION = '2022-03-09T02:00:00.000Z'
API_KEY = None
CACHE_DIR = None

OFFLINE = bool(int(os.environ.get('GW2_API_OFFLINE') or 0))

def _fetch_req(path):
    assert not OFFLINE
    headers = {
            'X-Schema-Version': API_VERSION,
            }
    if API_KEY is not None:
        headers['Authorization'] = 'Bearer ' + API_KEY
    url = API_BASE + path
    print('fetch ' + url, file=sys.stderr)
    #r = requests.get(url, headers=headers)
    for i in range(20):
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            break
        except requests.HTTPError as e:
            print('Error fetching path: %s (retry: %d)' % (e, i))
            time.sleep(i + 1)
    return r

def fetch(path, cache=False):
    if cache and CACHE_DIR is not None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_key = path.replace('/', '__')
        cache_path = os.path.join(CACHE_DIR, cache_key)
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return json.load(f)

    j = _fetch_req(path).json()

    if cache and CACHE_DIR is not None:
        with open(cache_path, 'w') as f:
            json.dump(j, f)

    return j

def fetch_with_retries(path, retry_count=3, seconds_between_retries=2, cache=False):
    return fetch(path, cache=cache)

def fetch_paginated(path):
    '''Fetch all pages of a paginated resource.  This is a generator that
    yields each page in sequence, so the caller can break out of the loop to
    stop fetching pages early.'''
    r = _fetch_req(path)
    yield r.json()

    num_pages = int(r.headers.get('X-Page-Total', 0))
    next_page = 1
    while next_page < num_pages:
        r = _fetch_req(path + '?page=%d' % next_page)
        yield r.json()
        num_pages = int(r.headers.get('X-Page-Total', 0))
        next_page += 1
