from collections import namedtuple, defaultdict
import json
import os
from pprint import pprint
import requests
import sys
import textwrap

API_BASE = 'https://api.guildwars2.com'

API_KEY = None

CACHE_DIR = None

def get(path):
    if CACHE_DIR is not None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_key = path.replace('/', '__')
        cache_path = os.path.join(CACHE_DIR, cache_key)
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return json.load(f)

    headers = {}
    if API_KEY is not None:
        headers['Authorization'] = 'Bearer ' + API_KEY
    j = requests.get(API_BASE + path, headers=headers).json()

    if CACHE_DIR is not None:
        with open(cache_path, 'w') as f:
            json.dump(j, f)

    return j

Item = namedtuple('Item', ('level', 'rarity', 'stats', 'upgrades'))

def get_item_stats(item, instance):
    infix = item.get('infix_upgrade')
    if infix is not None:
        return infix['id']

    stat_choices = item.get('stat_choices')
    if stat_choices is not None and len(stat_choices) > 0:
        stats = instance.get('stats')
        if stats is not None:
            return stats['id']

def mk_item(item, instance, items):
    level = item['level']
    rarity = item['rarity']



    #stats = 

Context = namedtuple('Context', ('items', 'itemstats', 'itemstats_seen', 'upgrades_seen'))

ItemstatsUse = namedtuple('ItemstatsUse',
        ('infix_upgrade', 'attribute_adjustment', 'slot'))

def describe_item(cx, equip, item):
    out = []
    details = item.get('details', {})

    out.append(details.get('type') or item['type'])

    prefix = None
    stats = equip.get('stats') or details.get('infix_upgrade')
    if stats is not None:
        itemstats_id = stats['id']
        prefix = cx.itemstats[itemstats_id]['name']
        cx.itemstats_seen[itemstats_id].append(ItemstatsUse(
            stats, details['attribute_adjustment'], equip['slot']))

    rarity = item['rarity']

    level = None
    if item['level'] != 80:
        level = '(%d)' % item['level']

    out.append(' '.join(x for x in (rarity, level, prefix) if x is not None))

    upgrades = equip.get('upgrades')
    if upgrades is not None:
        for u in upgrades:
            name = cx.items[u]['name']
            name = name.replace('Rune of the ', 'Rune: ')
            name = name.replace('Rune of ', 'Rune: ')
            name = name.replace('Sigil of the ', 'Sigil: ')
            name = name.replace('Sigil of ', 'Sigil: ')
            name = name.replace('Crest of the ', 'Crest: ')
            name = name.replace('Crest of ', 'Crest: ')
            grade, _, rest = name.partition(' ')
            if grade in ('Minor', 'Major'):
                name = '%s (%s)' % (rest, grade)
            elif grade == 'Superior':
                name = rest
            out.append(name)

            cx.upgrades_seen[u] += 1

    return out


def describe_upgrade(cx, upgrade_id, count):
    out = []
    item = cx.items[upgrade_id]
    details = item.get('details', {})


    if details['type'] == 'Rune':
        out.append('%s (%d):' % (item['name'], count))
        for bonus in details['bonuses'][:count]:
            out.append('  ' + bonus)

    else:
        count_str = ''
        if details['type'] != 'Sigil':
            count_str = ' (%d)' % count
        out.append(item['name'] + count_str + ':')

        desc = details['infix_upgrade']['buff']['description'] \
                .partition('<c=@reminder>')[0]
        if '<br>' in desc:
            desc_lines = desc.split('<br>')
        else:
            desc_lines = desc.split('\n')
        for line in desc_lines:
            line = line.strip()
            if line == '':
                continue
            out.append('  ' + line)

    return out

def slot_mask_char(slot, slots_used):
    if slot is None:
        return ' '
    elif slot in slots_used:
        return '*'
    else:
        return '-'

