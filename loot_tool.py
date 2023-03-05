from collections import defaultdict
import glob
import json
import os
import sys
import time
import urllib.parse
from typing import List

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

def loot_table_from_data_diff(data_diff: DataDiff) -> LootTable:
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

def cmd_gen_loot_tables() -> List[LootTable]:
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
            print(currency.quantity, '(copper)  ', currency.drop_rate, 'copper per container')
            total_worth += currency.drop_rate
        else:
            print(currency.id, '(todo) - ', currency.drop_rate)
    
    print()
    print('Item Drops:')
    print("{:<30} {:<11} {:<9} {:<15} {:<15}".format('Item Name','Total Count', 'Drop Rate','Unit Price', 'Net Price'))
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
        print("{:<30} {:<11} {:<9.3f} {:<15.3f} {:<15.3f}".format(
            dropped_item['name'],
            item.quantity,
            dropped_item_drop_rate,
            dropped_item_unit_price,
            dropped_item_net_price))

    print()
    print('Cost Per Bag: ', source_price)
    print('Total value: ', total_worth)
    print('Buy then instant sell ROI: ', ((total_worth / source_price) - 1) * 100, '%')
    return

def merge_drop_info_lists(drop_info_list_a, drop_info_list_b, source_item_quanity) -> List[DropInfo]:
    combined_drop_info_list = defaultdict(DropInfo)
    
    for drop_info_a in drop_info_list_a:
        combined_drop_info_list[drop_info_a.id] = DropInfo(drop_info_a.id, drop_info_a.quantity, drop_info_a.quantity / source_item_quanity)
    for drop_info_b in drop_info_list_b:
        if drop_info_b.id in combined_drop_info_list:
            combined_drop_info_list[drop_info_b.id].quantity += drop_info_b.quantity
            combined_drop_info_list[drop_info_b.id].drop_rate = combined_drop_info_list[drop_info_b.id].quantity / source_item_quanity
        else:
            combined_drop_info_list[drop_info_b.id] = DropInfo(drop_info_b.id, drop_info_b.quantity, drop_info_b.quantity / source_item_quanity)
    
    return [combined_drop_info_list[dropinfo] for dropinfo in combined_drop_info_list]


def merge_loot_tables(loot_table_a: LootTable, loot_table_b: LootTable) -> LootTable:
    if loot_table_a.source_item_id != loot_table_b.source_item_id:
        raise Exception('Cannot merge loot tables with different source items: ' + str(loot_table_a.source_item_id) + ' != ' + str(loot_table_b.source_item_id))

    source_item_id = loot_table_a.source_item_id
    if loot_table_a.timestamp < loot_table_b.timestamp:
        earliest_timestamp = loot_table_a.timestamp
    else: 
        earliest_timestamp = loot_table_b.timestamp
    source_item_quantity = loot_table_a.source_item_quantity + loot_table_b.source_item_quantity

    combined_item_list = merge_drop_info_lists(loot_table_a.item_drop_info_list, loot_table_b.item_drop_info_list, source_item_quantity)
    combined_currency_list = merge_drop_info_lists(loot_table_a.wallet_drop_info_list, loot_table_b.wallet_drop_info_list, source_item_quantity)

    combined_loot_table = LootTable(earliest_timestamp, source_item_id, source_item_quantity, combined_item_list, combined_currency_list)
    return combined_loot_table

def cmd_gen_worth_tables():
    loot_tables = cmd_gen_loot_tables()
    combined_table_dict = defaultdict(LootTable)

    for loot_table in loot_tables:
        if loot_table.source_item_id not in combined_table_dict:
            combined_table_dict[loot_table.source_item_id] = loot_table
        else:
            merged_loot_table = merge_loot_tables(combined_table_dict.get(loot_table.source_item_id), loot_table)
            combined_table_dict[loot_table.source_item_id] = merged_loot_table
    
    for loot_table in combined_table_dict:
        print_worth_table(combined_table_dict[loot_table])
        print('\n\n\n')
    
    return

