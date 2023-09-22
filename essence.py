import gw2.api
import gw2.items
import bookkeeper
import random

def essences_per_rift(tier, using_motivation):
    # Assumes that player has Rift Mastery
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
    print('Tier 1 without motivations:', essences_per_rift(1, False))
    print('Tier 2 without motivations:', essences_per_rift(2, False))
    print('Tier 3 without motivations:', essences_per_rift(3, False))
    print()
    print('Tier 1 with motivations:', essences_per_rift(1, True))
    print('Tier 2 with motivations:', essences_per_rift(2, True))
    print('Tier 3 with motivations:', essences_per_rift(3, True))

if __name__ == '__main__':
    main()
