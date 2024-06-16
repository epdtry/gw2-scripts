import os
import concurrent.futures
import time
import sys
from datetime import datetime, timedelta

import gw2.api
import gw2.recipes
import gw2.mystic_forge
import gw2.items
import gw2.trading_post

ASSUMED_ECTO_DROP_RATE = 0.75

def craftable_items():
    for r in gw2.recipes.iter_all():
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

    for r in gw2.mystic_forge.iter_all():
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

def get_prices(item_ids):
    sell_prices = {}

    for x in gw2.trading_post.get_prices_multi(item_ids):
        if x is None:
            continue

        # The trading post doesn't allow selling items at prices so low that
        # you would receive less than vendor price after taxes.
        item = gw2.items.get(x['id'])

        price = x['sells'].get('unit_price', 0) or x['buys'].get('unit_price', 0)
        if price != 0:
            sell_prices[x['id']] = price

    return sell_prices

def main():
    ''' A tool with several commands to help with data collection of loot. 
    '''
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    craftable_items_list = list(craftable_items())
    craftable_armor_items = []
    for item_id in craftable_items_list:
        item = gw2.items.get(item_id)
        if item['type'] == 'Armor' and item['rarity'] == 'Rare' and 'NoSalvage' not in item['flags']:
            craftable_armor_items.append(item)
    
    # print the number of craftable items
    print('Number of craftable items:', len(craftable_items_list))
    print('Number of craftable rare armor items:', len(craftable_armor_items))


if __name__ == '__main__':
    main()