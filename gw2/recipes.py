from collections import defaultdict
import functools
import json
import os
import requests
import time

from gw2.api import fetch
from gw2.constants import STORAGE_DIR
import gw2.build

RECIPES_DIR = os.path.join(STORAGE_DIR, 'recipes')
BUILD_FILE = os.path.join(RECIPES_DIR, 'build.txt')
INDEX_FILE = os.path.join(RECIPES_DIR, 'index.json')
DATA_FILE = os.path.join(RECIPES_DIR, 'data.json')

def _load_dict(path):
    with open(INDEX_FILE) as f:
        dct = {}
        for k,v in json.load(f):
            dct[k] = v
        return dct

_INDEX = None
def _get_index():
    global _INDEX
    if _INDEX is None:
        _refresh_if_needed()
        _INDEX = _load_dict(INDEX_FILE)
    return _INDEX

def _refresh():
    os.makedirs(RECIPES_DIR, exist_ok=True)

    all_ids = fetch('/v2/recipes')
    all_ids.sort()

    index = {}
    with open(DATA_FILE, 'wb') as data_file:
        pos = 0
        N = 100
        for i in range(0, len(all_ids), N):
            chunk = all_ids[i : i + N]
            recipes = fetch('/v2/recipes?ids=' + ','.join(str(i) for i in chunk))
            for r in recipes:
                index[r['id']] = pos
                s = json.dumps(r).encode('utf-8') + b'\n'
                data_file.write(s)
                pos += len(s)

    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f)

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))

def _refresh_if_needed():
    if gw2.build.need_refresh(BUILD_FILE):
        _refresh()

@functools.lru_cache(256)
def get(recipe_id):
    pos = _get_index()[recipe_id]
    with open(DATA_FILE) as f:
        f.seek(pos)
        return json.loads(f.readline())

def iter():
    _refresh_if_needed()
    with open(DATA_FILE) as f:
        for line in f:
            yield json.loads(line)

_BY_OUTPUT = None
def _by_output():
    global _BY_OUTPUT
    if _BY_OUTPUT is None:
        dct = defaultdict(list)
        for r in iter():
            output_item_id = r.get('output_item_id')
            if output_item_id is not None:
                dct[output_item_id].append(r['id'])
        _BY_OUTPUT = dict(dct)
    return _BY_OUTPUT

def search_output(output_item_id):
    return _by_output().get(output_item_id, [])


