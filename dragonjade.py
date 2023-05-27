from collections import defaultdict
import gw2.api
import gw2.items
import gw2.trading_post
from bookkeeper import format_price, parse_timestamp

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    item_id = gw2.items.search_name('Piece of Dragon Jade')
    base_sell_price = 10000

    sells = gw2.trading_post._get_history('sells')[0]
    count = 0
    revenue = 0
    base_revenue = 0
    for t in sells.iter():
        if t['item_id'] != item_id:
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
        print(t)
    print('Sold:       %5d  %s' % (count, gw2.items.name(item_id)))
    print('Revenue:        %12s' % format_price(revenue))
    print('Base revenue:   %12s' % format_price(base_revenue))
    excess_profit = revenue - base_revenue
    print('Excess profit:  %12s' % format_price(excess_profit))

if __name__ == '__main__':
    main()
