from collections import defaultdict
import json
import os
import sys
import time

import DataSnapshot
import DataDiff

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
GW2_DIFF_DATA_DIR = os.path.join(GW2_DATA_DIR, 'diffs')

def snapshot_from_file(file_path):
    with open(file_path) as f:
        text = f.read()
        data_snapshot_dict = json.loads(text)
    return DataSnapshot.DataSnapshot(**data_snapshot_dict)

def is_valid_comparison(snapshot1, snapshot2):
    if snapshot1.char_name != snapshot2.char_name:
        return False
    if snapshot1.magic_find != snapshot2.magic_find:
        return False
    if snapshot1.char_core['level'] != snapshot2.char_core['level']:
        return False
    if snapshot1.char_core['profession'] != snapshot2.char_core['profession']:
        return False
    return True

def diff_magic(magic1, magic2):
    return magic2 - magic1

def diff_wallet(wallet1, wallet2):
    wallet_diff = dict()

    wallet1_dict = dict((currency['id'], currency['value']) for currency in wallet1)
    wallet2_dict = dict((currency['id'], currency['value']) for currency in wallet2)

    wallet1_keys = wallet1_dict.keys()
    wallet2_keys = wallet2_dict.keys()
    all_keys = set().union(*[wallet1_keys, wallet2_keys])

    for currencyId in all_keys:
        wallet1_value = wallet1_dict.get(currencyId, 0)
        wallet2_value = wallet2_dict.get(currencyId, 0)
        diff_value = wallet2_value - wallet1_value
        if diff_value == 0:
            continue
        wallet_diff[currencyId] = diff_value

    return wallet_diff

def diff_items(inventory1, materials1, bank1, inventory2, materials2, bank2):
    items_diff = defaultdict(int)

    print()
    print("hey")
    print(inventory1)
    print()
    for bag in inventory1['bags']:
        print(bag)
        if bag is None:
            continue
        for item in bag['inventory']:
            if item is None or item['count'] == 0:
                continue
            items_diff[item['id']] += item['count']
    
    for item in materials1:
        if item is None or item['count'] == 0:
            continue
        items_diff[item['id']] += item['count']

    for item in bank1:
        if item is None or item['count'] == 0:
            continue
        items_diff[item['id']] += item['count']

    for bag in inventory2['bags']:
        if bag is None:
            continue
        for item in bag['inventory']:
            if item is None or item['count'] == 0:
                continue
            items_diff[item['id']] -= item['count']
    
    for item in materials2:
        if item is None or item['count'] == 0:
            continue
        items_diff[item['id']] -= item['count']

    for item in bank2:
        if item is None or item['count'] == 0:
            continue
        items_diff[item['id']] -= item['count']

    final_items_diff = { item_id: value for item_id, value in items_diff.items() if value != 0 }
    return final_items_diff



def compute_diff(snapshot1, snapshot2):
    wallet_diff = diff_wallet(snapshot1.wallet, snapshot2.wallet)

    item_diff = diff_items(snapshot1.inventory, snapshot1.materials, snapshot1.bank, snapshot2.inventory, snapshot2.materials, snapshot2.bank)
    print(item_diff)

    return DataDiff.DataDiff(time.time(), snapshot1.char_name, wallet_diff, item_diff)

def main():
    ''' Generates a diff given 2 files of snapshot data Invoke with:
        `python snapshot_diff <path_to_snapshot1> <path_to_snapshot2>`
    '''
    snapshot1_file = sys.argv[1]
    snapshot2_file = sys.argv[2]

    snapshot1 = snapshot_from_file(snapshot1_file)
    snapshot2 = snapshot_from_file(snapshot2_file)
    
    if not is_valid_comparison(snapshot1, snapshot2):
        print('These files are not comparable. Check character name, level, magic find%....')
        return
    
    diff_file_name = '-'.join(['diff', str(snapshot1.timestamp), str(snapshot2.timestamp)]) + '.json'
    diff_file = os.path.join(GW2_DIFF_DATA_DIR, diff_file_name)

    diff_data = compute_diff(snapshot1, snapshot2)

    with open(diff_file, 'w') as f:
        json.dump(diff_data, f, default=vars)
    print()
    print('Data written to: ', diff_file)

if __name__ == '__main__':
    main()