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

ITEMS_DIR = os.path.join(STORAGE_DIR, 'items')
BUILD_FILE = os.path.join(ITEMS_DIR, 'build.txt')
INDEX_FILE = os.path.join(ITEMS_DIR, 'index.json')
DATA_FILE = os.path.join(ITEMS_DIR, 'data.json')

_DATA = None
def _get_data():
    global _DATA
    if _DATA is None:
        _refresh_if_needed()
        _DATA = DataStorage(INDEX_FILE, DATA_FILE)
    return _DATA

def _refresh_if_needed():
    if gw2.build.need_refresh(BUILD_FILE):
        # Clear the index and data files.
        os.makedirs(ITEMS_DIR, exist_ok=True)
        with open(INDEX_FILE, 'w'):
            pass
        with open(DATA_FILE, 'w'):
            pass
        with open(BUILD_FILE, 'w') as f:
            f.write(str(gw2.build.current()))

@functools.lru_cache(256)
def get(item_id):
    data = _get_data()
    if not data.contains(item_id):
        item = fetch('/v2/items?id=%d' % item_id)
        data.add(item_id, item)
        return item
    else:
        return data.get(item_id)

def get_multi(item_ids):
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
        items = fetch('/v2/items?ids=' + ','.join(str(x) for x in chunk))
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

def name(item_id):
    return get(item_id)['name']
