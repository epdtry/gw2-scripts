from collections import defaultdict
import json
import os
import glob
import sys


import gw2.api
import gw2.items
import gw2.trading_post

from DataDiff import DataDiff, LootTable, DropInfo

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
GW2_DIFFS_DATA_DIR = os.path.join(GW2_DATA_DIR, 'diffs')

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


def cmd_gen_loot_tables():
    diffs_paths = os.path.join(GW2_DIFFS_DATA_DIR, 'diff-*.json')
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
    return

def cmd_gen_worth_tables():
    loot_tables = cmd_gen_loot_tables()
    
    for loot_table in loot_tables:
        print_worth_table(loot_table)
        print('\n\n\n')

    return

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'gen_loot_tables':
        assert len(args) == 0
        cmd_gen_loot_tables()
    elif cmd == 'gen_worth_tables':
        assert len(args) == 0
        cmd_gen_worth_tables()
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
