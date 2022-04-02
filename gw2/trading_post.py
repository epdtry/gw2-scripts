from collections import defaultdict
import functools
import json
import os
import requests
import time

from gw2.api import fetch, fetch_paginated
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


def get_listings_multi(item_ids):
    dct = {}
    query_ids = []
    for item_id in item_ids:
        query_ids.append(item_id)
    query_ids = sorted(set(query_ids))

    N = 30
    for i in range(0, len(query_ids), N):
        chunk = query_ids[i : i + N]
        items = []
        try:
            items = fetch('/v2/commerce/listings?ids=' + ','.join(str(x) for x in chunk))
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        for item in items:
            dct[item['id']] = item

    out = []
    for item_id in item_ids:
        out.append(dct.get(item_id))
    return out


def _update_history(kind):
    '''Update the transaction history for `kind`, which must be either `'buys'`
    or `'sells'`.  Returns the `DataStorage` object containing all the
    transactions and a dict mapping item IDs to total quantity bought/sold.'''

    os.makedirs(TRADING_POST_DIR, exist_ok=True)
    index_file = os.path.join(TRADING_POST_DIR, 'history_%s_index.json' % kind)
    data_file = os.path.join(TRADING_POST_DIR, 'history_%s_data.json' % kind)
    data = DataStorage(index_file, data_file)

    totals_file = os.path.join(TRADING_POST_DIR, 'history_%s_totals.json' % kind)
    if os.path.exists(totals_file):
        with open(totals_file) as f:
            totals = defaultdict(int)
            totals.update(dict(json.load(f)))
    else:
        totals = None

    updated_totals = False
    for page in fetch_paginated('/v2/commerce/transactions/history/%s' % kind):
        done = False
        for tx in page:
            if data.contains(tx['id']):
                done = True
                break

            data.add(tx['id'], tx)
            if totals is not None:
                totals[tx['item_id']] += tx['quantity']
                updated_totals = True

        if done:
            break

    if totals is None:
        totals = defaultdict(int)
        for tx in data.iter():
            totals[tx['item_id']] += tx['quantity']
        updated_totals = True

    if updated_totals:
        with open(totals_file, 'w') as f:
            json.dump(list(totals.items()), f)

    return data, totals

@functools.lru_cache(2)
def _get_history(kind):
    return _update_history(kind)

def total_bought():
    return _get_history('buys')[1]

def total_sold():
    return _get_history('sells')[1]


@functools.lru_cache(2)
def _fetch_current(kind):
    '''Fetch all current transactions for `kind`, which must be either `'buys'`
    or `'sells'`.  Returns a dict mapping item IDs to total quantity across all
    pending transactions.'''
    transactions = []
    counts = defaultdict(int)
    for page in fetch_paginated('/v2/commerce/transactions/current/%s' % kind):
        for tx in page:
            counts[tx['item_id']] += tx['quantity']
        transactions.extend(page)

    return transactions, counts

def pending_buys():
    return _fetch_current('buys')

def pending_sells():
    return _fetch_current('sells')
