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
        input_strs = '  '.join('%4d  %-15.15s' % (count, name)
                for count, name, kind in inputs)
        print('%6d   %s' % (times * output_count, input_strs))

    report([(1, 'Mystic Clover', 'item')])
    report([
        (30, 'Magnetite Shard', 'currency'),
        (2, 'Mystic Coin', 'item'),
        (2, 'Glob of Ectoplasm', 'item'),
        (2, 'Spirit Shard', 'currency'),
        ])
    report([
        (150, 'Fractal Relic', 'currency'),
        (2, 'Mystic Coin', 'item'),
        (2, 'Glob of Ectoplasm', 'item'),
        (2, 'Spirit Shard', 'currency'),
        ])
    report([
        (30, 'Green Prophet Shard', 'currency'),
        (2, 'Mystic Coin', 'item'),
        (2, 'Glob of Ectoplasm', 'item'),
        (2, 'Spirit Shard', 'currency'),
        ])

if __name__ == '__main__':
    main()
