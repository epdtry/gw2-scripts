from collections import defaultdict
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

def crafting_inputs(item_id, count, materials):
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


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    materials = fetch('/v2/account/materials', cache=True)
    material_counts = {}
    for m in materials:
        material_counts[m['id']] = m['count']

#    all_items = set()
#    for r in gw2.recipes.iter_all():
#        if can_craft(r):
#            for i in r['ingredients']:
#                all_items.add(i['item_id'])
#            all_items.add(r['output_item_id'])
#    for k,v in material_counts.items():
#        if v > 0:
#            all_items.add(k)
#
#    gw2.trading_post.get_prices_multi(all_items)
#    print('got prices for %d items' % len(all_items))
#    return


    craftable_items = []
    for r in gw2.recipes.iter_all():
        item_id = r['output_item_id']
        inputs = crafting_inputs(item_id, 1, material_counts)
        if inputs is not None:
            craftable_items.append((item_id, inputs))

    gw2.items.get_multi([x for x,_ in craftable_items])

    for item_id, inputs in craftable_items:
        print(gw2.items.name(item_id), inputs)

    all_item_ids = set()
    for item_id, inputs in craftable_items:
        all_item_ids.add(item_id)
        for input_item_id in inputs.keys():
            all_item_ids.add(input_item_id)

    gw2.trading_post.get_prices_multi(all_item_ids)

    profitable_crafts = []
    for item_id, inputs in craftable_items:
        prices = gw2.trading_post.get_prices(item_id)
        if prices is None or 'sells' not in prices:
            continue
        if prices['sells']['unit_price'] < 10000:
            continue
        if prices['sells']['quantity'] < 100:
            continue
        crafted_price = prices['sells']['unit_price']

        inputs_price = 0
        for input_item_id, count in inputs.items():
            input_prices = gw2.trading_post.get_prices(input_item_id)
            if input_prices is None or 'sells' not in input_prices:
                inputs_price = 999999999
                break
            inputs_price += input_prices['sells']['unit_price'] * count
        if inputs_price < crafted_price:
            ratio = crafted_price / inputs_price
            profit = crafted_price - inputs_price
            profitable_crafts.append((ratio, item_id, crafted_price, profit))

    profitable_crafts.sort(reverse=True)
    for ratio, item_id, crafted_price, profit in profitable_crafts:
        print('%6.2f%%   %6d   %6d   %s' % ((ratio - 1) * 100, crafted_price,
            profit, gw2.items.name(item_id)))



if __name__ == '__main__':
    main()
