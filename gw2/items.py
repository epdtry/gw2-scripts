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
        if gw2.build.need_refresh(BUILD_FILE):
            _DATA = _refresh()
        else:
            _DATA = DataStorage(INDEX_FILE, DATA_FILE)
    return _DATA

def _refresh():
    # Clear the index and data files.
    os.makedirs(ITEMS_DIR, exist_ok=True)
    with open(INDEX_FILE, 'w'):
        pass
    with open(DATA_FILE, 'w'):
        pass

    data = DataStorage(INDEX_FILE, DATA_FILE)

    all_ids = fetch('/v2/items')
    all_ids.sort()

    pos = 0
    N = 100
    for i in range(0, len(all_ids), N):
        chunk = all_ids[i : i + N]
        items = fetch('/v2/items?ids=' + ','.join(str(i) for i in chunk))
        for i in items:
            data.add(i['id'], i)

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))

    return data

@functools.lru_cache(256)
def get(item_id):
    return _get_data().get(item_id)

def iter_all():
    data = _get_data()
    return (data.get(k) for k in data.keys())

def get_multi(item_ids):
    return [get(i) for i in item_ids]

def name(item_id):
    return get(item_id)['name']
