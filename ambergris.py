import sys
import gw2.api
import gw2.items
import gw2.recipes
import bookkeeper
from bookkeeper import format_price


FISH_TIERS = (
        'Fine',
        'Fabulous',
        'Flavorful',
        'Fantastic',
        'Flawless',
        )


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    target_item_id = gw2.items.search_name('Chunk of Ancient Ambergris')

    item_ids = (target_item_id,) + \
            tuple(gw2.items.search_name('%s Fish Fillet' % x) for x in FISH_TIERS)
    related_items = bookkeeper.gather_related_items(item_ids)
    buy_prices, sell_prices = bookkeeper.get_prices(related_items)

    for i, tier in enumerate(FISH_TIERS):
        name = '%s Fish Fillet' % tier
        source_item_id = gw2.items.search_name(name)
        count = 10 * 5 ** (len(FISH_TIERS) - i - 1)
        cost = count * buy_prices[source_item_id]
        profit = sell_prices[target_item_id] * 0.85 - cost
        print('%10d  %-30.30s  %10s  %10s  %7.1f%%' % (
            count, name, format_price(cost), format_price(profit), profit / cost * 100))


if __name__ == '__main__':
    main()
