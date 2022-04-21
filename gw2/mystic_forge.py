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


    # Legendary crafting - generic recipes

    add(1, 'Mystic Clover', (
        (3, 'Obsidian Shard'),
        (3, 'Mystic Coin'),
        (3, 'Glob of Ectoplasm'),
        (6, "Philosopher's Stone"),
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

    add(1, 'Gift of the Mists', (
        (1, 'Gift of Glory'),
        (1, 'Gift of Battle'),
        (1, 'Gift of War'),
        (1, 'Cube of Stabilized Dark Energy'),
    ))

    add(1, 'Gift of Glory', ((250, 'Shard of Glory'),))
    add(1, 'Gift of War', ((250, 'Memory of Battle'),))

    # Legendary crafting - gen3 weapon generic components

    add(1, 'Gift of Cantha', (
        (1, 'Gift of Seitung Province'),
        (1, 'Gift of New Kaineng City'),
        (1, 'Gift of the Echovald Forest'),
        (1, "Gift of Dragon's End"),
    ))

    add(1, 'Draconic Tribute', (
        (1, 'Gift of Condensed Might'),
        (1, 'Gift of Condensed Magic'),
        (1, 'Amalgamated Draconic Lodestone'),
        (1, 'Mystic Clover'),
    ))

    add(1, 'Gift of Research', (
        (250, 'Thermocatalytic Reagent'),
        (250, 45178),   # Essence of Luck (exotic)
        (250, 'Hydrocatalytic Reagent'),
        (250, 'Hydrocatalytic Reagent'),
    ))

    add(1, 'Gift of the Dragon Empire', (
        (100, 'Jade Runestone'),
        (200, 'Chunk of Pure Jade'),
        (100, 'Chunk of Ancient Ambergris'),
        (5, 'Blessing of the Jade Empress'),
    ))

    add(1, 'Gift of Jade Mastery', (
        (1, 'Gift of the Dragon Empire'),
        (1, 'Bloodstone Shard'),
        (1, 'Gift of Cantha'),
        (100, 'Antique Summoning Stone'),
    ))

    # Legendary crafting - gen3 Aurene's Wisdom

    add(1, "Gift of Aurene's Wisdom", (
        (1, 'Poem on Scepters'),
        (100, 'Mystic Runestone'),
        (1, 'Gift of Research'),
        (1, 'Gift of the Mists'),
    ))

    add(1, "Aurene's Wisdom", (
        (1, "Dragon's Wisdom"),
        (1, "Gift of Aurene's Wisdom"),
        (1, 'Gift of Jade Mastery'),
        (1, 'Draconic Tribute'),
    ))

    add(1, 'Poem on Scepters', (
        (10, 'Tale of Adventure'),
        (10, "Lamplighter's Badge"),
        (1, 'Spiritwood Scepter Core'),
        (1, 'Sheet of Premium Paper'),
    ))


    # Bought from vendors
    add(1, 'Chunk of Ancient Ambergris', ((10, 'Flawless Fish Fillet'),))
    add(1, 'Flawless Fish Fillet', ((5, 'Fantastic Fish Fillet'),))
    add(1, 'Fantastic Fish Fillet', ((5, 'Flavorful Fish Fillet'),))
    add(1, 'Flavorful Fish Fillet', ((5, 'Fabulous Fish Fillet'),))
    add(1, 'Fabulous Fish Fillet', ((5, 'Fine Fish Fillet'),))


    # Bought from vendors
    add(10, 'Hydrocatalytic Reagent', ((50, 'Research Note'),))


    # Ecto salvaging
    add(45, 'Pile of Crystalline Dust', ((25, 'Glob of Ectoplasm'), (1, "Master's Salvage Kit")))


    _RECIPES = recipes
    return recipes

def get(mystic_recipe_id):
    return _get()[mystic_recipe_id]

def iter_all():
    return iter(_get())

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
