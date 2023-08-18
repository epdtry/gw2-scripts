import sys
import gw2.api
import gw2.character
import gw2.items
import bookkeeper

CURRENCY_SPIRIT_SHARDS = 23
CURRENCY_FRACTAL_RELIC = 7
CURRENCY_PRISTINE_FRACTAL_RELIC = 24

MYSTIC_CLOVER_COST = 1.8
ELDRITCH_SCROLL_COST = 50
BLOODSTONE_SHARD_COST = 200
VISION_CRYSTAL_COST = 20

# Eldritch Scroll is part of the precursor
GEN3_LEGENDARY_COST = BLOODSTONE_SHARD_COST + \
    38 * MYSTIC_CLOVER_COST + \
    + ELDRITCH_SCROLL_COST

LEGENDARY_COST_MAP = {
    # Gen 1
    'Incinerator': BLOODSTONE_SHARD_COST + 77 * MYSTIC_CLOVER_COST,
    # Gen 2
    'Nevermore': BLOODSTONE_SHARD_COST + 77 * MYSTIC_CLOVER_COST
        # Vision crystals for the collection (part 4)
        + 2 * VISION_CRYSTAL_COST,
    # Gen 2.5
    'The Binding of Ipos': BLOODSTONE_SHARD_COST + 77 * MYSTIC_CLOVER_COST
        # Vision crystal for the ascended precursor
        + VISION_CRYSTAL_COST,
    # Gen 3
    "Aurene's Rending": GEN3_LEGENDARY_COST,
    "Aurene's Claw": GEN3_LEGENDARY_COST,
    "Aurene's Tail": GEN3_LEGENDARY_COST,
    "Aurene's Argument": GEN3_LEGENDARY_COST,
    "Aurene's Wisdom": GEN3_LEGENDARY_COST,
    "Aurene's Fang": GEN3_LEGENDARY_COST,
    "Aurene's Gaze": GEN3_LEGENDARY_COST,
    "Aurene's Scale": GEN3_LEGENDARY_COST,
    "Aurene's Breath": GEN3_LEGENDARY_COST,
    "Aurene's Voice": GEN3_LEGENDARY_COST,
    "Aurene's Bite": GEN3_LEGENDARY_COST,
    "Aurene's Weight": GEN3_LEGENDARY_COST,
    "Aurene's Flight": GEN3_LEGENDARY_COST,
    "Aurene's Persuasion": GEN3_LEGENDARY_COST,
    "Aurene's Wing": GEN3_LEGENDARY_COST,
    "Aurene's Insight": GEN3_LEGENDARY_COST,
    # Envoy armor
    'Perfected Envoy Cowl': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    'Perfected Envoy Mantle': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    'Perfected Envoy Vestments': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    'Perfected Envoy Gloves': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    'Perfected Envoy Pants': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    'Perfected Envoy Shoes': 15 * MYSTIC_CLOVER_COST + ELDRITCH_SCROLL_COST,
    # Other
    'Legendary Rune': 20 * MYSTIC_CLOVER_COST,
    'Legendary Sigil': 30 * MYSTIC_CLOVER_COST,
    "Prismatic Champion's Regalia": 0,
    'Aurora': BLOODSTONE_SHARD_COST + 77 * MYSTIC_CLOVER_COST,
    'Ad Infinitum': 77 * MYSTIC_CLOVER_COST
        # 3x Prototype Fractal Capacitor
        + 3 * 24
        # Each "wings" step requires a vision crystal
        + 3 * VISION_CRYSTAL_COST
        # Opportunity cost of fractal relics
        + 5350 * 1/35
        # Opportunity cost of pristine fractal relics
        + 140 * 15/35,
}

# Gen 1 and 2 precursor recipes have a one-time cost in spirit shards
LEGENDARY_ONE_TIME_COST_MAP = {
    # Gen 1
    'Incinerator': 2 * 5,
    # Gen 2
    'Nevermore': 2 * 5,
    # Gen 2.5
    'The Binding of Ipos': 2 * 5,
}

