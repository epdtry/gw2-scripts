import urllib.request
import ssl
from bs4 import BeautifulSoup
import hashlib
import os
import re
import sys
import urllib.parse
import requests

import gw2.api
import gw2.items
import gw2.itemstats

CACHE_DIR = 'cache/scbuilds'

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


def main():
    profession_name_strings = [
        'Elementalist',
        'Engineer',
        # 'Guardian',
        'Mesmer',
        'Necromancer',
        # 'Ranger',
        'Revenant',
        # 'Thief',
        # 'Warrior',
        ]
    weapons_count = {}
    armor_stats_count = {}

    ssl._create_default_https_context = ssl._create_unverified_context
    all_urls = fetch_all_sc_build_urls()
    print('There are ', len(all_urls), ' urls from snowcrows...')
    for url_to_get in all_urls:
        html_string = fetch_cached(url_to_get)
        soup = BeautifulSoup(html_string, 'html.parser')
        title_text = soup.find('title').text
        prof_found = False
        for prof in profession_name_strings:
            if prof in title_text:
                prof_found = True
                break
        if not prof_found:
            continue

        allspans = soup.findAll('div', {'data-armory-ids' : True})
        found_first_helm = False
        for span in allspans:
            if (len(span.attrs['data-armory-ids'].split(',')) > 1):
                continue
            if (span.attrs.get('data-armory-embed', None) is not None):
                if span.attrs['data-armory-embed'] == 'specializations':
                    continue
            armory_id = int(span.attrs['data-armory-ids'])
            armory_item = gw2.items.get(armory_id)

            if armory_item == None:
                continue


            if armory_item['type'] == 'Weapon':
                weapon_type = armory_item['details']['type']
                if weapon_type == 'SmallBundle':
                    continue
                # if weapon_type == 'Shield':
                #     print(weapon_type, ' build: ', url_to_get)
                weapons_count[weapon_type] = weapons_count.get(weapon_type, 0) + 1
            if armory_item['type'] == 'Armor' or armory_item['type'] == 'Trinket':
                armory_type = armory_item['details']['type']

                # Uncomment below if you only want first build of a page
                # if armory_type == 'Helm': 
                #     if not found_first_helm:
                #         found_first_helm = True
                #     else:
                #         break
                
                # if armory_type != 'Ring':
                #     continue
                stat_number_attrib_name = 'data-armory-' + str(armory_id) + '-stat'
                stat_number = span.attrs.get(stat_number_attrib_name, '-1')
                itemstats = gw2.itemstats.get(int(stat_number))
                stats_name = itemstats['name']
                armor_stats_count[stats_name] = armor_stats_count.get(stats_name, 0) + 1

    sorted_weapons = dict(sorted(weapons_count.items(), key=lambda item: item[1], reverse=True))
    sorted_armor = dict(sorted(armor_stats_count.items(), key=lambda item: item[1], reverse=True))
    print(sorted_weapons)
    print(sorted_armor)
    return

def fetch_all_sc_build_urls():
    print('fetching all sc builds')
    all_builds_query_url = 'https://snowcrows.com/builds?profession=any&category=recommended'
    r = requests.get(all_builds_query_url)
    r.raise_for_status()
    html_string = r.text
    soup = BeautifulSoup(html_string, 'html.parser')

    all_build_urls = []
    for a in soup.findAll('a', href=True):
        href_link = a['href']
        if(href_link.startswith('/builds/')):
            all_build_urls.append('https://snowcrows.com' + href_link)

    print('done fetching all sc builds')
    return all_build_urls

if __name__ == '__main__':
    main()