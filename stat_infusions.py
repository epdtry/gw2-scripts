from collections import defaultdict
import sys
import gw2.api
import gw2.items
import gw2.recipes
import bookkeeper


STAT_ALIASES = [
        ('BoonDuration', 'Concentration'),
        ('ConditionDamage', 'condi',),
        ('ConditionDuration', 'Expertise'),
        ('HealingPower', 'Healing'),
        ('Power',),
        ('Precision',),
        ('Toughness',),
        ('Vitality',),
        ]

def resolve_alias(name, aliases):
    name = name.lower()
    found = []
    found_exact = []
    for row in aliases:
        match = False
        match_exact = False
        for x in row:
            x = x.lower()
            if x == name:
                match_exact = True
            if x.startswith(name):
                match = True
        if match:
            found.append(row[0])
        if match_exact:
            found_exact.append(row[0])

    if found_exact:
        found = found_exact

    if len(found) == 0:
        raise ValueError('unrecognized input %r' % (name,))
    elif len(found) >= 2:
        raise ValueError('input %r is ambiguous: could be %r' % (name, found))

    return found[0]

def all_for_stat(stat):
    item_ids = []
    for item in gw2.items.iter_all():
        if item['type'] != 'UpgradeComponent':
            continue
        infix = item['details'].get('infix_upgrade')
        if infix is None:
            continue

        has_9_ar = False
        has_5_stat = False
        for attr in infix['attributes']:
            if attr['attribute'] == 'AgonyResistance' and attr['modifier'] == 9:
                has_9_ar = True
            if attr['attribute'] == stat and attr['modifier'] == 5:
                has_5_stat = True

        if not has_9_ar or not has_5_stat:
            continue
        item_ids.append(item['id'])

    buy_prices, sell_prices = bookkeeper.get_prices(item_ids)

    lines = []
    for item_id in item_ids:
        price = sell_prices.get(item_id)
        if price is None:
            continue
        lines.append((price, gw2.items.name(item_id)))
    lines.sort()

    for (price, name) in lines:
        print('%10s  %s' % (bookkeeper.format_price(price), name))

def cheapest_per_stat():
    item_ids_for_stat = defaultdict(list)
    for item in gw2.items.iter_all():
        if item['type'] != 'UpgradeComponent':
            continue
        infix = item['details'].get('infix_upgrade')
        if infix is None:
            continue

        has_9_ar = False
        plus_5_stat = []
        for attr in infix['attributes']:
            if attr['attribute'] == 'AgonyResistance' and attr['modifier'] == 9:
                has_9_ar = True
            if attr['modifier'] == 5:
                plus_5_stat.append(attr['attribute'])

        if not has_9_ar or len(plus_5_stat) == 0:
            continue
        if len(plus_5_stat) >= 2:
            print('item %d %r has multiple stats? %r' % (item['id'], item['name'], plus_5_stat))
            continue
        item_ids_for_stat[plus_5_stat[0]].append(item['id'])

    buy_prices, sell_prices = bookkeeper.get_prices([item_id
            for item_ids in item_ids_for_stat.values() for item_id in item_ids])

    for stat in sorted(item_ids_for_stat.keys()):
        item_ids = item_ids_for_stat[stat]
        cheapest_price = None
        cheapest_item_id = None
        for item_id in item_ids:
            price = sell_prices.get(item_id)
            if price is None:
                continue
            if cheapest_price is None or price < cheapest_price:
                cheapest_price = price
                cheapest_item_id = item_id

        print('%-17s  %10s  %s' % (stat,
            bookkeeper.format_price(cheapest_price),
            gw2.items.name(cheapest_item_id)))

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    if len(sys.argv) == 1:
        cheapest_per_stat()
    else:
        stat, = sys.argv[1:]
        stat = resolve_alias(stat, STAT_ALIASES)
        all_for_stat(stat)


if __name__ == '__main__':
    main()
