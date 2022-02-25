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

    craftable_items = []
    for r in gw2.recipes.iter_all():
        item_id = r['output_item_id']
        inputs = crafting_inputs(item_id, 1, material_counts)
        if inputs is not None:
            craftable_items.append((item_id, inputs))

    xs = gw2.items.get_multi([x for x,_ in craftable_items])

    for item_id, inputs in craftable_items:
        print(gw2.items.name(item_id), inputs)



if __name__ == '__main__':
    main()
