from collections import defaultdict
import gw2.api
import gw2.items
import gw2.trading_post
from bookkeeper import format_price, parse_timestamp

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    buys = gw2.trading_post._get_history('buys')[0]
    total_buy = 0
    buy_item_counts = defaultdict(int)
    buy_item_prices = defaultdict(int)
    oldest_buy = None
    oldest_buy_str = None
    for t in buys.iter():
        total_buy += t['quantity'] * t['price']
        buy_item_counts[t['item_id']] += t['quantity']
        buy_item_prices[t['item_id']] += t['quantity'] * t['price']
        timestamp = parse_timestamp(t['purchased'])
        if oldest_buy is None or timestamp < oldest_buy:
            oldest_buy = timestamp
            oldest_buy_str = t['purchased']

    sells = gw2.trading_post._get_history('sells')[0]
    total_sell = 0
    sell_item_counts = defaultdict(int)
    sell_item_prices = defaultdict(int)
    for t in sells.iter():
        timestamp = parse_timestamp(t['purchased'])
        if timestamp < oldest_buy:
            continue
        total_sell += t['quantity'] * t['price'] * 0.85
        sell_item_counts[t['item_id']] += t['quantity']
        sell_item_prices[t['item_id']] += t['quantity'] * t['price'] * 0.85

    def top_n(xs, n=None):
        s = sorted(xs, key=lambda x: x[1], reverse=True)
        if n is not None:
            s = s[:n]
        return s

    #N = 10
    N = None

    print('\nTop items bought:')
    for item_id, count in top_n(buy_item_counts.items(), N):
        print('%8d  %s' % (count, gw2.items.name(item_id)))

    print('\nTop items bought, by gold spent:')
    for item_id, price in top_n(buy_item_prices.items(), N):
        print('%12s  %s' % (format_price(price), gw2.items.name(item_id)))

    print('\nTop items sold:')
    for item_id, count in top_n(sell_item_counts.items(), N):
        print('%8d  %s' % (count, gw2.items.name(item_id)))

    print('\nTop items sold, by gold received:')
    for item_id, price in top_n(sell_item_prices.items(), N):
        print('%12s  %s' % (format_price(price), gw2.items.name(item_id)))

    print('\nTotals since %s:' % oldest_buy_str)

    print('Bought:  %12s' % format_price(total_buy))
    print('Sold:    %12s' % format_price(total_sell))
    profit = total_sell - total_buy
    print('Profit:  %12s' % format_price(profit))
    print('ROI:     %7.1f%%' % (100 * profit / total_buy))

if __name__ == '__main__':
    main()
