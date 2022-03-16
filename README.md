# How to use Bookkeepr

```
python3 bookkeeper.py init
python3 bookkeeper.py goal 50 'Piece of Dragon Jade'
python3 bookkeeper.py stockpile 100 'Orichalcum Ingot'
python3 bookkeeper.py status
```

goal <count> <item> increases the target amount sold for item, after which status will tell you what to buy/craft/etc in order to reach the goal.  stockpile <count> <item> increases the stockpile target, which is the minimum amount to keep on hand at all times (defaults to zero).  count can be negative to reduce the goal/stockpile value.  for runes/sigils, currently you must use the numeric ID for item instead of the name, since otherwise it will pick the non-craftable legendary version with the same name (currently gw2.items.search_name doesn't properly handle the case of multiple items with the same name)

**NOTE** the script is always in "use own materials" mode.  it only sees a snapshot of your current inventory, and doesn't try to determine whether you bought some items for crafting/selling purposes or if you just happened to have them on hand for other reasons.  if you need to stop it from cleaning out your material storage, set the stockpile amount