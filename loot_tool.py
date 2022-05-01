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

def cmd_get_inventory(char_name):
    inventory = get_inventory(char_name)
    print(inventory)
    return

def cmd_print_help():
    help_string = '''
    Command - Defition
    help - prints this documentation
    inventory <char_name> - lists inventory of <char name>
    container_list - writes list of purchasable containers to ../gw2-data/loot_bags.txt
    snapshot <char_name> <magic_find> - creates a snapshot of char_name including inventory, materials, bank, wallet, and profession. This is all written to the ../gw2-data/snapshots/ directory
    diff - todo
    todomore
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
    else:
        raise ValueError('unknown command %r' % cmd)
    


if __name__ == '__main__':
    main()