from collections import defaultdict
import json
import os
import sys
import time

import gw2.api
import gw2.items
import gw2.mystic_forge
import gw2.recipes
import gw2.trading_post

import DataDiff

def cmd_gen_loot_tables():
    return

def cmd_gen_loot_tables_value():
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
    elif cmd == 'gen_loot_tables_value':
        assert len(args) == 0
        cmd_gen_loot_tables_value()
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
