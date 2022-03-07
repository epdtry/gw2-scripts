from collections import defaultdict
import functools
import json
import os
import requests
import time

from gw2.api import fetch
from gw2.constants import STORAGE_DIR
import gw2.build
from gw2.util import DataStorage

TRADING_POST_DIR = os.path.join(STORAGE_DIR, 'trading_post')
INDEX_FILE = os.path.join(TRADING_POST_DIR, 'index.json')
DATA_FILE = os.path.join(TRADING_POST_DIR, 'data.json')

_DATA = None
def _get_data():
    global _DATA
    if _DATA is None:
        os.makedirs(TRADING_POST_DIR, exist_ok=True)
        _DATA = DataStorage(INDEX_FILE, DATA_FILE)
    return _DATA

@functools.lru_cache(256)
def get_prices(item_id):
    data = _get_data()
    if not data.contains(item_id):
        item = fetch('/v2/commerce/prices?id=%d' % item_id)
        data.add(item_id, item)
        return item
    else:
        return data.get(item_id)

def get_prices_multi(item_ids):
    data = _get_data()
    
    dct = {}
    query_ids = []
    for item_id in item_ids:
        if data.contains(item_id):
            dct[item_id] = data.get(item_id)
        else:
            query_ids.append(item_id)
    query_ids = sorted(set(query_ids))
    
    N = 100
    for i in range(0, len(query_ids), N):
        chunk = query_ids[i : i + N]
        items = []
        try:
            items = fetch('/v2/commerce/prices?ids=' + ','.join(str(x) for x in chunk))
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        for item in items:
            data.add(item['id'], item)
            dct[item['id']] = item

    out = []
    for item_id in item_ids:
        if item_id not in dct:
            # Record that this item was not available from the API.
            data.add(item_id, None)
        out.append(dct.get(item_id))
    return out
