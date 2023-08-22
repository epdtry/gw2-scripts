import functools
import itertools
import json
import os

class DataStorage:
    def __init__(self, index_path, data_path):
        # Read the existing index
        dct = {}
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                for i, line in enumerate(f):
                    k, v = json.loads(line)
                    assert k not in dct, 'duplicate key %r on line %d' % (k, i + 1)
                    dct[k] = v
        self.index = dct

        self.index_file = open(index_path, 'a')
        self.data_file = open(data_path, 'a+')

        self.augment_dct = None

    def contains(self, k):
        if self.augment_dct is not None and k in self.augment_dct:
            return True
        return k in self.index

    @functools.lru_cache(256)
    def get(self, k):
        if self.augment_dct is not None:
            v = self.augment_dct.get(k)
            if v is not None:
                return v
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
        if self.augment_dct is not None:
            return itertools.chain(self.index.keys(), self.augment_dct.keys)
        return self.index.keys()

    def iter(self):
        for pos in self.index.values():
            if pos is None:
                continue
            self.data_file.seek(pos)
            yield json.loads(self.data_file.readline())

        if self.augment_dct is not None:
            yield from self.augment_dct.values()

    def augment(self, dct):
        if self.augment_dct is None:
            self.augment_dct = dct
        else:
            self.augment_dct.update(dct)

