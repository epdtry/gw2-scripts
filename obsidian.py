import gw2.api
import gw2.items
import bookkeeper

CURRENCY_SPIRIT_SHARDS = 23
CURRENCY_FRACTAL_RELIC = 7
CURRENCY_PRISTINE_FRACTAL_RELIC = 24

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    currencies_raw = gw2.api.fetch('/v2/currencies?ids=all')
    currencies_by_name = {x['name']: x['id'] for x in currencies_raw}

    inventory = bookkeeper.get_inventory()
    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    def count_input(kind, name):
        if kind == 'item':
            return inventory.get(gw2.items.search_name(name), 0)
        elif kind == 'currency':
            return wallet.get(currencies_by_name[name], 0)
        else:
            raise ValueError('bad input kind %r' % (kind,))

    def report(inputs, output_count=1):
        times = min(count_input(kind, name) // count
                for count, name, kind in inputs)
        input_strs = '  '.join('%6d  %-15.15s' % (count, name)
                for count, name, kind in inputs)
        print('%6d   %s' % (times * output_count, input_strs))

    report([(1, 'Obsidian Shard', 'item')])
    report([(2100, 'Karma', 'currency')])
    report([(3, 'Laurel', 'currency')], output_count=3)
    report([(30, 'Fractal Relic', 'currency'), (96, 'Coin', 'currency')])
    report([(50, 'Bandit Crest', 'currency'), (96, 'Coin', 'currency')])
    report([(100, 'Unbound Magic', 'currency'), (96, 'Coin', 'currency')])
    report([(100, 'Volatile Magic', 'currency'), (96, 'Coin', 'currency')])
    report([(25, 'Airship Part', 'currency'), (1050, 'Karma', 'currency')])
    report([(25, 'Lump of Aurillium', 'currency'), (1050, 'Karma', 'currency')])
    report([(25, 'Ley Line Crystal', 'currency'), (1050, 'Karma', 'currency')])
    report([(45, 'WvW Skirmish Claim Ticket', 'currency'), (20, 'Memory of Battle', 'item')])

if __name__ == '__main__':
    main()
