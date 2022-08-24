from pprint import pprint

import gw2.api
import gw2.items
import bookkeeper

TOP_ACHIEVEMENT = 5790
SUB_ACHIEVEMENTS = [
        5773,
        5804,
        5829,
        5758,
        5742,
        5743,
        5779,
        5756,
        5751,
        'sirens_landing_hack',
        5948,
        5884,
        6005,
        5901,
        6023,
        5995,
        5888,
        5991,
        6024,
        5886,
        5869,
        5926,
        5861,
        ]

SIRENS_LANDING_ACHIEVEMENTS = [
        5739, 5746, 5794, 5795, 5811, 5815, 5821, 5824
        ]

ALL_ACHIEVEMENTS = [TOP_ACHIEVEMENT] + SUB_ACHIEVEMENTS + SIRENS_LANDING_ACHIEVEMENTS


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    achieves_raw = gw2.api.fetch('/v2/achievements?ids=' +
            ','.join(str(i) for i in ALL_ACHIEVEMENTS))
    achieves = {a['id']: a for a in achieves_raw}

    progress_raw = gw2.api.fetch('/v2/account/achievements?ids=' +
            ','.join(str(i) for i in ALL_ACHIEVEMENTS))
    progress = {p['id']: p for p in progress_raw}

    max_tiers = max(len(a['tiers']) for a in achieves.values())

    def render_progress(a, cur):
        tiers_done = 0
        next_goal = None
        for tier in a['tiers']:
            goal = tier['count']
            if cur >= goal:
                tiers_done += 1
            else:
                if next_goal is None:
                    next_goal = goal

        stars = ' ' * (max_tiers - len(a['tiers'])) + \
                '*' * tiers_done + \
                ' ' * (len(a['tiers']) - tiers_done)

        if next_goal is not None:
            next_goal_str = '%2d/%-2d' % (cur, next_goal)
        else:
            next_goal_str = ' ' * 5
        last_goal_str = '%2d/%-2d' % (cur, a['tiers'][-1]['count'])

        return '%s  %s  %s' % (stars, next_goal_str, last_goal_str)
            
    def print_achievement(achieve_id):
        a = achieves[achieve_id]
        p = progress.get(achieve_id)
        if p is None:
            cur = 0
        else:
            cur = p.get('current', 0)
        print('%s  %s' % (render_progress(a, cur), a['name']))

    def print_sirens_landing():
        # The top-level Siren's Landing achievement is missing from the API.
        cur = 0
        for achieve_id in SIRENS_LANDING_ACHIEVEMENTS:
            a = achieves[achieve_id]
            p = progress.get(achieve_id)
            if p is not None and p.get('current', 0) >= a['tiers'][-1]['count']:
                cur += 1

        a = {
                'name': "Return to Siren's Landing",
                'tiers': [
                    {'count': 3},
                    {'count': 5},
                    {'count': 7},
                    # Actually 9, but the ore miner achievement is also missing
                    {'count': 8},
                ],
            }

        print('%s  %s' % (render_progress(a, cur), a['name']))

    print('')
    print_achievement(TOP_ACHIEVEMENT)
    print('')
    for achieve_id in SUB_ACHIEVEMENTS:
        if achieve_id == 'sirens_landing_hack':
            print_sirens_landing()
            continue
        print_achievement(achieve_id)


if __name__ == '__main__':
    main()
