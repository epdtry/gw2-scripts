# a script that fetches all of the craftable item historical data from bltc api
import os
import concurrent.futures
import time
import sys
from datetime import datetime, timedelta

import bltc.api
import gw2.api
import gw2.recipes
import gw2.mystic_forge
import gw2.items
import gw2.trading_post
from gw2.util import DataStorage
from gw2.constants import STORAGE_DIR

HISTORICAL_DATA_DIR = os.path.join(STORAGE_DIR, 'historical_data')
HISTORICAL_DATA_BACKUP_DIR = os.path.join(HISTORICAL_DATA_DIR, 'backup')
NEW_INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'index_new.json')
NEW_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'data_new.json')
RAW_INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'index.json')
RAW_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'data.json')
PROCESSED_INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'processed_index.json')
PROCESSED_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'processed_data.json')

# a function that gets the date the file was created
def get_file_date(file_path):
    return os.path.getmtime(file_path)

def ensure_backup_dir():
    os.makedirs(HISTORICAL_DATA_BACKUP_DIR, exist_ok=True)

def backup_file(file_path):
    # ensure the backup directory exists
    ensure_backup_dir()
    # if the file exists, rename it to a backup name that includes the date in the backup directory
    if os.path.exists(file_path):
        os.rename(file_path, os.path.join(HISTORICAL_DATA_BACKUP_DIR, os.path.basename(file_path) + '-' + str(get_file_date(file_path)) + '.json.bak'))

def cmd_backup_files():
    backup_file(RAW_INDEX_FILE)
    backup_file(RAW_DATA_FILE)
    backup_file(PROCESSED_INDEX_FILE)
    backup_file(PROCESSED_DATA_FILE)

# a function that updates the new index file to the raw index file
def update_raw_index_file():
    # if the new index file exists, rename it to the raw index file
    if os.path.exists(NEW_INDEX_FILE):
        os.rename(NEW_INDEX_FILE, RAW_INDEX_FILE)

# a function that updates the new data file to the raw data file
def update_raw_data_file():
    # if the new data file exists, rename it to the raw data file
    if os.path.exists(NEW_DATA_FILE):
        os.rename(NEW_DATA_FILE, RAW_DATA_FILE)

# function to clear the cache
def clear_raw_data_cache():
    if os.path.exists(NEW_INDEX_FILE):
        os.remove(NEW_INDEX_FILE)
    if os.path.exists(NEW_DATA_FILE):
        os.remove(NEW_DATA_FILE)

# function to get the data
_HDATA = None
def _get_data():
    global _HDATA
    os.makedirs(HISTORICAL_DATA_DIR, exist_ok=True)
    _HDATA = DataStorage(NEW_INDEX_FILE, NEW_DATA_FILE)  
    return _HDATA

def craftable_items():
    for r in gw2.recipes.iter_all():
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

    for r in gw2.mystic_forge.iter_all():
        item_id = r['output_item_id']
        if not gw2.items.is_known(item_id):
            continue
        yield item_id

def get_prices(item_ids):
    sell_prices = {}

    for x in gw2.trading_post.get_prices_multi(item_ids):
        if x is None:
            continue

        # The trading post doesn't allow selling items at prices so low that
        # you would receive less than vendor price after taxes.
        item = gw2.items.get(x['id'])

        price = x['sells'].get('unit_price', 0) or x['buys'].get('unit_price', 0)
        if price != 0:
            sell_prices[x['id']] = price

    return sell_prices

# function that given a list of item ids, returns a list of sellable item ids
def sellable_items(item_ids):
    # get the prices of the items
    sell_prices = get_prices(item_ids)
    # for each item, if the price is greater than 0, add it to the list
    sellable_item_ids = []
    for item_id in item_ids:
        if item_id in sell_prices:
            sellable_item_ids.append(item_id)
    return sellable_item_ids

# Function to fetch item data for a given item_id
def fetch_item_data(item_id):
    try:
        item_data = bltc.api.fetch_with_retries(item_id)
        return item_id, item_data
    except:
        # fail silently
        return item_id, None

def cmd_download_new_data():
    # clear the cache
    clear_raw_data_cache()

    # get the data
    data = _get_data()

    # start a timer
    start = time.perf_counter()

    # get the list of items
    craftable_items_list = set(craftable_items())
    output_item_ids = sellable_items(craftable_items_list)

    # Create a ThreadPoolExecutor with a maximum of 8 concurrent threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Submit the tasks to fetch item data in parallel
        futures = [executor.submit(fetch_item_data, item_id) for item_id in output_item_ids]

        # Process the results as they become available
        for future in concurrent.futures.as_completed(futures):
            item_id, item_data = future.result()
            # Add the item data to the cache
            data.add(item_id, item_data)
    
    # stop the timer
    finish = time.perf_counter()
    print(f'Finished in {round(finish-start, 2)} second(s)')

def cmd_print_help():
    help_string = '''
    Command - Defition
    help - prints this documentation
    download - downloads the new data
    backup - move the old raw and processed data to the backup folder
    update - renames the new data to the raw data
    '''
    print(help_string)
    return

# function to get the raw data
_RAWDATA = None
def _get_raw_data():
    global _RAWDATA
    os.makedirs(HISTORICAL_DATA_DIR, exist_ok=True)
    _RAWDATA = DataStorage(RAW_INDEX_FILE, RAW_DATA_FILE)  
    return _RAWDATA

def get_raw_item_data(item_id):
    raw_data = _get_raw_data()
    if raw_data.contains(item_id):
        return raw_data.get(item_id)
    return None

def test():
    item_id = 97487
    raw_item_data = get_raw_item_data(item_id)
    first_raw_data_date = raw_item_data[0][0]
    last_raw_data_date = raw_item_data[-1][0]
    converted_first_date = datetime.fromtimestamp(first_raw_data_date)
    converted_last_date = datetime.fromtimestamp(last_raw_data_date)
    print(f'Item {item_id} has {len(raw_item_data)} data points from {converted_first_date} to {converted_last_date}')

    latest_date = datetime.fromtimestamp(raw_item_data[-1][0])
    yesterday = latest_date - timedelta(days=1)
    two_days_ago = latest_date - timedelta(days=2)
    three_days_ago = latest_date - timedelta(days=3)
    sold_one_day_ago = 0
    sold_two_days_ago = 0
    sold_three_days_ago = 0

    for dp in raw_item_data:
        date = datetime.fromtimestamp(dp[0])
        if date > yesterday:
            sold_one_day_ago += dp[5]
        if date > two_days_ago and date <= yesterday:
            sold_two_days_ago += dp[5]
        if date > three_days_ago and date <= two_days_ago:
            sold_three_days_ago += dp[5]
    print(f'Item {item_id} sold {sold_one_day_ago} yesterday, {sold_two_days_ago} two days ago, and {sold_three_days_ago} three days ago')

def main():
    ''' A tool with several commands to help with data collection of loot. 
    '''
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'help':
        assert len(args) == 0
        cmd_print_help()
    elif cmd == 'download':
        assert len(args) == 0
        cmd_download_new_data()
    elif cmd == 'backup':
        assert len(args) == 0
        cmd_backup_files()
    elif cmd == 'update':
        assert len(args) == 0
        update_raw_index_file()
        update_raw_data_file()
    elif cmd == 'test':
        assert len(args) == 0
        test()
    else:
        raise ValueError('unknown command %r' % cmd)

if __name__ == '__main__':
    main()