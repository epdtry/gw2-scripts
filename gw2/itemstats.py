from collections import defaultdict
import functools
import json
import os

from gw2.api import fetch_with_retries
from gw2.constants import STORAGE_DIR
import gw2.build
from gw2.util import DataStorage

ITEMSTATS_DIR = os.path.join(STORAGE_DIR, 'itemstats')
BUILD_FILE = os.path.join(ITEMSTATS_DIR, 'build.txt')
INDEX_FILE = os.path.join(ITEMSTATS_DIR, 'index.json')
DATA_FILE = os.path.join(ITEMSTATS_DIR, 'data.json')

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
    os.makedirs(ITEMSTATS_DIR, exist_ok=True)
    with open(INDEX_FILE, 'w'):
        pass
    with open(DATA_FILE, 'w'):
        pass

    data = DataStorage(INDEX_FILE, DATA_FILE)

    all_ids = fetch_with_retries('/v2/itemstats')
    all_ids.sort()

    N = 100
    for i in range(0, len(all_ids), N):
        chunk = all_ids[i : i + N]
        itemstats = fetch_with_retries('/v2/itemstats?ids=' + ','.join(str(i) for i in chunk))
        for itemstat in itemstats:
            data.add(itemstat['id'], itemstat)

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))

    return data

@functools.lru_cache(256)
def get(itemstat_id):
    return _get_data().get(itemstat_id)

def iter_all():
    data = _get_data()
    return (data.get(k) for k in data.keys())

