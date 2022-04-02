from collections import defaultdict
import functools
import json
import os

from gw2.api import fetch, fetch_with_retries
from gw2.constants import STORAGE_DIR
import gw2.build
from gw2.util import DataStorage

ITEMS_DIR = os.path.join(STORAGE_DIR, 'items')
BUILD_FILE = os.path.join(ITEMS_DIR, 'build.txt')
INDEX_FILE = os.path.join(ITEMS_DIR, 'index.json')
DATA_FILE = os.path.join(ITEMS_DIR, 'data.json')
BY_NAME_FILE = os.path.join(ITEMS_DIR, 'by_name.json')

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

    by_name = {}

    N = 100
    for i in range(0, len(all_ids), N):
        chunk = all_ids[i : i + N]
        items = fetch_with_retries('/v2/items?ids=' + ','.join(str(i) for i in chunk), retry_count=20)
        
        for i in items:
            data.add(i['id'], i)

            # Hack: omit legendary versions of runes/sigils, so that "Superior
            # Rune of Xyz" resolves to the exotic craftable version.
            if i['type'] == 'UpgradeComponent' \
                    and i['details']['type'] in ('Rune', 'Sigil') \
                    and i['rarity'] == 'Legendary':
                pass
            else:
                by_name[i['name']] = i['id']

    with open(BY_NAME_FILE, 'w') as f:
        json.dump(list(by_name.items()), f)

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))

    return data

@functools.lru_cache(256)
def get(item_id):
    return _get_data().get(item_id)

def is_known(item_id):
    return _get_data().contains(item_id)

def iter_all():
    data = _get_data()
    return (data.get(k) for k in data.keys())

def get_multi(item_ids):
    return [get(i) for i in item_ids]

def name(item_id):
    return get(item_id)['name']

_BY_NAME = None
def _by_name():
    global _BY_NAME
    if _BY_NAME is None:
        _get_data()
        with open(BY_NAME_FILE) as f:
            _BY_NAME = dict(json.load(f))
    return _BY_NAME

def search_name(name):
    return _by_name().get(name)
