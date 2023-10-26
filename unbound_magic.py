import gw2.api
import gw2.items
import bookkeeper

Materials_From_Magic_Warped_Bundle_Used_In_Legendary = {
    'Vial of Powerful Blood': True,
    'Ancient Bone': True,
    'Elaborate Totem': True,
    'Pile of Crystalline Dust': True,
    'Armored Scale': True,
    'Powerful Venom Sac': True,
    'Vicious Fang': True,
    'Vicious Claw': True,
    'Karka Shell': False,
    'Pristine Toxic Spore Sample': False,
    'Glob of Ectoplasm': True,
    'Pile of Putrid Essence': True,
    'Charged Lodestone': False,
    'Molten Lodestone': False,
    'Crystal Lodestone': True,
    'Destroyer Lodestone': True,
    'Glacial Lodestone': False,
    'Onyx Lodestone': False,
    'Evergreen Lodestone': False,
    'Mordrem Lodestone': False,
    'Amalgamated Gemstone': True,
    'Ebony Orb': False,
    'Moonstone Orb': False,
    'Maguuma Lily': False,
    'Maguuma Burl': False,
    'Mystic Clover': True,
    'Freshwater Pearl': False,
    'Giant Eye': False,
    'Black Diamond': False,
    'Flax Blossom': False
}

Normalized_Magic_Warped_Bundle_500_Item_Drop_Rate = {
    'Vial of Powerful Blood': 0.9496,
    'Ancient Bone': 0.9438,
    'Elaborate Totem': 0.9606,
    'Pile of Crystalline Dust': 0.9408,
    'Armored Scale': 0.891,
    'Powerful Venom Sac': 0.889,
    'Vicious Fang': 0.905,
    'Vicious Claw': 0.9596,
    'Karka Shell': 0.9646,
    'Pristine Toxic Spore Sample': 0.9168,
    'Glob of Ectoplasm': 0.4162,
    'Pile of Putrid Essence': 0.1798,
    'Charged Lodestone': 0.1132,
    'Molten Lodestone': 0.1198,
    'Crystal Lodestone': 0.127,
    'Destroyer Lodestone': 0.1144,
    'Glacial Lodestone': 0.2416,
    'Onyx Lodestone': 0.1148,
    'Evergreen Lodestone': 0.1234,
    'Mordrem Lodestone': 0.1312,
    'Amalgamated Gemstone': 0.0828,
    'Ebony Orb': 0.0296,
    'Moonstone Orb': 0.0306,
    'Maguuma Lily': 0.0306,
    'Maguuma Burl': 0.0296,
    'Mystic Clover': 0.0768,
    'Freshwater Pearl': 0.0294,
    'Giant Eye': 0.0284,
    'Black Diamond': 0.0284,
    'Flax Blossom': 0.0288
}

Normalized_Magic_Warped_Bundle_1250_Item_Drop_Rate = {
    'Vial of Powerful Blood': 0.37984,
    'Ancient Bone': 0.37752,
    'Elaborate Totem': 0.38424,
    'Pile of Crystalline Dust': 0.37632,
    'Armored Scale': 0.3564,
    'Powerful Venom Sac': 0.3556,
    'Vicious Fang': 0.362,
    'Vicious Claw': 0.38384,
    'Karka Shell': 0.38584,
    'Pristine Toxic Spore Sample': 0.36672,
    'Glob of Ectoplasm': 0.16648,
    'Pile of Putrid Essence': 0.07192,
    'Charged Lodestone': 0.04528,
    'Molten Lodestone': 0.04792,
    'Crystal Lodestone': 0.0508,
    'Destroyer Lodestone': 0.04576,
    'Glacial Lodestone': 0.09664,
    'Onyx Lodestone': 0.04592,
    'Evergreen Lodestone': 0.04936,
    'Mordrem Lodestone': 0.05248,
    'Amalgamated Gemstone': 0.03312,
    'Ebony Orb': 0.01184,
    'Moonstone Orb': 0.01224,
    'Maguuma Lily': 0.01224,
    'Maguuma Burl': 0.01184,
    'Mystic Clover': 0.03072,
    'Freshwater Pearl': 0.01176,
    'Giant Eye': 0.01136,
    'Black Diamond': 0.01136,
    'Flax Blossom': 0.01152
}

