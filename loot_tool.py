import json
import os
import sys
import time
import urllib.parse

import gw2.api
import gw2.items
import gw2.recipes
import gw2.mystic_forge
import gw2.trading_post

import DataSnapshot
from loot_tool_models import *

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
GW2_SNAPSHOT_DATA_DIR = os.path.join(GW2_DATA_DIR, "snapshots")
LOOT_BAG_FILE = os.path.join(GW2_DATA_DIR, 'loot_bags.txt')

def cmd_get_inventory(char_name):
    inventory = gw2.api.fetch('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))
    print(inventory)
    return

def cmd_print_help():
    help_string = '''
    Command - Defition
    help - this
    inventory <char name> - lists inventory of <char name>
    container_list - writes list of purchasable containers to ../gw-data/loot_bags.txt
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
    with open(LOOT_BAG_FILE, 'w') as f:
        json.dump(loot_bags, f, default=vars)
    print('Data written to file: ', LOOT_BAG_FILE)



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
    elif cmd == 'goal':
        count, name = args
        cmd_goal(count, name)
    elif cmd == 'craft_profit_buy':
        assert len(args) == 0
        cmd_craft_profit_buy()
    else:
        raise ValueError('unknown command %r' % cmd)
    


if __name__ == '__main__':
    main()