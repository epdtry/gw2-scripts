from collections import defaultdict
import functools
import json
import os
import urllib.parse

from gw2.api import fetch, fetch_with_retries
from gw2.constants import STORAGE_DIR
import gw2.build

CHARACTERS_DIR = os.path.join(STORAGE_DIR, 'characters')
CHARACTERS_FILE = os.path.join(CHARACTERS_DIR, 'characters.txt')
BUILD_FILE = os.path.join(CHARACTERS_DIR, 'build.txt')
CRAFTING_DISCIPLINES_FILE = os.path.join(CHARACTERS_DIR, 'characters_crafting.json')

_CHARACTERS = None
def _get_characters():
    global _CHARACTERS
    if _CHARACTERS is None:
        if gw2.build.need_refresh(BUILD_FILE):
            _CHARACTERS = _refresh()
        else:
            with open(CHARACTERS_FILE) as f:
                text = f.read()
                _CHARACTERS = [s for s in text.splitlines() if s]
    return _CHARACTERS

def _refresh():
    char_names = fetch_with_retries('/v2/characters')
    characters = [i for i in char_names]
    os.makedirs(CHARACTERS_DIR, exist_ok=True)
    with open(CHARACTERS_FILE, 'w') as f:
        for c in characters:
            f.write(c + "\n")

    with open(BUILD_FILE, 'w') as f:
        f.write(str(gw2.build.current()))
    
    return characters

def get_all_names():
    return _get_characters()

_CHARACTERS_CRAFTING = None
def _get_characters_crafting():
    global _CHARACTERS_CRAFTING
    if _CHARACTERS_CRAFTING is None:
        if gw2.build.need_refresh(BUILD_FILE):
            _CHARACTERS_CRAFTING = _refresh_crafting()
        else:
            with open(CRAFTING_DISCIPLINES_FILE) as f:
                text = f.read()
                _CHARACTERS_CRAFTING = json.loads(text)
    return _CHARACTERS_CRAFTING

def _refresh_crafting():
    char_names = _get_characters()
    all_craftings = {}
    for c in char_names:
        craftings = get_crafting_for_character(c)
        all_craftings[c] = craftings

    os.makedirs(CHARACTERS_DIR, exist_ok=True)
    with open(CRAFTING_DISCIPLINES_FILE, 'w') as f:
        json.dump(all_craftings, f)

    return all_craftings

def get_crafting_for_character(character_name):
    crafting_response = fetch_with_retries('/v2/characters/%s/crafting' %
                urllib.parse.quote(character_name))
    crafts = {}
    for craft_skill in crafting_response['crafting']:
        if craft_skill['active'] == True:
            crafts[craft_skill['discipline']] = craft_skill['rating']
    return crafts

def get_equipment_for_character(character_name):
    response = fetch_with_retries('/v2/characters/%s/equipment' %
                urllib.parse.quote(character_name))
    return response['equipment']


def get_all_character_disciplines():
    return _get_characters_crafting()

def get_max_of_each_discipline():
    characters_disciplines = get_all_character_disciplines()
    max_disciplines = {
        "Armorsmith": 0,
        "Artificer": 0,
        "Chef": 0,
        "Huntsman": 0,
        "Jeweler": 0,
        "Leatherworker": 0,
        "Scribe": 0,
        "Tailor": 0,
        "Weaponsmith": 0
    }
    
    for character in characters_disciplines.keys():
        for discipline in characters_disciplines[character].keys():
            if characters_disciplines[character][discipline] > max_disciplines[discipline]:
                max_disciplines[discipline] = characters_disciplines[character][discipline]

    return max_disciplines
