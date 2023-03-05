from collections import defaultdict
import datetime
from pprint import pprint
import re

import gw2.build
import gw2.items
import gw2.itemstats


def get_slot_points(dct):
    out = {}
    for slot_name, item_name in dct.items():
        item_id = gw2.items.search_name(item_name, allow_multiple=False)
        item = gw2.items.get(item_id)
        points = item['details']['attribute_adjustment']
        out[slot_name] = points
    return out


def get_pve_stats():
    # We first gather the list of valid prefix names from a stat-selectable
    # ascended weapon.  This excludes some unusual prefixes that are only
    # available on jewelry.
    item_id = gw2.items.search_name('The Raven Staff', allow_multiple=False)
    item = gw2.items.get(item_id)
    valid_prefix_names = set(
            gw2.itemstats.get(itemstats_id)['name']
            for itemstats_id in item['details']['stat_choices'])


    # For the actual stat formulas, we use a legendary backpiece to get the
    # list because the backpiece versions of the `itemstats` include the base
    # value used in ascended trinkets to account for the lack of a gemstone
    # slot.
    item_id = gw2.items.search_name('Ad Infinitum', allow_multiple=False)
    item = gw2.items.get(item_id)
    out = {}
    for itemstats_id in item['details']['stat_choices']:
        itemstats = gw2.itemstats.get(itemstats_id)

        if itemstats['name'] not in valid_prefix_names:
            continue

        #if itemstats['name'] not in ("Viper's", "Rampager's", 'Sinister'): continue

        mults = sorted(set(stat['multiplier'] for stat in itemstats['attributes']),
            reverse=True)
        mult_rank = {x: i for i,x in enumerate(mults)}

        stat_formulas = {}
        for stat in itemstats['attributes']:
            rank = mult_rank[stat['multiplier']]
            # As a special case, exotic celestial jewels don't provide
            # expertise or concentration.
            if itemstats['name'] == 'Celestial':
                rank = 1 if stat['attribute'] in ('ConditionDuration', 'BoonDuration') else 0
            stat_formulas[stat['attribute']] = {
                    'factor': stat['multiplier'],
                    'base_ascended': stat['value'],
                    # Rank is 0 for the major stat of the prefix and 1 for
                    # minor.
                    'rank': rank,
                    }

        # Figure out the base value for exotic trinkets
        num_stats = len(itemstats['attributes'])
        if num_stats == 3:
            # Berserker's exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Ruby Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], dct['Precision']]
        elif num_stats == 4:
            # Viper's exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Black Diamond Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], dct['Precision']]
        elif num_stats == 9:
            # Celestial exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Charged Quartz Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], 0]
        else:
            raise ValueError('unrecognized stat count in %r' % (itemstats,))

        for formula in stat_formulas.values():
            formula['base_exotic'] = base_exotic_by_rank[formula['rank']]

        out[itemstats['name']] = stat_formulas
    return out


TRINKET_SLOTS = {'amulet', 'ring1', 'ring2', 'accessory1', 'accessory2', 'backpack'}


def main():
    points_exotic = get_slot_points({
        'weapon_1h': "Berserker's Pearl Carver",
        'weapon_2h': "Berserker's Pearl Broadsword",
        'helm': 'Bladed Cowl',
        'shoulders': 'Bladed Mantle',
        'coat': 'Bladed Vestments',
        'gloves': 'Bladed Gloves',
        'leggings': 'Bladed Pants',
        'boots': 'Bladed Shoes',
        'amulet': 'Ruby Orichalcum Amulet',
        'ring1': 'Ruby Orichalcum Ring',
        'ring2': 'Ruby Orichalcum Ring',
        'accessory1': 'Ruby Orichalcum Earring',
        'accessory2': 'Ruby Orichalcum Earring',
        'backpack': "Elite's Wings of Glory",
    })

    points_ascended = get_slot_points({
        'weapon_1h': "Zojja's Razor",
        'weapon_2h': "Zojja's Claymore",
        'helm': 'Experimental Envoy Cowl',
        'shoulders': 'Experimental Envoy Mantle',
        'coat': 'Experimental Envoy Vestments',
        'gloves': 'Experimental Envoy Gloves',
        'leggings': 'Experimental Envoy Pants',
        'boots': 'Experimental Envoy Shoes',
        'amulet': 'Scion-Spike Amulet',
        'ring1': 'Mistborn Band',
        'ring2': 'Mistborn Band',
        'accessory1': 'Mists-Charged Treasure',
        'accessory2': 'Mists-Charged Treasure',
        'backpack': 'Relic of Balthazar',
    })

    prefixes = get_pve_stats()

    print('// BEGIN GENERATED CODE')
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    print('// Generated by gen_gear_tables.py for GW2 build %s at %s' %
            (gw2.build.current(), now))

    assert len(points_exotic) == len(points_ascended)
    print('\npub static GEAR_SLOTS: PerGearSlot<SlotInfo> = PerGearSlot {')
    for slot, exotic in points_exotic.items():
        ascended = points_ascended[slot]
        print('    %s: SlotInfo {' % slot)
        print('        points: PerQuality {')
        print('            exotic: %s,' % float(exotic))
        print('            ascended: %s,' % float(ascended))
        print('        },')
        is_trinket = slot in TRINKET_SLOTS
        print('        add_base: %s,' % ('true' if is_trinket else 'false'))
        print('    },')
    print('};')

    print('\npub const NUM_PREFIXES: usize = %d;' % len(prefixes))
    print('\npub static PREFIXES: [Prefix; NUM_PREFIXES] = [')
    for name in sorted(prefixes.keys()):
        prefix = prefixes[name]
        print('    Prefix {')
        print('        name: "%s",' % name)
        print('        formulas: PerStat {')

        def print_formula(field_name, stat_key):
            formula = prefix.get(stat_key)
            if formula is not None:
                print('            %s: StatFormula {' % field_name)
                print('                factor: %s,' % float(formula['factor']))
                print('                base: PerQuality {')
                print('                    exotic: %s,' % float(formula['base_exotic']))
                print('                    ascended: %s,' % float(formula['base_ascended']))
                print('                },')
                print('            },')
            else:
                print('            %s: StatFormula::ZERO,' % field_name)

        print_formula('power', 'Power')
        print_formula('precision', 'Precision')
        print_formula('ferocity', 'CritDamage')
        print_formula('condition_damage', 'ConditionDamage')
        print_formula('expertise', 'ConditionDuration')
        print_formula('vitality', 'Vitality')
        print_formula('toughness', 'Toughness')
        print_formula('healing_power', 'Healing')
        print_formula('concentration', 'BoonDuration')

        print('        },')
        print('    },')
    print('];')

    print('\n// END GENERATED CODE')




if __name__ == '__main__':
    main()

