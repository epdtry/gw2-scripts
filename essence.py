import gw2.api
import gw2.items
import bookkeeper
import math
import random
import datetime


RIFTS_PER_HOUR = 20

def essences_per_kryptis_extraction():
    return [5.08, 4.79, 2.13]

def optimal_rifts_per_week(essences_needed):
    print()
    print('OPTIMAL RIFTS PER WEEK (ALWAYS BUYING MOTIVATIONS))')
    # There are weekly bonuses for doing 5 rifts in each zone.
    # Two of the zones you can only do t2 rifts in.
    # Each zones bonus gives 6 kryptis extractions if you do 5 rifts in that zone.
    # We need to do at least 1 of rift of each tier per week, except for the two zones that only have t2 rifts.
    # Calculate the minimum number of rifts needed for each zone until we have enough essences needed.
    remaining_essences_needed = essences_needed.copy()

    essences_per_t3_rift = essences_per_rift(3, True)
    essences_per_t2_rift = essences_per_rift(2, True)
    essences_per_t1_rift = essences_per_rift(1, True)
    essences_per_extraction = essences_per_kryptis_extraction()

    best_num_weeks = math.inf
    best_essences_left_over = [0, 0, 0]

    # Do 5 t1 rifts for Archipelago
    zone_1_tier = 1
    zone_1_essences = [5 * essences for essences in essences_per_rift(zone_1_tier, True)] # Archipelago
    zone_1_essences[0] += 6 * essences_per_extraction[0]
    zone_1_essences[1] += 6 * essences_per_extraction[1]
    zone_1_essences[2] += 6 * essences_per_extraction[2]
    # Do 5 t1 rifts for Amnytas
    zone_2_tier = 1
    zone_2_essences = [5 * essences for essences in essences_per_rift(zone_2_tier, True)] # Amnytas
    zone_2_essences[0] += 6 * essences_per_extraction[0]
    zone_2_essences[1] += 6 * essences_per_extraction[1]
    zone_2_essences[2] += 6 * essences_per_extraction[2]

    # Brute force all possible combinations of rifts for the remaining 3 zones
    # Make it the same number of rifts for each zone
    remaining_zones = 3
    for t3_rifts_per_zone in range(1, 6):
        for t2_rifts_per_zone in range(1, 6):
            for t1_rifts_per_zone in range(1, 6):
                if t3_rifts_per_zone + t2_rifts_per_zone + t1_rifts_per_zone != 5:
                    continue

                essences_gained = [0, 0, 0] # [despair, greed, triumph]
                essences_gained[0] = math.floor(zone_1_essences[0] + zone_2_essences[0])
                essences_gained[1] = math.floor(zone_1_essences[1] + zone_2_essences[1])
                essences_gained[2] = math.floor(zone_1_essences[2] + zone_2_essences[2])

                essences_gained[0] += remaining_zones * ((t3_rifts_per_zone * essences_per_t3_rift[0]) + (t2_rifts_per_zone * essences_per_t2_rift[0]) + (t1_rifts_per_zone * essences_per_t1_rift[0]) + (6 * essences_per_extraction[0]))
                essences_gained[1] += remaining_zones * ((t2_rifts_per_zone * essences_per_t2_rift[1]) + (6 * essences_per_extraction[1]))
                essences_gained[2] += remaining_zones * ((t3_rifts_per_zone * essences_per_t3_rift[2]) + (6 * essences_per_extraction[2]))

                num_weeks_remaining = [0, 0, 0] # [despair, greed, triumph]
                num_weeks_remaining[0] = math.ceil(remaining_essences_needed[0] / essences_gained[0])
                num_weeks_remaining[1] = math.ceil(remaining_essences_needed[1] / essences_gained[1])
                num_weeks_remaining[2] = math.ceil(remaining_essences_needed[2] / essences_gained[2])

                # print('debug essences gained: ', essences_gained[0], essences_gained[1], essences_gained[2])
                # print('debug t1 rifts per zone: %d' % t1_rifts_per_zone)
                # print('debug t2 rifts per zone: %d' % t2_rifts_per_zone)
                # print('debug t3 rifts per zone: %d' % t3_rifts_per_zone)
                # print('debug essences left over: ', num_weeks_remaining[0], num_weeks_remaining[1], num_weeks_remaining[2])
                
                # if we have a new best number of weeks, then save it
                num_weeks = max(num_weeks_remaining[0], num_weeks_remaining[1], num_weeks_remaining[2])
                if num_weeks < best_num_weeks:
                    best_num_weeks = num_weeks
                    best_t3_rifts_per_zone = t3_rifts_per_zone
                    best_t2_rifts_per_zone = t2_rifts_per_zone
                    best_t1_rifts_per_zone = t1_rifts_per_zone
                    best_weeks_remaining = num_weeks_remaining

    print('Best number of weeks: %d' % best_num_weeks)
    print('Do 5x t%d rifts per week for Archipelago' % zone_1_tier)
    print('Do 5x t%d rifts per week for Amnytas' % zone_2_tier)
    print('Do %dx t1 rifts per week per remaining zone: %d' % (best_t1_rifts_per_zone, best_t1_rifts_per_zone))
    print('Do %dx t2 rifts per week per remaining zone: %d' % (best_t2_rifts_per_zone, best_t2_rifts_per_zone))
    print('Do %dx t3 rifts per week per remaining zone: %d' % (best_t3_rifts_per_zone, best_t3_rifts_per_zone))
    
    print('Number of weeks remaining: ', best_weeks_remaining[0], best_weeks_remaining[1], best_weeks_remaining[2])
    current_date = datetime.date.today()
    
    # Calculate the future date by adding NumWeeks weeks to the current date
    future_date = current_date + datetime.timedelta(weeks=best_num_weeks)
    print('Completion date: ', future_date)

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
        input_strs = '  '.join('%-18.18s' % (name)
                for count, name, kind in inputs)
        produces_str = '' if output_count == 1 else ' (produces %d)' % output_count
        print('%6d   %s%s' % (times * output_count, input_strs, produces_str))


    total_essences_needed = [18000, 7200, 3900]
    essence_of_despair_count = count_input('item', 'Essence of Despair')
    essence_of_greed_count = count_input('item', 'Essence of Greed')
    essence_of_triumph_count = count_input('item', 'Essence of Triumph')
    print()
    print('Total amount of essences needed for full legendary armor:')
    print('%6d   %s' % (total_essences_needed[0], 'Essence of Despair'))
    print('%6d   %s' % (total_essences_needed[1], 'Essence of Greed'))
    print('%6d   %s' % (total_essences_needed[2], 'Essence of Triumph'))
    print()
    print('Current amount of Essence:')
    report([(1, 'Essence of Despair', 'item')])
    report([(1, 'Essence of Greed', 'item')])
    report([(1, 'Essence of Triumph', 'item')])
    print()
    print('Remaining essences needed for full legendary armor:')
    essences_needed = [total_essences_needed[0] - essence_of_despair_count, total_essences_needed[1] - essence_of_greed_count, total_essences_needed[2] - essence_of_triumph_count]
    print('%6d   %s' % (essences_needed[0], 'Essence of Despair'))
    print('%6d   %s' % (essences_needed[1], 'Essence of Greed'))
    print('%6d   %s' % (essences_needed[2], 'Essence of Triumph'))
    print()

    print('Rifts needed for full legendary armor using motivations:')
    print('\nBuying all motivations')
    # Taken from https://www.reddit.com/r/Guildwars2/comments/1653lii/cost_of_obsidian_legendary_armor_summarized/?rdt=62704

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

    print()
    print('Strategy only doing weeklies using motivations')
    # 5 zones
    # each zone do 3 t1, 1 t2, and 1 t3
    krypits_extractions_per_week = 30
    num_weekly_t1_rifts = 3 * 5
    num_weekly_t2_rifts = 1 * 5
    num_weekly_t3_rifts = 1 * 5

    # how many essences gained each week?
    essences_per_extraction = essences_per_kryptis_extraction()
    essences_per_t1_rift = [num_weekly_t1_rifts * essences for essences in essences_per_rift(1, True)]
    essences_per_t2_rift = [num_weekly_t2_rifts * essences for essences in essences_per_rift(2, True)]
    essences_per_t3_rift = [num_weekly_t3_rifts * essences for essences in essences_per_rift(3, True)]
    num_weekly_t1_essences = essences_per_t1_rift[0] + essences_per_t2_rift[0] + essences_per_t3_rift[0] + (krypits_extractions_per_week * essences_per_extraction[0])
    num_weekly_t2_essences = essences_per_t1_rift[1] + essences_per_t2_rift[1] + essences_per_t3_rift[1] + (krypits_extractions_per_week * essences_per_extraction[1])
    num_weekly_t3_essences = essences_per_t1_rift[2] + essences_per_t2_rift[2] + essences_per_t3_rift[2] + (krypits_extractions_per_week * essences_per_extraction[2])

    print('Tier 1 Essences per week: %d' % num_weekly_t1_essences)
    print('Tier 2 Essences per week: %d' % num_weekly_t2_essences)
    print('Tier 3 Essences per week: %d' % num_weekly_t3_essences)    

    # how many weeks to get all essences?
    num_weeks_t1 = math.ceil(essences_needed[0] / num_weekly_t1_essences)
    num_weeks_t2 = math.ceil(essences_needed[1] / num_weekly_t2_essences)
    num_weeks_t3 = math.ceil(essences_needed[2] / num_weekly_t3_essences)
    print('Tier 1 Remaining Weeks: %d' % num_weeks_t1)
    print('Tier 2 Remaining Weeks: %d' % num_weeks_t2)
    print('Tier 3 Remaining Weeks: %d' % num_weeks_t3)
    print()

    # optimal number of rifts per week
    optimal_rifts_per_week(essences_needed)


if __name__ == '__main__':
    main()
