import json
import requests
import sys

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