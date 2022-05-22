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

    inventory = bookkeeper.get_inventory()
    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    wallet_shards = wallet.get(CURRENCY_SPIRIT_SHARDS, 0)
    fractal_shards = wallet.get(CURRENCY_FRACTAL_RELIC, 0) / 35
    pristine_fractal_shards = wallet.get(CURRENCY_PRISTINE_FRACTAL_RELIC, 0) * 15 / 35
    tome_shards = inventory.get(gw2.items.search_name('Tome of Knowledge'), 0)
    writ_shards = inventory.get(gw2.items.search_name('Writ of Experience'), 0) / 20

    total = wallet_shards + fractal_shards + pristine_fractal_shards + \
            tome_shards + writ_shards

    philosopher_shards = inventory.get(gw2.items.search_name("Philosopher's Stone"), 0) * 0.1
    mystic_crystal_shards = inventory.get(gw2.items.search_name('Mystic Crystal'), 0) * 0.6
    clover_shards = inventory.get(gw2.items.search_name('Mystic Clover'), 0) * 1.8

    clover_total = philosopher_shards + mystic_crystal_shards + clover_shards

    augur_shards = inventory.get(gw2.items.search_name("Augur's Stone"), 0) * 20
    vision_shards = inventory.get(gw2.items.search_name('Vision Crystal'), 0) * 20
    lesser_vision_shards = inventory.get(gw2.items.search_name('Lesser Vision Crystal'), 0) * 20

    vision_total = augur_shards + vision_shards + lesser_vision_shards

    print('%6.1f  Spirit Shard' % wallet_shards)
    print('%6.1f  from Fractal Relic' % fractal_shards)
    print('%6.1f  from Pristine Fractal Relic' % pristine_fractal_shards)
    print('%6.1f  from Tome of Knowledge' % tome_shards)
    print('%6.1f  from Writ of Experience' % writ_shards)
    print('%6.1f  Total' % total)
    print('')
    print("%6.1f  in Philosopher's Stone" % philosopher_shards)
    print('%6.1f  in Mystic Crystal' % mystic_crystal_shards)
    print('%6.1f  in Mystic Clover' % clover_shards)
    print('%6.1f  Total' % clover_total)
    print('')
    print("%6.1f  in Augur's Stone" % augur_shards)
    print('%6.1f  in Vision Crystal' % vision_shards)
    print('%6.1f  in Lesser Vision Crystal' % lesser_vision_shards)
    print('%6.1f  Total' % vision_total)
    print('')
    print('%6.1f  Grand Total' % (total + clover_total + vision_total))

if __name__ == '__main__':
    main()
