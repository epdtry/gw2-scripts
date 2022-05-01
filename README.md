# How to use Bookkeeper

```
python3 bookkeeper.py init
python3 bookkeeper.py goal 50 'Piece of Dragon Jade'
python3 bookkeeper.py stockpile 100 'Orichalcum Ingot'
python3 bookkeeper.py status
```

goal <count> <item> increases the target amount sold for item, after which status will tell you what to buy/craft/etc in order to reach the goal.  stockpile <count> <item> increases the stockpile target, which is the minimum amount to keep on hand at all times (defaults to zero).  count can be negative to reduce the goal/stockpile value.  for runes/sigils, currently you must use the numeric ID for item instead of the name, since otherwise it will pick the non-craftable legendary version with the same name (currently gw2.items.search_name doesn't properly handle the case of multiple items with the same name)

**NOTE** the script is always in "use own materials" mode.  it only sees a snapshot of your current inventory, and doesn't try to determine whether you bought some items for crafting/selling purposes or if you just happened to have them on hand for other reasons.  if you need to stop it from cleaning out your material storage, set the stockpile amount

# How to use Loot Tool

First, you can always list commands with:
```python loot_tool.py help```

Typical usage is:
1. Clean up inventory space and place target container to open in your inventory. Wait ~5minutes. you can optionally use ```python loot_tool.py inventory``` to see the rough data of what's in your inventory to know if the snapshots are ready to be taken.
2. Get a base snapshot of your character. You'll need your characters current magic find from you're hero's equipment panel (h).  The magic find has no symbols. so:
```python loot_tool.py snapshot <char_name> <magic_find>```
example:  ```python loot_tool.py snapshot "Your Char" 196```
3. If you didn't wait or check your inventory, go check your snapshot info out at ```../gw2-data/snapshots/*.json``` to see if things look correctly (data is raw json, but maybe another tool could be added to make this easier)
4. Open up all the bags. Wait ~5 minutes and/or check inventory.
5. Take next the next snapshot with the same command as before
example: ```python loot_tool.py snapshot "Your Char" 196```
6. Create a diff from the two snapshots, where ```filename1.json``` is the base snapshot
```python loot_tool.py diff ../path/to/filename1.json ../path/to/filename2.json```
7. Print the results:
```python loot_tool.py gen_worth_tables```

Simplified example usage:
```
* put 250 bags in a (mostly) clean inventory. wait 5 minutes
python loot_tool.py snapshot "Your Char" 196
* open 250 bags. wait 5 minutes.
python loot_tool.py snapshot "Your Char" 196
python loot_tool.py diff ../path/to/filename1.json ../path/to/filename2.json
python loot_tool.py gen_worth_tables
```

**NOTE** this script assumes you have the ```../gw2-data``` directories from the private repo already cloned. If not, create ```../gw2-data/diffs``` and ```../gw2-data/snapshots``` before running these tools.