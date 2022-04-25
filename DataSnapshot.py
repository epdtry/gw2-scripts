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