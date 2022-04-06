import hashlib
import os
import re
import sys
import urllib.parse

import requests


CACHE_DIR = 'cache/builds'

NON_SAFE_RE = re.compile('[^a-zA-Z0-9-_.]+')

def clean(s):
    return NON_SAFE_RE.sub('_', s)

def fetch_cached(url):
    parts = urllib.parse.urlparse(url)
    host = clean(parts.hostname)[:50]
    name = clean(parts.path.rpartition('/')[2])[:50]
    hash_ = hashlib.sha256(url.encode('utf-8')).hexdigest()
    cache_key = '%s__%s__%s' % (host, name, hash_)

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_key)
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return f.read()

    print('fetch ' + url, file=sys.stderr)
    r = requests.get(url)
    r.raise_for_status()
    text = r.text
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


PROFESSIONS = (
        'Elementalist',
        'Engineer',
        'Guardian',
        'Mesmer',
        'Necromancer',
        'Ranger',
        'Revenant',
        'Thief',
        'Warrior',
        )
