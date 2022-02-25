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

RECIPES_DIR = os.path.join(STORAGE_DIR, 'recipes')
BUILD_FILE = os.path.join(RECIPES_DIR, 'build.txt')
INDEX_FILE = os.path.join(RECIPES_DIR, 'index.json')
DATA_FILE = os.path.join(RECIPES_DIR, 'data.json')

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
    os.makedirs(RECIPES_DIR, exist_ok=True)
    with open(INDEX_FILE, 'w'):
        pass
    with open(DATA_FILE, 'w'):
        pass

    data = DataStorage(INDEX_FILE, DATA_FILE)

    all_ids = fetch('/v2/recipes')
    all_ids.sort()

    pos = 0
    N = 100
    for i in range(0, len(all_ids), N):
        chunk = all_ids[i : i + N]
        recipes = fetch('/v2/recipes?ids=' + ','.join(str(i) for i in chunk))
        for r in recipes:
            data.add(r['id'], r)

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))

    return data

@functools.lru_cache(256)
def get(recipe_id):
    return _get_data().get(recipe_id)

def iter_all():
    data = _get_data()
    return (data.get(k) for k in data.keys())

_BY_OUTPUT = None
def _by_output():
    global _BY_OUTPUT
    if _BY_OUTPUT is None:
        dct = defaultdict(list)
        for r in iter_all():
            output_item_id = r.get('output_item_id')
            if output_item_id is not None:
                dct[output_item_id].append(r['id'])
        _BY_OUTPUT = dict(dct)
    return _BY_OUTPUT

def search_output(output_item_id):
    return _by_output().get(output_item_id, [])