ATTRIBUTE_ORDER = [
        ('Power', 'Power'),
        ('Precision', 'Precision'),
        ('Toughness', 'Toughness'),
        ('Vitality', 'Vitality'),
        ('CritDamage', 'Ferocity'),
        ('Healing', 'Healing Power'),
        ('ConditionDamage', 'Condition Damage'),
        ('BoonDuration', 'Concentration'),
        ('ConditionDuration', 'Expertise'),
        ]

ATTRIBUTE_INDEX_MAP = {k: i for i, (k, _) in enumerate(ATTRIBUTE_ORDER)}

def describe_itemstats(cx, itemstats_id, uses, slot_order):
    out = []
    itemstats = cx.itemstats.get(itemstats_id)
    if itemstats is None:
        return []

    name = itemstats['name']

    slots_used = set(use.slot for use in uses)
    slot_mask = ''.join(slot_mask_char(slot, slots_used) for slot in slot_order)

    name_width = STATS_COLUMN_WIDTH - (3 + len(slot_mask))
    fmt = '%-{w}.{w}s (%s)'.format(w=name_width)
    out.append(fmt % (name, slot_mask))

    #pprint(itemstats)
    #pprint(uses)

    stat_sum = defaultdict(int)
    for use in uses:
        for a in itemstats['attributes']:
            k = ATTRIBUTE_INDEX_MAP[a['attribute']]
            stat_sum[k] += int(
                    a['multiplier'] * use.attribute_adjustment + a['value'])

    for idx, amount in sorted(stat_sum.items(), key=lambda x: (-x[1], x[0])):
        out.append('  +%d %s' % (amount, ATTRIBUTE_ORDER[idx][1]))

    return out

EQUIPMENT_COLUMN_WIDTH = 24
STATS_COLUMN_WIDTH = 33
UPGRADE_COLUMN_WIDTH = 44

