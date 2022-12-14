import gw2.api
import gw2.items
import bookkeeper

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

    acc = 0
    def report(inputs, output_count=1, note=None):
        nonlocal acc
        times = min(count_input(kind, name) // count
                for count, name, kind in inputs)
        input_strs = '  '.join('%4d  %-15.15s' % (count, name)
                for count, name, kind in inputs)
        if output_count != 1:
            if note is None:
                note = 'produces %d' % output_count
            else:
                note = 'produces %d, %s' % (output_count, note)
        note_str = '' if not note else ' (%s)' % note
        print('%6d   %s%s' % (times * output_count, input_strs, note_str))
        acc += times * output_count

    report([(1, 'Funerary Incense', 'item')])
    report([(3, 'Elegy Mosaic', 'currency')])
    report([(100, 'Trade Contract', 'currency')])
    report([(1, 'Tyrian Exchange Voucher', 'item')], output_count=10)
    print('%6d   Total' % acc)
    print()

    report([(1, 'Crystalline Ingot', 'item')], note='5/day')
    report([(5, 'Trade Contract', 'currency')], note='8/day')

if __name__ == '__main__':
    main()
