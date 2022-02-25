import os
import requests
import time

from gw2.constants import STORAGE_DIR

STORAGE_PATH = os.path.join(STORAGE_DIR, 'build.txt')

_CURRENT = None
def current():
    '''Get the current build ID of the game.  The result of this call is cached
    for 24 hours.  Clear the cache by removing storage/build.txt.'''
    global _CURRENT

    # The result is cached in memory, so we don't have to worry about the build
    # changing partway through the execution of the script.
    if _CURRENT is None:
        try:
            mtime = os.stat(STORAGE_PATH).st_mtime
            refresh = mtime < time.time() - 86400
        except OSError:
            refresh = True

        if refresh:
            # As of 2022-02-24, the /v2/build API endpoint is stuck at 115267.  A
            # thread on the forums suggests reading this file from the CDN instead.
            # https://en-forum.guildwars2.com/topic/96243-gw2-client-build-number-stuck-at-115267/
            # This URL returns several numbers, the first of which is the build ID.
            r = requests.get('http://assetcdn.101.arenanetworks.com/latest64/101')
            r.raise_for_status()
            text = r.text

            os.makedirs(STORAGE_DIR, exist_ok=True)
            with open(STORAGE_PATH, 'w') as f:
                f.write(text)
        else:
            with open(STORAGE_PATH) as f:
                text = f.read()

        _CURRENT = int(text.split()[0])

    return _CURRENT

def need_refresh(build_file):
    try:
        with open(build_file) as f:
            cached_build = int(f.read().strip())
        return cached_build != current()
    except:
        return True
