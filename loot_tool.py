from collections import defaultdict
import glob
import json
import os
import sys
import time
import urllib.parse

import gw2.api
import gw2.items
import gw2.recipes
import gw2.trading_post

from loot_tool_models import *

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
GW2_SNAPSHOT_DATA_DIR = os.path.join(GW2_DATA_DIR, "snapshots")
GW2_DIFF_DATA_DIR = os.path.join(GW2_DATA_DIR, 'diffs')
GW2_LOOT_BAG_FILE = os.path.join(GW2_DATA_DIR, 'loot_bags.txt')

def get_inventory(char_name):
    return gw2.api.fetch('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))

def get_materials():
    return gw2.api.fetch('/v2/account/materials')

def get_bank():
    return gw2.api.fetch('/v2/account/bank')

def get_wallet():
    return gw2.api.fetch('/v2/account/wallet')

def get_character_core(char_name):
    return gw2.api.fetch('/v2/characters/%s/core' %
            urllib.parse.quote(char_name))

def snapshot_from_file(file_path):
    with open(file_path) as f:
        text = f.read()
        data_snapshot_dict = json.loads(text)
    return DataSnapshot(**data_snapshot_dict)

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

    for bag in inventory2['bags']:
        if bag is None:
            continue
        for item in bag['inventory']:
            if item is None:
                continue
            items_diff[item['id']] += item['count']
    
    for item in materials2:
        if item is None:
            continue
        items_diff[item['id']] += item['count']

    for item in bank2:
        if item is None:
            continue
        items_diff[item['id']] += item['count']

    for bag in inventory1['bags']:
        if bag is None:
            continue
        for item in bag['inventory']:
            if item is None:
                continue
            items_diff[item['id']] -= item['count']
    
    for item in materials1:
        if item is None:
            continue
        items_diff[item['id']] -= item['count']

    for item in bank1:
        if item is None:
            continue
        items_diff[item['id']] -= item['count']

    final_items_diff = { item_id: value for item_id, value in items_diff.items() if value != 0 }
    return final_items_diff

def compute_diff(snapshot1, snapshot2):
    wallet_diff = diff_wallet(snapshot1.wallet, snapshot2.wallet)
    item_diff = diff_items(snapshot1.inventory, snapshot1.materials, snapshot1.bank, snapshot2.inventory, snapshot2.materials, snapshot2.bank)

    return DataDiff(time.time(), snapshot1.char_name, wallet_diff, item_diff)

def data_diff_from_file(file_path) -> DataDiff:
    with open(file_path) as f:
        text = f.read()
        data_diff_dict = json.loads(text)
    return DataDiff(**data_diff_dict)

def extract_source_item(data_diff: DataDiff):
    source_found = False
    for item in data_diff.item_diff:
        item_id = int(item)
        quantity = data_diff.item_diff.get(item)
        if quantity < 0:
            if source_found:
                raise Exception('Multiple source items detected in diff')
            source_found = True
            source_item = item_id
            source_quantity = quantity * -1
    
    if not source_found:
        raise Exception('No source item detected in diff')
    return source_item, source_quantity

def loot_table_from_data_diff(data_diff: DataDiff):
    source_item, source_quantity = extract_source_item(data_diff)

    item_drop_info_list = []
    for item in data_diff.item_diff:
        item_id = int(item)
        if(item_id == source_item):
            continue

        quantity = data_diff.item_diff.get(item)
        drop_rate = quantity / source_quantity
        item_drop_info_list.append(DropInfo(item_id, quantity, drop_rate))
    item_drop_info_list.sort(key = lambda x: x.drop_rate, reverse=True)

    wallet_drop_info_list = []
    for currency in data_diff.wallet_diff:
        currency_id = int(currency)
        quantity = data_diff.wallet_diff.get(currency)
        drop_rate = quantity / source_quantity
        wallet_drop_info_list.append(DropInfo(currency_id, quantity, drop_rate))
    
    return LootTable(data_diff.timestamp, source_item, source_quantity, item_drop_info_list, wallet_drop_info_list)

def cmd_get_inventory(char_name):
    inventory = get_inventory(char_name)
    for bag in inventory['bags']:
            if bag is None:
                continue
            for item in bag['inventory']:
                if item is None or item['count'] == 0:
                    continue
                print(gw2.items.name(item['id']), '-', item['count'])
    return

def cmd_print_help():
    help_string = '''
    Command - Defition
    help - prints this documentation
    inventory <char_name> - lists inventory of <char name>. Helper to see what info the snapshot command would fetch
    container_list - writes list of purchasable containers to ../gw2-data/loot_bags.txt
    snapshot <char_name> <magic_find> - creates a snapshot of char_name including inventory, materials, bank, wallet, and profession. This is all written to the ../gw2-data/snapshots/ directory
    diff <file_path_to_snapshot_1> <file_path_to_snapshot_2> - takes a diff of two snapshots (snapshot2 - snapshot1) and writes the diff to the ../gw2-data/snapshot/ directory
    gen_loot_tables - prints the loot tables from all of the snapshots from ../gw2-data/snapshots/ directory
    gen_worth_tables - prints the worth tables of the loot tables from all of the snapshots from ../gw2-data/snapshots/ directory
    '''
    print(help_string)
    return

def cmd_container_list():
    all_items = gw2.items.iter_all()
    container_items = [item for item in all_items if item['type'] == 'Container']
    

    container_items_ids = [t['id'] for t in container_items]
    non_craftable_item_ids = [id for id in container_items_ids if not gw2.recipes.search_output(id)]

    item_prices = gw2.trading_post.get_prices_multi(non_craftable_item_ids)

    loot_bags = []
    for ip in item_prices:
        if ip == None: 
            continue
        ip_buys = ip['buys']
        if ip_buys == None:
            ip_buys['price'] = 0
            ip_buys['quantity'] = 0
        loot_bag = LootBag(gw2.items.name(ip['id']), ip_buys['unit_price'], ip_buys['quantity'], ip['id'])
        loot_bags.append(loot_bag)

    print('Total containers: ', len(container_items))
    print('Total non craftable containers: ', len(non_craftable_item_ids))
    print('Total semi-buyable non craftable containers: ', len(loot_bags))

    loot_bags.sort(key=lambda x: x.price)
    data = [lb for lb in loot_bags]
    with open(GW2_LOOT_BAG_FILE, 'w') as f:
        json.dump(loot_bags, f, default=vars)
    print('Data written to file: ', GW2_LOOT_BAG_FILE)

def cmd_take_snapshot(char_name, char_magic_find):
    char_inventory = get_inventory(char_name)
    char_materials = get_materials()
    char_bank = get_bank()
    char_wallet = get_wallet()
    char_core = get_character_core(char_name)

    timestamp = time.time()
    data = DataSnapshot(timestamp, char_name, char_inventory, char_materials, char_bank, char_wallet, char_core, char_magic_find)

    data_file_name = str(int(timestamp)) + '.json'
    data_file = os.path.join(GW2_SNAPSHOT_DATA_DIR, data_file_name)

    with open(data_file, 'w') as f:
        json.dump(data, f, default=vars)
    print()
    print('Data written to: ', data_file)
    return

def cmd_take_diff(snapshot1_file, snapshot2_file):
    snapshot1 = snapshot_from_file(snapshot1_file)
    snapshot2 = snapshot_from_file(snapshot2_file)
    
    if not is_valid_comparison(snapshot1, snapshot2):
        print('These files are not comparable. Check character name, level, magic find%....')
        return
    
    diff_file_name = '-'.join(['diff', str(int(snapshot1.timestamp)), str(int(snapshot2.timestamp))]) + '.json'
    diff_file = os.path.join(GW2_DIFF_DATA_DIR, diff_file_name)

    diff_data = compute_diff(snapshot1, snapshot2)

    with open(diff_file, 'w') as f:
        json.dump(diff_data, f, default=vars)
    print()
    print('Data written to: ', diff_file)
    return

def cmd_gen_loot_tables():
    diffs_paths = os.path.join(GW2_DIFF_DATA_DIR, 'diff-*.json')
    diff_files = glob.glob(diffs_paths)

    loot_tables = []
    for diff_file in diff_files:
        data_diff = data_diff_from_file(diff_file)
        loot_table = loot_table_from_data_diff(data_diff)
        loot_tables.append(loot_table)
        
    return loot_tables

def print_worth_table(loot_table: LootTable):
    source_item = gw2.items.get(loot_table.source_item_id)
    print('Worth Table For: ', source_item['name'], '-----------')
    print('Data from: ', loot_table.source_item_quantity, ' opens')
    source_price = gw2.trading_post.get_prices(source_item['id'])['buys']['unit_price'] + 1

    total_worth = 0
    print()
    print('Currency Drops:')
    # translate currency names later
    for currency in loot_table.wallet_drop_info_list:
        if(currency.id == 1):
            print(currency.id, '(copper) - ', currency.drop_rate)
            total_worth += currency.drop_rate
        else:
            print(currency.id, '(todo) - ', currency.drop_rate)
    
    print()
    print('Item Drops:')
    print("{:<30} {:<9} {:<15} {:<15}".format('Item Name','Drop Rate','Unit Price', 'Net Price'))
    for item in loot_table.item_drop_info_list:
        dropped_item = gw2.items.get(item.id)
        dropped_item_drop_rate = item.drop_rate
        dropped_item_unit_price = 0
        try:
            dropped_item_unit_price = gw2.trading_post.get_prices(dropped_item['id'])['buys']['unit_price']
        except:
            pass
        dropped_item_net_price = dropped_item_unit_price * dropped_item_drop_rate
        total_worth += dropped_item_net_price
        print("{:<30} {:<9.3f} {:<15.3f} {:<15.3f}".format(
            dropped_item['name'],
            dropped_item_drop_rate,
            dropped_item_unit_price,
            dropped_item_net_price))

    print()
    print('Cost: ', source_price)
    print('Total value: ', total_worth)
    print('Buy then instant sell ROI: ', ((total_worth / source_price) - 1) * 100, '%')
    return

def cmd_gen_worth_tables():
    loot_tables = cmd_gen_loot_tables()
    
    for loot_table in loot_tables:
        print_worth_table(loot_table)
        print('\n\n\n')

    return

def main():
    ''' A tool with several commands to help with data collection of loot. 
    '''
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'help':
        assert len(args) == 0
        cmd_print_help()
    elif cmd == 'inventory':
        name, = args
        cmd_get_inventory(name)
    elif cmd == 'container_list':
        assert len(args) == 0
        cmd_container_list()
    elif cmd == 'snapshot':
        char_name, char_magic_find = args
        cmd_take_snapshot(char_name, char_magic_find)
    elif cmd == 'diff':
        snapshot1_file, snapshot2_file = args
        cmd_take_diff(snapshot1_file, snapshot2_file)
    elif cmd == 'gen_loot_tables':
        assert len(args) == 0
        cmd_gen_loot_tables()
    elif cmd == 'gen_worth_tables':
        assert len(args) == 0
        cmd_gen_worth_tables()
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()