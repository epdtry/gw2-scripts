import sys
import gw2.api
import gw2.items
import gw2.recipes
import bookkeeper
from bookkeeper import format_price


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    args = sys.argv[1:]
    if len(args) == 0:
        js = list(range(1, 23))
    else:
        js = [int(args[0])]

    related_items = bookkeeper.gather_related_items(
            gw2.items.search_name('+%d Agony Infusion' % i) for i in range(2, 23))
    buy_prices, sell_prices = bookkeeper.get_prices(related_items)

    bookkeeper.set_strategy_params(
            buy_prices,
            {gw2.items.search_name('+%d Agony Infusion' % i) for i in range(2, 23)},
            bookkeeper.policy_forbid_craft(),
            bookkeeper.policy_can_craft_recipe,
            )

    catalyst_item_id = gw2.items.search_name('Thermocatalytic Reagent')
    catalyst_cost = buy_prices.get(catalyst_item_id, 0)

    results = []

    for i in range(1, 23):
        base_infusion_item_id = gw2.items.search_name('+%d Agony Infusion' % i)
        base_infusion_cost = buy_prices.get(base_infusion_item_id, 0)

        for j in (j for j in js if j >= i):
            name = '+%d Agony Infusion' % j
            item_id = gw2.items.search_name(name)
            buy_price = buy_prices.get(item_id, 0)
            sell_price = sell_prices.get(item_id, 0)

            n = 2 ** (j - i)
            craft_cost = base_infusion_cost * n + catalyst_cost * (n - 1)
            profit = sell_price * 0.85 - craft_cost
            roi = profit / craft_cost
            if profit >= 0:
                results.append((roi, i, j, craft_cost, sell_price))

            #buy_discount = craft_cost - buy_price
            #buy_discount_pct = 100 * buy_discount / craft_cost
            #sell_discount = craft_cost - sell_price
            #sell_discount_pct = 100 * sell_discount / craft_cost
            #print('%-20s  %12s  %12s  %12s  %7.1f%%  %12s  %12s  %7.1f%%' % (
            #    name, format_price(craft_cost),
            #    format_price(buy_price), format_price(buy_discount), buy_discount_pct,
            #    format_price(sell_price), format_price(sell_discount), sell_discount_pct,
            #    ))

    seen = set()
    for roi, i, j, craft_cost, sell_price in reversed(sorted(results)):
        if j in seen:
            continue
        #seen.add(j)
        print('%2d -> %2d  %10s  %10s  %7.1f%%' % (
            i, j, format_price(craft_cost), format_price(sell_price), 100 * roi))



if __name__ == '__main__':
    main()
