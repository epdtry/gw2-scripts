from collections import defaultdict
import datetime
from pprint import pprint
import re
import sys

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

TRINKET_SLOTS = {'amulet', 'ring1', 'ring2', 'accessory1', 'accessory2', 'backpack'}

def do_gear_slots():
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

def do_prefixes():
    prefixes = get_pve_stats()

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


def camel_to_snake(s):
    s = re.sub('[A-Z]', lambda m: '_' + m.group().lower())
    if s.startswith('_'):
        s = s[1:]
    return s

def interpret_bonus(s):
    s = s.lower()
    s = re.sub('<c=@reminder>[^<>]*</c>', '', s)
    s = s.strip()
    s = s.removesuffix('.')

    stat_name_map = {
            'power': 'power',
            'precision': 'precision',
            'ferocity': 'ferocity',
            'ferocity': 'ferocity',
            'condition damage': 'condition_damage',
            'condition damage': 'condition_damage',
            'expertise': 'expertise',
            'vitality': 'vitality',
            'toughness': 'toughness',
            'healing': 'healing_power',
            'healing power': 'healing_power',
            'concentration': 'concentration',
            }
    stat_name_re = '|'.join(re.escape(k) for k in stat_name_map.keys())

    condi_name_map = {
            'poison': 'poison',
            'bleeding': 'bleed',
            'burning': 'burn',
            'burn': 'burn',
            'confusion': 'confuse',
            'torment': 'torment',
            'weakness': None,
            'chill': None,
            'fear': None,
            'cripple': None,
            'vulnerability': None,
            # These are actually CC, not conditions
            'daze': None,
            'stun': None,
            }
    condi_name_re = '|'.join(re.escape(k) for k in condi_name_map.keys())

    boon_name_map = {
            'might': 'might',
            'fury': 'fury',
            'swiftness': 'swiftness',
            'regeneration': 'regeneration',
            'protection': 'protection',
            'quickness': 'quickness',
            }
    boon_name_re = '|'.join(re.escape(k) for k in boon_name_map.keys())

    def match(*re_fmts):
        for re_fmt in re_fmts:
            m = re.fullmatch(re_fmt.format(
                stat_name_re = stat_name_re,
                condi_name_re = condi_name_re,
                boon_name_re = boon_name_re), s)
            if m:
                return m
        return None

    if m := match(r'\+([0-9]+) ({stat_name_re})'):
        return 's.%s += %s;' % (stat_name_map[m.group(2)], float(m.group(1)))
    elif m := match(r'\+([0-9]+) to all stats'):
        return '*s += %s;' % (float(m.group(1)),)
    elif m := match(r'convert ([0-9]+)% of your ({stat_name_re}) into ({stat_name_re})',
            r'([0-9]+)% of (?:your )?({stat_name_re}) is converted '
                '(?:in)?to ({stat_name_re})'):
        return ('distribute', 's.%s += s.%s * %s;' % (
            stat_name_map[m.group(3)], stat_name_map[m.group(2)],
            float(m.group(1)) / 100))

    elif m := match(r'\+(?P<n>[0-9]+)% (?P<c>{condi_name_re}) duration',
            r'increase inflicted (?P<c>{condi_name_re}) duration: (?P<n>[0-9]+)%',
            r'increase the duration of inflicted (?P<c>{condi_name_re}) by (?P<n>[0-9]+)%'):
        condi = condi_name_map[m.group('c')]
        if condi is not None:
            return 'm.condition_duration.%s += %s;' % (condi, float(m.group('n')))
        else:
            return '//m.condition_duration.<%s> += %s;' % (m.group('c'), float(m.group('n')))
    elif m := match(r'\+([0-9]+)% condition duration'):
        return 'm.condition_duration += %s;' % (float(m.group(1)),)
    elif m := match(r'\+([0-9]+)% condition damage'):
        return 'm.condition_damage += %s;' % (float(m.group(1)),)

    elif m := match(r'\+?([0-9]+)% ({boon_name_re}) duration'):
        boon = boon_name_map[m.group(2)]
        if boon is not None:
            return 'm.boon_duration.%s += %s;' % (boon, float(m.group(1)))
        else:
            return '//m.boon_duration.<%s> += %s;' % (m.group(2), float(m.group(1)))
    elif m := match(r'\+([0-9]+)% boon duration'):
        return 'm.boon_duration += %s;' % (float(m.group(1)),)

    elif m := match(r'\+([0-9]+)% (increased )?maximum health'):
        return 'm.max_health += %s;' % (float(m.group(1)),)
    elif m := match(r'increase strike damage dealt by \+([0-9]+)%'):
        return 'm.strike_damage += %s;' % (float(m.group(1)),)
    elif m := match(r'\+([0-9]+)% (?:strike )?damage'):
        return 'm.strike_damage += %s;' % (float(m.group(1)),)
    elif m := match(r'\+([0-9]+)% damage and \+([0-9]+)% condition damage'):
        return 'm.strike_damage += %s; m.condition_damage += %s;' % (
                float(m.group(1)), float(m.group(2)))
    if m := match(r'\+([0-9]+) critical chance'):
        return 'm.crit_chance += %s;' % (float(m.group(1)),)

    elif m := match(r'(?:gain |\+)?([0-9]+)% movement speed'):
        return '// +%s movement speed' % (float(m.group(1)),)
    elif m := match(r'-([0-9]+)% incoming ([^ ]*) duration'):
        return '// -%s incoming %s duration' % (float(m.group(1)), m.group(2))
    elif m := match(r'-([0-9]+)% incoming ([^ ]*) damage'):
        return '// -%s incoming %s damage' % (float(m.group(1)), m.group(2))
    elif m := match(r'\+([0-9]+)% incoming heal effectiveness'):
        return '// +%s incoming heal effectiveness' % (float(m.group(1)),)

    else:
        return '// unknown effect: %r' % (s,)


