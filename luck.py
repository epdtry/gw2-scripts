from collections import defaultdict
import urllib.parse
import sys
import gw2.api
import gw2.items

LUCK_AMOUNT = {
    45178: 200,
    45177: 100,
    45176: 50,
    45175: 10,
}

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    char_name, = sys.argv[1:]
    char = gw2.api.fetch('/v2/characters/%s/inventory' %
            urllib.parse.quote(char_name))
    counts = defaultdict(int)
    for bag in char['bags']:
        for item in bag['inventory']:
            if item is None or item['count'] == 0:
                continue
            counts[item['id']] += item['count']

    total = 0
    for item_id, luck in LUCK_AMOUNT.items():
        count = counts[item_id]
        print('%6d  %s (%d)' % (count, gw2.items.name(item_id), luck))
        total += count * luck

    print('%6d  Total' % total)

if __name__ == '__main__':
    main()
