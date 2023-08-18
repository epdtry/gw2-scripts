from collections import defaultdict
import gw2.api
import gw2.items
import gw2.trading_post
from bookkeeper import format_price, parse_timestamp

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    sell_item_id = gw2.items.search_name('Piece of Dragon Jade')
    start_time = '2023-05-23T14'
    base_sell_price = 10000

    sells = gw2.trading_post._get_history('sells')[0]
    count = 0
    revenue = 0
    base_revenue = 0
    for t in sells.iter():
        if t['item_id'] != sell_item_id:
            continue
        if t['purchased'] < '2023-05-23T14':
            continue
        elif t['purchased'] < '2023-05-26T14':
            base_price = 10000
        else:
            base_price = 11000
        revenue += t['quantity'] * t['price'] * 0.85
        base_revenue += t['quantity'] * base_price * 0.85
        count += t['quantity']
        #print(t)

    jade_count = count

    buys = gw2.trading_post._get_history('buys')[0]
    buys_list = sorted(
            (t for t in buys.iter() if t['purchased'] >= start_time),
                key=lambda t: t['purchased'])

    orig_need = {
            'pure_jade': count * 4,
            'insignia': count * 30 / 75 * 1,
            'gossamer_bolt': count * 30 / 75 * 5,
            'gossamer_thread': count * 30 / 75 * 3,
            'ecto': count * 2,
            'orichalcum_ingot': count * 5,
            }
    need = orig_need.copy()

    item_kind_map = {
            gw2.items.search_name('Chunk of Pure Jade'): ('pure_jade', 1),
            gw2.items.search_name("Dire Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name("Rabid Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name("Magi's Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name("Shaman's Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name("Soldier's Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name("Cavalier's Intricate Gossamer Insignia"): ('insignia', 1),
            gw2.items.search_name('Bolt of Gossamer'): ('gossamer_bolt', 1),
            gw2.items.search_name('Gossamer Scrap'): ('gossamer_bolt', 1/2),
            gw2.items.search_name('Glob of Ectoplasm'): ('ecto', 1),
            gw2.items.search_name('Orichalcum Ingot'): ('orichalcum_ingot', 1),
            gw2.items.search_name('Orichalcum Ore'): ('orichalcum_ingot', 1/2),
            }

    material_costs = { kind: 0 for kind in need.keys() }

    buy_counts = {i: 0 for i in item_kind_map.keys()}
    buy_totals = {i: 0 for i in item_kind_map.keys()}

    # Gossamer thread comes from a vendor
    used = need['gossamer_thread']
    ITEM_THREAD = gw2.items.search_name('Spool of Gossamer Thread')
    material_costs['gossamer_thread'] = used * 64
    need['gossamer_thread'] = 0
    buy_counts[ITEM_THREAD] = used
    buy_totals[ITEM_THREAD] = used * 64

    for t in reversed(buys_list):
        x = item_kind_map.get(t['item_id'])
        if x is None:
            continue
        kind, frac = x
        used = min(t['quantity'], need[kind] / frac)
        need[kind] -= used * frac
        material_costs[kind] += used * t['price']
        buy_counts[t['item_id']] += used
        buy_totals[t['item_id']] += used * t['price']

        if need[kind] <= 1e-3 and all(x <= 1e-3 for x in need.values()):
            print('stop early at %s' % t['purchased'])
            break

    print('need', need)

    print('Items bought:')
    for item_id, count in buy_counts.items():
        cost = buy_totals[item_id]
        print('%12s  %12s  %6d  %s' %
                (format_price(cost),
                    format_price(cost / count) if count != 0 else 0, count,
                    gw2.items.name(item_id)))
    print()

    print('Costs:')
    for kind, cost in material_costs.items():
        count = orig_need[kind]
        print('%12s  %12s  %6d  %s' %
                (format_price(cost), format_price(cost / count), count, kind))
    total_cost = sum(material_costs.values())
    #print('%12s  %12s  %6d  %s' %
    #    (format_price(total_cost), format_price(total_cost / jade_count),
    #        jade_count, gw2.items.name(item_id)))

    print()
    print('Quantity:     %6d  %s' % (jade_count, gw2.items.name(sell_item_id)))
    print('Total Cost:     %12s' % format_price(total_cost))
    print('Revenue:        %12s' % format_price(revenue))
    print('Profit:         %12s (%.1f%%)' %
            (format_price(revenue - total_cost),
                100 * (revenue - total_cost) / total_cost))

    print()
    print('Average cost:        %12s' % format_price(total_cost / jade_count))
    print('Average sell price:  %12s' % format_price(revenue / 0.85 / jade_count))
    print('Average revenue:     %12s' % format_price(revenue / jade_count))

if __name__ == '__main__':
    main()
