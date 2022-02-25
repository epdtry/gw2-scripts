from collections import defaultdict
from pprint import pprint

import gw2.api
from gw2.api import fetch
import gw2.items
import gw2.recipes


def can_craft(r):
    min_rating = r['min_rating']
    for d in r['disciplines']:
        if d == 'Tailor' and min_rating <= 500:
            return True
        if d == 'Artificer' and min_rating <= 450:
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
                    for i in r['ingredients']:
                        need[i['item_id']] += i['count'] * count
                        print('for %dx %s, need %dx %s' % (
                            count, gw2.items.name(item_id),
                            i['count'] * count, gw2.items.name(i['item_id'])))
                    found_recipe = True
                    break
            if not found_recipe:
                print('found no craftable recipe for %s (need %d)' %
                        (gw2.items.name(item_id), count))
                #return None

    return dict(spent)


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    materials = fetch('/v2/account/materials', cache=True)
    material_counts = {}
    for m in materials:
        material_counts[m['id']] = m['count']

    for k,v in crafting_inputs(11271, 1, material_counts).items():
        print('%4d %s' % (v, gw2.items.name(k)))
    print('')
    for k,v in crafting_inputs(13983, 1, material_counts).items():
        print('%4d %s' % (v, gw2.items.name(k)))

if __name__ == '__main__':
    main()