def calculate_mystic_clover_cost():
    SPIRIT_SHARD_COST = 25000
    MYSTIC_CLOVER_CRAFT_REQUIREMENTS = {
        'Mystic Coin': 3.2,
        'Glob of Ectoplasm': 3.2,
        'Obsidian Shard': 3.2,
        'Spirit Shard': 1.94
    }
    items_needed = ['Mystic Coin', 'Glob of Ectoplasm']
    item_ids = [gw2.items.search_name(key) for key in items_needed]
    buy_prices, sell_prices = bookkeeper.get_prices(item_ids)
    total_cost = 0
    for item in ['Mystic Coin', 'Glob of Ectoplasm', 'Spirit Shard']:
        price = buy_prices[gw2.items.search_name(item)] if item != 'Spirit Shard' else SPIRIT_SHARD_COST
        cost = price * MYSTIC_CLOVER_CRAFT_REQUIREMENTS[item]
        total_cost += cost
    print("Cost of Mystic Clover:", total_cost)
    return total_cost

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'
    print()
    # Conservative value used via obtaining fractal boxes and stabalizing matrices
    # Can make this more real time later
    MYSTIC_CLOVER_VALUE = calculate_mystic_clover_cost()
    MYSTIC_CLOVER_ITEM_ID = 19675

    # get a list of the keys from dictionary
    key_list = list(Materials_From_Magic_Warped_Bundle_Used_In_Legendary.keys())
    item_ids = [gw2.items.search_name(key) for key in key_list]
    buy_prices, sell_prices = bookkeeper.get_prices(item_ids)
    buy_prices[MYSTIC_CLOVER_ITEM_ID] = MYSTIC_CLOVER_VALUE
    

    total_value_for_500_bundle = 0
    normalized_cost_for_500_bundle = 20000
    for item, drop_rate in Normalized_Magic_Warped_Bundle_500_Item_Drop_Rate.items():
        # Find the total value of the bundle
        # Value is determined by using buy price if it's used in legendarys and sell price * 0.85 otherwise
        is_used_in_legendary = Materials_From_Magic_Warped_Bundle_Used_In_Legendary[item]
        total_value_for_500_bundle += buy_prices[gw2.items.search_name(item)] * drop_rate
        
        # if is_used_in_legendary:
        #     total_value_for_500_bundle += buy_prices[gw2.items.search_name(item)] * drop_rate
        # else:
        #     total_value_for_500_bundle += sell_prices[gw2.items.search_name(item)] * drop_rate * 0.85


    total_value_for_500_bundle -= normalized_cost_for_500_bundle
    print("Total value for 500 bundle:", total_value_for_500_bundle)

    total_value_for_1250_bundle = 0
    normalized_cost_for_1250_bundle = 3200
    for item, drop_rate in Normalized_Magic_Warped_Bundle_1250_Item_Drop_Rate.items():
        # Find the total value of the bundle
        # Value is determined by using buy price if it's used in legendarys and sell price * 0.85 otherwise
        is_used_in_legendary = Materials_From_Magic_Warped_Bundle_Used_In_Legendary[item]
        total_value_for_1250_bundle += buy_prices[gw2.items.search_name(item)] * drop_rate
        # if is_used_in_legendary:
        #     total_value_for_1250_bundle += buy_prices[gw2.items.search_name(item)] * drop_rate
        # else:
        #    total_value_for_1250_bundle += sell_prices[gw2.items.search_name(item)] * drop_rate * 0.85

    total_value_for_1250_bundle -= normalized_cost_for_1250_bundle
    print("Total value for 1250 bundle:", total_value_for_1250_bundle)

if __name__ == '__main__':
    main()
