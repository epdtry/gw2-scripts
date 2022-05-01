class LootBag:
    def __init__(self, name, price, quantity, id):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.id = id
 
    def __repr__(self):
        return json.dumps(self.__dict__)