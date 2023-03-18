import sys
import gw2.api
import gw2.items
import gw2.trading_post
from bookkeeper import format_price


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()

    item_name, = sys.argv[1:]
    item_id = gw2.items.search_name(item_name, allow_multiple=False)
    listings = gw2.trading_post.get_listings(item_id)

    current_price = listings['sells'][0]['unit_price']
    buyout_cost = 0
    buyout_count = 0
    for sell in listings['sells']:
        # How many cores do we need to sell at this price to break even,
        # compared to selling at the current price?
        #
        # Option 1: sell `N` cores at `p0`, for profit of `N * p0 * 0.85`
        # Option 2: buy `M` cores at cost `c`, then sell `N + M` cores at `p`,
        # for profit of `(N + M) * p * 0.85 - c`
        #
        # p0 = current_price
        # p = listing_price
        # M = buyout_count
        # c = buyout_cost
        # N = break_even_count

        listing_price = sell['unit_price']
        if listing_price == current_price:
            break_even_count = 0
        else:
            break_even_count = (buyout_cost - 0.85 * buyout_count * listing_price) / \
                    (0.85 * (listing_price - current_price))

        print('%10s   buyout = %4d, %12s   break even = %7d' %
                (format_price(listing_price), buyout_count,
                    format_price(buyout_cost), break_even_count))

        buyout_count += sell['quantity']
        buyout_cost += sell['unit_price'] * sell['quantity']

if __name__ == '__main__':
    main()
