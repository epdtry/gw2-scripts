from collections import defaultdict, namedtuple
import json
import os
import sys
import urllib.parse

import gw2.api
import gw2.items
import gw2.recipes
import gw2.trading_post


def _load_dict(path):
    if os.path.exists(path):
        with open(path) as f:
            return dict(json.load(f))
    else:
        return {}

def _dump_dict(dct, path):
    with open(path, 'w') as f:
        json.dump(list(dct.items()), f)

def _load_zero_dict(path):
    dct = defaultdict(int)
    if os.path.exists(path):
        with open(path) as f:
            dct.update(dict((k,v) for k,v in json.load(f) if v != 0))
    return dct

def _dump_zero_dict(dct, path):
    with open(path, 'w') as f:
        json.dump([(k,v) for k,v in dct.items() if v != 0], f)

GOALS_PATH = 'books/goals.json'
STOCKPILE_PATH = 'books/stockpile.json'


def parse_item_id(s):
    try:
        return int(s)
    except ValueError:
        pass
    item_id = gw2.items.search_name(s)
    if item_id is None:
        raise ValueError('unknown item: %r' % s)
    return item_id

def format_price(price):
    if price < 100:
        return '%d' % price
    elif price < 10000:
        return '%d.%02d' % (price // 100, price % 100)
    else:
        return '%d.%02d.%02d' % (price // 10000, price // 100 % 100, price % 100)


DAILY_CRAFT_ITEMS = set((
    46742,  # Lump of Mithrillium
    46744,  # Glob of Elder Spirit Residue
    46745,  # Spool of Thick Elonian Cord
    46740,  # Spool of Silk Weaving Thread
    43772,  # Charged Quartz Crystal
))

def can_craft(r):
    if r['output_item_id'] in DAILY_CRAFT_ITEMS:
        return False

    min_rating = r['min_rating']
    for d in r['disciplines']:
        if d == 'Tailor' and min_rating <= 500:
            return True
        if d == 'Artificer' and min_rating <= 500:
            return True
    return False

def get_prices(item_ids):
    buy_prices = {}
    sell_prices = {}

    for x in gw2.trading_post.get_prices_multi(item_ids):
        if x is None:
            continue

        # Try to buy at the buy price.  If there is no buy price (for example,
        # certain items that trade very close to their vendor price), then use
        # the sell price ("instant buy") instead.
        price = x['buys'].get('unit_price', 0) or x['sells'].get('unit_price', 0)
        if price != 0:
            buy_prices[x['id']] = price

        price = x['sells'].get('unit_price', 0) or x['buys'].get('unit_price', 0)
        if price != 0:
            sell_prices[x['id']] = price

    # Allow buying any vendor items that are priced in gold.
    with open('vendorprices.json') as f:
        j = json.load(f)
    for k, v in j.items():
        if k == '_origin':
            print('using vendor prices from %s' % v)
            continue

        k = int(k)
        if v['type'] != 'gold':
            continue
        price = v['cost'] / v['quantity']
        buy_prices[k] = price

    return buy_prices, sell_prices


def get_inventory():
    '''Return a dict listing the quantities of all items in material storage,
    the bank, and character inventories.'''
    counts = defaultdict(int)

    char_names = gw2.api.fetch('/v2/characters')
    for char_name in char_names:
        char = gw2.api.fetch('/v2/characters/%s/inventory' %
                urllib.parse.quote(char_name))
        for bag in char['bags']:
            for item in bag['inventory']:
                if item is None or item['count'] == 0:
                    continue
                counts[item['id']] += item['count']

    materials = gw2.api.fetch('/v2/account/materials')
    for item in materials:
        if item is None or item['count'] == 0:
            continue
        counts[item['id']] += item['count']

    bank = gw2.api.fetch('/v2/account/bank')
    for item in bank:
        if item is None or item['count'] == 0:
            continue
        counts[item['id']] += item['count']

    return dict(counts)


State = namedtuple('State', (
    'inventory',
    'pending_items',
    'buy_items',
    'craft_items',
    'obtain_items',
))

def sum_costs(xs):
    cost = 0
    for count, unit_cost in xs:
        if unit_cost is None:
            return None
        cost += count * unit_cost
    return cost

class StrategyBuy:
    def __init__(self, item_id, price):
        self.item_id = item_id
        self.price = price

    def cost(self):
        return self.price

    def apply(self, state, count):
        state.buy_items[self.item_id] += count
        state.inventory[self.item_id] += count

    def related_items(self):
        return ()

class StrategyCraft:
    def __init__(self, recipe):
        self.recipe = recipe

    def cost(self):
        output_count = self.recipe['output_item_count']
        #x = tuple(
        #    (i['count'] / output_count, optimal_strategy(i['item_id']).cost())
        #        for i in self.recipe['ingredients'])
        #print('crafting %s: inputs = %r' %
        #(gw2.items.name(self.recipe['output_item_id']), x))
        return sum_costs(tuple(
            (i['count'] / output_count, optimal_cost(i['item_id']))
                for i in self.recipe['ingredients']))

    def apply(self, state, count):
        r = self.recipe
        item_id = r['output_item_id']
        times = (count + r['output_item_count'] - 1) // r['output_item_count']
        state.craft_items[item_id] += r['output_item_count'] * times
        state.inventory[item_id] += r['output_item_count'] * times
        for i in r['ingredients']:
            state.inventory[i['item_id']] -= i['count'] * times
            state.pending_items.add(i['item_id'])

    def related_items(self):
        return tuple(i['item_id'] for i in self.recipe['ingredients'])

class StrategyUnknown:
    def __init__(self, item_id):
        self.item_id = item_id

    def cost(self):
        return None

    def apply(self, state, count):
        state.obtain_items[self.item_id] += count
        state.inventory[self.item_id] += count

    def related_items(self):
        return ()

ITEM_PIECE_OF_DRAGON_JADE = gw2.items.search_name('Piece of Dragon Jade')
ITEM_CHUNK_OF_PURE_JADE = gw2.items.search_name('Chunk of Pure Jade')
ITEM_RESEARCH_NOTE = gw2.items.search_name('Research Note')
ITEM_GLOB_OF_ECTOPLASM = gw2.items.search_name('Glob of Ectoplasm')
ITEM_ORICHALCUM_INGOT = gw2.items.search_name('Orichalcum Ingot')

class StrategyDragonJade:
    def __init__(self):
        pass

    def cost(self):
        return sum_costs((
            (4, optimal_cost(ITEM_CHUNK_OF_PURE_JADE)),
            (30, optimal_cost(ITEM_RESEARCH_NOTE)),
            (2, optimal_cost(ITEM_GLOB_OF_ECTOPLASM)),
            (5, optimal_cost(ITEM_ORICHALCUM_INGOT)),
        ))

    def apply(self, state, count):
        state.craft_items[ITEM_PIECE_OF_DRAGON_JADE] += count
        state.inventory[ITEM_PIECE_OF_DRAGON_JADE] += count
        state.inventory[ITEM_CHUNK_OF_PURE_JADE] -= count * 4
        # Note this is the research note item, which we use as a proxy for the
        # currency.
        state.inventory[ITEM_RESEARCH_NOTE] -= count * 30
        state.inventory[ITEM_GLOB_OF_ECTOPLASM] -= count * 2
        state.inventory[ITEM_ORICHALCUM_INGOT] -= count * 5
        state.pending_items.update((ITEM_CHUNK_OF_PURE_JADE,
            ITEM_RESEARCH_NOTE, ITEM_GLOB_OF_ECTOPLASM, ITEM_ORICHALCUM_INGOT))

    def related_items(self):
        return (ITEM_CHUNK_OF_PURE_JADE, ITEM_RESEARCH_NOTE,
                ITEM_GLOB_OF_ECTOPLASM, ITEM_ORICHALCUM_INGOT)

CHEAP_INSIGNIA_PREFIXES = (
        "Cavalier's", "Shaman's", "Dire", "Rabid", "Soldier's", "Magi's")

RESEARCH_NOTE_PANTS = tuple(gw2.items.search_name('%s Exalted Pants' % prefix)
    for prefix in CHEAP_INSIGNIA_PREFIXES)

RESEARCH_NOTES_PER_PANTS = 75

class StrategyResearchNote:
    def __init__(self):
        pass

    def cost(self):
        pants_sum = 0
        count = 0
        for item_id in RESEARCH_NOTE_PANTS:
            cost = optimal_cost(item_id)
            if cost is None:
                continue
            pants_sum += cost
            count += 1
        if count == 0:
            return None
        return pants_sum / (count * RESEARCH_NOTES_PER_PANTS)

    def apply(self, state, count):
        notes_per_set = RESEARCH_NOTES_PER_PANTS * len(RESEARCH_NOTE_PANTS)
        times = (count + notes_per_set - 1) // notes_per_set

        state.craft_items[ITEM_RESEARCH_NOTE] += notes_per_set * times
        state.inventory[ITEM_RESEARCH_NOTE] += notes_per_set * times

        for pants_item_id in RESEARCH_NOTE_PANTS:
            state.inventory[pants_item_id] -= times
            state.pending_items.add(pants_item_id)

    def related_items(self):
        return RESEARCH_NOTE_PANTS


STRATEGY_PRICES = {}
_OPTIMAL_STRATEGY_CACHE = {}
_OPTIMAL_COST_CACHE = {}

def set_strategy_params(prices):
    '''Set prices to use for `StrategyBuy`.'''
    global STRATEGY_PRICES
    global _OPTIMAL_STRATEGY_CACHE
    global _OPTIMAL_COST_CACHE
    STRATEGY_PRICES = prices
    _OPTIMAL_STRATEGY_CACHE = {}
    _OPTIMAL_COST_CACHE = {}

def valid_strategies(item_id):
    price = STRATEGY_PRICES.get(item_id)
    if price is not None:
        yield StrategyBuy(item_id, price)

    recipe_ids = gw2.recipes.search_output(item_id)
    print('recipes for %s: %r' % (gw2.items.name(item_id), recipe_ids))
    for recipe_id in recipe_ids:
        r = gw2.recipes.get(recipe_id)
        if can_craft(r):
            yield StrategyCraft(r)

    if item_id == ITEM_PIECE_OF_DRAGON_JADE:
        yield StrategyDragonJade()

    if item_id == ITEM_RESEARCH_NOTE:
        yield StrategyResearchNote()

def optimal_strategy(item_id):
    best_strategy = _OPTIMAL_STRATEGY_CACHE.get(item_id)
    if best_strategy is None:
        strats = []
        best_strategy = None
        best_cost = None
        for strategy in valid_strategies(item_id):
            cost = strategy.cost()
            strats.append((strategy, cost))
            if cost is None:
                # If all strategies have infinite cost, take the first one.
                if best_strategy is None:
                    best_strategy = strategy
            else:
                # Take this strategy if it beats the current best cost.
                if best_cost is None or cost < best_cost:
                    best_strategy = strategy
                    best_cost = cost
        if best_strategy is None:
            best_strategy = StrategyUnknown(item_id)
        print('strategies for %s = %r; winner = %r' % (gw2.items.name(item_id),
            strats, best_strategy))
        _OPTIMAL_STRATEGY_CACHE[item_id] = best_strategy
    return best_strategy

def optimal_cost(item_id):
    cost = _OPTIMAL_COST_CACHE.get(item_id)
    if cost is None:
        cost = optimal_strategy(item_id).cost()
        _OPTIMAL_COST_CACHE[item_id] = cost
    return cost


def cmd_init():
    os.makedirs('books', exist_ok=True)

CURRENCY_COIN = 1

def cmd_status():
    '''Print a report listing the following:

    * Items to buy
    * Pending buy orders
    * Items to craft
    * Items to obtain by unknown means
    * Existing items to be sold
    * Pending sell orders
    '''

    # Strategy:
    #
    # We keep a dict called `inventory`, which maps each item ID to an integer
    # that indicates how many of that item we currently have (if positive) or
    # how much of that item we need to obtain (if negative).  The `inventory`
    # dict starts out with the total of all items in character inventories, the
    # bank, material storage, and outstanding buy orders.  Then we subtract
    # items we mean to sell, which consists of `goals` minus all pending and
    # historical sell orders.
    #
    # This will typically result in `inventory` containing negative values (or,
    # at least, values less than the stockpile target) for some items.  We next
    # try to resolve this and bring all items up to their stockpile targets
    # (which is usually zero, but can be higher).  For each item, we try two
    # different options: buy at the trading post, and craft from materials.
    # The "buy" option decreases gold and increases the inventory amount; the
    # "craft" option increases the inventory amount of the target item and
    # decreases the amounts of the materials used to make it (which may cause
    # the inventory amounts for those materials to go negative).  If only one
    # option is available, we always choose it; otherwise, we compare the gold
    # costs of the two options and choose the cheaper one.  If neither option
    # succeeds, we simply increase the amount to the target and indicate that
    # the item must be "obtained from an unknown source".
    #
    # - for each item where inventory < stockpile:
    #   - compute optimal buy/craft price
    #   - buy: add count items; subtract count * price gold
    #   - craft: add count items; subtract count copies of ingredient items
    #   - neither: add count items; record in "obtain by unknown means" list
    # - state: inventory (ID -> count), to_check (set of IDs)
    #   - update to_check when subtracting craft ingredients
    #   - loop until to_check is empty

    goals = _load_zero_dict(GOALS_PATH)
    stockpile = _load_zero_dict(STOCKPILE_PATH)

    sold = gw2.trading_post.total_sold()
    sell_orders, selling_items = gw2.trading_post.pending_sells()
    buy_orders, buying_items = gw2.trading_post.pending_buys()
    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    # TODO: add money and items in delivery box

    inventory = defaultdict(int)
    inventory.update(get_inventory())
    # We assume all pending buy orders will eventually be fulfilled.
    for item_id, count in buying_items.items():
        inventory[item_id] += count

    orig_inventory = inventory.copy()


    # Subtract from `inventory` any additional sell orders we need to place to
    # achieve the current `goals`.
    
    # `sell_items` records existing items that should be sold to satisfy a
    # goal.
    sell_goal_items = defaultdict(int)
    craft_goal_items = defaultdict(int)
    for item_id, goal in goals.items():
        to_sell = goal - (selling_items.get(item_id, 0) + sold.get(item_id, 0))
        if to_sell <= 0:
            continue
        sell_goal_items[item_id] += min(to_sell, inventory[item_id])
        craft_goal_items[item_id] += max(0, to_sell - inventory[item_id])
        inventory[item_id] -= to_sell

    # Find all items whose `inventory` amount is currently below the
    # `stockpile` target.
    keys = set(stockpile.keys())
    keys.update(inventory.keys())
    pending_items = set()
    for item_id in keys:
        if inventory.get(item_id, 0) < stockpile.get(item_id, 0):
            pending_items.add(item_id)


    # Gather all items we might need to buy or sell, and obtain their current
    # prices.
    all_items = set()
    def add_item_and_related(item_id):
        if item_id in all_items:
            return
        all_items.add(item_id)
        for strategy in valid_strategies(item_id):
            for related_item_id in strategy.related_items():
                add_item_and_related(related_item_id)
    for item_id in pending_items:
        add_item_and_related(item_id)
    for item_id in goals.keys():
        all_items.add(item_id)

    from pprint import pprint
    pprint(sorted(gw2.items.name(i) for i in all_items))

    buy_prices, sell_prices = get_prices(all_items)

    for item_id, buy_price in buy_prices.items():
        if item_id not in sell_prices:
            sell_prices[item_id] = buy_price

    # Forbid strategies from buying certain items
    strategy_prices = buy_prices.copy()
    for r in gw2.recipes.iter_all():
        # Forbid buying or selling intermediate crafting items.
        if r['type'] in ('Refinement', 'Component'):
            item_id = r['output_item_id']
            strategy_prices.pop(item_id, None)
    for item_id in goals.keys():
        strategy_prices.pop(item_id, None)
    for item_id in RESEARCH_NOTE_PANTS:
        strategy_prices.pop(item_id, None)
    set_strategy_params(strategy_prices)


    # Process items until all stockpile requirements are satisfied.
    buy_items = defaultdict(int)
    craft_items = defaultdict(int)
    obtain_items = defaultdict(int)
    state = State(
            inventory,
            pending_items,
            buy_items,
            craft_items,
            obtain_items,
            )
    while len(pending_items) > 0:
        item_id = pending_items.pop()
        shortage = stockpile.get(item_id, 0) - inventory.get(item_id, 0)
        if shortage <= 0:
            continue

        strategy = optimal_strategy(item_id)
        strategy.apply(state, shortage)
        assert inventory.get(item_id, 0) >= stockpile.get(item_id, 0), \
                'strategy %r failed to produce %d %s' % (
                        strategy, shortage, gw2.items.name(item_id))


    used_items = {}
    for item_id, old_count in orig_inventory.items():
        new_count = inventory.get(item_id, 0)
        delta = new_count - old_count
        if delta < 0:
            used_items[item_id] = -delta


    def print_table(desc, item_counts, prices={}):
        rows = []
        grand_total = 0
        for item_id, count in item_counts.items():
            if count == 0:
                continue
            unit_price = prices.get(item_id)
            total_price = unit_price * count if unit_price is not None else None
            rows.append((
                str(count),
                gw2.items.name(item_id),
                format_price(unit_price) if unit_price is not None else '',
                format_price(total_price) if total_price is not None else '',
            ))
            if total_price is not None:
                grand_total += total_price

        if len(rows) == 0:
            return

        if grand_total != 0:
            rows.append(('', 'Total', '', format_price(grand_total)))

        print('\n%s:' % desc)
        for x in rows:
            print('%10s  %-50.50s  %12s  %12s' % x)

    def print_order_table(desc, transactions):
        rows = []
        grand_total = 0
        for transaction in transactions:
            item_id = transaction['item_id']
            count = transaction['quantity']
            unit_price = transaction['price']
            if count == 0:
                continue
            total_price = unit_price * count
            rows.append((
                str(count),
                gw2.items.name(item_id),
                format_price(unit_price),
                format_price(total_price),
            ))
            grand_total += total_price

        if len(rows) == 0:
            return

        if grand_total != 0:
            rows.append(('', 'Total', '', format_price(grand_total)))

        print('\n%s:' % desc)
        for x in rows:
            print('%10s  %-50.50s  %12s  %12s' % x)

    print_table('Buy', buy_items, buy_prices)
    print_order_table('Buy orders', buy_orders)
    print_table('Obtain', obtain_items)
    print_table('Use', used_items, sell_prices)
    print_table('Craft', craft_goal_items)
    print_table('Sell', sell_goal_items, sell_prices)
    print_order_table('Sell orders', sell_orders)

    print('')
    gold = wallet[CURRENCY_COIN]
    current_buy_total = sum(t['price'] * t['quantity'] for t in buy_orders)
    future_buy_total = sum(count * buy_prices[item_id] for item_id, count in buy_items.items())
    current_sell_total = sum(t['price'] * t['quantity'] * 0.90 for t in sell_orders)
    future_sell_total = sum((count - (selling_items.get(item_id, 0) + sold.get(item_id, 0)))
                * sell_prices[item_id] * 0.85 for item_id, count in goals.items())
    used_sell_total = sum(count * (sell_prices.get(item_id, 0) or buy_prices.get(item_id, 0)) * 0.85
            for item_id, count in used_items.items())
    print('Current gold: %s' % format_price(gold))
    print('After current sales: %s' % format_price(gold + current_sell_total))
    print('Target gold: %s' % format_price(gold - current_buy_total -
        future_buy_total + current_sell_total + future_sell_total))

def cmd_goal(count, name):
    count = int(count)
    item_id = parse_item_id(name)

    goals = _load_dict(GOALS_PATH)

    goal = goals.get(item_id, 0)
    cur = gw2.trading_post.total_sold().get(item_id, 0)
    if count < cur:
        goal = cur + count
    else:
        goal += count

    goals[item_id] = goal

    _dump_dict(goals, GOALS_PATH)
    fmt = 'added %d %s to goals' if count >= 0 else 'subtracted %d %s from goals'
    print(fmt % (count, gw2.items.name(item_id)))

def cmd_stockpile(count, name):
    count = int(count)
    item_id = parse_item_id(name)

    stockpile = _load_dict(STOCKPILE_PATH)
    stockpile[item_id] = stockpile.get(item_id, 0) + count
    _dump_dict(stockpile, STOCKPILE_PATH)
    print('%s stockpile target to %d %s' % (
        'increased' if count >= 0 else 'decreased',
        stockpile[item_id], gw2.items.name(item_id)))

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'init':
        assert len(args) == 0
        cmd_init()
    elif cmd == 'status':
        assert len(args) == 0
        cmd_status()
    elif cmd == 'goal':
        count, name = args
        cmd_goal(count, name)
    elif cmd == 'stockpile':
        count, name = args
        cmd_stockpile(count, name)
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
