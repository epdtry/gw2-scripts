import json
import sys
import urllib.parse
from bs4 import BeautifulSoup

import gw2.items
from gw2_builds.util import fetch_cached, PROFESSIONS


def is_item_embed(tag):
    return tag.has_attr('data-armory-embed') and tag['data-armory-embed'] == 'items'


def fetch_build(url):
    item_ids = []

    text = fetch_cached(url)
    soup = BeautifulSoup(text, 'html.parser')
    for tag in soup.find_all(is_item_embed):
        if not tag.has_attr('data-armory-ids'):
            continue
        ids_str = tag['data-armory-ids'].split(',')
        for id_str in ids_str:
            try:
                item_id = int(id_str)
            except ValueError as e:
                print('bad item ID %r: %s' % (id_str, e), file=sys.stderr)
        if item_id != -1:
            item_ids.append(item_id)

    return item_ids

def fetch_build_list(url):
    build_urls = []

    text = fetch_cached(url)
    soup = BeautifulSoup(text, 'html.parser')
    for tag in soup.find_all(class_='build-row'):
        for link in tag.find_all('a'):
            if not link.has_attr('href'):
                continue
            href = link['href']
            if not href.startswith('/wiki/Build:'):
                print('bad link: %r' % (href,), file=sys.stderr)
                continue
            build_url = urllib.parse.urljoin(url, href)
            build_urls.append(build_url)

    return build_urls

def cmd_fetch(url):
    item_ids = fetch_metabattle(url)
    for item_id in item_ids:
        print('%d = %s' % (item_id, gw2.items.name(item_id)))

def cmd_list(url):
    for build_url in fetch_build_list(url):
        print(build_url)

def cmd_list_all():
    for profession in PROFESSIONS:
        list_url = 'https://metabattle.com/wiki/' + profession
        for build_url in fetch_build_list(list_url):
            print(build_url)

def cmd_fetch_all():
    all_build_items = {}
    for profession in PROFESSIONS:
        print(profession, file=sys.stderr)
        list_url = 'https://metabattle.com/wiki/' + profession
        all_build_items[profession] = []
        for build_url in fetch_build_list(list_url):
            item_ids = fetch_build(build_url)
            all_build_items[profession].append(item_ids)
    with open('builds_metabattle.json', 'w') as f:
        json.dump(all_build_items, f)


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'fetch':
        url, = args
        cmd_fetch(url)
    elif cmd == 'list':
        url, = args
        cmd_list(url)
    elif cmd == 'list_all':
        assert len(args) == 0
        cmd_list_all()
    elif cmd == 'fetch_all':
        assert len(args) == 0
        cmd_fetch_all()
    else:
        raise ValueError('unknown command %r' % (cmd,))

if __name__ == '__main__':
    main()
