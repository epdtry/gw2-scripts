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

    def add(count, item, inputs, refine_only=False):
        item_id = parse(item)
        recipes.append({
            'id': len(recipes),
            'output_item_id': item_id,
            'output_item_count': count,
            'ingredients': [{
                'item_id': parse(input_item),
                'count': input_count,
            } for input_count, input_item in inputs],
            'bookkeeper_refine_only': refine_only,
        })


    add(1, "There with Yakkington: A Traveler's Tale", (
        (1, 'Vial of Condensed Mists Essence'),
        (40, 'Mystic Crystal'),
        (50, 'Glob of Ectoplasm'),
        (250, 'Vicious Claw'),
    ))

    add(1, 'Charged Quartz Crystal', ((25, 'Quartz Crystal'),))


    # Spirit shard conversions

    add(1, 'Spirit Shard', (
        (1, 'Tome of Knowledge'),
    ), refine_only=True)

    add(1, 'Spirit Shard', (
        (20, 'Writ of Experience'),
    ), refine_only=True)

    add(1, 'Spirit Shard', (
        (35, 'Fractal Relic'),
    ), refine_only=True)

    #add(3, 'Spirit Shard', (
    #    (7, 'Pristine Fractal Relic'),
    #), refine_only=True)


    # Imperial favor conversions

    add(5, 'Imperial Favor', (
        (1, 'Writ of Seitung Province'),
    ), refine_only=True)

    add(5, 'Imperial Favor', (
        (1, 'Writ of New Kaineng City'),
    ), refine_only=True)

    add(5, 'Imperial Favor', (
        (1, 'Writ of Echovald Wilds'),
    ), refine_only=True)

    add(5, 'Imperial Favor', (
        (1, "Writ of Dragon's End"),
    ), refine_only=True)

    # SoTO specific recipes

    add(5, 'Pouch of Stardust', (
        (250, 'Pinch of Stardust'),
    ), refine_only=True)


    # Legendary crafting - generic recipes

    add(10, "Philosopher's Stone", (
        (1, 'Spirit Shard'),
    ))

    add(5, 'Mystic Crystal', (
        (3, 'Spirit Shard'),
    ))

    add(1, 'Bloodstone Shard', (
        (200, 'Spirit Shard'),
    ))

    add(1, 'Eldritch Scroll', (
        (50, 'Spirit Shard'),
    ))

    add(1, "Augur's Stone", (
        (20, 'Spirit Shard'),
    ))

    add(1, 'Mystic Clover', (
        (3, 'Obsidian Shard'),
        (3, 'Mystic Coin'),
        (3, 'Glob of Ectoplasm'),
        (18, "Philosopher's Stone"),
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

    # Legendary crafting - gen1 weapon generic components

    add(1, 'Gift of Might', (
        (250, 'Vicious Fang'),
        (250, 'Armored Scale'),
        (250, 'Vicious Claw'),
        (250, 'Ancient Bone'),
    ))

    add(1, 'Gift of Magic', (
        (250, 'Vial of Powerful Blood'),
        (250, 'Powerful Venom Sac'),
        (250, 'Elaborate Totem'),
        (250, 'Pile of Crystalline Dust'),
    ))

    add(1, 'Gift of Fortune', (
        (1, 'Gift of Magic'),
        (1, 'Gift of Might'),
        (77, 'Mystic Clover'),
        (250, 'Glob of Ectoplasm'),
    ))

    add(1, 'Gift of Mastery', (
        (1, 'Gift of Battle'),
        (1, 'Gift of Exploration'),
        (250, 'Obsidian Shard'),
        (1, 'Bloodstone Shard'),
    ))

    # Legendary crafting - gen1 Incinerator

    add(1, 'Gift of Incinerator', (
        (1, 'Gift of Metal'),
        (1, 'Vial of Liquid Flame'),
        (100, 'Icy Runestone'),
        (1, 'Superior Sigil of Fire'),
    ))

    # Legendary crafting - gen2 weapon generic components

    add(1, 'Gift of Maguuma Mastery', (
        (1, 'Gift of Maguuma'),
        (1, 'Gift of Insights'),
        (1, 'Bloodstone Shard'),
        (250, 'Crystalline Ingot'),
    ))

    add(1, 'Gift of Desert Mastery', (
        (1, 'Gift of the Desert'),
        (1, 'Gift of the Rider'),
        (1, 'Bloodstone Shard'),
        (250, 'Funerary Incense'),
    ))

    add(1, 'Gift of the Desert', (
        (1, 'Gift of the Oasis'),
        (1, 'Gift of the Highlands'),
        (1, 'Gift of the Riverlands'),
        (1, 'Gift of the Desolation'),
    ))

    add(1, 'Gift of the Rider', (
        (1, 'Spirit of the Raptor'),
        (1, 'Spirit of the Springer'),
        (1, 'Spirit of the Skimmer'),
        (1, 'Spirit of the Jackal'),
    ))

    add(1, 'Spirit of the Raptor', (
        (75, 'Corrupted Facet Elegy Mosaic'),
    ))

    add(1, 'Spirit of the Springer', (
        (75, 'Corrupted Facet Elegy Mosaic'),
    ))

    add(1, 'Spirit of the Skimmer', (
        (75, 'Corrupted Facet Elegy Mosaic'),
    ))

    add(1, 'Spirit of the Jackal', (
        (75, 'Corrupted Facet Elegy Mosaic'),
    ))

    add(1, 'Mystic Tribute', (
        (2, 'Gift of Condensed Might'),
        (2, 'Gift of Condensed Magic'),
        (77, 'Mystic Clover'),
        (250, 'Mystic Coin'),
    ))

    # Legendary crafting - gen2.5 The Binding of Ipos

    add(1, 'Gift of Ipos', (
        (1, 'Gift of the Mists'),
        (100, 'Mystic Runestone'),
        (100, 'Shard of the Dark Arts'),
        (1, 'Gift of Energy'),
    ))

    # Legendary crafting - gen2.5 The Shining Blade

    add(1, 'Gift of the Blade', (
        (1, 'Gift of the Mists'),
        (100, 'Mystic Runestone'),
        (100, 'Shard of the Crown'),
        (1, 'Gift of Metal'),
    ))

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
        (5, 'Amalgamated Draconic Lodestone'),
        (38, 'Mystic Clover'),
    ))

    add(1, 'Gift of Research', (
        (250, 'Thermocatalytic Reagent'),
        (250, 'Exotic Essence of Luck'),
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

    add(1, 'Blessing of the Jade Empress', (
        (500, 'Imperial Favor'),
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

    # Legendary crafting - gen3 Aurene's Claw

    add(1, "Gift of Aurene's Claw", (
        (1, 'Poem on Daggers'),
        (100, 'Mystic Runestone'),
        (1, 'Gift of Research'),
        (1, 'Gift of the Mists'),
    ))

    add(1, "Aurene's Claw", (
        (1, "Dragon's Claw"),
        (1, "Gift of Aurene's Claw"),
        (1, 'Gift of Jade Mastery'),
        (1, 'Draconic Tribute'),
    ))

    add(1, 'Poem on Daggers', (
        (10, 'Tale of Adventure'),
        (10, "Lamplighter's Badge"),
        (1, 'Deldrimor Steel Dagger Blade'),
        (1, 'Sheet of Premium Paper'),
    ))

    # Legendary crafting - gen3 Aurene's Voice

    add(1, "Gift of Aurene's Horn", (
        (1, 'Poem on Warhorns'),
        (100, 'Mystic Runestone'),
        (1, 'Gift of Research'),
        (1, 'Gift of the Mists'),
    ))

    add(1, "Aurene's Voice", (
        (1, "Dragon's Voice"),
        (1, "Gift of Aurene's Horn"),
        (1, 'Gift of Jade Mastery'),
        (1, 'Draconic Tribute'),
    ))

    add(1, 'Poem on Warhorns', (
        (10, 'Tale of Adventure'),
        (10, "Lamplighter's Badge"),
        (1, 'Deldrimor Steel Horn'),
        (1, 'Sheet of Premium Paper'),
    ))

    # Legendary crafting - gen3 Aurene's Argument

    add(1, "Gift of Aurene's Argument", (
        (1, 'Poem on Warhorns'),
        (100, 'Mystic Runestone'),
        (1, 'Gift of Research'),
        (1, 'Gift of the Mists'),
    ))

    add(1, "Aurene's Argument", (
        (1, "Dragon's Argument"),
        (1, "Gift of Aurene's Argument"),
        (1, 'Gift of Jade Mastery'),
        (1, 'Draconic Tribute'),
    ))

    add(1, 'Poem on Warhorns', (
        (10, 'Tale of Adventure'),
        (10, "Lamplighter's Badge"),
        (1, 'Deldrimor Steel Pistol Barrel'),
        (1, 'Sheet of Premium Paper'),
    ))

    # Legendary crafting - runes and sigils

    add(1, 'Gift of Sigils', (
        (75, 'Mystic Mote'),
        (30, 'Mystic Clover'),
        (150, 'Glob of Ectoplasm'),
        (75, 'Obsidian Shard'),
    ))

    # Legendary crafting - raid armor

    add(1, 'Gift of Prosperity', (
        (1, 'Gift of Craftsmanship'),
        (15, 'Mystic Clover'),
        (1, 'Gift of Condensed Might'),
        (1, 'Gift of Condensed Magic'),
    ))

    add(1, 'Gift of Prowess', (
        (25, 'Legendary Insight'),
        (1, 'Eldritch Scroll'),
        (50, 'Obsidian Shard'),
        (1, 'Cube of Stabilized Dark Energy'),
    ))

    add(1, 'Gift of Dedication', (
        (5, 'Auric Ingot'),
        (5, 'Reclaimed Metal Plate'),
        (5, 'Chak Egg'),
        (1, 'Gift of the Pact'),
    ))

    add(1, 'Gift of the Pact', (
        (250, 'Airship Part'),
        (250, 'Lump of Aurillium'),
        # Bag of Ley-Line Crystals, which we currently use as a stand-in due to
        # lack of an actual Ley Line Crystal item
        (250, 70072),
    ))

    add(1, 'Gift of Craftsmanship', (
        (50, '1 Provisioner Token'),
    ))

    # Legendary crafting - Aurora
    add(1, 'Gift of Sentience', (
        (1, 'Gift of the Mists'),
        (100, 'Icy Runestone'),
        (1, 'Gift of Valor'),
        (1, 'Gift of Energy'),
    ))

    add(1, 'Gift of Draconic Mastery', (
        (1, 'Gift of Bloodstone Magic'),
        (1, 'Gift of Dragon Magic'),
        (1, 'Bloodstone Shard'),
        (1, 'Crystalline Ingot'),
    ))

    add(1, 'Gift of Bloodstone Magic', (
        (250, 'Blood Ruby'),
        (250, 'Jade Shard'),
        (250, 'Orrian Pearl'),
    ))

    add(1, 'Gift of Dragon Magic', (
        (250, 'Petrified Wood'),
        (250, 'Fresh Winterberry'),
        (250, 'Fire Orchid Blossom'),
    ))

    # Legendary crafting - Orrax Manifested
    add(1, 'Orrax Contained', (
        (1, 'Binding of the Dragon'),
        (1, 'Draconic Tribute'),
        (1, 'Salmon of Knowledge Backpiece'),
        (1, 'Askur Camping Cookout Backpiece'),
    ))

    add(1, 'Orrax Manifested', (
        (1, 'Gift of the Mistburned Isles'),
        (1, 'Gift of Shadows'),
        (1, 'Gift of the Feast'),
        (1, 'Orrax Contained'),
    ))

    add(1, 'Gift of the Mistburned Isles', (
        (1, 'Gift of the Mursaat Ruins'),
        (1, 'Gift of Janthir Wanderlust'),
        (250, 'Mursaat Runestone'),
        (250, 'Mystic Runestone'),
    ))

    add(1, 'Gift of the Mursaat Ruins', (
        (100, 'Vial of Titan Melted Liquid Obsidian'),
        (50, 'Mists Gate Residue'),
        (100, 'Shard of Mistburned Barrens'),
        (100, 'Shard of Bava Nisos'),
    ))

    add(1, 'Gift of Janthir Wanderlust', (
        (1, 'Gift of Lowland Shore'),
        (1, 'Gift of Janthir Syntri'),
        (1, 'Gift of Mistburned Barrens'),
        (1, 'Gift of Bava Nisos'),
    ))

    add(1, 'Gift of Shadows', (
        (1, 'Gift of Darkness'),
        (1, 'Gift of Scales'),
        (1, 'Gift of Titan Understanding'),
        (1, 'Bloodstone Shard'),
    ))

    add(1, 'Gift of the Feast', (
        (1, 'Gift of the Appetizer'),
        (1, 'Gift of the Entrée'),
        (1, 'Gift of the Side Course'),
        (1, 'Gift of the Dessert'),
    ))

    add(1, 'Gift of the Appetizer', (
        (200, 'Bowl of Poultry Satay'),
        (100, 'Red-Lentil Saobosa'),
        (50, 'Spicy Marinated Mushroom'),
        (5, 'Fruit of the Shadow'),
    ))

    add(1, 'Gift of the Entrée', (
        (200, 'Plate of Orrian Steak Frittes'),
        (100, 'Plate of Truffle Steak'),
        (50, 'Plate of Spicy Herbed Chicken'),
        (5, 'Fruit of the Shadow'),
    ))

    add(1, 'Gift of the Side Course', (
        (200, 'Meaty Asparagus Skewer'),
        (100, 'Bowl of Black Pepper Cactus Salad'),
        (30, 'Mystic Clover'),
        (5, 'Fruit of the Shadow'),
    ))

    add(1, 'Gift of the Dessert', (
        (200, 'Bowl of Prickly Pear Sorbet'),
        (50, 'Bowl of Passion Fruit Tapioca Pudding'),
        (2, 'Amalgamated Rift Essence'),
        (5, 'Fruit of the Shadow'),
    ))

    # Vendor: Ward Trader Sampaguita, Bava Nisos
    add(1, 'Gift of Titan Understanding', (
        (25, 'Curious Mursaat Ruin Shard'),
        (25, 'Curious Mursaat Remnants'),
        (25, 'Amalgamated Rift Essence'),
        (1250, 'Ursus Oblige'),
    ))

    # Amalgamated Gemstone
    opts = [
            'Crest of the Assassin',
            'Crest of the Magi',
            'Crest of the Rabid',
            'Crest of the Shaman',
            'Crest of the Soldier',
            'Agate Orb',
            'Azurite Orb',
            'Beryl Orb',
            'Black Diamond',
            'Chrysocola Orb',
            'Coral Orb',
            'Ebony Orb',
            'Emerald Orb',
            'Flax Blossom',
            'Freshwater Pearl',
            'Maguuma Burl',
            'Maguuma Lily',
            'Moonstone Orb',
            'Opal Orb',
            'Ruby Orb',
            'Sapphire Orb',
            'Copper Doubloon',
            'Silver Doubloon',
            'Gold Doubloon',
            'Platinum Doubloon',
            ]
    for opt in opts:
        # You can actually use any combination of inputs here, such as 3 crests
        # + 3 orbs + 3 doubloons.  We include only the cases where all three
        # inputs are the same, since the cheapest recipe is the one that uses
        # the cheapest input in all three slots.
        add(1, 'Amalgamated Gemstone', (
            (1, 'Pile of Crystalline Dust'),
            (3, opt),
            (3, opt),
            (3, opt),
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
    add(43, 'Pile of Crystalline Dust', ((25, 'Glob of Ectoplasm'), (25, "Copper-Fed Salvage-o-Matic")))
    add(10, gw2.items.search_name('Fine Essence of Luck'),
            ((1, 'Glob of Ectoplasm'), (1, "Copper-Fed Salvage-o-Matic")))
    add(21, gw2.items.search_name('Fine Essence of Luck'),
            ((2, 'Glob of Ectoplasm'), (2, "Silver-Fed Salvage-o-Matic")))

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
