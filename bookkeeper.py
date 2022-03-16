from collections import defaultdict, namedtuple
from itertools import chain
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
    if price < 0:
        return '-' + format_price(-price)
    if price < 100:
        return '%d' % price
    elif price < 10000:
        return '%d.%02d' % (price // 100, price % 100)
    else:
        return '%d.%02d.%02d' % (price // 10000, price // 100 % 100, price % 100)


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

def condense_transactions(transactions):
    '''Combine transactions with the same item and price.'''
    dct = {}
    out = []
    for t in transactions:
        key = (t['item_id'], t['price'])
        if key in dct:
            old_t = dct[key]
            old_t['quantity'] += t['quantity']
        else:
            dct[key] = t
            out.append(t)
    return out


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
STRATEGY_FORBID_BUY = set()
STRATEGY_FORBID_CRAFT = set()
STRATEGY_CAN_CRAFT_RECIPE = lambda r: True
_OPTIMAL_STRATEGY_CACHE = {}
_OPTIMAL_COST_CACHE = {}

def set_strategy_params(prices, forbid_buy, forbid_craft, can_craft_recipe):
    '''Set prices to use for `StrategyBuy`.'''
    global STRATEGY_PRICES, STRATEGY_FORBID_BUY, STRATEGY_FORBID_CRAFT, STRATEGY_CAN_CRAFT
    global _OPTIMAL_STRATEGY_CACHE, _OPTIMAL_COST_CACHE
    STRATEGY_PRICES = prices
    STRATEGY_FORBID_BUY = forbid_buy
    STRATEGY_FORBID_CRAFT = forbid_craft
    STRATEGY_CAN_CRAFT_RECIPE = can_craft_recipe
    _OPTIMAL_STRATEGY_CACHE = {}
    _OPTIMAL_COST_CACHE = {}

def valid_strategies(item_id):
    if item_id not in STRATEGY_FORBID_BUY:
        price = STRATEGY_PRICES.get(item_id)
        if price is not None:
            yield StrategyBuy(item_id, price)

    if item_id not in STRATEGY_FORBID_CRAFT:
        recipe_ids = gw2.recipes.search_output(item_id)
        for recipe_id in recipe_ids:
            r = gw2.recipes.get(recipe_id)
            if STRATEGY_CAN_CRAFT_RECIPE(r):
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
        _OPTIMAL_STRATEGY_CACHE[item_id] = best_strategy
    return best_strategy

def optimal_cost(item_id):
    cost = _OPTIMAL_COST_CACHE.get(item_id)
    if cost is None:
        cost = optimal_strategy(item_id).cost()
        _OPTIMAL_COST_CACHE[item_id] = cost
    return cost


def gather_related_items(item_ids):
    all_items = set()
    def add_item_and_related(item_id):
        if item_id in all_items:
            return
        all_items.add(item_id)
        for strategy in valid_strategies(item_id):
            for related_item_id in strategy.related_items():
                add_item_and_related(related_item_id)
    for item_id in item_ids:
        add_item_and_related(item_id)
    return all_items

def count_craftable(targets, inventory):
    '''Given a list `targets` of item IDs and counts, return the number of
    requested items that can be crafted via the optimal strategy, using only
    items that are currently available in `inventory`.  Items are tried in
    order, so an earlier item may consume materials and make a later item
    uncraftable.'''
    orig_inventory = inventory
    inventory = defaultdict(int)
    inventory.update(orig_inventory)

    target_goals = {item_id: inventory[item_id] + count
            for item_id, count in targets}

    for target_item_id, _ in targets:
        # Craft up to `target_count` copies of `target_item_id`.  Our approach
        # here is the following:
        #
        # 1. Find a set of available materials that can be used to craft one copy
        #    of `target_item_id`.  This may be a mix of  raw materials and/or
        #    intermediate items that happen to be available.  This is called
        #    `delta`.
        # 2. Apply `delta` to inventory as many times as we can while keeping all
        #    item quantities non-negative.
        # 3. Repeat steps 1-2 until no `delta` can be found.

        target_goal = target_goals[target_item_id]

        while inventory[target_item_id] < target_goal:
            delta = defaultdict(int)
            pending_items = set()
            state = State(delta, pending_items,
                    defaultdict(int), defaultdict(int), defaultdict(int))

            optimal_strategy(target_item_id).apply(state, 1)
            while len(pending_items) > 0:
                item_id = pending_items.pop()
                if delta[item_id] >= 0:
                    continue
                # Figure out how many of this item we need to craft.
                craft_count = -delta[item_id] - inventory[item_id]
                if craft_count <= 0:
                    # We can fulfill this requirement using only items currently
                    # available in the inventory.
                    continue
                optimal_strategy(item_id).apply(state, craft_count)

            # Make sure all requirements were satisfied by crafting.
            if any(v > 0 for v in state.buy_items.values()):
                break
            if any(v > 0 for v in state.obtain_items.values()):
                break

            # Now `delta[target_item_id]` should be positive, and `delta` should
            # have negative values for all the raw materials it consumes.  (Note
            # some intermediate materials may have positive values, such as if the
            # recipe produces 5 per craft but we only consume 1.)
            assert delta[target_item_id] > 0

            # Figure out how many times we can apply `delta` without making any
            # `inventory` entry negative.
            remaining = target_goal - inventory[target_item_id]
            max_apply = (remaining + delta[target_item_id] - 1) // delta[target_item_id]
            for item_id, count in delta.items():
                if count >= 0:
                    continue
                item_max_apply = inventory[item_id] // -count
                assert item_max_apply >= 1
                if max_apply is None or item_max_apply < max_apply:
                    max_apply = item_max_apply

            # Apply `delta` to `inventory` that many times.
            for item_id, count in delta.items():
                inventory[item_id] += count * max_apply

            # Now repeat.  The next iteration will compute a different `delta`.
            # For example, we may have used up all of some intermediate material,
            # so the next iteration must craft it from raw materials instead.

    return {item_id: inventory[item_id] - orig_inventory[item_id]
            for item_id, _ in targets}


def policy_can_craft_recipe(r):
    min_rating = r['min_rating']
    for d in r['disciplines']:
        if d == 'Tailor' and min_rating <= 500:
            return True
        if d == 'Artificer' and min_rating <= 500:
            return True
    return False

def policy_forbid_buy():
    forbid = set()

    # Forbid buying or selling intermediate crafting items.
    for r in gw2.recipes.iter_all():
        if r['type'] in ('Refinement', 'Component'):
            forbid.add(r['output_item_id'])

    ascended_refinement = [
        gw2.items.search_name('Deldrimor Steel Ingot'),
        gw2.items.search_name('Elonian Leather Square'),
        gw2.items.search_name('Bolt of Damask'),
        gw2.items.search_name('Spiritwood Plank'),
    ]
    for item_id in ascended_refinement:
        if item_id in forbid:
            forbid.remove(item_id)

    forbid.update(RESEARCH_NOTE_PANTS)

    return forbid

def policy_forbid_craft():
    forbid = set()

    # Forbid relying on time-gated recipes
    forbid.add(gw2.items.search_name('Lump of Mithrillium'))
    forbid.add(gw2.items.search_name('Glob of Elder Spirit Residue'))
    forbid.add(gw2.items.search_name('Spool of Thick Elonian Cord'))
    forbid.add(gw2.items.search_name('Spool of Silk Weaving Thread'))
    forbid.add(gw2.items.search_name('Charged Quartz Crystal'))

    return forbid


def cmd_init():
    os.makedirs('books', exist_ok=True)

CURRENCY_COIN = 1
CURRENCY_RESEARCH_NOTE = 61

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
    delivery = gw2.api.fetch('/v2/commerce/delivery')
    wallet_raw = gw2.api.fetch('/v2/account/wallet')
    wallet = {x['id']: x['value'] for x in wallet_raw}

    gold = wallet[CURRENCY_COIN]
    gold += delivery['coins']

    inventory = defaultdict(int)
    inventory.update(get_inventory())
    # Convert research notes in wallet to research note items
    inventory[ITEM_RESEARCH_NOTE] += wallet[CURRENCY_RESEARCH_NOTE]
    # Add items in the delivery box
    for i in delivery['items']:
        print('delivery: %d %s  %r' % (i['count'], gw2.items.name(i['id']), i))
        inventory[i['id']] += i['count']

    orig_inventory = inventory.copy()

    # We assume all pending buy orders will eventually be fulfilled.
    for item_id, count in buying_items.items():
        inventory[item_id] += count



    # Subtract from `inventory` any additional sell orders we need to place to
    # achieve the current `goals`.
    
    sell_goal_items = defaultdict(int)
    craft_goal_items = defaultdict(int)
    for item_id, goal in goals.items():
        to_sell = goal - (selling_items.get(item_id, 0) + sold.get(item_id, 0))
        if to_sell <= 0:
            continue
        sell_goal_items[item_id] += min(to_sell, inventory[item_id])
        craft_goal_items[item_id] += max(0, to_sell - sell_goal_items[item_id])
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
    related_items = gather_related_items(chain(pending_items, goals.keys()))
    buy_prices, sell_prices = get_prices(related_items)

    for item_id, buy_price in buy_prices.items():
        if item_id not in sell_prices:
            sell_prices[item_id] = buy_price

    set_strategy_params(
            buy_prices,
            set(chain(policy_forbid_buy(), goals.keys())),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )


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
        used_items[item_id] = -delta


    def print_table(desc, item_counts, prices={}, price_mult=1, extra_counts=None):
        rows = []
        grand_total = 0
        for item_id, count in item_counts.items():
            if count == 0:
                continue
            unit_price = prices.get(item_id)
            total_price = unit_price * count if unit_price is not None else None

            count_str = str(count)
            if extra_counts is not None:
                extra_count = extra_counts.get(item_id)
                if extra_count is not None:
                    count_str = '%d / %d' % (extra_count, count)

            rows.append((
                count_str,
                gw2.items.name(item_id),
                format_price(unit_price) if unit_price is not None else '',
                format_price(total_price * price_mult) if total_price is not None else '',
            ))
            if total_price is not None:
                grand_total += total_price * price_mult

        if len(rows) == 0:
            return

        if grand_total != 0:
            rows.append(('', 'Total', '', format_price(grand_total)))

        print('\n%s:' % desc)
        for x in rows:
            print('%10s  %-50.50s  %12s  %12s' % x)

    def print_order_table(desc, transactions, price_mult=1):
        rows = []
        grand_total = 0
        for transaction in transactions:
            item_id = transaction['item_id']
            count = transaction['quantity']
            unit_price = transaction['price']
            if count == 0:
                continue
            total_price = unit_price * count * price_mult
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

    sell_orders = condense_transactions(sell_orders)
    buy_orders = condense_transactions(buy_orders)
    craft_counts = count_craftable(list(craft_goal_items.items()), orig_inventory)

    print_table('Buy', buy_items, buy_prices)
    print_order_table('Buy orders', buy_orders)
    print_table('Obtain', obtain_items)
    print_table('Use', used_items, sell_prices)
    print_table('Craft', craft_goal_items, sell_prices, price_mult=0.85,
            extra_counts=craft_counts)
    print_table('Sell', sell_goal_items, sell_prices, price_mult=0.85)
    print_order_table('Sell orders', sell_orders, price_mult=0.90)

    print('')
    # We don't subtract `buy_orders`, since the gold for those orders was
    # removed from the wallet when the orders were placed.
    future_buy_total = sum(count * buy_prices[item_id] for item_id, count in buy_items.items())
    current_sell_total = sum(t['price'] * t['quantity'] * 0.90 for t in sell_orders)
    future_sell_total = sum(count * sell_prices[item_id] * 0.85 for item_id,
            count in sell_goal_items.items()) + \
        sum(count * sell_prices[item_id] * 0.85 for item_id,
            count in craft_goal_items.items())
    used_sell_total = sum(count * (sell_prices.get(item_id, 0) or buy_prices.get(item_id, 0)) * 0.85
            for item_id, count in used_items.items())

    # "Cash out" means cancel all buy orders, cancel all sell orders and relist
    # them at the buy price, and sell everything waiting to be listed at its
    # buy price.
    cash_out_buy_orders = sum(t['price'] * t['quantity'] for t in buy_orders)
    cash_out_sell_orders = sum(
            buy_prices.get(t['item_id'], 0) * t['quantity'] * 0.85
            for t in sell_orders)
    cash_out_sell_goal_items = sum(buy_prices.get(item_id, 0) * count * 0.85
            for item_id, count in sell_goal_items.items())

    print('Current gold: %s' % format_price(gold))
    print('After current sales: %s' % format_price(gold + current_sell_total))
    print('Cash out: %s' % format_price(gold + cash_out_buy_orders +
        cash_out_sell_orders + cash_out_sell_goal_items))
    print('Target gold: %s' % format_price(gold - future_buy_total +
        current_sell_total + future_sell_total))


def cmd_goal(count, name):
    count = int(count)
    item_id = parse_item_id(name)

    goals = _load_dict(GOALS_PATH)
    goal = goals.get(item_id, 0)

    # If we sold extra since the last time we increased this goal, reset to the
    # current amount sold.  If the amount left to sell is negative, the item is
    # omitted from `status`, so the user will likely think the amount to sell
    # is zero, and expects adding `count` to increase it to exactly `count`.
    cur = gw2.trading_post.total_sold().get(item_id, 0)
    if goal < cur:
        goal = cur

    goals[item_id] = goal + count

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

def cmd_profit(name):
    item_id = parse_item_id(name)

    related_items = gather_related_items([item_id])
    buy_prices, sell_prices = get_prices(related_items)

    set_strategy_params(
            buy_prices,
            policy_forbid_buy(),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    sell_price = sell_prices[item_id]
    cost = optimal_cost(item_id)
    print('%s (%d)' % (gw2.items.name(item_id), item_id))
    print('Cost:        %s' % format_price(cost))
    print('Sell price:  %s' % format_price(sell_price))
    profit = sell_price * 0.85 - cost
    profit_pct = 100 * profit / cost
    print('Profit:      %s (%.1f%%)' % (format_price(profit), profit_pct))

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
    elif cmd == 'profit':
        name, = args
        cmd_profit(name)
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
