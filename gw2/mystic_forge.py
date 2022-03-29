from collections import defaultdict

import gw2.items


_RECIPES = None
def _get():
    global _RECIPES
    if _RECIPES is not None:
        return _RECIPES

    recipes = []

    def parse(item):
        if isinstance(item, int):
            return item
        elif isinstance(item, str):
            return gw2.items.search_name(item)
        else:
            raise TypeError('unsupported item %r' % item)

    def add(count, item, inputs):
        item_id = parse(item)
        recipes.append({
            'id': len(recipes),
            'output_item_id': item_id,
            'output_item_count': count,
            'ingredients': [{
                'item_id': parse(input_item),
                'count': input_count,
            } for input_count, input_item in inputs],
        })


    add(1, "There with Yakkington: A Traveler's Tale", (
        (1, 'Vial of Condensed Mists Essence'),
        (40, 'Mystic Crystal'),
        (50, 'Glob of Ectoplasm'),
        (250, 'Vicious Claw'),
    ))


    add(1, 'Gift of Condensed Might', (
        (1, 'Gift of Claws'),
        (1, 'Gift of Scales'),
        (1, 'Gift of Bones'),
        (1, 'Gift of Fangs'),
    ))

    add(1, 'Gift of Condensed Magic', (
        (1, 'Gift of Blood'),
        (1, 'Gift of Venom'),
        (1, 'Gift of Totems'),
        (1, 'Gift of Dust'),
    ))

    add(1, 'Draconic Tribute', (
        (1, 'Gift of Condensed Might'),
        (1, 'Gift of Condensed Magic'),
        (1, 'Amalgamated Draconic Lodestone'),
        (1, 'Mystic Clover'),
    ))


    # Bought from vendors
    add(1, 'Chunk of Ancient Ambergris', ((10, 'Flawless Fish Fillet'),))
    add(1, 'Flawless Fish Fillet', ((5, 'Fantastic Fish Fillet'),))
    add(1, 'Fantastic Fish Fillet', ((5, 'Flavorful Fish Fillet'),))
    add(1, 'Flavorful Fish Fillet', ((5, 'Fabulous Fish Fillet'),))
    add(1, 'Fabulous Fish Fillet', ((5, 'Fine Fish Fillet'),))


    # Bought from vendors
    add(10, 'Hydrocatalytic Reagent', ((50, 'Research Note'),))


    _RECIPES = recipes
    return recipes

def get(mystic_recipe_id):
    return _get()[mystic_recipe_id]

def iter_all():
    return range(len(_get()))

_BY_OUTPUT = None
def _by_output():
    global _BY_OUTPUT
    if _BY_OUTPUT is None:
        recipes = _get()
        _BY_OUTPUT = defaultdict(list)
        for r in recipes:
            _BY_OUTPUT[r['output_item_id']].append(r['id'])
    return _BY_OUTPUT

def search_output(output_item_id):
    return _by_output().get(output_item_id, [])
