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
BY_NAME_MULTI_FILE = os.path.join(ITEMS_DIR, 'by_name_multi.json')

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
    by_name_multi = defaultdict(list)

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
            # Hack: omit account-bound versions of certain soto items
            elif (i['name'] == 'Uncommon Kryptis Motivation' or i['type'] == 'Relic') \
                    and ('SoulbindOnAcquire' in i['flags']
                        or 'AccountBound' in i['flags']):
                pass
            else:
                by_name[i['name']] = i['id']
                by_name_multi[i['name']].append(i['id'])

    with open(BY_NAME_FILE, 'w') as f:
        json.dump(list(by_name.items()), f)

    with open(BY_NAME_MULTI_FILE, 'w') as f:
        json.dump(list(by_name_multi.items()), f)

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

_BY_NAME_MULTI = None
def _by_name_multi():
    global _BY_NAME_MULTI
    if _BY_NAME_MULTI is None:
        _get_data()
        with open(BY_NAME_MULTI_FILE) as f:
            _BY_NAME_MULTI = dict(json.load(f))
    return _BY_NAME_MULTI

def search_name(name, rarity=None, level=None, with_flags=None, without_flags=None,
        allow_multiple=None):
    if rarity is None and level is None and with_flags is None and without_flags is None and \
             allow_multiple is None:
        return _by_name().get(name)

    candidates = _by_name_multi().get(name)
    if candidates is None:
        return None
    candidates = [get(item_id) for item_id in candidates]

    if rarity is not None:
        candidates = [item for item in candidates
                if item['rarity'] == rarity]

    if level is not None:
        candidates = [item for item in candidates
                if item['level'] == level]

    if with_flags is not None:
        candidates = [item for item in candidates
                if all(flag in item['flags'] for flag in with_flags)]

    if without_flags is not None:
        candidates = [item for item in candidates
                if all(flag not in item['flags'] for flag in without_flags)]

    candidates = [item['id'] for item in candidates]
    if allow_multiple:
        return candidates
    if len(candidates) == 0:
        return None
    elif len(candidates) == 1:
        return candidates[0]
    else:
        raise ValueError('ambiguous lookup for %r, %r: %r' %
                (name, rarity, candidates))


AUGMENT_IDS_FILE = os.path.join(ITEMS_DIR, 'augment_ids.json')
# We assign ids starting at a high number, on the assumption that these won't
# collide with any real items.
AUGMENT_ID_BASE = 300000

def augment(names):
    if os.path.exists(AUGMENT_IDS_FILE):
        with open(AUGMENT_IDS_FILE) as f:
            augment_ids = json.load(f)
    else:
        augment_ids = {}
    assigned_ids = False

    aug_items = {}

    by_name = _by_name()
    by_name_multi = _by_name_multi()

    with open(AUGMENT_IDS_FILE, 'a') as f:
        for name in names:
            if name in by_name:
                continue

            aug_id = augment_ids.get(name)
            if aug_id is None:
                aug_id = len(augment_ids) + AUGMENT_ID_BASE
                augment_ids[name] = aug_id
                assigned_ids = True

            by_name[name] = aug_id
            by_name_multi[name] = [aug_id]
            aug_items[aug_id] = {
                    'id': aug_id,
                    'name': name,
                    'type': 'Fake',
                    'rarity': 'Basic',
                    'level': 0,
                    'vendor_value': 0,
                    'flags': [],
                    }

    _get_data().augment(aug_items)


    if assigned_ids:
        with open(AUGMENT_IDS_FILE, 'w') as f:
            json.dump(augment_ids, f)
