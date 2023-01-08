from collections import defaultdict, namedtuple
import datetime
from itertools import chain
import json
import math
import os
import sqlite3
import sys
import time
import urllib.parse

import gw2.api
import gw2.items
import gw2.mystic_forge
import gw2.recipes
import gw2.trading_post
import gw2.character


def _load_dict(path):
    if os.path.exists(path):
        with open(path) as f:
            return dict(json.load(f))
    else:
        return {}

def _dump_dict(dct, path):
    with open(path + '.new', 'w') as f:
        json.dump(list(dct.items()), f)
    os.replace(path + '.new', path)

def _load_zero_dict(path):
    dct = defaultdict(int)
    if os.path.exists(path):
        with open(path) as f:
            dct.update(dict((k,v) for k,v in json.load(f) if v != 0))
    return dct

def _dump_zero_dict(dct, path):
    with open(path + '.new', 'w') as f:
        json.dump([(k,v) for k,v in dct.items() if v != 0], f)
    os.rename(path + '.new', path)

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

def format_price_float(price, precision=3):
    if price < 0:
        return '-' + format_price(-price)
    last = '%0{}.{}f'.format(precision + 3, precision)
    if price < 100:
        return last % price
    elif price < 10000:
        return ('%d.' + last) % (price // 100, price % 100)
    else:
        return ('%d.%02d.' + last) % (price // 10000, price // 100 % 100, price % 100)

def format_price_delta(price):
    if price < 0:
        return '-' + format_price(-price)
    elif price > 0:
        return '+' + format_price(price)
    else:
        return '0'

def parse_timestamp(s):
    dt = datetime.datetime.fromisoformat(s)
    return dt.timestamp()


_PRINTED_ORIGINS=set()

def add_vendor_prices(buy_prices):
    # Allow buying any vendor items that are priced in gold.
    with open('vendorprices.json') as f:
        j = json.load(f)
    for k, v in j.items():
        if k == '_origin':
            if v not in _PRINTED_ORIGINS:
                print('using vendor prices from %s' % v)
                _PRINTED_ORIGINS.add(v)
            continue

        k = int(k)
        if v['type'] != 'gold':
            continue
        price = v['cost'] / v['quantity']
        buy_prices[k] = price

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

    add_vendor_prices(buy_prices)
    return buy_prices, sell_prices


def get_prices_and_listings(item_ids):
    buy_prices = {}
    sell_prices = {}
    buy_listings = {}
    sell_listings = {}

    for x in gw2.trading_post.get_listings_multi(item_ids):
        if x is None:
            continue

        item = gw2.items.get(x['id'])
        min_price = item['vendor_value'] / 0.85

        # Filter out buy orders for less than the minimum trading post price.
        # Notably, ruby crystals (for mithril earrings) have some old
        # unfillable buy orders, but the actual trading price is usually set by
        # the sell side, close to the minimum.
        buys = [l for l in x['buys'] if l['unit_price'] >= min_price]
        sells = x['sells']

        buy_listings[x['id']] = buys
        sell_listings[x['id']] = sells

        buy_price = None
        sell_price = None

        if len(buys) > 0:
            buy_price = max(b['unit_price'] for b in buys)
        if len(sells) > 0:
            sell_price = min(s['unit_price'] for s in sells)

        if buy_price is None:
            buy_price = sell_price
        if sell_price is None:
            sell_price = buy_price

        buy_prices[x['id']] = buy_price
        sell_prices[x['id']] = sell_price

    add_vendor_prices(buy_prices)
    return buy_prices, sell_prices, buy_listings, sell_listings


def get_inventory():
    '''Return a dict listing the quantities of all items in material storage,
    the bank, and character inventories.'''
    counts = defaultdict(int)

    char_names = gw2.api.fetch('/v2/characters')
    for char_name in char_names:
        char = gw2.api.fetch('/v2/characters/%s/inventory' %
                urllib.parse.quote(char_name))
        for bag in char['bags']:
            if bag is None:
                continue
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


def craftable_items():
    for r in gw2.recipes.iter_all():
        if not policy_can_craft_recipe(r):
            continue
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

    for r in gw2.mystic_forge.iter_all():
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

CURRENCY_COIN = 1
CURRENCY_RESEARCH_NOTE = 61
CURRENCY_SPIRIT_SHARDS = 23
CURRENCY_IMPERIAL_FAVOR = 68
CURRENCY_FRACTAL_RELIC = 7
CURRENCY_PRISTINE_FRACTAL_RELIC = 24
ITEM_RESEARCH_NOTE = gw2.items.search_name('Research Note')
ITEM_SPIRIT_SHARD = gw2.items.search_name('Spirit Shard')
ITEM_IMPERIAL_FAVOR = gw2.items.search_name('Imperial Favor')
ITEM_FRACTAL_RELIC = gw2.items.search_name('Fractal Relic')
ITEM_PRISTINE_FRACTAL_RELIC = gw2.items.search_name('Pristine Fractal Relic')

CURRENCY_ITEMS = [
        (CURRENCY_RESEARCH_NOTE, ITEM_RESEARCH_NOTE),
        (CURRENCY_SPIRIT_SHARDS, ITEM_SPIRIT_SHARD),
        (CURRENCY_IMPERIAL_FAVOR, ITEM_IMPERIAL_FAVOR),
        (CURRENCY_FRACTAL_RELIC, ITEM_FRACTAL_RELIC),
        (CURRENCY_PRISTINE_FRACTAL_RELIC, ITEM_PRISTINE_FRACTAL_RELIC),
        ]

CURRENCY_TO_ITEM = {c: i for c, i in CURRENCY_ITEMS}
ITEM_TO_CURRENCY = {i: c for c, i in CURRENCY_ITEMS}

def recipe_ingredient_items(r):
    '''Get item equivalents for all ingredients of recipe `r`.  Yields
    `item_id, count` for each ingredient.  For currency ingredients, the item
    ID is obtained from `CURRENCY_TO_ITEM[currency_id]`.  Yields `None, count`
    for currencies with no known conversion.'''
    for i in r['ingredients']:
        if 'type' in i:
            # New format, which supports currency inputs
            if i['type'] == 'Item':
                yield i['id'], i['count']
            elif i['type'] == 'Currency':
                yield CURRENCY_TO_ITEM.get(i['id']), i['count']
        else:
            yield i['item_id'], i['count']


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

    def describe(self, count):
        return count, 'Buy ' + gw2.items.name(self.item_id)


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
        costs = []
        for item_id, count in recipe_ingredient_items(self.recipe):
            if item_id is None:
                costs.append((None, None))
            else:
                costs.append((count / output_count, optimal_cost(item_id)))
        return sum_costs(costs)

    def max_count(self, state, exclude=None, max_output=None):
        '''Return the maximum number of outputs that can be crafted using only
        available inputs.

        * `exclude` (dict): Subtract the quantities in this dict from the
          inventory contents when counting inputs.
        * `max_output` (int): Don't produce more than this many output items.
        '''
        max_times = None
        for item_id, count in recipe_ingredient_items(self.recipe):
            avail = state.inventory[item_id]
            if exclude:
                avail -= exclude.get(item_id, 0)
            times = avail // count
            if max_times is None or max_times > times:
                max_times = times

        if max_output is not None:
            times = max_output // self.recipe['output_item_count']
            if max_times is None or max_times > times:
                max_times = times

        if max_times is None:
            max_times = 0
        return max_times * self.recipe['output_item_count']

    def apply(self, state, count):
        r = self.recipe
        item_id = r['output_item_id']
        times = (count + r['output_item_count'] - 1) // r['output_item_count']
        state.craft_items[item_id] += r['output_item_count'] * times
        state.inventory[item_id] += r['output_item_count'] * times
        for item_id, count in recipe_ingredient_items(self.recipe):
            state.inventory[item_id] -= count * times
            state.pending_items.add(item_id)

    def related_items(self):
        return tuple(item_id for item_id, count in recipe_ingredient_items(self.recipe))

    def describe(self, count):
        r = self.recipe
        times = (count + r['output_item_count'] - 1) // r['output_item_count']
        return times, 'Craft ' + gw2.items.name(self.recipe['output_item_id'])

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

    def describe(self, count):
        return count, 'Obtain ' + gw2.items.name(self.item_id)

CHEAP_INSIGNIA_PREFIXES = (
        "Shaman's", "Dire", "Rabid", "Magi's")
RESEARCH_NOTE_PANTS = tuple(gw2.items.search_name('%s Exalted Pants' % prefix)
    for prefix in CHEAP_INSIGNIA_PREFIXES)
RESEARCH_NOTES_PER_PANTS = 75

CHEAP_JEWEL_NAMES = (
        'Ruby', 'Beryl', 'Coral', 'Emerald', 'Opal', 'Sapphire', 'Chrysocola')
RESEARCH_NOTE_EARRINGS = tuple(
        gw2.items.search_name('%s Mithril Earring' % jewel,
            rarity='Fine', without_flags=('AccountBound',))
        for jewel in CHEAP_JEWEL_NAMES)
RESEARCH_NOTES_PER_EARRING = 5

PEARL_WEAPON_TYPES = (
        #'Reaver', 'Carver', 'Bludgeoner', 'Handcannon', 'Rod', 'Sabre',
        #'Shell', 'Brazier', 'Siren',
        #'Broadsword', 'Crusher', 'Stinger', 'Blunderbuss', 'Needler', 'Quarterstaff',
        #'Speargun', 'Impaler', 'Trident',
        )
RESEARCH_NOTE_WEAPONS = [
        tuple(gw2.items.search_name('%s Pearl %s' % (prefix, weapon))
            for prefix in CHEAP_INSIGNIA_PREFIXES)
        for weapon in PEARL_WEAPON_TYPES]
RESEARCH_NOTES_PER_WEAPON = 45

SLAYING_POTION_TYPES = (
        #'Undead', 'Sons of Svanir', 'Destroyer', 'Grawl',
        #'Nightmare Court', 'Ogre', 'Outlaw', 'Ice Brood', 'Dredge',
        #'Mordrem',  # Only available as "powerful potion", not "potent potion"
        )
RESEARCH_NOTE_POTIONS = tuple(
        gw2.items.search_name('Potent Potion of %s Slaying' % x)
        for x in SLAYING_POTION_TYPES)
RESEARCH_NOTES_PER_POTION = 1

class StrategyResearchNote:
    def __init__(self, items, notes_per_item):
        '''Build a strategy that salvages one of each item in `items` for a
        total of `notes_per_item * len(itmes)` research notes.'''
        self.items = items
        self.notes_per_item = notes_per_item

    def cost(self):
        items_sum = 0
        count = 0
        for item_id in self.items:
            cost = optimal_cost(item_id)
            if cost is None:
                continue
            items_sum += cost
            count += 1
        if count == 0:
            return None
        return items_sum / (count * self.notes_per_item)

    def apply(self, state, count):
        notes_per_set = self.notes_per_item * len(self.items)
        times = (count + notes_per_set - 1) // notes_per_set

        state.craft_items[ITEM_RESEARCH_NOTE] += notes_per_set * times
        state.inventory[ITEM_RESEARCH_NOTE] += notes_per_set * times

        for item_id in self.items:
            state.inventory[item_id] -= times
            state.pending_items.add(item_id)

    def related_items(self):
        return self.items

    def describe(self, count):
        times = (count + self.notes_per_item - 1) // self.notes_per_item
        return times, 'Salvage items for research notes'


STRATEGY_PRICES = {}
STRATEGY_FORBID_BUY = set()
STRATEGY_FORBID_CRAFT = set()
STRATEGY_CAN_CRAFT_RECIPE = lambda r: True
_OPTIMAL_STRATEGY_CACHE = {}
_OPTIMAL_COST_CACHE = {}

def set_strategy_params(prices, forbid_buy, forbid_craft, can_craft_recipe):
    '''Set prices to use for `StrategyBuy`.'''
    global STRATEGY_PRICES, STRATEGY_FORBID_BUY, STRATEGY_FORBID_CRAFT, STRATEGY_CAN_CRAFT_RECIPE
    global _OPTIMAL_STRATEGY_CACHE, _OPTIMAL_COST_CACHE
    STRATEGY_PRICES = prices
    STRATEGY_FORBID_BUY = forbid_buy
    STRATEGY_FORBID_CRAFT = forbid_craft
    STRATEGY_CAN_CRAFT_RECIPE = can_craft_recipe
    _OPTIMAL_STRATEGY_CACHE = {}
    _OPTIMAL_COST_CACHE = {}

def valid_strategies(item_id, allow_refine_only=False):
    if item_id not in STRATEGY_FORBID_BUY:
        price = STRATEGY_PRICES.get(item_id)
        if price is not None:
            yield StrategyBuy(item_id, price)

    if item_id not in STRATEGY_FORBID_CRAFT:
        recipe_ids = gw2.recipes.search_output(item_id)
        for recipe_id in recipe_ids:
            r = gw2.recipes.get(recipe_id)
            if r.get('bookkeeper_refine_only') and not allow_refine_only:
                continue
            if STRATEGY_CAN_CRAFT_RECIPE(r):
                yield StrategyCraft(r)

        mystic_recipe_ids = gw2.mystic_forge.search_output(item_id)
        for mystic_recipe_id in mystic_recipe_ids:
            r = gw2.mystic_forge.get(mystic_recipe_id)
            if r.get('bookkeeper_refine_only') and not allow_refine_only:
                continue
            yield StrategyCraft(r)

        if item_id == ITEM_RESEARCH_NOTE:
            yield StrategyResearchNote(RESEARCH_NOTE_PANTS, RESEARCH_NOTES_PER_PANTS)
            yield StrategyResearchNote(RESEARCH_NOTE_EARRINGS, RESEARCH_NOTES_PER_EARRING)
            for weapons in RESEARCH_NOTE_WEAPONS:
                yield StrategyResearchNote(weapons, RESEARCH_NOTES_PER_WEAPON)
            yield StrategyResearchNote(RESEARCH_NOTE_POTIONS, RESEARCH_NOTES_PER_POTION)

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

def count_craftable(targets, inventory, buy_on_demand):
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
    craft_counts = {}

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
                # If this item is bought on demand, buy it
                if item_id in buy_on_demand:
                    inventory[item_id] += craft_count
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

        # Record the amount crafted, then subtract out the target items so they
        # can't be used as mats for later steps.
        craft_counts[target_item_id] = max(0,
                inventory[target_item_id] - orig_inventory[target_item_id])
        inventory[target_item_id] -= min(inventory[target_item_id], target_goal)

    return craft_counts


def policy_can_craft_recipe(r):
    min_rating = r['min_rating']
    discipline_levels = gw2.character.get_max_of_each_discipline()
    for d in r['disciplines']:
        if discipline_levels[d] != None and min_rating <= discipline_levels[d]:
            return True
    return False

def policy_forbid_buy():
    forbid = set()

    # Forbid buying or selling intermediate crafting items.
    for r in gw2.recipes.iter_all():
        if not policy_can_craft_recipe(r):
            continue

        item = gw2.items.get(r['output_item_id'])
        if item is not None:
            if item['type'] == 'UpgradeComponent' and item['details']['type'] == 'Gem':
                continue

        if r['type'] in ('Refinement', 'Component'):
            forbid.add(r['output_item_id'])

        if item is not None:
            if item['name'].startswith('Embellished'):
                forbid.add(item['id'])
            if item['name'].startswith('Exquisite'):
                forbid.add(item['id'])
            if 'Inscription' in item['name'] or 'Insignia' in item['name']:
                forbid.add(item['id'])

            if item['type'] in ('Weapon', 'Armor') and item['id'] in ALL_PROVISIONER_ITEMS:
                forbid.add(item['id'])

    ascended_refinement = [
        gw2.items.search_name('Deldrimor Steel Ingot'),
        gw2.items.search_name('Elonian Leather Square'),
        gw2.items.search_name('Bolt of Damask'),
        gw2.items.search_name('Spiritwood Plank'),
        gw2.items.search_name('Xunlai Electrum Ingot'),
    ]
    for item_id in ascended_refinement:
        if item_id in forbid:
            forbid.remove(item_id)

    forbid.update(RESEARCH_NOTE_PANTS)
    forbid.update(RESEARCH_NOTE_EARRINGS)
    for weapons in RESEARCH_NOTE_WEAPONS:
        forbid.update(weapons)
    forbid.update(RESEARCH_NOTE_POTIONS)

    forbid.add(gw2.items.search_name('20 Slot Invisible Bag'))
    forbid.add(gw2.items.search_name('20 Slot Gossamer Bag'))
    forbid.add(gw2.items.search_name("Berserker's Orichalcum Imbued Inscription"))

    forbid.remove(gw2.items.search_name('Pile of Lucent Crystal'))
    forbid.add(gw2.items.search_name('Lucent Mote'))
    forbid.add(gw2.items.search_name('Mithril Ore'))
    #forbid.remove(gw2.items.search_name('Vial of Linseed Oil'))

    # T6 mats
    forbid.remove(gw2.items.search_name('Orichalcum Ingot'))
    forbid.remove(gw2.items.search_name('Ancient Wood Plank'))
    forbid.remove(gw2.items.search_name('Bolt of Gossamer'))
    forbid.remove(gw2.items.search_name('Cured Hardened Leather Square'))

    # T5 mats
    forbid.remove(gw2.items.search_name('Mithril Ingot'))
    forbid.remove(gw2.items.search_name('Elder Wood Plank'))
    forbid.remove(gw2.items.search_name('Bolt of Silk'))
    forbid.remove(gw2.items.search_name('Cured Thick Leather Square'))

    # Refinement items that are usually very cheap to instant-buy
    forbid.remove(gw2.items.search_name('Pulsing Brandspark'))

    for i in range(2,23):
        forbid.add(gw2.items.search_name('+%d Agony Infusion' % i))

    for i in range(1, 11):
        forbid.add(gw2.items.search_name('Jade Bot Core: Tier %d' % i))

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

def policy_buy_on_demand():
    buy = set()

    buy.add(gw2.items.search_name('Piece of Ambrite'))
    buy.add(gw2.items.search_name('Congealed Putrescence'))
    buy.add(gw2.items.search_name('Evergreen Lodestone'))
    buy.add(gw2.items.search_name('Leaf Fossil'))
    buy.add(gw2.items.search_name('Ley-Infused Sand'))

    buy.add(gw2.items.search_name('Pulsing Brandspark'))
    buy.add(gw2.items.search_name('Eye of Kormir'))
    buy.add(gw2.items.search_name('Sliver of Twitching Forgemetal'))

    # Vendor items
    # TODO: include all vendor items in this set automatically
    buy.add(gw2.items.search_name('Lump of Tin'))
    buy.add(gw2.items.search_name('Lump of Coal'))
    buy.add(gw2.items.search_name('Superior Rune of Holding'))
    buy.add(gw2.items.search_name('Thermocatalytic Reagent'))
    buy.add(gw2.items.search_name('Spool of Gossamer Thread'))
    buy.add(gw2.items.search_name('Milling Basin'))

    return buy

def policy_auto_refine():
    '''Items that should be crafted if their inputs are already available, even
    if it's cheaper to buy.'''
    return (
            gw2.items.search_name('Copper Ingot'),
            gw2.items.search_name('Bronze Ingot'),
            gw2.items.search_name('Iron Ingot'),
            gw2.items.search_name('Steel Ingot'),
            gw2.items.search_name('Silver Ingot'),
            gw2.items.search_name('Gold Ingot'),
            gw2.items.search_name('Platinum Ingot'),
            gw2.items.search_name('Darksteel Ingot'),
            gw2.items.search_name('Mithril Ingot'),
            gw2.items.search_name('Orichalcum Ingot'),

            gw2.items.search_name('Elder Wood Log'),
            gw2.items.search_name('Ancient Wood Log'),

            gw2.items.search_name('Cured Thick Leather Square'),
            gw2.items.search_name('Cured Hardened Leather Square'),

            gw2.items.search_name('Bolt of Silk'),
            gw2.items.search_name('Bolt of Gossamer'),

            gw2.items.search_name('Pile of Lucent Crystal'),

            gw2.items.search_name('Spirit Shard'),
            gw2.items.search_name('Imperial Favor'),
            )


def cmd_init():
    os.makedirs('books', exist_ok=True)

def calculate_status():
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
    for c, i in CURRENCY_ITEMS:
        if c in wallet:
            inventory[i] += wallet[c]
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


    # Gather all items we might need to buy or sell, and obtain their current
    # prices to use as parameters for strategies.

    keys = set(stockpile.keys())
    keys.update(inventory.keys())
    shortage_items = set()
    for item_id in keys:
        if inventory.get(item_id, 0) < stockpile.get(item_id, 0):
            shortage_items.add(item_id)

    related_items = gather_related_items(chain(shortage_items, goals.keys()))
    buy_prices, sell_prices, buy_listings, sell_listings = \
            get_prices_and_listings(related_items)

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
    pending_items = set()
    state = State(
            inventory,
            pending_items,
            buy_items,
            craft_items,
            obtain_items,
            )

    # First pass: run until all inventory quantities are non-negative.  This
    # amounts to successfully crafting all the goal items.
    pending_items.update(shortage_items)
    while len(pending_items) > 0:
        item_id = pending_items.pop()
        shortage = -inventory.get(item_id, 0)
        if shortage <= 0:
            continue

        strategy = optimal_strategy(item_id)
        strategy.apply(state, shortage)
        assert inventory.get(item_id, 0) >= 0, \
                'strategy %r failed to produce %d %s' % (
                        strategy, shortage, gw2.items.name(item_id))

    # Compute what items we need to craft to restore all stockpiles.
    craft_stockpile_items = {}
    for item_id in keys:
        shortage = stockpile.get(item_id, 0) - inventory.get(item_id, 0)
        if shortage <= 0:
            continue
        shortage_items.add(item_id)
        if isinstance(optimal_strategy(item_id), (StrategyBuy, StrategyUnknown)):
            continue
        craft_stockpile_items[item_id] = shortage

    # Second pass: run until stockpile requirements are satisfied.
    assert len(pending_items) == 0
    pending_items.update(shortage_items)
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

    # Third pass: for items to be bought or otherwise obtained, try refining
    # the item from extra materials on hand.
    for item_id in policy_auto_refine():
        buy_shortage = buy_items.get(item_id, 0)
        obtain_shortage = obtain_items.get(item_id, 0)
        shortage = buy_shortage + obtain_shortage
        if shortage <= 0:
            continue

        total_refined = 0
        for strategy in valid_strategies(item_id, allow_refine_only=True):
            if not isinstance(strategy, StrategyCraft):
                continue
            count = strategy.max_count(state, exclude=stockpile, max_output=shortage)
            strategy.apply(state, count)
            shortage -= count
            total_refined += count

        print('auto-refined %d %s' % (total_refined,
            gw2.items.name(item_id)))

        # Undo the previous decision to buy/obtain this item, since we can
        # refine it instead.
        count = total_refined
        skip_buy = min(count, buy_shortage)
        if skip_buy > 0:
            buy_items[item_id] -= skip_buy
            count -= skip_buy
        skip_obtain = min(count, obtain_shortage)
        if skip_obtain > 0:
            obtain_items[item_id] -= skip_obtain
            count -= skip_obtain
        # `total_refined` should never exceed `buy_shortage + obtain_shortage`.
        assert count == 0


    used_items = {}
    for item_id, old_count in orig_inventory.items():
        new_count = inventory.get(item_id, 0)
        delta = new_count - old_count
        used_items[item_id] = -delta


    craft_items = defaultdict(int)
    for item_id, count in chain(
            sorted(craft_goal_items.items(), key=lambda x: gw2.items.name(x[0])),
            sorted(craft_stockpile_items.items(), key=lambda x: gw2.items.name(x[0]))):
        craft_items[item_id] += count
    craft_counts = count_craftable(list(craft_items.items()), orig_inventory,
            policy_buy_on_demand())

    craft_only_counts = {
            item_id: count_craftable([(item_id, count)], orig_inventory,
                policy_buy_on_demand()).get(item_id, 0)
            for item_id, count in craft_items.items()
            }

    return {
            'gold': gold,
            'orig_inventory': orig_inventory,
            'buy_prices': buy_prices,
            'sell_prices': sell_prices,
            'buy_listings': buy_listings,
            'sell_listings': sell_listings,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'sold': sold,
            'goals': goals,
            'craft_goal_items': craft_goal_items,
            'craft_stockpile_items': craft_stockpile_items,
            'craft_items': craft_items,
            'craft_counts': craft_counts,
            'craft_only_counts': craft_only_counts,
            'buy_items': buy_items,
            'obtain_items': obtain_items,
            'used_items': used_items,
            'sell_goal_items': sell_goal_items,
            }

def cmd_status():
    '''Print a report listing the following:

    * Items to buy
    * Pending buy orders
    * Items to craft
    * Items to obtain by unknown means
    * Existing items to be sold
    * Pending sell orders
    '''

    x = calculate_status()
    gold = x['gold']
    buy_prices = x['buy_prices']
    sell_prices = x['sell_prices']
    buy_listings = x['buy_listings']
    sell_listings = x['sell_listings']
    buy_orders = x['buy_orders']
    sell_orders = x['sell_orders']
    sold = x['sold']
    goals = x['goals']
    craft_items = x['craft_items']
    craft_goal_items = x['craft_goal_items']
    craft_counts = x['craft_counts']
    craft_only_counts = x['craft_only_counts']
    buy_items = x['buy_items']
    obtain_items = x['obtain_items']
    used_items = x['used_items']
    sell_goal_items = x['sell_goal_items']

    # Render output

    sell_orders = condense_transactions(sell_orders)
    buy_orders = condense_transactions(buy_orders)


    now = time.time()
    print('\nStatus at:', datetime.datetime.now())

    def row_buy(item_id, count):
        if count == 0:
            return None
        return {
                'item_id': item_id,
                'count': count,
                'unit_price': buy_prices.get(item_id),
                'alt_unit_price': sell_prices.get(item_id),
                }

    render_table('Buy',
            (CountColumn(), ItemNameColumn(), UnitPriceColumn(),
                TotalPriceColumn(), AltPriceDeltaColumn(), NumberOfStacksColumn()),
            (row_buy(item_id, count) for item_id, count in buy_items.items()))

    def row_buy_order(transaction):
        if transaction['quantity'] == 0:
            return None

        buried = 0
        buy_price = buy_prices.get(transaction['item_id'])
        if buy_price is not None:
            bury_count = sum(l['quantity']
                    for l in buy_listings[transaction['item_id']]
                    if l['unit_price'] > transaction['price'])
            tx_count = transaction['quantity']
            buried = (bury_count + tx_count - 1) // tx_count

        return {
                'item_id': transaction['item_id'],
                'count': transaction['quantity'],
                'unit_price': transaction['price'],
                'alt_unit_price': sell_prices.get(transaction['item_id']),
                'age_sec': now - parse_timestamp(transaction['created']),
                'buried': buried,
                }

    render_table('Buy orders',
            (CountColumn(), ItemNameColumn(), UnitPriceColumn(show_buried=True),
                TotalPriceColumn(), AltPriceDeltaColumn(), AgeColumn(), NumberOfStacksColumn()),
            (row_buy_order(t) for t in buy_orders))

    def row_obtain(item_id, count):
        if count == 0:
            return None
        return {
                'item_id': item_id,
                'count': count,
                }

    render_table('Obtain',
            (CountColumn(), ItemNameColumn()),
            (row_obtain(item_id, count) for item_id, count in obtain_items.items()))

    def row_use(item_id, count):
        if count == 0:
            return None
        return {
                'item_id': item_id,
                'count': count,
                'unit_price': sell_prices.get(item_id),
                }

    render_table('Use',
            (CountColumn(), ItemNameColumn(), UnitPriceColumn(), TotalPriceColumn()),
            (row_use(item_id, count) for item_id, count in used_items.items()))

    def rows_sell():
        orders_by_item = defaultdict(list)
        for t in sell_orders:
            if t['quantity'] == 0:
                continue
            orders_by_item[t['item_id']].append((t, parse_timestamp(t['created'])))

        sell_amounts = {}
        sell_age = {}
        recent_sell_amounts = {}
        for item_id, orders in orders_by_item.items():
            if len(orders) == 0:
                continue
            orders.sort(key=lambda x: x[1], reverse=True)
            _, recent_timestamp = orders[0]
            recent_sell_amounts[item_id] = sum(t['quantity']
                    for t, timestamp in orders
                    if timestamp >= recent_timestamp - 3600)
            sell_amounts[item_id] = sum(t['quantity'] for t, timestamp in orders)
            sell_age[item_id] = now - recent_timestamp

        sell_rows = {}
        def sell_row(item_id):
            if item_id not in sell_rows:
                count = craft_goal_items.get(item_id, 0) + sell_goal_items.get(item_id, 0)
                if count == 0:
                    count = None
                unit_price = sell_prices.get(item_id)
                craft_cost = optimal_cost(item_id)
                if unit_price is not None and craft_cost is not None:
                    roi = unit_price * 0.85 / craft_cost - 1
                else:
                    roi = None
                sell_rows[item_id] = {
                        'item_id': item_id,
                        'count': count,
                        'count_wait': None,
                        'count_craft': None,
                        'count_craft_only': None,
                        'count_sell': None,
                        'count_wait_craft': None,
                        'count_craft_sell': None,
                        'count_listed': None,
                        'unit_price': unit_price,
                        'age_sec': None,
                        'roi': roi,
                        }
            return sell_rows[item_id]

        for item_id, count in craft_items.items():
            row = sell_row(item_id)
            craft_count = craft_counts.get(item_id, 0)
            craft_only_count = craft_only_counts.get(item_id, 0)
            row['count_craft'] = craft_count
            row['count_craft_only'] = craft_only_count
            row['count_wait'] = count - craft_count

        for item_id, count in sell_goal_items.items():
            row = sell_row(item_id)
            row['count_sell'] = count

        for item_id, count in sell_amounts.items():
            row = sell_row(item_id)
            row['count_listed'] = count
            row['recent_age_sec'] = sell_age[item_id]
            row['recent_count'] = recent_sell_amounts[item_id]

        for row in sell_rows.values():
            count_wait = row.get('count_wait') or 0
            count_craft = row.get('count_craft') or 0
            count_craft_only = row.get('count_craft_only') or 0
            count_sell = row.get('count_sell') or 0
            if count_wait + count_craft != 0:
                row['count_wait_craft'] = count_wait + count_craft
            if count_craft_only + count_sell != 0:
                row['count_craft_sell'] = count_craft_only + count_sell

        #return sorted(sell_rows.values(), key=lambda x: gw2.items.name(x['item_id']))
        return list(sell_rows.values())

    rows_sell_list = rows_sell()

    render_table('Craft',
            (CountColumn(), ItemNameColumn(),
                AltCountColumn('wait', 'Wait'), AltCountColumn('craft', 'Craft'),
                AltCountColumn('sell', 'Sell'), AltCountColumn('listed', 'Listed'),
                PercentColumn()),
            [r for r in rows_sell_list if (r.get('count_wait_craft') or 0) != 0],
            render_title=True,
            render_total=False)

    render_table('Sell',
            (CountColumn(), ItemNameColumn(),
                DualCountColumn('sell', 'craft_sell', 'Sell'),
                RecentColumn(), AltCountColumn('listed', 'Listed'),
                PercentColumn()),
            [r for r in rows_sell_list
                if ((r.get('count') or 0) != 0 and
                        (r.get('count_craft_sell') or 0) != 0) or
                    (r.get('count_listed') or 0) != 0],
            render_title=True,
            render_total=False)

    def row_sell_order(transaction):
        if transaction['quantity'] == 0:
            return None

        buried = 0
        sell_price = sell_prices.get(transaction['item_id'])
        if sell_price is not None:
            bury_count = sum(l['quantity']
                    for l in sell_listings[transaction['item_id']]
                    if l['unit_price'] < transaction['price'])
            tx_count = transaction['quantity']
            buried = (bury_count + tx_count - 1) // tx_count

        return {
                'item_id': transaction['item_id'],
                'count': transaction['quantity'],
                'unit_price': transaction['price'],
                'age_sec': now - parse_timestamp(transaction['created']),
                'buried': buried,
                }

    render_table('Sell orders',
            (CountColumn(), ItemNameColumn(), UnitPriceColumn(show_buried=True),
                TotalPriceColumn(0.9), AgeColumn()),
            (row_sell_order(t) for t in sell_orders))

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

    # "Cash out" means to do the following:
    # * Cancel all buy orders
    # * Cancel all sell orders and instant-sell them at the buy price
    # * Sell everything waiting to be listed at its buy price
    # * Craft everything that's currently craftable and sell at the buy price
    #
    # The purpose of that last point is to give a more useful number in the
    # case where the player is deliberately waiting to craft an item in order
    # to save on bag space.
    cash_out_buy_orders = sum(t['price'] * t['quantity'] for t in buy_orders)
    cash_out_sell_orders = sum(
            buy_prices.get(t['item_id'], 0) * t['quantity'] * 0.85
            for t in sell_orders)
    cash_out_sell_goal_items = sum(buy_prices.get(item_id, 0) * count * 0.85
            for item_id, count in sell_goal_items.items())
    cash_out_craft_counts = sum(
            buy_prices.get(item_id, 0) * craft_counts.get(item_id, 0) * 0.85
            for item_id in craft_items.keys())

    print('Current gold: %s' % format_price(gold))
    print('After current sales: %s' % format_price(gold + current_sell_total))
    print('Cash out: %s' % format_price(gold + cash_out_buy_orders +
        cash_out_sell_orders + cash_out_sell_goal_items + cash_out_craft_counts))
    print('Target gold: %s' % format_price(gold - future_buy_total +
        current_sell_total + future_sell_total))

class CountColumn:
    def format(self):
        return '%6s'

    def title(self):
        return 'Count'

    def render(self, row):
        count = row.get('count')
        if count is None:
            return ''
        return str(count)

    def render_total(self):
        return ''

class AltCountColumn:
    def __init__(self, suffix, title):
        self.suffix = suffix
        self.title_ = title

    def format(self):
        return '%6s'

    def title(self):
        return self.title_

    def render(self, row):
        count = row.get('count_' + self.suffix)
        if count is None:
            return ''
        if count == 0:
            return '-'
        return str(count)

    def render_total(self):
        return ''

class DualCountColumn:
    def __init__(self, suffix1, suffix2, title):
        self.suffix1 = suffix1
        self.suffix2 = suffix2
        self.title_ = title

    def format(self):
        return '%9s'

    def title(self):
        return self.title_

    def render(self, row):
        count1 = row.get('count_' + self.suffix1)
        count2 = row.get('count_' + self.suffix2)
        if count1 is None and count2 is None:
            return ''
        if count1 in (0, None) and count2 in (0, None):
            return '-'
        if count1 == count2:
            return str(count1)
        count1_str = '-' if count1 in (0, None) else str(count1)
        count2_str = '-' if count2 in (0, None) else str(count2)
        return '%s/%s' % (count1_str, count2_str)

    def render_total(self):
        return ''

class AgeColumn:
    def format(self):
        return '%6s'

    def title(self):
        return 'Age'

    def render(self, row):
        age_sec = row.get('age_sec')
        if age_sec is None:
            return ''
        days = age_sec // 86400
        hours = age_sec // 3600 % 24
        if days == 0:
            return '%dh' % hours
        else:
            return '%dd%02dh' % (days, hours)

    def render_total(self):
        return ''

class NumberOfStacksColumn:
    def format(self):
        return '%8s'

    def title(self):
        return 'Number Of Stacks'

    def render(self, row):
        count = row.get('count')
        stack_size = 250
        if count is None:
            return ''
        number_of_stacks = int(count/stack_size)
        remainder = count % stack_size
        return str(number_of_stacks) + 'x' + str(remainder)

    def render_total(self):
        return ''

class RecentColumn:
    def format(self):
        return '%10s'

    def title(self):
        return 'Recent'

    def render(self, row):
        parts = []

        count = row.get('recent_count')
        if count is not None:
            parts.append(str(count))

        age_sec = row.get('recent_age_sec')
        if age_sec is not None:
            days = age_sec // 86400
            hours = age_sec // 3600 % 24
            if days == 0:
                parts.append('%dh' % hours)
            else:
                parts.append('%dd%02dh' % (days, hours))

        return '/'.join(parts)

    def render_total(self):
        return ''

class ItemNameColumn:
    def format(self):
        return '%-35.35s'

    def title(self):
        return 'Item'

    def render(self, row):
        item_id = row.get('item_id')
        if item_id is None:
            return ''
        return gw2.items.name(item_id)

    def render_total(self):
        return 'Total'

class UnitPriceColumn:
    def __init__(self, key='unit_price', title='Unit Price', show_buried=False):
        self.key = key
        self.title_ = title
        self.show_buried = show_buried

    def format(self):
        if self.show_buried:
            return '%13s'
        else:
            return '%11s'

    def title(self):
        return self.title_

    def render(self, row):
        unit_price = row.get(self.key)
        if unit_price is None:
            return ''
        unit_price_str = format_price(unit_price)

        buried_str = ''
        if self.show_buried:
            buried = row.get('buried', 0)
            if buried <= 0:
                buried_str = '  '
            elif buried == 1:
                buried_str = '! '
            elif buried == 2:
                buried_str = '!!'
            elif buried <= 10:
                buried_str = '!%d' % (buried - 1)
            else:
                buried_str = '!*'

        return unit_price_str + buried_str

    def render_total(self):
        return ''

class TotalPriceColumn:
    def __init__(self, mult=1):
        self.total = 0
        self.mult = mult

    def title(self):
        return 'Total Price'

    def format(self):
        return '%11s'

    def render(self, row):
        count = row.get('count')
        unit_price = row.get('unit_price')
        if count is None or unit_price is None:
            return ''
        self.total += count * unit_price
        return format_price(count * unit_price * self.mult)

    def render_total(self):
        return format_price(self.total * self.mult)

class PercentColumn:
    def __init__(self, key='roi', title='ROI'):
        self.key = key
        self.title_ = title

    def format(self):
        return '%8s'

    def title(self):
        return self.title_

    def render(self, row):
        roi = row.get(self.key)
        if roi is None:
            return ''
        return '%5.1f%%' % (roi * 100)

    def render_total(self):
        return ''

class AltPriceDeltaColumn:
    def __init__(self):
        self.total = 0

    def title(self):
        return 'Inst. Delta'

    def format(self):
        return '%11s'

    def render(self, row):
        count = row.get('count')
        unit_price = row.get('unit_price')
        alt_unit_price = row.get('alt_unit_price')
        if count is None or unit_price is None or alt_unit_price is None:
            return ''
        delta = count * (alt_unit_price - unit_price)
        self.total += delta
        return format_price_delta(delta)

    def render_total(self):
        return format_price_delta(self.total)


def render_table(name, columns, rows, render_title=False, render_total=True):
    rows = [r for r in rows if r is not None]
    if len(rows) == 0:
        return
    print('\n%s:' % name)
    fmt = '  '.join(col.format() for col in columns)
    if render_title:
        print((fmt % tuple(col.title() for col in columns)).rstrip())
    for row in rows:
        print((fmt % tuple(col.render(row) for col in columns)).rstrip())
    if render_total:
        print((fmt % tuple(col.render_total() for col in columns)).rstrip())


def cmd_steps(names):
    if len(names) == 0:
        filter_item_ids = None
    else:
        filter_item_ids = set(parse_item_id(name) for name in names)

    # Note that `calculate_status` also sets the strategy parameters.
    x = calculate_status()
    craft_goal_items = x['craft_goal_items']
    craft_stockpile_items = x['craft_stockpile_items']
    orig_inventory = x['orig_inventory']

    craft_items = defaultdict(int)
    for item_id, count in chain(craft_goal_items.items(), craft_stockpile_items.items()):
        if filter_item_ids is not None and item_id not in filter_item_ids:
            continue
        craft_items[item_id] += count
    craft_counts = count_craftable(list(craft_items.items()), orig_inventory,
            policy_buy_on_demand())

    class StackSet:
        '''Provides an API like `set()`, but `pop()` always returns the most
        recently added item.'''
        def __init__(self):
            self.set = set()
            self.lst = []

        def add(self, x):
            self.lst.append(x)
            self.set.add(x)

        def pop(self):
            if len(self.set) == 0:
                raise KeyError('pop from an empty set')
            x = self.lst.pop()
            while x not in self.set:
                x = self.lst.pop()
            self.set.remove(x)
            return x

        def __len__(self):
            return len(self.set)

    pending_items = StackSet()
    inventory = orig_inventory.copy()
    state = State(inventory, pending_items,
            defaultdict(int), defaultdict(int), defaultdict(int))
    steps = []

    for item_id, count in reversed(craft_counts.items()):
        strategy = optimal_strategy(item_id)
        strategy.apply(state, count)
        steps.append((strategy, count))

        while len(pending_items) > 0:
            item_id = pending_items.pop()
            shortage = -inventory.get(item_id, 0)
            if shortage <= 0:
                continue
            strategy = optimal_strategy(item_id)
            strategy.apply(state, shortage)
            steps.append((strategy, shortage))

    # Postprocess steps
    steps.reverse()
    strat_count = {}
    strat_order = []
    for i, (strat, count) in enumerate(steps):
        if count == 0:
            continue
        if id(strat) not in strat_count:
            strat_count[id(strat)] = count
            strat_order.append(strat)
        else:
            strat_count[id(strat)] += count
    steps = [(strat, strat_count[id(strat)]) for strat in strat_order]

    for strat, count in steps:
        adj_count, desc = strat.describe(count)
        print('%6d  %s' % (adj_count, desc))


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


    if count > 0:
        related_items = gather_related_items([item_id])
        buy_prices, sell_prices = get_prices(related_items)

        set_strategy_params(
                buy_prices,
                policy_forbid_buy().union((item_id,)),
                policy_forbid_craft(),
                policy_can_craft_recipe,
                )

        sell_price = sell_prices[item_id]
        buy_price = buy_prices[item_id]
        cost = optimal_cost(item_id)
        print('%d %s (%d)' % (count, gw2.items.name(item_id), item_id))
        print('Cost:        %s' % format_price(cost * count))
        print('Sell price:  %s' % format_price(sell_price * count))
        print('Buy price:   %s' % format_price(buy_price * count))
        profit = sell_price * 0.85 - cost
        profit_pct = 100 * profit / cost
        print('Profit:      %s (%.1f%%)' % (format_price(profit * count), profit_pct))

def cmd_stockpile(count, name):
    count = int(count)
    item_id = parse_item_id(name)

    stockpile = _load_dict(STOCKPILE_PATH)
    stockpile[item_id] = stockpile.get(item_id, 0) + count
    _dump_dict(stockpile, STOCKPILE_PATH)
    print('%s stockpile target to %d %s' % (
        'increased' if count >= 0 else 'decreased',
        stockpile[item_id], gw2.items.name(item_id)))

def cmd_stockpile_list():
    stockpile = _load_dict(STOCKPILE_PATH)
    entries = [(gw2.items.name(item_id), count, item_id)
            for item_id, count in stockpile.items() if count != 0]
    for name, count, item_id in sorted(entries):
        print('%6d  %s  - %d' % (count, name, item_id))

def cmd_profit(name):
    '''Show the profit to be made by crafting the named item.'''
    item_id = parse_item_id(name)

    related_items = gather_related_items([item_id])
    buy_prices, sell_prices = get_prices(related_items)

    set_strategy_params(
            buy_prices,
            policy_forbid_buy().union((item_id,)),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    buy_price = buy_prices[item_id]
    sell_price = sell_prices[item_id]
    cost = optimal_cost(item_id)
    print('%s (%d)' % (gw2.items.name(item_id), item_id))
    print('Cost:        %s' % format_price(cost))
    print('Break even:  %s' % format_price(math.ceil(cost / 0.85)))
    print('Buy price:   %s' % format_price(buy_price))
    print('Sell price:  %s' % format_price(sell_price))
    profit = sell_price * 0.85 - cost
    profit_pct = 100 * profit / cost
    print('Profit:      %s (%.1f%%)' % (format_price(profit), profit_pct))

def cmd_jade_bot_core_profits():
    for tier_level in range(1,11):
     cmd_profit('Jade Bot Core: Tier ' + str(tier_level))

# One line per category.  In each category, you can only sell one item per day.
# TODO: switch to string search terms once gw2.items handles name collisions
# TODO: fill in remaining options
PROVISIONER_ITEMS = [
    ("Lion's Arch", {19983: 1}),
    ("Lion's Arch", {19721: 5}),
    ("Lion's Arch", {24830: 1}),

    ('Black Citadel', {19925: 1}),
    ('Black Citadel', {24366: 20}),
    ('Black Citadel', {24741: 12}),

    ("Divinity's Reach", {46742: 1}),
    ("Divinity's Reach", {24678: 34}),
    ("Divinity's Reach", {24732: 4}),

    ('Hoelbrak', {46745: 1}),
    ('Hoelbrak', {24651: 20}),
    ('Hoelbrak', {24729: 14}),

    ('Rata Sum', {43772: 1}),
    ('Rata Sum', {24330: 24}),
    ('Rata Sum', {24726: 14}),

    ('The Grove', {46744: 1}),
    ('The Grove', {66650: 3}),
    ('The Grove', {24735: 14}),

    ('Verdant Brink', {74356: 1}),
    ('Verdant Brink', {46281: 1, 46040: 1, 46186: 1, 45731: 1, 45765: 1, 45622: 1}),
    ('Verdant Brink', {15465: 1, 13924: 1, 14469: 1, 11121: 1, 11876: 1, 10702: 1}),
    ('Verdant Brink', {15394: 1, 13895: 1, 14517: 1, 11295: 1, 11798: 1, 10722: 1}),
    ('Verdant Brink', {15508: 1, 13974: 1, 14596: 1, 11248: 1, 11835: 1, 10710: 1}),
    ('Verdant Brink', {36779: 1, 36813: 1, 36750: 1, 36892: 1, 36891: 1, 36746: 1}),

    ('Auric Basin', {73537: 1}),
    ('Auric Basin', {38336: 1, 38415: 1, 38367: 1, 38228: 1, 38264: 1, 38179: 1}),
    ('Auric Basin', {15352: 1, 13895: 1, 14566: 1, 11295: 1, 11798: 1, 10722: 1}),
    ('Auric Basin', {15427: 1, 13928: 1, 14648: 1, 11167: 1, 11754: 1, 10699: 1}),

    ('Tangled Depths', {72205: 1}),
    ('Tangled Depths', {15391: 1, 13976: 1, 14563: 1, 11341: 1, 11921: 1, 10691: 1}),
    ('Tangled Depths', {15423: 1, 13973: 1, 14428: 1, 11247: 1, 11834: 1, 10709: 1}),
    ('Tangled Depths', {15512: 1, 13894: 1, 14516: 1, 11126: 1, 11881: 1, 10707: 1}),
    ('Tangled Depths', {36779: 1, 36780: 1, 36812: 1, 36844: 1, 36842: 1, 36806: 1}),
]

ALL_PROVISIONER_ITEMS = set(item_id for name, items in PROVISIONER_ITEMS
        for item_id in items.keys())

def cmd_provisioner():
    related_items = gather_related_items(item_id
            for _, category in PROVISIONER_ITEMS for item_id in category.keys())
    buy_prices, sell_prices = get_prices(related_items)

    set_strategy_params(
            buy_prices,
            policy_forbid_buy(),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    best_in_category = []
    for cat_name, category in PROVISIONER_ITEMS:
        best_item_id = None
        best_count = None
        best_cost = None
        for item_id, count in category.items():
            unit_cost = optimal_cost(item_id)
            if unit_cost is None:
                continue
            cost = unit_cost * count
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_item_id = item_id
                best_count = count
        if best_cost is not None:
            best_in_category.append((best_cost, best_item_id, best_count, cat_name))
    best_in_category.sort(key=lambda x: x[0])
    for cost, item_id, count, cat_name in best_in_category:
        desc = '%s (%d)' % (gw2.items.name(item_id), item_id)
        print('%10d  %-50.50s  %12s  %-20s' % (count, desc, format_price(cost), cat_name))

def cmd_obtain(name):
    '''Print out the optimal strategy for obtaining the named item.'''
    item_id = parse_item_id(name)

    related_items = gather_related_items([item_id])
    buy_prices, sell_prices = get_prices(related_items)

    set_strategy_params(
            buy_prices,
            policy_forbid_buy(),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    inventory = defaultdict(int)
    inventory[item_id] = -1

    # Process items until all stockpile requirements are satisfied.
    buy_items = defaultdict(int)
    craft_items = defaultdict(int)
    obtain_items = defaultdict(int)
    pending_items = set()
    state = State(
            inventory,
            pending_items,
            buy_items,
            craft_items,
            obtain_items,
            )

    # First pass: run until all inventory quantities are non-negative.  This
    # amounts to successfully crafting all the goal items.
    pending_items.add(item_id)
    while len(pending_items) > 0:
        item_id = pending_items.pop()
        shortage = -inventory.get(item_id, 0)
        if shortage <= 0:
            continue

        strategy = optimal_strategy(item_id)
        strategy.apply(state, shortage)
        assert inventory.get(item_id, 0) >= 0, \
                'strategy %r failed to produce %d %s' % (
                        strategy, shortage, gw2.items.name(item_id))

    if len(buy_items) > 0:
        print('\nBuy:')
        for item_id, count in buy_items.items():
            print('%10d  %-45.45s' % (count, gw2.items.name(item_id)))

    if len(craft_items) > 0:
        print('\nCraft:')
        for item_id, count in craft_items.items():
            print('%10d  %-45.45s' % (count, gw2.items.name(item_id)))

    if len(obtain_items) > 0:
        print('\nObtain:')
        for item_id, count in obtain_items.items():
            print('%10d  %-45.45s' % (count, gw2.items.name(item_id)))

def gen_profit_sql(path):
    if os.path.exists(path):
        os.unlink(path)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE items (
            id INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            buy_price INTEGER,
            sell_price INTEGER,
            demand INTEGER,
            supply INTEGER,
            cost INTEGER,
            craft_roi REAL,
            craft_roi_buy REAL
        )
    ''')

    output_item_ids = set(craftable_items())

    related_items = gather_related_items(output_item_ids)
    buy_prices, sell_prices = get_prices(related_items)
    forbid_buy = policy_forbid_buy()
    forbid_craft = policy_forbid_craft()

    print('processing %d items' % len(output_item_ids))
    num_written = 0
    for item_id in output_item_ids:
        set_strategy_params(
                buy_prices,
                set(chain(forbid_buy, (item_id,))),
                forbid_craft,
                policy_can_craft_recipe,
                )
        craft_cost = optimal_cost(item_id)
        if craft_cost is None:
            continue

        craft_roi = None
        sell_price = sell_prices.get(item_id)
        if sell_price is not None:
            profit = sell_price * 0.85 - craft_cost
            craft_roi = profit / craft_cost

        craft_roi_buy = None
        buy_price = buy_prices.get(item_id)
        if buy_price is not None:
            profit = buy_price * 0.85 - craft_cost
            craft_roi_buy = profit / craft_cost

        prices = gw2.trading_post.get_prices(item_id)
        if prices is None:
            continue

        item = gw2.items.get(item_id)
        if item is None:
            continue

        cur.execute('''
            INSERT INTO items
                (id, name, buy_price, sell_price, demand, supply, cost,
                    craft_roi, craft_roi_buy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                item['name'],
                buy_price,
                sell_price,
                prices['buys'].get('quantity'),
                prices['sells'].get('quantity'),
                craft_cost,
                craft_roi,
                craft_roi_buy,
            ))
        num_written += 1

    print('wrote %d items to %s' % (num_written, path))
    conn.commit()
    conn.close()

def cmd_gen_profit_sql():
    '''Generate a sqlite database containing information on profitable
    recipes.'''
    gen_profit_sql('profit.sqlite')

def do_craft_profit(item_ids=None, sort=True, row_filter=None, title='Profits'):
    if row_filter is None:
        def row_filter(x):
            if x['sell_price'] >= x['buy_price'] * 1.5:
                return False
            if x['demand'] < 100: # or x['demand'] < x['supply']: - this isn't a good filter for gw2. see: Peice of Dragon Jade or Sup Rune of the Elementalist
                return False
            if x['roi'] < 0.08 or x['roi'] > 2:
                return False
            if x['craft_cost'] < 2000:
                return False

            item = x['item']
            if item['level'] != 80 and item['type'] in ('Weapon', 'Armor', 'Consumable'):
                return False
            if item['level'] < 60 and item['type'] in ('UpgradeComponent',):
                return False
            if item['type'] in ('Weapon', 'Armor'):
                if item['rarity'] not in ('Exotic', 'Ascended', 'Legendary'):
                    return False

            return True

    if item_ids is None:
        output_item_ids = set(craftable_items())
    else:
        output_item_ids = set(item_ids)

    related_items = gather_related_items(output_item_ids)
    buy_prices, sell_prices = get_prices(related_items)
    forbid_buy = policy_forbid_buy()
    forbid_craft = policy_forbid_craft()

    rows = []
    for item_id in output_item_ids:
        set_strategy_params(
                buy_prices,
                set(chain(forbid_buy, (item_id,))),
                forbid_craft,
                policy_can_craft_recipe,
                )

        sell_price = sell_prices.get(item_id)
        cost = optimal_cost(item_id)
        if sell_price is None or cost is None:
            continue

        profit = sell_price * 0.85 - cost
        if profit <= 0:
            continue

        prices = gw2.trading_post.get_prices(item_id)

        row = {
            'item_id': item_id,
            'item': gw2.items.get(item_id),
            'craft_cost': cost,
            'profit': profit,
            'roi': profit / cost,
            'supply': prices['sells'].get('quantity', 0),
            'demand': prices['buys'].get('quantity', 0),
            'sell_price': sell_prices.get(item_id, 0),
            'buy_price': buy_prices.get(item_id, 0),
            }
        if row_filter(row):
            rows.append(row)

    if sort:
        rows.sort(key=lambda row: row.get('roi', 0), reverse=True)

    render_table(title,
            (ItemNameColumn(),
                PercentColumn(),
                UnitPriceColumn('craft_cost', 'Craft Cost'),
                UnitPriceColumn('profit', 'Unit Profit'),
                ),
            rows,
            render_title=True,
            render_total=False)

def cmd_craft_profit():
    '''Print a table of recipes that are profitable at the buy price, along
    with market depth for each one.'''
    do_craft_profit()

def cmd_craft_profit_buy():
    '''Print a table of recipes that are profitable at the buy price, along
    with market depth for each one.'''
    output_item_ids = set(craftable_items())

    related_items = gather_related_items(output_item_ids)
    buy_prices, sell_prices = get_prices(related_items)

    set_strategy_params(
            buy_prices,
            policy_forbid_buy(),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    rows = []
    for item_id in output_item_ids:
        buy_price = buy_prices.get(item_id)
        cost = optimal_cost(item_id)
        if buy_price is None or cost is None:
            continue

        profit = buy_price * 0.85 - cost
        if profit <= 0:
            continue

        rows.append({
            'item_id': item_id,
            'craft_cost': cost,
            'min_sell_price': math.ceil(cost / 0.85),
            'unit_price': buy_price,
            })

    # Collect detailed trading post data for profitable items.
    item_listings = gw2.trading_post.get_listings_multi([x['item_id'] for x in rows])
    for (row, listings) in zip(rows, item_listings):
        if listings is None or len(listings) == 0:
            continue

        cost = row['craft_cost']
        total_count = 0
        total_profit = 0
        for buy in listings['buys']:
            price = buy['unit_price']
            count = buy['quantity']
            profit = price * 0.85 - cost
            if profit <= 0:
                continue
            total_profit += profit * count
            total_count += count

        row['count'] = total_count
        row['total_profit'] = total_profit


    render_table('Buy-price Profits',
            (CountColumn(), ItemNameColumn(),
                UnitPriceColumn('craft_cost', 'Craft Cost'),
                UnitPriceColumn('min_sell_price', 'Min. Sell'),
                UnitPriceColumn(),
                UnitPriceColumn('total_profit', 'Max Profit')),
            sorted(rows, key=lambda row: row.get('total_profit', 0), reverse=True),
            render_title=True,
            render_total=False)

def cmd_research_notes():
    '''Print a list of items that can be crafted for research notes and the
    cost per note for each one.'''
    related_items = gather_related_items([item_id
        for s in valid_strategies(ITEM_RESEARCH_NOTE)
        if isinstance(s, StrategyResearchNote)
        for item_id in s.items])
    buy_prices, sell_prices = get_prices(related_items)
    set_strategy_params(
            buy_prices,
            policy_forbid_buy(),
            policy_forbid_craft(),
            policy_can_craft_recipe,
            )

    xs = []
    for strategy in valid_strategies(ITEM_RESEARCH_NOTE):
        if not isinstance(strategy, StrategyResearchNote):
            continue
        for item_id in strategy.items:
            cost = optimal_cost(item_id)
            if cost is None:
                print('no cost for item %s?' % gw2.items.name(item_id))
                continue
            cost_per_note = cost / strategy.notes_per_item
            xs.append((cost_per_note, item_id))
    for cost_per_note, item_id in sorted(xs):
        print('%15s  %s' % (format_price_float(cost_per_note),
            gw2.items.name(item_id)))

def cmd_charr_commendations():
    '''Print a list of items that can be traded for Charr Comendations and the
    cost per reward track (5,000 commendations) for each one.'''
    # Format: (commendations produced, item count required, item name)
    options = (
            (125, 100, gw2.items.search_name('Elder Wood Log'), ''),
            (125, 100, gw2.items.search_name('Mithril Ore'), ''),
            (125, 100, gw2.items.search_name('Thick Leather Section'), ''),
            (125, 200, gw2.items.search_name('Silk Scrap'), ''),
            (250, 100, gw2.items.search_name('Ancient Wood Log'), 'generic'),
            (250, 100, gw2.items.search_name('Orichalcum Ore'), 'generic'),
            (250, 100, gw2.items.search_name('Thick Leather Section'), 'generic'),
            (250, 200, gw2.items.search_name('Gossamer Scrap'), 'generic'),
            (250, 50, gw2.items.search_name('Ancient Wood Log'), 'specific'),
            (250, 50, gw2.items.search_name('Orichalcum Ore'), 'specific'),
            (250, 50, gw2.items.search_name('Thick Leather Section'), 'specific'),
            (250, 100, gw2.items.search_name('Gossamer Scrap'), 'specific'),
    )
    related_items = gather_related_items([i for _,_,i,_ in options])
    buy_prices, sell_prices = get_prices(related_items)

    xs = []
    for opt in options:
        out_count, in_count, item_id, _ = opt
        cost = buy_prices[item_id] * in_count * (5000 / out_count)
        xs.append((cost, opt))

    for cost, (out_count, in_count, item_id, desc) in sorted(xs):
        desc_str = '' if desc == '' else ' (%s)' % desc
        print('%9s  %3d %s%s' % (format_price(cost),
            in_count, gw2.items.name(item_id), desc_str))

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
    elif cmd == 'steps':
        cmd_steps(args)
    elif cmd == 'goal':
        count, name = args
        cmd_goal(count, name)
    elif cmd == 'stockpile':
        count, name = args
        cmd_stockpile(count, name)
    elif cmd == 'stockpile_list':
        assert len(args) == 0
        cmd_stockpile_list()
    elif cmd == 'profit':
        name, = args
        cmd_profit(name)
    elif cmd == 'provisioner':
        assert len(args) == 0
        cmd_provisioner()
    elif cmd == 'obtain':
        name, = args
        cmd_obtain(name)
    elif cmd == 'gen_profit_sql':
        assert len(args) == 0
        cmd_gen_profit_sql()
    elif cmd == 'craft_profit':
        assert len(args) == 0
        cmd_craft_profit()
    elif cmd == 'craft_profit_buy':
        assert len(args) == 0
        cmd_craft_profit_buy()
    elif cmd == 'research_notes':
        assert len(args) == 0
        cmd_research_notes()
    elif cmd == 'jade_core_profits':
        assert len(args) == 0
        cmd_jade_bot_core_profits()
    elif cmd == 'charr_commendations':
        assert len(args) == 0
        cmd_charr_commendations()
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()
