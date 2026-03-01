import bookkeeper
import gw2.api
import gw2.items

CURRENCY_VOE_MAP1 = 83
CURRENCY_VOE_MAP2 = 81

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    inventory = bookkeeper.get_inventory()

    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    total = 0

    n = wallet.get(CURRENCY_VOE_MAP1, 0) / 5
    print('%8.1f  Aether-Rich Sap' % n)
    total += n

    item_id = gw2.items.search_name('Chromatic Sap')
    n = inventory.get(item_id, 0)
    print('%6d    %s' % (n, gw2.items.name(item_id)))
    total += n

    n = wallet.get(CURRENCY_VOE_MAP2, 0) / 5
    print('%8.1f  Antiquated Ducat' % n)
    total += n

    item_id = gw2.items.search_name('Raw Enchanting Stone')
    n = inventory.get(item_id, 0)
    print('%6d    %s' % (n, gw2.items.name(item_id)))
    total += n

    item_id = gw2.items.search_name("Castora: Hero's Choice Chest")
    n = inventory.get(item_id, 0) * 25
    print('%6d    %s' % (n, gw2.items.name(item_id)))
    total += n

    item_id = 91108     # Black Lion Delivery Box (combined)
    n = inventory.get(item_id, 0) * 2.5
    print('%8.1f  %s' % (n, gw2.items.name(item_id)))
    total += n

    print()
    print('%8.1f  Total' % total)

if __name__ == '__main__':
    main()
