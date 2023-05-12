# a script that fetches all of the craftable item historical data from bltc api
import os
import concurrent.futures
import time

import bltc.api
import gw2.api
import gw2.recipes
import gw2.mystic_forge
import gw2.items
from gw2.util import DataStorage
from gw2.constants import STORAGE_DIR

HISTORICAL_DATA_DIR = os.path.join(STORAGE_DIR, 'historical_data')
INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'index_new.json')
DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'data_new.json')

# function to clear the cache
def clear_raw_data_cache():
    if os.path.exists(INDEX_FILE):
        os.remove(INDEX_FILE)
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

# function to get the data
_HDATA = None
def _get_data():
    global _HDATA
    os.makedirs(HISTORICAL_DATA_DIR, exist_ok=True)
    _HDATA = DataStorage(INDEX_FILE, DATA_FILE)  
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

# Function to fetch item data for a given item_id
def fetch_item_data(item_id):
    try:
        item_data = bltc.api.fetch_with_retries(item_id)
        return item_id, item_data
    except:
        # fail silently
        return item_id, None

def main():
    # clear the cache
    clear_raw_data_cache()

    # get the data
    data = _get_data()

    # start a timer
    start = time.perf_counter()

    # get the list of items
    output_item_ids = set(craftable_items())

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

if __name__ == '__main__':
    main()