import json
import os
import sys
import time
import urllib.parse

import gw2.api
import DataSnapshot

def snapshot_from_file(file_path):
    with open(file_path) as f:
        text = f.read()
        data_snapshot_dict = json.loads(text)
    return DataSnapshot.DataSnapshot(**data_snapshot_dict)


def main():
    original_file = sys.argv[1]
    new_file = sys.argv[2]

    original_snapshot = snapshot_from_file(original_file)
    new_snapshot = snapshot_from_file(new_file)
    print(original_snapshot.char_name)
    print(new_snapshot.char_name)

if __name__ == '__main__':
    main()