import gw2.api
import gw2.items

CURRENCY_IMPERIAL_FAVOR = 68

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    materials_raw = gw2.api.fetch('/v2/account/materials')
    materials = {x['id']: x['count'] for x in materials_raw}
    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    total = 0

    favor = wallet.get(CURRENCY_IMPERIAL_FAVOR, 0)
    total += favor
    print('%6d  Imperial Favor' % favor)

    for x in ('Seitung Province', 'New Kaineng City', 'Echovald Wilds', "Dragon's End"):
        name = 'Writ of %s' % x
        item_id = gw2.items.search_name(name)
        count = materials.get(item_id, 0)
        print('%6d  %s' % (count, name))
        total += 5 * count

    print('%6d  Total' % total)

if __name__ == '__main__':
    main()
