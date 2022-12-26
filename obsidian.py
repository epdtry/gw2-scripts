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
        produces_str = '' if output_count == 1 else ' (produces %d)' % output_count
        print('%6d   %s%s' % (times * output_count, input_strs, produces_str))

    report([(1, 'Obsidian Shard', 'item')])
    report([(2100, 'Karma', 'currency')])
    report([(3, 'Laurel', 'currency')], output_count=3)
    report([(30, 'Fractal Relic', 'currency'), (96, 'Coin', 'currency')])
    report([(2, 'Pristine Fractal Relic', 'currency'), (96, 'Coin', 'currency')])
    report([(50, 'Bandit Crest', 'currency'), (96, 'Coin', 'currency')])
    report([(25, 'Airship Part', 'currency'), (1050, 'Karma', 'currency')])
    report([(25, 'Lump of Aurillium', 'currency'), (1050, 'Karma', 'currency')])
    report([(25, 'Ley Line Crystal', 'currency'), (1050, 'Karma', 'currency')])

    report([(100, 'Unbound Magic', 'currency'), (96, 'Coin', 'currency')])
    # Consume X map currency -> 100 unbound magic -> obsidian
    report([(3, 'Blood Ruby', 'item'), (96, 'Coin', 'currency')])
    report([(3, 'Petrified Wood', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Fresh Winterberry', 'item'), (96, 'Coin', 'currency')])
    report([(3, 'Jade Shard', 'item'), (96, 'Coin', 'currency')])
    report([(3, 'Fire Orchid Blossom', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Orrian Pearl', 'item'), (96, 'Coin', 'currency')])

    report([(100, 'Volatile Magic', 'currency'), (96, 'Coin', 'currency')])
    # Consume X map currency -> 100 volatile -> obsidian
    report([(25, 'Kralkatite Ore', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Difluorite Crystal', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Inscribed Shard', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Lump of Mistonium', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Branded Mass', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Mistborn Mote', 'item'), (96, 'Coin', 'currency')])
    report([(5, 'Difluorite Crystal', 'item'), (96, 'Coin', 'currency')])

    # 75 eternal ice -> 10 mistborn mote -> 200 VM -> 2 obsidian
    report([(75, 'Eternal Ice Shard', 'item'), (2688, 'Karma', 'currency')],
            output_count=2)
    # 10 blue shards -> 5 mistborn mote -> 100 VM -> obsidian
    report([(10, 'Blue Prophet Shard', 'currency'), (96, 'Coin', 'currency')])
    # 10 green shards -> 10 blue shards, then as above
    report([(10, 'Green Prophet Shard', 'currency'), (96, 'Coin', 'currency')])
    report([
        (45, 'WvW Skirmish Claim Ticket', 'currency'),
        #(20, 'Memory of Battle', 'item'),
        ], output_count=15)
    # 100 jade sliver -> 10 mistborn mote -> 200 VM -> 2 obsidian
    report([(100, 'Jade Sliver', 'currency'),],
            output_count=2)

if __name__ == '__main__':
    main()
