import gw2.api
import gw2.trading_post
from bookkeeper import format_price, parse_timestamp

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    buys = gw2.trading_post._get_history('buys')[0]
    total_buy = 0
    oldest_buy = None
    oldest_buy_str = None
    for t in buys.iter():
        total_buy += t['quantity'] * t['price']
        timestamp = parse_timestamp(t['purchased'])
        if oldest_buy is None or timestamp < oldest_buy:
            oldest_buy = timestamp
            oldest_buy_str = t['purchased']

    sells = gw2.trading_post._get_history('sells')[0]
    total_sell = 0
    for t in sells.iter():
        timestamp = parse_timestamp(t['purchased'])
        if timestamp < oldest_buy:
            continue
        total_sell += t['quantity'] * t['price'] * 0.85

    print('\nTotals since %s:' % oldest_buy_str)

    print('Bought:  %12s' % format_price(total_buy))
    print('Sold:    %12s' % format_price(total_sell))
    profit = total_sell - total_buy
    print('Profit:  %12s' % format_price(profit))
    print('ROI:     %7.1f%%' % (100 * profit / total_buy))

if __name__ == '__main__':
    main()
