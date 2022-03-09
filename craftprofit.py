from collections import defaultdict
import json
from pprint import pprint

import gw2.api
from gw2.api import fetch
import gw2.items
import gw2.recipes
import gw2.trading_post


def can_craft(r):
    min_rating = r['min_rating']
    for d in r['disciplines']:
        if d == 'Tailor' and min_rating <= 500:
            return True
        if d == 'Artificer' and min_rating <= 500:
            return True
    return False

def crafting_inputs_own_materials(item_id, count, materials):
    '''Find the ingredients required to craft `item_id`, using only the
    `materials` that are already available.'''
    need = defaultdict(int)
    spent = defaultdict(int)
    need[item_id] += count
    while len(need) > 0:
        item_id = next(iter(need.keys()))
        count = need.pop(item_id)
        avail = materials.get(item_id, 0) - spent.get(item_id, 0)

        # Use items available in material storage if possible
        if avail > 0:
            spent[item_id] += min(avail, count)
            count -= min(avail, count)

        # Remaining items must be crafted using a recipe.
        if count > 0:
            recipe_ids = gw2.recipes.search_output(item_id)

            found_recipe = False
            for recipe_id in recipe_ids:
                r = gw2.recipes.get(recipe_id)
                if can_craft(r):
                    per_craft = r['output_item_count']
                    num_crafts = (count + per_craft - 1) // per_craft
                    for i in r['ingredients']:
                        need[i['item_id']] += i['count'] * num_crafts
                        #print('for %dx %s, need %dx %s' % (
                        #    count, gw2.items.name(item_id),
                        #    i['count'] * count, gw2.items.name(i['item_id'])))
                    found_recipe = True
                    break
            if not found_recipe:
                #print('found no craftable recipe for %s (need %d)' %
                #        (gw2.items.name(item_id), count))
                return None

    return dict(spent)

DAILY_CRAFT_ITEMS = set((
    46742,  # Lump of Mithrillium
    46744,  # Glob of Elder Spirit Residue
    46745,  # Spool of Thick Elonian Cord
    46740,  # Spool of Silk Weaving Thread
    43772,  # Charged Quartz Crystal
))


_CRAFT_OR_BUY_CACHE = {}
def craft_or_buy_cost(item_id, prices, force_craft=False):
    '''Compute the cost to craft or buy `item_id`, given current trading post
    `prices` (a dict mapping item ID to integer cost).

    Note that this function caches outputs, and changes to `prices` don't
    invalidate the cache.  So this function should only be called with a single
    `prices` dict in each execution.'''
    key = (item_id, force_craft)
    if item_id in _CRAFT_OR_BUY_CACHE:
        return _CRAFT_OR_BUY_CACHE[key]

    min_price = None
    should_craft = None

    price = prices.get(item_id)
    if price is not None and not force_craft:
        min_price = price
        should_craft = False

    recipe_ids = gw2.recipes.search_output(item_id)

    # Forbid crafting daily-craft items
    if item_id in DAILY_CRAFT_ITEMS:
        recipe_ids = []

    for recipe_id in recipe_ids:
        r = gw2.recipes.get(recipe_id)
        if not can_craft(r):
            continue

        price = 0
        for i in r['ingredients']:
            input_cost, _ = craft_or_buy_cost(i['item_id'], prices)
            if input_cost is None:
                price = None
                break
            price += input_cost * i['count']
        if price is None:
            continue
        price = (price + r['output_item_count'] - 1) // r['output_item_count']

        if min_price is None or price < min_price:
            min_price = price
            should_craft = True

    _CRAFT_OR_BUY_CACHE[key] = (min_price, should_craft)
    #print('cost of %s = %s' % (gw2.items.name(item_id), _CRAFT_OR_BUY_CACHE[item_id]))
    return min_price, should_craft


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    print("Fetching account materials")
    materials = fetch('/v2/account/materials', cache=True)
    material_counts = {}
    for m in materials:
        material_counts[m['id']] = m['count']

    print("Fetching recipes")
    all_items = set()
    for r in gw2.recipes.iter_all():
        if can_craft(r):
            for i in r['ingredients']:
                all_items.add(i['item_id'])
            all_items.add(r['output_item_id'])

    print("Fetching items")
    gw2.items.get_multi(all_items)

    print("Fetching trading post prices")
    buy_prices = {}
    sell_prices = {}
    for x in gw2.trading_post.get_prices_multi(all_items):
        if x is None:
            continue

        # Try to buy at the buy price.  If there is no buy price (for example,
        # certain items that trade very close to their vendor price), then use
        # the sell price ("instant buy") instead.
        price = x['buys'].get('unit_price', 0) or x['sells'].get('unit_price', 0)
        if price != 0:
            buy_prices[x['id']] = price

        price = x['sells'].get('unit_price', 0) or x['buys'].get('unit_price', 0)
        if price != 0:
            sell_prices[x['id']] = price

    for r in gw2.recipes.iter_all():
        # Forbid buying or selling intermediate crafting items.
        if r['type'] in ('Refinement', 'Component'):
            item_id = r['output_item_id']
            if item_id in buy_prices:
                del buy_prices[item_id]
            if item_id in sell_prices:
                del sell_prices[item_id]

    # Allow buying any vendor items that are priced in gold.
    with open('vendorprices.json') as f:
        j = json.load(f)
    for k, v in j.items():
        if k == '_origin':
            print('using vendor prices from %s' % v)
            continue

        k = int(k)
        if v['type'] != 'gold':
            continue
        price = v['cost'] / v['quantity']
        buy_prices[k] = price

    profitable_crafts = []
    for item_id, sell_price in sell_prices.items():
        x = gw2.trading_post.get_prices(item_id)
        if x['buys']['unit_price'] == 0:
            continue
        if x['buys']['quantity'] < 100:
            continue
        if x['sells']['quantity'] > x['buys']['quantity']:
            continue
        if x['sells']['unit_price'] / x['buys']['unit_price'] > 1.5:
            continue

        item = gw2.items.get(item_id)
        if item['level'] != 80 and item['type'] in ('Weapon', 'Armor', 'Consumable'):
            continue
        if item['level'] < 60 and item['type'] in ('UpgradeComponent',):
            continue
        if item['type'] in ('Weapon', 'Armor'):
            if item['rarity'] not in ('Exotic', 'Ascended', 'Legendary'):
                continue

        cost, should_craft = craft_or_buy_cost(item_id, buy_prices, force_craft=True)

        if not should_craft:
            continue

        mode = 'craft' if should_craft else 'flip'
        revenue = sell_price * 0.85
        profit = revenue - cost
        if profit <= 0:
            continue
        ratio = revenue / cost

        profitable_crafts.append((item_id, cost, revenue, profit, ratio, mode))


    profitable_crafts.sort(key=lambda x: x[4], reverse=True)
    for item_id, cost, revenue, profit, ratio, mode in profitable_crafts:
        print('%6.2f%%  %8d  %+9d  %5s   %s' % ((ratio - 1) * 100, cost,
            profit, mode, gw2.items.name(item_id)))



if __name__ == '__main__':
    main()
