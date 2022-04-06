from collections import defaultdict
import json

import bookkeeper

def craft_profit_filter(row):
    return True
    #return row['roi'] >= 0.10

def main():
    with open('builds_metabattle.json') as f:
        builds = json.load(f)

    counts = defaultdict(int)
    for prof, builds in builds.items():
        all_item_ids = set(i for item_ids in builds for i in item_ids)
        for item_id in all_item_ids:
            counts[item_id] += 1

    by_count = []
    for item_id, count in counts.items():
        while count >= len(by_count):
            by_count.append([])
        by_count[count].append(item_id)

    for count in reversed(range(len(by_count))):
        item_ids = by_count[count]
        if len(item_ids) == 0:
            continue

        bookkeeper.do_craft_profit(item_ids, row_filter=craft_profit_filter,
                title='Used by %d professions' % count)


if __name__ == '__main__':
    main()
