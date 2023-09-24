import gw2.api
import gw2.items
import bookkeeper
import math

RIFTS_PER_HOUR = 20

def essences_per_rift(tier, using_motivation):
    # Assumes that player has Rift Mastery
    # Comments of rewards are from the gw2 wiki
    num_essence_of_despair = 0
    num_essence_of_greed = 0
    num_essence_of_triumph = 0

    if tier == 1:
        # Essence of Despair (3-7)
        average_pre_event_essence = (3+7)/2
        # Essence of Despair (6-13) with Rift Mastery
        average_boss_event_essence = (6+13)/2
        # Additional essence gain when using a motivation seems to be between 19 - 31 with Rift Mastery
        motivation_bonus = (19+31)/2 if using_motivation else 0

        num_essence_of_despair = average_pre_event_essence + average_boss_event_essence + motivation_bonus
    elif tier == 2:
        # Essence of Despair (3-5)
        average_pre_event_essence = (3+5)/2
        # Essence of Greed (6-14) with Rift Mastery
        average_boss_event_essence = (6+14)/2
        # When using Uncommon Motivation: Essence of Greed (21-22) with Rift Mastery
        motivation_bonus = (21+22)/2 if using_motivation else 0

        num_essence_of_despair = average_pre_event_essence
        num_essence_of_greed = average_boss_event_essence + motivation_bonus
    elif tier == 3:
        # Essence of Despair (3)
        average_pre_event_essence = 3
        # Essence of Triumph (9-11) with Rift Mastery
        average_boss_event_essence = (9+11)/2
        # When using Rare Motivation: Essence of Triumph (22-27) with Rift Mastery
        motivation_bonus = (22+27)/2 if using_motivation else 0
        
        num_essence_of_despair = average_pre_event_essence
        num_essence_of_triumph = average_boss_event_essence + motivation_bonus
    
    return [num_essence_of_despair, num_essence_of_greed, num_essence_of_triumph]

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    inventory = bookkeeper.get_inventory()

    def count_input(kind, name):
        if kind == 'item':
            return inventory.get(gw2.items.search_name(name), 0)
        else:
            raise ValueError('bad input kind %r' % (kind,))

    def report(inputs, output_count=1):
        times = min(count_input(kind, name) // count
                for count, name, kind in inputs)
        input_strs = '  '.join('%5d  %-18.18s' % (count, name)
                for count, name, kind in inputs)
        produces_str = '' if output_count == 1 else ' (produces %d)' % output_count
        print('%6d   %s%s' % (times * output_count, input_strs, produces_str))

    print()
    print('Current amount of Essence:')
    report([(1, 'Essence of Despair', 'item')])
    report([(1, 'Essence of Greed', 'item')])
    report([(1, 'Essence of Triumph', 'item')])
    print()
    print('Rifts needed for full legendary armor using motivations:')
    print('\nBuying all motivations')
    # Taken from https://www.reddit.com/r/Guildwars2/comments/1653lii/cost_of_obsidian_legendary_armor_summarized/?rdt=62704
    essences_needed = [18000, 7200, 3900]

    essences_per_t3_rift = essences_per_rift(3, True)
    t3_rifts_needed = math.ceil(essences_needed[2] / essences_per_t3_rift[2])
    t1_essences_gained_from_t3_rifts = t3_rifts_needed * essences_per_t3_rift[0]

    essences_per_t2_rift = essences_per_rift(2, True)
    t2_rifts_needed = math.ceil(essences_needed[1] / essences_per_t2_rift[1])
    t1_essences_gained_from_t2_rifts = t2_rifts_needed * essences_per_t2_rift[0]

    essences_per_t1_rift = essences_per_rift(1, True)
    total_t1_essences_gained = t1_essences_gained_from_t3_rifts + t1_essences_gained_from_t2_rifts
    t1_rifts_needed = math.ceil((essences_needed[0]- total_t1_essences_gained) / essences_per_t1_rift[0])

    total_number_rifts_needed = t1_rifts_needed + t2_rifts_needed + t3_rifts_needed

    print('Tier 1 Rifts Needed: %d' % t1_rifts_needed)
    print('Tier 2 Rifts Needed: %d' % t2_rifts_needed)
    print('Tier 3 Rifts Needed: %d' % t3_rifts_needed)
    print()
    t1_motivation_item = gw2.items.search_name('Common Kryptis Motivation')
    t2_motivation_item = gw2.items.search_name('Uncommon Kryptis Motivation')
    t3_motivation_item = gw2.items.search_name('Rare Kryptis Motivation')
    t1_motivations_needed = t1_rifts_needed
    t2_motivations_needed = t2_rifts_needed
    t3_motivations_needed = t3_rifts_needed
    buy_prices, sell_prices = bookkeeper.get_prices([t1_motivation_item, t2_motivation_item, t3_motivation_item])
    t1_motivation_buy_price = buy_prices[t1_motivation_item]
    t2_motivation_buy_price = buy_prices[t2_motivation_item]
    t3_motivation_buy_price = buy_prices[t3_motivation_item]
    t1_motivation_cost = t1_motivations_needed * t1_motivation_buy_price
    t2_motivation_cost = t2_motivations_needed * t2_motivation_buy_price
    t3_motivation_cost = t3_motivations_needed * t3_motivation_buy_price
    total_motivation_cost = t1_motivation_cost + t2_motivation_cost + t3_motivation_cost
    print('Tier 1 Motivations: %d (cost: %s)' % (t1_motivations_needed, bookkeeper.format_price(t1_motivation_cost)))
    print('Tier 2 Motivations: %d (cost: %s)' % (t2_motivations_needed, bookkeeper.format_price(t2_motivation_cost)))
    print('Tier 3 Motivations: %d (cost: %s)' % (t3_motivations_needed, bookkeeper.format_price(t3_motivation_cost)))
    print()
    print('Total Rifts Needed: %d' % total_number_rifts_needed)
    print('Total Hours Needed: %d' % math.ceil(total_number_rifts_needed / RIFTS_PER_HOUR))
    print('Total Motivation Cost: %s' % bookkeeper.format_price(total_motivation_cost))

    print('\nNot using motivations')
    essences_per_t3_rift = essences_per_rift(3, False)
    t3_rifts_needed = math.ceil(essences_needed[2] / essences_per_t3_rift[2])
    t1_essences_gained_from_t3_rifts = t3_rifts_needed * essences_per_t3_rift[0]

    essences_per_t2_rift = essences_per_rift(2, False)
    t2_rifts_needed = math.ceil(essences_needed[1] / essences_per_t2_rift[1])
    t1_essences_gained_from_t2_rifts = t2_rifts_needed * essences_per_t2_rift[0]

    essences_per_t1_rift = essences_per_rift(1, False)
    total_t1_essences_gained = t1_essences_gained_from_t3_rifts + t1_essences_gained_from_t2_rifts
    t1_rifts_needed = math.ceil((essences_needed[0]- total_t1_essences_gained) / essences_per_t1_rift[0])

    total_number_rifts_needed = t1_rifts_needed + t2_rifts_needed + t3_rifts_needed

    print('Tier 1 Rifts Needed: %d' % t1_rifts_needed)
    print('Tier 2 Rifts Needed: %d' % t2_rifts_needed)
    print('Tier 3 Rifts Needed: %d' % t3_rifts_needed)
    print()
    print('Total Rifts Needed: %d' % total_number_rifts_needed)
    print('Total Hours Needed: %d' % math.ceil(total_number_rifts_needed / RIFTS_PER_HOUR))


if __name__ == '__main__':
    main()