def cmd_diff_to_text(diff_path, text_path):
    diff_file = open(diff_path, 'r') if diff_path is not None else sys.stdin
    diff = DataDiff(**json.load(diff_file))
    diff_file = None

    currencies_raw = gw2.api.fetch('/v2/currencies?ids=all')
    currency_name = {x['id']: x['name'] for x in currencies_raw}

    text_file = open(text_path, 'w') if text_path is not None else sys.stdout
    text_file.write('character %s\n' % (diff.char_name,))
    text_file.write('timestamp %f\n' % (diff.timestamp,))

    currency_entries = []
    for currency_id_str, count in diff.wallet_diff.items():
        currency_id = int(currency_id_str)
        currency_entries.append((currency_name[currency_id], count, currency_id))
    for name, count, currency_id in sorted(currency_entries):
        text_file.write('%+7d  c%-5d %s\n' % (count, currency_id, name))

    item_entries = []
    for item_id_str, count in diff.item_diff.items():
        item_id = int(item_id_str)
        item_entries.append((gw2.items.name(item_id), count, item_id))
    for name, count, item_id in sorted(item_entries):
        text_file.write('%+7d  %-5d %s\n' % (count, item_id, name))

def cmd_text_to_diff(text_path, diff_path):
    char_name = None
    timestamp = None
    wallet_diff = defaultdict(int)
    item_diff = defaultdict(int)

    text_file = open(text_path, 'r') if text_path is not None else sys.stdin
    for line in text_file:
        parts = line.strip().split()
        if len(parts) < 2 or parts[0].startswith('#'):
            print('skip: %r' % (line,))
            continue

        if parts[0] == 'character':
            char_name = parts[1]
            continue
        elif parts[0] == 'timestamp':
            timestamp = float(parts[1])
            continue

        count = int(parts[0])
        id_str = parts[1]
        if id_str.startswith('c'):
            wallet_diff[int(id_str[1:])] += count
        else:
            item_diff[int(id_str)] += count

    diff = DataDiff(
            char_name = char_name,
            timestamp = timestamp,
            wallet_diff = wallet_diff,
            item_diff = item_diff)

    diff_file = open(diff_path, 'w') if diff_path is not None else sys.stdout
    json.dump(diff, diff_file, default=vars)

ITEM_CRACKED_FRACTAL_ENCRYPTION = gw2.items.search_name('Cracked Fractal Encryption')
ITEM_FRACTAL_ENCRYPTION_KEY = gw2.items.search_name('Fractal Encryption Key')
ITEM_PLUS1_AGONY_INFUSION = gw2.items.search_name('+1 Agony Infusion')
ITEM_MINI_PROFESSOR_MEW = gw2.items.search_name('Mini Professor Mew')
ITEMS_HANDFUL_OF_FRACTAL_RELICS = set(
        gw2.items.search_name('Handful of Fractal Relics', allow_multiple=True))
CURRENCY_COIN = 1
CURRENCY_FRACTAL_RELIC = 7

FRACTAL_JUNK_ITEMS = set(gw2.items.search_name(x, rarity='Junk') for x in '''
Manuscript of 'Halfway There and...'
Manuscript of 'Proposal for a 1:1 Scale Map of Tyria'
Manuscript of 'This Book Is False'
Postulate of Construction
Postulate of Continuity
Postulate of Diameter
Postulate of Parallels
Postulate of Rectitude
Postulate of Superposition
Proof of Bask's Theorem
Proof of Dekin's Rational Cuts
Proof of Drik's Transformations
Proof of Gali's Proportional Traversal
Proof of Gott's Integral Derivation
Proof of Neta's Square Inversion Law
Treatise on Commensurability
Treatise on Convergence
Treatise on Divergence
Treatise on Equivalence
Treatise on Iteration
Treatise on Symmetry
'''.strip().splitlines())

ASCENDED_MATERIAL_ITEMS = set(gw2.items.search_name(x) for x in '''
Dragonite Ore
Empyreal Fragment
Pile of Bloodstone Dust
'''.strip().splitlines())