def spent(inventory):
    ascended_cost = 0

    # Add equipped items to `inventory`
    character_names = gw2.character.get_all_names()
    for char_name in character_names:
        equip = gw2.character.get_equipment_for_character(char_name)
        for info in equip:
            if info['location'] not in ('Equipped', 'Armory'):
                continue
            if info['id'] not in inventory:
                inventory[info['id']] = 0
            inventory[info['id']] += 1

    for item_id, count in inventory.items():
        info = gw2.items.get(item_id)
        if info is None:
            continue
        if info['rarity'] != 'Ascended':
            continue
        if info['type'] in ('Weapon', 'Armor'):
            item_cost = 20 * count
        elif info['type'] == 'Back':
            item_cost = 24 * count
        else:
            continue
        print('%6d   %6d %s' % (item_cost, count, info['name']))
        ascended_cost += item_cost
    print('%6d   Total in ascended gear' % ascended_cost)

    print('')
    armory = gw2.api.fetch('/v2/account/legendaryarmory')
    legendary_cost = 0
    for entry in armory:
        name = gw2.items.name(entry['id'])
        if name in LEGENDARY_ONE_TIME_COST_MAP:
            one_time_cost = LEGENDARY_ONE_TIME_COST_MAP[name]
            print('%6d   %1d %s (one-time cost)' % (one_time_cost, entry['count'], name))
            legendary_cost += one_time_cost
        if name in LEGENDARY_COST_MAP:
            item_cost = entry['count'] * LEGENDARY_COST_MAP[name]
        else:
            print('warning: unknown legendary item %s' % name)
            item_cost = 0
        print('%6d   %1d %s' % (item_cost, entry['count'], name))
        legendary_cost += item_cost
    print('%6d   Total in legendary gear' % legendary_cost)

    print('')
    print('%6d   Grand Total' % (ascended_cost + legendary_cost))

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    inventory = bookkeeper.get_inventory()
    if sys.argv[1:] == ['spent']:
        spent(inventory)
        return

    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    wallet_shards = wallet.get(CURRENCY_SPIRIT_SHARDS, 0)
    fractal_shards = wallet.get(CURRENCY_FRACTAL_RELIC, 0) / 35
    pristine_fractal_shards = wallet.get(CURRENCY_PRISTINE_FRACTAL_RELIC, 0) * 15 / 35
    tome_shards = inventory.get(gw2.items.search_name('Tome of Knowledge'), 0)
    writ_shards = inventory.get(gw2.items.search_name('Writ of Experience'), 0) / 20

    total = fractal_shards + pristine_fractal_shards + \
            tome_shards + writ_shards

    philosopher_shards = inventory.get(gw2.items.search_name("Philosopher's Stone"), 0) * 0.1
    mystic_crystal_shards = inventory.get(gw2.items.search_name('Mystic Crystal'), 0) * 0.6
    clover_shards = inventory.get(gw2.items.search_name('Mystic Clover'), 0) * 1.8

    clover_total = philosopher_shards + mystic_crystal_shards + clover_shards

    augur_shards = inventory.get(gw2.items.search_name("Augur's Stone"), 0) * 20
    vision_shards = inventory.get(gw2.items.search_name('Vision Crystal'), 0) * 20
    lesser_vision_shards = inventory.get(gw2.items.search_name('Lesser Vision Crystal'), 0) * 20

    vision_total = augur_shards + vision_shards + lesser_vision_shards

    print('%6.1f  Spirit Shard' % wallet_shards)
    print('')
    print('%6.1f  from Fractal Relic' % fractal_shards)
    print('%6.1f  from Pristine Fractal Relic' % pristine_fractal_shards)
    print('%6.1f  from Tome of Knowledge' % tome_shards)
    print('%6.1f  from Writ of Experience' % writ_shards)
    print('%6.1f  Total from other currencies' % total)
    print('%6.1f  Total raw shards available' % (wallet_shards + total))
    print('')
    print("%6.1f  in Philosopher's Stone" % philosopher_shards)
    print('%6.1f  in Mystic Crystal' % mystic_crystal_shards)
    print('%6.1f  in Mystic Clover' % clover_shards)
    print('%6.1f  Total in legendary materials' % clover_total)
    print('')
    print("%6.1f  in Augur's Stone" % augur_shards)
    print('%6.1f  in Vision Crystal' % vision_shards)
    print('%6.1f  in Lesser Vision Crystal' % lesser_vision_shards)
    print('%6.1f  Total in ascended materials' % vision_total)
    print('')
    print('%6.1f  Grand Total' % (wallet_shards + total + clover_total + vision_total))

if __name__ == '__main__':
    main()
