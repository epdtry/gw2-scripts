import os
from datetime import datetime, timedelta

from gw2.util import DataStorage
from gw2.constants import STORAGE_DIR

HISTORICAL_DATA_DIR = os.path.join(STORAGE_DIR, 'historical_data')
RAW_INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'index.json')
RAW_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'data.json')
PROCESSED_INDEX_FILE = os.path.join(HISTORICAL_DATA_DIR, 'processed_index.json')
PROCESSED_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, 'processed_data.json')

_RAWDATA = None
def _get_raw_data():
    global _RAWDATA

    if _RAWDATA is None:
        if not os.path.exists(RAW_INDEX_FILE):
            print('No raw index file for bltc data')
            raise Exception('No raw index file for bltc data')
        if not os.path.exists(RAW_DATA_FILE):
            print('No raw data file for bltc data')
            raise Exception('No raw data file for bltc data')
        _RAWDATA = DataStorage(RAW_INDEX_FILE, RAW_DATA_FILE)
    return _RAWDATA

_PROCDATA = None
def _get_processed_data():
    global _PROCDATA

    if _PROCDATA is None:
        os.makedirs(HISTORICAL_DATA_DIR, exist_ok=True)
        _PROCDATA = DataStorage(PROCESSED_INDEX_FILE, PROCESSED_DATA_FILE)
    return _PROCDATA

'''
Timestamp: The time of the data point.
Sell: The lowest sell offer price.
Buy: The highest buy order price.
Supply: The amount of items being sold.
Demand: The amount of items being bought.
Sold: Sell offers were filled or cancelled.
Offers: New sell offers.
Bought: Buy orders were filled or cancelled.
Bids: New buy orders.
* Sold, Offers, Bought and Bids are estimations.
'''

class ProcessedData:
    def __init__(self, sold_daily, sold_weekly, bought_daily, bought_weekly):
        self.sold_daily = sold_daily
        self.sold_weekly = sold_weekly
        self.bought_daily = bought_daily
        self.bought_weekly = bought_weekly

def get_raw_item_data(item_id):
    raw_data = _get_raw_data()
    if raw_data.contains(item_id):
        return raw_data.get(item_id)
    return None

def get_processed_data(item_id):
    result = None
    processed_data = _get_processed_data()
    if processed_data.contains(item_id):
        result = processed_data.get(item_id)
        return result
    
    raw_item_data_points = get_raw_item_data(item_id)
    if raw_item_data_points is None:
        return None
    
    latest_date = datetime.fromtimestamp(raw_item_data_points[-1][0])
    
    yesterday = latest_date - timedelta(days=1)
    week_ago = latest_date - timedelta(days=7)
    sold_daily = 0
    sold_weekly = 0
    bought_daily = 0
    bought_weekly = 0

    for dp in raw_item_data_points:
        date = datetime.fromtimestamp(dp[0])
        if date > yesterday:
            sold_daily += dp[5]
            bought_daily += dp[7]
        if date > week_ago:
            sold_weekly += dp[5]
            bought_weekly += dp[7]

    result = {
        'sold_daily': sold_daily,
        'sold_weekly': sold_weekly,
        'bought_daily': bought_daily,
        'bought_weekly': bought_weekly,
    }
    processed_data.add(item_id, result)

    return result

def get_items_processed_historical_data(item_ids):
    out = {}
    for item_id in item_ids:
        out[item_id] = get_processed_data(item_id)
    return out