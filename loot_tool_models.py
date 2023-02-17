import json

class LootBag:
    def __init__(self, name, price, quantity, id):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.id = id
 
    def __repr__(self):
        return json.dumps(self.__dict__)

class DataSnapshot:
    def __init__(self, timestamp, char_name, inventory, materials, bank, wallet, char_core, magic_find):
        self.timestamp = timestamp
        self.char_name = char_name
        self.inventory = inventory
        self.materials = materials
        self.bank = bank
        self.wallet = wallet
        self.char_core = char_core
        self.magic_find = magic_find

class DataDiff:
    def __init__(self, timestamp, char_name, wallet_diff, item_diff):
        self.timestamp = timestamp
        self.char_name = char_name
        self.wallet_diff = {int(k): v for k,v in wallet_diff.items()}
        self.item_diff = {int(k): v for k,v in item_diff.items()}

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
