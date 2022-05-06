from datetime import datetime, timedelta
from typing import List

import gw2.api
import gw2.items
import bltc.api

'''
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
class ChartDataPoint:
    def __init__(self, timestamp, Sell, Buy, Supply, Demand, Sold, Offers, Bought, Bids):
        self.timestamp = timestamp
        self.Sell = Sell
        self.Buy = Buy
        self.Supply = Supply
        self.Demand = Demand
        self.Sold = Sold
        self.Offers = Offers
        self.Bought = Bought
        self.Bids = Bids

def get_data_points_from_raw(item_id: int) -> List[ChartDataPoint]:
    historical_data = bltc.api.fetch(item_id)
    data_point_list = []
    for data_list in historical_data:
        chart_data_point = ChartDataPoint(data_list[0], data_list[1], data_list[2], data_list[3], data_list[4], data_list[5], data_list[6], data_list[7], data_list[8])
        data_point_list.append(chart_data_point)
    return data_point_list

def is_within_range(timestamp, day_range):
    date = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    span = now - date
    if span.days < day_range:
        return True
    return False

def supply_greater_than_demand(data_points:List[ChartDataPoint], threshold: float = 0.95) -> bool:
    supply_greater_than_demand_count = 0
    for dp in data_points:
        if dp.Supply > dp.Demand:
            supply_greater_than_demand_count += 1
    
    supply_greater_than_demand_count_pct = supply_greater_than_demand_count / len(data_points)
    print('Pct Time Supply is Greater Than Demand:', supply_greater_than_demand_count_pct)

    return supply_greater_than_demand_count_pct > threshold

def calculate_daily_velocity(data_points:List[ChartDataPoint]) -> float:
    daily_avgs_list = []
    daily_buys_and_sells = []
    current_day = datetime.fromtimestamp(data_points[0].timestamp).day
    for dp in data_points:
        dp_date = datetime.fromtimestamp(dp.timestamp)
        if dp_date.day != current_day:
            daily_sum = sum(daily_buys_and_sells)
            daily_avgs_list.append(daily_sum)
            current_day = dp_date.day
            daily_buys_and_sells = []
        buys_and_sells = dp.Bought + dp.Sold
        daily_buys_and_sells.append(buys_and_sells)
    velocity = sum(daily_avgs_list) / len(daily_avgs_list)
    return velocity

def calculate_daily_buys(data_points:List[ChartDataPoint]) -> float:
    daily_avgs_list = []
    daily_buys = []
    current_day = datetime.fromtimestamp(data_points[0].timestamp).day
    for dp in data_points:
        dp_date = datetime.fromtimestamp(dp.timestamp)
        if dp_date.day != current_day:
            daily_sum = sum(daily_buys)
            daily_avgs_list.append(daily_sum)
            current_day = dp_date.day
            daily_buys = []
        buys = dp.Bought
        daily_buys.append(buys)
    buys = sum(daily_avgs_list) / len(daily_avgs_list)
    return buys

def calculate_daily_sells(data_points:List[ChartDataPoint]) -> float:
    print('Sells')
    daily_avgs_list = []
    daily_sells = []
    current_day = datetime.fromtimestamp(data_points[0].timestamp).day
    for dp in data_points:
        dp_date = datetime.fromtimestamp(dp.timestamp)
        if dp_date.day != current_day:
            print(dp_date, '-', sum(daily_sells))
            daily_sum = sum(daily_sells)
            daily_avgs_list.append(daily_sum)
            current_day = dp_date.day
            daily_sells = []
        sells = dp.Sold
        daily_sells.append(sells)
    sells = sum(daily_avgs_list) / len(daily_avgs_list)
    return sells

# Assumes data_points are in chronological order
def calculate_outbid_time(data_points:List[ChartDataPoint]) -> float:
    # Get all points where buy price changes
    inflection_points:List[ChartDataPoint] = []
    current_buy_price = -1
    for dp in data_points:
        if dp.Buy != current_buy_price:
            inflection_points.append(dp)
            current_buy_price = dp.Buy
    
    current_point = inflection_points[0]
    delta_list = []
    for dp in inflection_points:
        if dp.timestamp == current_point.timestamp:
            continue
        #if price goes up between current_point and pointN+1
        if current_point.Buy == dp.Buy:
            print('this shouldnt happen')
        
        if current_point.Buy - dp.Buy > 0: # price went down, aka outbid
            #calculate delta time between those, add to list
            current_date = datetime.fromtimestamp(current_point.timestamp)
            next_change_date = datetime.fromtimestamp(dp.timestamp)
            delta = next_change_date - current_date
            delta_list.append(delta)

        if current_point.Buy - dp.Buy < 0: # price went up, aka sold/cancel
            pass

        current_point = dp

    average_outbid_time = sum(delta_list, timedelta(0)) / len(delta_list)
    return average_outbid_time

def calculate_bought_time(data_points:List[ChartDataPoint]) -> float:
    # Get all points where buy price changes
    inflection_points:List[ChartDataPoint] = []
    current_buy_price = -1
    for dp in data_points:
        if dp.Bought > 0:
            inflection_points.append(dp)
    
    current_point = inflection_points[0]
    delta_list = []
    for dp in inflection_points:
        if dp.timestamp == current_point.timestamp:
            continue
        
        #calculate delta time between those, add to list
        current_date = datetime.fromtimestamp(current_point.timestamp)
        next_change_date = datetime.fromtimestamp(dp.timestamp)
        delta = next_change_date - current_date
        delta_list.append(delta)
        current_point = dp

    avg_time_between_boughts = sum(delta_list, timedelta(0)) / len(delta_list)
    return avg_time_between_boughts

def main():
    '''
    97487 - Piece of Dragon Jade
    24824 - Superior Rune of the Guardian
    83338 - Superior Rune of the Firebrand
    '''
    day_range = 8
    id_list = [97487, 24824, 19701, 19685, 89103, 96221]
    for item_id in id_list:
        item_name = gw2.items.name(item_id)
        print()
        print(item_name)
        data_point_list = get_data_points_from_raw(item_id)
        first_data_point_time = data_point_list[0].timestamp
        first_date = datetime.fromtimestamp(first_data_point_time)
        last_data_point_time = data_point_list[-1].timestamp
        last_date = datetime.fromtimestamp(last_data_point_time)

        days_of_data = last_date - first_date
        
        relevant_data_points:List[ChartDataPoint] = []
        for data_point in data_point_list:
            if is_within_range(data_point.timestamp, day_range):
                relevant_data_points.append(data_point)
        
        supply_greater_than_demand(relevant_data_points)
        velocity = calculate_daily_velocity(relevant_data_points)
        
        buys = calculate_daily_buys(relevant_data_points)
        outbid_time = calculate_outbid_time(relevant_data_points)
        bought_time = calculate_bought_time(relevant_data_points)

        print('Days of data:', days_of_data.days)
        print('Buys per day:', buys)
        print('Buys per hour:', buys/24)
        print('Average time between buys fulfilled: ', bought_time)
        print('Average time between outbids: ', outbid_time)


if __name__ == '__main__':
    main()