TIER_5_MATERIAL_ITEMS = set(gw2.items.search_name(x) for x in '''
Intricate Totem
Large Bone
Large Claw
Large Fang
Large Scale
Pile of Incandescent Dust
Potent Venom Sac
Vial of Potent Blood
'''.strip().splitlines())

def cmd_fractal_encryption(args):
    loot_table = None
    for path in args:
        with open(path) as f:
            diff = DataDiff(**json.load(f))
        negative_item_ids = [int(item_id_str)
                for item_id_str, count in diff.item_diff.items() if count < 0]
        if negative_item_ids != [ITEM_CRACKED_FRACTAL_ENCRYPTION]:
            print('skipping %s because items %r have negative counts' %
                    (path, [gw2.items.name(item_id) for item_id in negative_item_ids]))
            continue

        if loot_table is None:
            loot_table = loot_table_from_data_diff(diff)
        else:
            loot_table = merge_loot_tables(loot_table,
                    loot_table_from_data_diff(diff))

    gold_sum = 0
    relics_sum = 0
    ascended_mats_sum = 0
    tier_5_mats_sum = 0
    keys_sum = 0
    infusion_sum = 0
    mini_sum = 0
    armor_recipes_sum = 0
    weapon_recipes_sum = 0

    for drop in loot_table.item_drop_info_list:
        item = gw2.items.get(drop.id)
        if drop.id in FRACTAL_JUNK_ITEMS:
            gold_sum += drop.quantity * item['vendor_value']
        elif drop.id in ITEMS_HANDFUL_OF_FRACTAL_RELICS:
            relics_sum += drop.quantity * 3
        elif drop.id in ASCENDED_MATERIAL_ITEMS:
            ascended_mats_sum += drop.quantity
        elif drop.id in TIER_5_MATERIAL_ITEMS:
            tier_5_mats_sum += drop.quantity
        elif drop.id == ITEM_FRACTAL_ENCRYPTION_KEY:
            keys_sum += drop.quantity
        elif drop.id == ITEM_PLUS1_AGONY_INFUSION:
            infusion_sum += drop.quantity
        elif drop.id == ITEM_MINI_PROFESSOR_MEW:
            mini_sum += drop.quantity
        elif item['name'].startswith('Recipe: Ascended'):
            if item['name'].split()[2] in ('Light', 'Medium', 'Heavy'):
                armor_recipes_sum += drop.quantity
            else:
                weapon_recipes_sum += drop.quantity
        else:
            print('unrecognized drop: %s' % gw2.items.name(drop.id))

    for drop in loot_table.wallet_drop_info_list:
        if drop.id == CURRENCY_COIN:
            gold_sum += drop.quantity
        elif drop.id == CURRENCY_FRACTAL_RELIC:
            relics_sum += drop.quantity

    entries = [
            ('Cracked Fractal Encryption', -loot_table.source_item_quantity),
            ('Silver', gold_sum / 100),
            ('Fractal Relic', relics_sum),
            ('Ascended Material', ascended_mats_sum),
            ('Tier 5 Material', tier_5_mats_sum),
            ('Fractal Encryption Key', keys_sum),
            ('+1 Agony Infusion', infusion_sum),
            ('Mini Professor Mew', mini_sum),
            ('Ascended Armor Recipe', armor_recipes_sum),
            ('Ascended Weapon Recipe', weapon_recipes_sum),
            ]
    for name, count in entries:
        print('%8.3f  %10d  %s' % (count / loot_table.source_item_quantity,
            count, name))



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
    elif cmd == 'diff_to_text':
        assert len(args) <= 2
        cmd_diff_to_text(
                args[0] if len(args) >= 1 else None,
                args[1] if len(args) >= 2 else None)
    elif cmd == 'text_to_diff':
        assert len(args) <= 2
        cmd_text_to_diff(
                args[0] if len(args) >= 1 else None,
                args[1] if len(args) >= 2 else None)
    elif cmd == 'fractal_encryption':
        assert len(args) >= 1
        cmd_fractal_encryption(args)
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
