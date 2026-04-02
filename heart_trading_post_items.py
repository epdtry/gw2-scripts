import gw2.api
import gw2.items
import gw2.character
import bookkeeper
import urllib.parse
from collections import defaultdict

Trading_Post_Items_For_Core_Tyria_Map_Completions = { 
    19189: 20, # Caledon Lavender
    19186: 20, # Hylek Armor
    24419: 34, # Crab Meat
    24223: 20, # Seraph Badge (Sergeant Rane)
    24234: 20, # Piece of Charr Scrap Metal
    24415: 34, # Cursed Pirate Artifact
    24149: 13, # Pirate Outfit
    24455: 25, # Skritt Artifact
    19271: 50, # Special Root
    19217: 20, # Supplies
    24249: 20, # Volcanic Earth Elemental Core
    24250: 20, # Alpha Inquest Control Key
    24454: 25 # Barracuda Meat
}

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'
    print()

    # Swap with name you really need
    current_map_comp_char = gw2.character.get_all_names()[0] 

    # get a list of the keys from dictionary
    key_list = list(Trading_Post_Items_For_Core_Tyria_Map_Completions.keys())
    item_ids = [key for key in key_list]
    buy_prices, sell_prices = bookkeeper.get_prices(item_ids)
    
    print()
    total_cost_buy = 0
    total_cost_sell = 0
    print('%30s %5s %10s %10s' % ('Item Name', 'Count', 'Buy Cost', 'InstaBuy Cost'))
    for item_id, count in Trading_Post_Items_For_Core_Tyria_Map_Completions.items():
        item_name = gw2.items.name(item_id)
        items_cost_sell = sell_prices[item_id] * count
        total_cost_sell += items_cost_sell

        items_cost_buy = buy_prices[item_id] * count
        total_cost_buy += items_cost_buy
        
        print('%30s %5s %10s %10s' % (item_name, count, bookkeeper.format_price(items_cost_buy), bookkeeper.format_price(items_cost_sell)))
    print()
    print('%30s %5s %10s %10s' % ('Total cost', '', bookkeeper.format_price(total_cost_buy), bookkeeper.format_price(total_cost_sell)))

    inventory = get_char_inventory(current_map_comp_char)
    print()
    print('Items needed for %s' % current_map_comp_char)
    print('%30s %5s' % ('Item Name', 'Count Needed'))
    for item_id, count in Trading_Post_Items_For_Core_Tyria_Map_Completions.items():
        # check if we have enough of the item
        if item_id in inventory:
            print('%30s %5s' % (gw2.items.name(item_id), count-inventory[item_id]))
        else:
            print('%30s %5s' % (gw2.items.name(item_id), count))
                

def get_char_inventory(char_name):
    '''Return a dict listing the quantities of all items in material storage,
    the bank, and character inventories.'''
    counts = defaultdict(int)

    char = gw2.api.fetch_with_retries('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))
    for bag in char['bags']:
        if bag is None:
            continue
        for item in bag['inventory']:
            if item is None or item['count'] == 0:
                continue
            counts[item['id']] += item['count']

    return dict(counts)


if __name__ == '__main__':
    main()
