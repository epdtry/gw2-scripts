import json
import os
import sys
import time
import urllib.parse

import gw2.api
import DataSnapshot

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')

def get_inventory(char_name):
    return gw2.api.fetch('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))

def get_materials():
    return gw2.api.fetch('/v2/account/materials')

def get_bank():
    return gw2.api.fetch('/v2/account/bank')

def get_character_core(char_name):
    return gw2.api.fetch('/v2/characters/%s/core' %
            urllib.parse.quote(char_name))

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    char_name = sys.argv[1]
    char_magic_find = sys.argv[2]

    char_inventory = get_inventory(char_name)
    char_materials = get_materials()
    char_bank = get_bank()
    char_core = get_character_core(char_name)

    data = DataSnapshot.DataSnapshot(char_name, char_inventory, char_materials, char_bank, char_core, char_magic_find)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    data_file_name = timestamp + '.json'
    print()
    print('Data written to: ', data_file_name)
    data_file = os.path.join(GW2_DATA_DIR, data_file_name)

    with open(data_file, 'w') as f:
        json.dump(data, f, default=vars)

if __name__ == '__main__':
    main()