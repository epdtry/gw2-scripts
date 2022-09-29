from collections import defaultdict
import gw2.api
import gw2.items
import gw2.trading_post
from bookkeeper import format_price, parse_timestamp

def format_duration(dur):
    days = dur // 86400
    hours = dur // 3600 % 24
    minutes = dur // 60 % 60
    if days > 0:
        return '%dd%02dh' % (days, hours)
    elif hours > 0:
        return '%dh%02dm' % (hours, minutes)
    else:
        return '%dm' % minutes

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    sells = gw2.trading_post._get_history('sells')[0]
    sells_by_age = []
    for t in sells.iter():
        listing_time = parse_timestamp(t['created'])
        sale_time = parse_timestamp(t['purchased'])
        duration = sale_time - listing_time
        sells_by_age.append((duration, t))

    sells_by_age.sort(key=lambda x: x[0])

    for dur, t in sells_by_age:
        print('%10s  %3d %-40.40s  %s  %s' % (
            format_duration(dur), t['quantity'], gw2.items.name(t['item_id']),
                t['created'], t['purchased']))

if __name__ == '__main__':
    main()