def print_effect_impl(name, parts):
    print('#[allow(unused_variables)]')
    print('impl Effect for %s {' % name)
    for method, lines in parts.items():
        if len(lines) == 0:
            continue
        print('    fn %s(&self, s: &mut Stats, m: &mut Modifiers) {' % method)
        print('\n'.join('        ' + line for line in lines))
        print('    }')
    print('}')

def print_dispatch_enum(name, items):
    print('\n#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]')
    print('pub enum %s {' % name)
    for item in items:
        print('    %s(%s),' % (item, item))
    print('}')
    print('impl Effect for %s {' % name)
    for method in ['add_permanent', 'distribute', 'add_temporary']:
        print('    fn %s(&self, s: &mut Stats, m: &mut Modifiers) {' % method)
        print('        match *self {')
        for item in items:
            print('            %s::%s(x) => x.%s(s, m),' % (name, item, method))
        print('        }')
        print('    }')
    print('}')
    print('impl %s {' % name)
    print('    pub const COUNT: usize = %d;' % len(items))
    print('    pub fn from_index(i: usize) -> %s {' % name)
    print('        match i {')
    for i, item in enumerate(items):
        print('            %d => %s::%s(%s),' % (i, name, item, item))
    print('            _ => panic!("index {} out of range for %s", i),' % name)
    print('        }')
    print('    }')
    print('    pub fn iter() -> impl Iterator<Item = %s> {' % name)
    print('        (0 .. %s::COUNT).map(%s::from_index)' % (name, name))
    print('    }')
    print('}')
    for item in items:
        print('impl From<%s> for %s {' % (item, name))
        print('    fn from(x: %s) -> %s { %s::%s(x) }' % (item, name, name, item))
        print('}')

def do_runes_sigils(kind):
    items = []

    for item in gw2.items.iter_all():
        if not item['name'].startswith('Superior %s of ' % kind):
            continue
        if item['rarity'] != 'Exotic':
            continue
        if item['name'] == 'Superior Rune of Holding':
            continue
        items.append(item)

    all_names = []
    for item in sorted(items, key=lambda i: i['name']):
        name = item['name']
        name = name.removeprefix('Superior %s of ' % kind)
        name = name.removeprefix('the ')
        name = ''.join(name.split())
        name = re.sub('[^a-zA-Z]', '', name)

        if kind == 'Rune':
            bonus_descs = item['details']['bonuses']
        elif kind == 'Sigil':
            bonus_descs = [item['details']['infix_upgrade']['buff']['description']]
        else:
            raise ValueError('bad rune/sigil kind %r' % kind)

        bonuses = [interpret_bonus(part)
                for bonus in bonus_descs
                for part in re.split(r';|(?<!\bvs)\. \b|\n', bonus)]


        effect_lines = {
                'add_permanent': [],
                'distribute': [],
                'add_temporary': [],
                }
        for line in bonuses:
            if isinstance(line, str):
                effect_lines['add_permanent'].append(line)
            else:
                func, line = line
                effect_lines[func].append(line)

        print('\n#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]')
        print('pub struct %s;' % name)
        print_effect_impl(name, effect_lines)

        all_names.append(name)

    print_dispatch_enum(kind, all_names)




def main():
    modes = sys.argv[1:]
    if len(modes) == 0:
        raise ValueError('expected at least 1 mode argument')

    print('// BEGIN GENERATED CODE')
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    print('// Generated by gen_gear_tables.py for GW2 build %s at %s' %
            (gw2.build.current(), now))

    for mode in modes:
        if mode == 'gear':
            do_gear_slots()
        elif mode == 'prefixes':
            do_prefixes()
        elif mode == 'runes':
            do_runes_sigils('Rune')
        elif mode == 'sigils':
            do_runes_sigils('Sigil')
        else:
            raise ValueError('unknown mode %r' % mode)

    print('\n// END GENERATED CODE')




if __name__ == '__main__':
    main()