def main():
    global API_KEY
    if len(sys.argv) == 2:
        API_KEY = sys.argv[1]
        j = get('/v2/characters')
        for name in j:
            print(name)
        return
    elif len(sys.argv) == 3:
        API_KEY = sys.argv[1]
        char_name = sys.argv[2]
    else:
        raise ValueError('usage: python3 showbuild.py <API_KEY> [character]')

    print('get character info')
    j_char = get('/v2/characters/%s' % requests.utils.quote(char_name))
    equip = {x['slot']: x for x in j_char['equipment']}

    print('get equipped item details')
    j_items = get('/v2/items?ids=' + ','.join(str(x['id']) for x in equip.values()))
    items = {x['id']: x for x in j_items}

    upgrade_ids = set()
    for e in equip.values():
        for i in e.get('upgrades', []) + e.get('infusions', []):
            upgrade_ids.add(i)
    for i in items.values():
        details = i.get('details')
        if details is None:
            continue
        suffix_item = details.get('suffix_item_id')
        if suffix_item is not None:
            upgrade_ids.add(suffix_item)
        secondary_suffix_item = details.get('secondary_suffix_item_id')
        if secondary_suffix_item is not None and secondary_suffix_item != '':
            upgrade_ids.add(int(secondary_suffix_item))
    print('get upgrade item details')
    j_upgrade_items = get('/v2/items?ids=' + ','.join(str(i) for i in upgrade_ids))
    items.update({x['id']: x for x in j_upgrade_items})

    itemstats_ids = set()
    for i in items.values():
        details = i.get('details')
        if details is None:
            print('item %s: no details' % i['id'])
            continue
        infix = details.get('infix_upgrade')
        if infix is not None:
            itemstats_ids.add(infix['id'])
            print('item %s: itemstats %s' % (i['id'], infix['id']))
        else:
            print('item %s: no infix_upgrade' % i['id'])
    for e in equip.values():
        stats = e.get('stats')
        if stats is not None:
            itemstats_ids.add(stats['id'])
    print('get itemstats details (%d)' % len(itemstats_ids))
    j_itemstats = get('/v2/itemstats?ids=' + ','.join(str(i) for i in itemstats_ids))
    itemstats = {x['id']: x for x in j_itemstats}


    pprint(equip)
    pprint(items)
    pprint(itemstats)

    weapon_id = equip['WeaponA1']['id']
    weapon_name = items[weapon_id]['name']
    print(weapon_id, weapon_name)

    cx = Context(items, itemstats, defaultdict(list), defaultdict(int))


    columns = []
    column_width = []
    column_format = ''
    slot_order = []

    def start_column(width):
        nonlocal column_format
        columns.append([])
        column_width.append(width)
        if len(column_format) > 0:
            column_format += ' | '
        column_format += '%-{w}.{w}s'.format(w=width)

    def emit_wrapped_line(line):
        indent_width = len(line) - len(line.lstrip())
        indent = line[:indent_width]
        line = line[indent_width:]
        columns[-1].extend(textwrap.wrap(line, column_width[-1],
            initial_indent=indent, subsequent_indent=indent + '  '))

    def emit_wrapped_lines(lines):
        for line in lines:
            emit_wrapped_line(line)

    def emit_lines(lines):
        if len(lines) == 0:
            return
        col = columns[-1]
        if len(col) > 0:
            col.append('')
        emit_wrapped_lines(lines)

    def emit_header(name):
        col = columns[-1]
        if len(col) > 0:
            col.append('')
        pad_amount = column_width[-1] - (5 + len(name))
        emit_wrapped_line('=== %s %s' % (name, '=' * pad_amount))

        if len(slot_order) > 0:
            slot_order.append(None)

    def emit_slot(slot):
        e = equip.get(slot)
        if e is None:
            return
        item = items[e['id']]
        col = columns[-1]
        if len(col) > 0:
            col.append('')
        emit_wrapped_lines(describe_item(cx, e, item))
        slot_order.append(slot)

    start_column(EQUIPMENT_COLUMN_WIDTH)
    emit_header('Weapons')
    emit_slot('WeaponA1')
    emit_slot('WeaponA2')
    if 'WeaponB1' in equip or 'WeaponB2' in equip:
        emit_header('Alt. Weapons')
        emit_slot('WeaponB1')
        emit_slot('WeaponB2')

    start_column(EQUIPMENT_COLUMN_WIDTH)
    emit_header('Armor')
    emit_slot('Helm')
    emit_slot('Shoulders')
    emit_slot('Coat')
    emit_slot('Gloves')
    emit_slot('Leggings')
    emit_slot('Boots')

    start_column(EQUIPMENT_COLUMN_WIDTH)
    emit_header('Trinkets')
    emit_slot('Backpack')
    emit_slot('Accessory1')
    emit_slot('Accessory2')
    emit_slot('Amulet')
    emit_slot('Ring1')
    emit_slot('Ring2')

    print('\n')

    for i in range(max(len(c) for c in columns)):
        parts = []
        for c in columns:
            if i < len(c):
                parts.append(c[i])
            else:
                parts.append('')

        print(column_format % tuple(parts))


    columns = []
    column_width = []
    column_format = ''

    stats_slot_order = slot_order
    slot_order = []

    start_column(STATS_COLUMN_WIDTH)
    emit_header('Prefixes')

    itemstats_order = sorted(
            (i for i in cx.itemstats_seen.keys() if i in cx.itemstats),
            key=lambda i: cx.itemstats[i]['name'])
    for itemstats_id in itemstats_order:
        emit_lines(describe_itemstats(cx, itemstats_id,
                cx.itemstats_seen[itemstats_id], stats_slot_order))

    start_column(UPGRADE_COLUMN_WIDTH)
    emit_header('Upgrades')

    upgrade_order = sorted(cx.upgrades_seen.keys(), 
            key=lambda i: (cx.items[i]['details']['type'], cx.items[i]['name']))
    for upgrade_id in upgrade_order:
        emit_lines(describe_upgrade(cx, upgrade_id, cx.upgrades_seen[upgrade_id]))

    print('\n')

    for i in range(max(len(c) for c in columns)):
        parts = []
        for c in columns:
            if i < len(c):
                parts.append(c[i])
            else:
                parts.append('')

        print(column_format % tuple(parts))


if __name__ == '__main__':
    main()
