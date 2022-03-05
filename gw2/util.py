import functools
import json
import os

class DataStorage:
    def __init__(self, index_path, data_path):
        # Read the existing index
        dct = {}
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                for line in f:
                    k, v = json.loads(line)
                    assert k not in dct
                    dct[k] = v
        self.index = dct

        self.index_file = open(index_path, 'a')
        self.data_file = open(data_path, 'a+')

    def contains(self, k):
        return k in self.index

    @functools.lru_cache(256)
    def get(self, k):
        pos = self.index.get(k)
        if pos is None:
            return None
        self.data_file.seek(pos)
        return json.loads(self.data_file.readline())

    def add(self, k, v):
        assert k not in self.index
        self.data_file.seek(0, 2)
        pos = self.data_file.tell()
        self.index[k] = pos
        self.data_file.write(json.dumps(v) + '\n')
        self.index_file.write(json.dumps((k, pos)) + '\n')

    def keys(self):
        return self.index.keys()
