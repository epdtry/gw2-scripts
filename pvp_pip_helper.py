import sys
from datetime import datetime, timedelta

reward_chests =[
    # (chest_name, number_of_tiers, pips_per_tier, asog_rewarded)
    ('Cerulean', 3, 20, 25),
    ('Jasper', 4, 20, 50),
    ('Saffron', 5, 20, 75),
    ('Persimmon', 5, 20, 75),
    ('Amaranth', 5, 30, 75),
    ('Byzantium', 6, 30, 100), # repeats Byzantium
]

current_chest_level = 'Cerulean'
current_tier = 1 # 1 indexed
current_pips = 0

asog_wanted = 500 # for complete legendary piece

def get_chest_info(chest_name):
    for chest in reward_chests:
        if chest[0] == chest_name:
            return chest
    return None

current_chest_info = get_chest_info(current_chest_level)

if not current_chest_info:
    # print error and exit
    print('Chest not found')
    sys.exit()

print()
print('Current chest:', current_chest_info[0])
print('Target  ASOG:', asog_wanted)
print()

def get_remaining_pips_needed(current_chest_level, current_tier):
    chest_info = get_chest_info(current_chest_level)
    
    remaining_tiers = chest_info[1] - current_tier + 1
    remaining_pips = remaining_tiers * chest_info[2]
    return remaining_pips

def get_next_tier_info(tier_level):
    for i, tier in enumerate(reward_chests):
        if tier[0] == tier_level:
            if i+1 < len(reward_chests):
                return reward_chests[i+1]
            else:
                # return the last tier
                return reward_chests[i]


cumulative_pips_needed = get_remaining_pips_needed(current_chest_level, current_tier) - current_pips
cumulative_asog_rewarded = current_chest_info[3]
number_of_byzantiums = 0

while cumulative_asog_rewarded < asog_wanted:
    if current_chest_info[0] == 'Byzantium':
        number_of_byzantiums += 1
        print('Byzantiums:', number_of_byzantiums)
    next_tier_info = get_next_tier_info(current_chest_info[0])
    cumulative_pips_needed += next_tier_info[1] * next_tier_info[2]
    cumulative_asog_rewarded += next_tier_info[3]
    # print('Next tier:', next_tier_info[0])
    # print('Pips needed to complete next tier:', cumulative_pips_needed)
    # print('Cumulative ASOG rewarded:', cumulative_asog_rewarded)
    # print()
    current_chest_info = next_tier_info

print()
print('Pips needed to reach', asog_wanted, 'ASOG:', cumulative_pips_needed)
print('Number of Byzantiums repeats:', number_of_byzantiums)

# (Number of PvP games required) = (Number of PvP pips required) / [(7 x B) + C + (2 x D) + 3]
# B = Your win rate. A 60% win rate is 0.60 in this formula.
# C = Your top stats rate. If you get a top stats reward in 75% of games, this number is 0.75.
# D = Your near victory rate. If 3% of your games are a near victory that awards bonus pips, then this number is 0.03.

win_rate = 0.5
top_stats_rate = 0.85
near_victory_rate = 0.03
pips_required = cumulative_pips_needed
games_required = pips_required / ((7 * win_rate) + top_stats_rate + (2 * near_victory_rate) + 3)
print()
print('Games required:', round(games_required, 2))

# (Time required) = (Number of PvP games required) x (Average time per game)
# (Average time per game) = (Average game length) + (Average queue time)
average_queue_time = 4 # minutes
average_game_length = 13 # minutes
average_time_per_game = average_game_length + average_queue_time
minutes_required = games_required * average_time_per_game
time_required = minutes_required / 60
print()
print('Time spent in queue:', round(average_queue_time * games_required, 2), 'minutes')
print('Time required:', round(time_required, 2), 'hours')

season_end_date = datetime(2025, 9, 2)
now = datetime.now()
time_remaining = season_end_date - now
weeks_remaining = time_remaining.days / 7
# print('Days remaining in season:', time_remaining.days)
# print('Weeks remaining in season:', weeks_remaining)

games_per_day_required = games_required / (time_remaining.days - (weeks_remaining * 2))
print('Games per day required:', round(games_per_day_required, 2))
print()