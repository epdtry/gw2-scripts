import os
import json

import gw2.api
import gw2.items
import gw2.mystic_forge
import gw2.trading_post


GW2_SCRIPTS_DIR = os.getcwd()
GW2_DATA_DIR = os.path.join(os.path.abspath(os.path.join(GW2_SCRIPTS_DIR, os.pardir)), 'gw2-data')
LOOT_BAG_FILE = os.path.join(GW2_DATA_DIR, 'loot_bags.txt')

class LootBag:
    def __init__(self, name, price, quantity, id):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.id = id
 
    def __repr__(self):
        return json.dumps(self.__dict__)

def main():
    all_items = gw2.items.iter_all()
    container_items = []
    for item in all_items:
        if(item['type'] == 'Container'):
            container_items.append(item)

    container_items_ids = [t['id'] for t in container_items]
    item_prices = gw2.trading_post.get_prices_multi(container_items_ids)

    loot_bags = []
    for ip in item_prices:
        if ip == None: 
            continue
        ip_buys = ip['buys']
        if ip_buys == None:
            ip_buys['price'] = 0
            ip_buys['quantity'] = 0
        loot_bag = LootBag(gw2.items.name(ip['id']), ip_buys['unit_price'], ip_buys['quantity'], ip['id'])
        loot_bags.append(loot_bag)

    loot_bags.sort(key=lambda x: x.price)
    data = [lb for lb in loot_bags]
    with open(LOOT_BAG_FILE, 'w') as f:
        json.dump(loot_bags, f, default=vars)

    

if __name__ == '__main__':
    main()
