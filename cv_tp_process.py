from collections import defaultdict
import json
from pprint import pprint
import os
import sys

STORAGE_DIR = 'storage/cv_tp_prices'
os.makedirs(STORAGE_DIR, exist_ok = True)
MTIMES_FILE = os.path.join(STORAGE_DIR, 'mtimes.json')
PRICES_FILE = os.path.join(STORAGE_DIR, 'prices.json')

def load_dict(path):
    if os.path.exists(path):
        return dict(json.load(open(path)))
    else:
        return {}

def save_dict(dct, path):
    with open(path, 'w') as f:
        json.dump(sorted(dct.items()), f)

def process(path):
    '''Load observed states from `path` and extract the price data.  Returns a
    map from item name (string) to a dict containing keys `buy` (price),
    `buy_time` (last timestamp when that price was observed), `sell`, and
    `sell_time`.
    '''
    # Price events, sorted by name.  This is a map from item name (string) to a
    # list of entries; each entry is a dict containing `price`, `start_time`,
    # and `end_time`.
    by_name = {}

    def record(name, price, kind, start_time, end_time):
        '''Record that we observed `price` for item `name` from `start_time`
        until `end_time`.'''
        extend = None
        if name not in by_name:
            by_name[name] = []
        else:
            last = by_name[name][-1]
            if last['price'] == price and last['end_time'] == start_time \
                    and last['kind'] == kind:
                extend = last

        if extend is None:
            # Add a new entry.
            by_name[name].append({
                'price': price,
                'kind': kind,
                'start_time': start_time,
                'end_time': end_time,
            })
        else:
            # Extend the `end_time` of the existing entry.
            extend['end_time'] = end_time

    def record_state(s, start_time, end_time):
        '''Process state `s`, which was in effect from `start_time` until
        `end_time`.'''
        prices = s.get('prices')
        if prices is None:
            return
        # The buy tab shows the current sell price and vice versa.
        if s['tab'] == 'buy':
            kind = 'sell'
        elif s['tab'] == 'sell':
            kind = 'buy'
        else:
            return
        for (name, price) in prices:
            record(name, price, kind, start_time, end_time)

    timestamp = None
    state = None

    for line in open(path):
        next_timestamp, next_state = json.loads(line)
        if timestamp is not None:
            record_state(state, timestamp, next_timestamp)
        timestamp, state = next_timestamp, next_state

    if state is not None:
        record_state(state, timestamp, timestamp + 1.0)

    result = {}
    for name, entries in by_name.items():
        if name not in result:
            result[name] = {}
        dct = result[name]
        for entry in reversed(entries):
            dur = entry['end_time'] - entry['start_time']
            if dur < 0.3:
                continue
            if entry['kind'] == 'buy':
                dct['buy'] = entry['price']
                dct['buy_time'] = entry['end_time']
                break
            elif entry['kind'] == 'sell':
                dct['sell'] = entry['price']
                dct['sell_time'] = entry['end_time']
                break
    return result

def add_item_prices(dct, new_prices):
    '''Add price data from `new_prices` into `dct`.'''
    for name, new in new_prices.items():
        if name not in dct:
            dct[name] = new
            continue
        old = dct[name]
        if 'buy_time' in new and (
                'buy_time' not in old or new['buy_time'] > old['buy_time']):
            old['buy'] = new['buy']
            old['buy_time'] = new['buy_time']
        if 'sell_time' in new and (
                'sell_time' not in old or new['sell_time'] > old['sell_time']):
            old['sell'] = new['sell']
            old['sell_time'] = new['sell_time']

def main():
    records_dir, = sys.argv[1:]
    records_dir = os.path.realpath(records_dir)

    mtimes = load_dict(MTIMES_FILE)
    prices = load_dict(PRICES_FILE)

    count = 0
    for f in sorted(os.listdir(records_dir)):
        file_path = os.path.join(records_dir, f)

        mtime = os.stat(file_path).st_mtime
        expect_mtime = mtimes.get(file_path)
        if expect_mtime is not None and expect_mtime == mtime:
            continue
        mtimes[file_path] = mtime

        print('process %s' % f)
        file_prices = process(file_path)
        add_item_prices(prices, file_prices)
        count += 1

    print('%d files processed (this run)' % count)
    print('%d files processed (all time)' % len(mtimes))
    print('%d known items' % len(prices))

    save_dict(mtimes, MTIMES_FILE)
    save_dict(prices, PRICES_FILE)


if __name__ == '__main__':
    main()
