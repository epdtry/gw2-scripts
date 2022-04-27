class DataDiff:
    def __init__(self, timestamp, char_name, wallet_diff, item_diff):
        self.timestamp = timestamp
        self.char_name = char_name
        self.wallet_diff = wallet_diff
        self.item_diff = item_diff

class LootTable:
    def __init__(self, timestamp, source_item_id, source_item_quantity, item_drop_info_list, wallet_drop_info_list):
        self.timestamp = timestamp
        self.source_item_id = source_item_id
        self.source_item_quantity = source_item_quantity
        self.item_drop_info_list = item_drop_info_list
        self.wallet_drop_info_list = wallet_drop_info_list

class DropInfo:
    def __init__(self, id, quantity, drop_rate):
        self.id = id
        self.quantity = quantity
        self.drop_rate = drop_rate

