import json
import os
import sys
import time
import urllib.parse

import gw2.api
import DataSnapshot

GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
GW2_SNAPSHOT_DATA_DIR = os.path.join(GW2_DATA_DIR, "snapshots")

def cmd_get_inventory(char_name):
    inventory = gw2.api.fetch('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))
    print(inventory)
    return

def cmd_print_help():
    help_string = '''
    help - this
    inventory <char name> - lists inventory of <char name>
    todomore
    '''
    print(help_string)
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
    elif cmd == 'steps':
        cmd_steps(args)
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