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

    def report_part(count, cost):
        if cost is None:
            return ' ' * 10
        return '%3d x %-4d' % (count // cost, cost)

    def report(input_name, input_kind,
            amulet=None, ring=None, accessory=None, back=None, desc=None,
            override_count=None):
        count = count_input(input_kind, input_name) \
                if override_count is None else override_count
        parts = [
                report_part(count, amulet),
                report_part(count, ring),
                report_part(count, accessory),
                report_part(count, back),
                '%6d' % count,
                input_name + (' (%s)' % desc if desc is not None else ''),
                ]
        print('  '.join(parts))

    print('  '.join((
        '%-10s' % 'Amulet',
        '%-10s' % 'Ring',
        '%-10s' % 'Accessory',
        '%-10s' % 'Back',
        )))
    report('Laurel', 'currency', amulet=30, ring=35, accessory=40)
    report('Laurel', 'currency', amulet=20, ring=25, accessory=40, desc='WvW')
    report('Pristine Fractal Relic', 'currency',
            amulet=100, ring=100, accessory=100)
    report('Ascended Shards of Glory', 'currency',
            amulet=175, ring=200, accessory=150)
    report('WvW Skirmish Claim Ticket', 'currency',
            amulet=260, ring=350, accessory=175)
    report('Magnetite Shard', 'currency',
            amulet=250, ring=250, accessory=250, back=600)
    report('Magnetite Shard', 'currency',
            amulet=150, ring=175, accessory=200, desc='predefined stats')
    report('Blood Ruby', 'item', amulet=125, ring=100, back=200)
    report('Petrified Wood', 'item', accessory=150, back=200)
    report('Fresh Winterberry', 'item', ring=200, accessory=300, back=400)
    report('Jade Shard', 'item', amulet=125, back=200)
    report('Fire Orchid Blossom', 'item', amulet=125, ring=100, back=200)
    report('Orrian Pearl', 'item', amulet=125)
    report('Difluorite Crystal', 'item', ring=100, accessory=150)
    report('Mistborn Mote', 'item', amulet=125, ring=100, accessory=150)
    report('Eternal Ice Shard', 'item', amulet=375, accessory=375)
    report('Blue/Green Prophet Shard', 'currency', amulet=250, ring=200, accessory=300,
            override_count = count_input('currency', 'Blue Prophet Shard') +
                count_input('currency', 'Green Prophet Shard'))
    report('Jade Sliver', 'currency', amulet=1250, ring=1000, accessory=1500)

if __name__ == '__main__':
    main()
