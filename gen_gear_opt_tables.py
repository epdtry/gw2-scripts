from collections import defaultdict, namedtuple
from contextlib import contextmanager
import datetime
from pprint import pprint
import re
import sys

import gw2.build
import gw2.items
import gw2.itemstats


def get_slot_points(dct):
    out = {}
    for slot_name, item_name in dct.items():
        item_id = gw2.items.search_name(item_name, allow_multiple=False)
        item = gw2.items.get(item_id)
        points = item['details']['attribute_adjustment']
        out[slot_name] = points
    return out

TRINKET_SLOTS = {'amulet', 'ring1', 'ring2', 'accessory1', 'accessory2', 'backpack'}

def do_gear_slots():
    points_exotic = get_slot_points({
        'weapon_1h': "Berserker's Pearl Carver",
        'weapon_2h': "Berserker's Pearl Broadsword",
        'helm': 'Bladed Cowl',
        'shoulders': 'Bladed Mantle',
        'coat': 'Bladed Vestments',
        'gloves': 'Bladed Gloves',
        'leggings': 'Bladed Pants',
        'boots': 'Bladed Shoes',
        'amulet': 'Ruby Orichalcum Amulet',
        'ring1': 'Ruby Orichalcum Ring',
        'ring2': 'Ruby Orichalcum Ring',
        'accessory1': 'Ruby Orichalcum Earring',
        'accessory2': 'Ruby Orichalcum Earring',
        'backpack': "Elite's Wings of Glory",
    })

    points_ascended = get_slot_points({
        'weapon_1h': "Zojja's Razor",
        'weapon_2h': "Zojja's Claymore",
        'helm': 'Experimental Envoy Cowl',
        'shoulders': 'Experimental Envoy Mantle',
        'coat': 'Experimental Envoy Vestments',
        'gloves': 'Experimental Envoy Gloves',
        'leggings': 'Experimental Envoy Pants',
        'boots': 'Experimental Envoy Shoes',
        'amulet': 'Scion-Spike Amulet',
        'ring1': 'Mistborn Band',
        'ring2': 'Mistborn Band',
        'accessory1': 'Mists-Charged Treasure',
        'accessory2': 'Mists-Charged Treasure',
        'backpack': 'Relic of Balthazar',
    })

    assert len(points_exotic) == len(points_ascended)
    print('\npub static GEAR_SLOTS: PerGearSlot<SlotInfo> = PerGearSlot {')
    for slot, exotic in points_exotic.items():
        ascended = points_ascended[slot]
        print('    %s: SlotInfo {' % slot)
        print('        points: PerQuality {')
        print('            exotic: %s,' % float(exotic))
        print('            ascended: %s,' % float(ascended))
        print('        },')
        is_trinket = slot in TRINKET_SLOTS
        print('        add_base: %s,' % ('true' if is_trinket else 'false'))
        print('    },')
    print('};')


def get_pve_stats():
    # We first gather the list of valid prefix names from a stat-selectable
    # ascended weapon.  This excludes some unusual prefixes that are only
    # available on jewelry.
    item_id = gw2.items.search_name('The Raven Staff', allow_multiple=False)
    item = gw2.items.get(item_id)
    valid_prefix_names = set(
            gw2.itemstats.get(itemstats_id)['name']
            for itemstats_id in item['details']['stat_choices'])


    # For the actual stat formulas, we use a legendary backpiece to get the
    # list because the backpiece versions of the `itemstats` include the base
    # value used in ascended trinkets to account for the lack of a gemstone
    # slot.
    item_id = gw2.items.search_name('Ad Infinitum', allow_multiple=False)
    item = gw2.items.get(item_id)
    out = {}
    for itemstats_id in item['details']['stat_choices']:
        itemstats = gw2.itemstats.get(itemstats_id)

        if itemstats['name'] not in valid_prefix_names:
            continue

        #if itemstats['name'] not in ("Viper's", "Rampager's", 'Sinister'): continue

        mults = sorted(set(stat['multiplier'] for stat in itemstats['attributes']),
            reverse=True)
        mult_rank = {x: i for i,x in enumerate(mults)}

        stat_formulas = {}
        for stat in itemstats['attributes']:
            rank = mult_rank[stat['multiplier']]
            # As a special case, exotic celestial jewels don't provide
            # expertise or concentration.
            if itemstats['name'] == 'Celestial':
                rank = 1 if stat['attribute'] in ('ConditionDuration', 'BoonDuration') else 0
            stat_formulas[stat['attribute']] = {
                    'factor': stat['multiplier'],
                    'base_ascended': stat['value'],
                    # Rank is 0 for the major stat of the prefix and 1 for
                    # minor.
                    'rank': rank,
                    }

        # Figure out the base value for exotic trinkets
        num_stats = len(itemstats['attributes'])
        if num_stats == 3:
            # Berserker's exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Ruby Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], dct['Precision']]
        elif num_stats == 4:
            # Viper's exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Black Diamond Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], dct['Precision']]
        elif num_stats == 9:
            # Celestial exotic jewel
            jewel_item_id = gw2.items.search_name('Exquisite Charged Quartz Jewel')
            jewel_item = gw2.items.get(jewel_item_id)
            dct = {x['attribute']: x['modifier']
                    for x in jewel_item['details']['infix_upgrade']['attributes']}
            base_exotic_by_rank = [dct['Power'], 0]
        else:
            raise ValueError('unrecognized stat count in %r' % (itemstats,))

        for formula in stat_formulas.values():
            formula['base_exotic'] = base_exotic_by_rank[formula['rank']]

        out[itemstats['name']] = stat_formulas
    return out

def do_prefixes():
    prefixes = get_pve_stats()

    print('\npub const NUM_PREFIXES: usize = %d;' % len(prefixes))
    print('\npub static PREFIXES: [Prefix; NUM_PREFIXES] = [')
    for name in sorted(prefixes.keys()):
        prefix = prefixes[name]
        print('    Prefix {')
        print('        name: "%s",' % name)
        print('        formulas: PerStat {')

        def print_formula(field_name, stat_key):
            formula = prefix.get(stat_key)
            if formula is not None:
                print('            %s: StatFormula {' % field_name)
                print('                factor: %s,' % float(formula['factor']))
                print('                base: PerQuality {')
                print('                    exotic: %s,' % float(formula['base_exotic']))
                print('                    ascended: %s,' % float(formula['base_ascended']))
                print('                },')
                print('            },')
            else:
                print('            %s: StatFormula::ZERO,' % field_name)

        print_formula('power', 'Power')
        print_formula('precision', 'Precision')
        print_formula('ferocity', 'CritDamage')
        print_formula('condition_damage', 'ConditionDamage')
        print_formula('expertise', 'ConditionDuration')
        print_formula('vitality', 'Vitality')
        print_formula('toughness', 'Toughness')
        print_formula('healing_power', 'Healing')
        print_formula('concentration', 'BoonDuration')

        print('        },')
        print('    },')
    print('];')


def camel_to_snake(s):
    s = re.sub('[A-Z]', lambda m: '_' + m.group().lower())
    if s.startswith('_'):
        s = s[1:]
    return s

def interpret_bonus(s):
    '''Parse a bonus effect description from a rune, sigil, food, or utility
    item.  Returns a pair of a key indicating which stat or modifier should be
    increased and the floating-point amount of the increase.  Different bonuses
    with the same key stack by adding their values.  The key is always a tuple;
    the first field is a string giving the general effect type, and the
    remaining fields are parameters.  For example, the `stat_bonus` effect type
    takes a stat name as a parameter.

    As a special case, instead of returning a single key-value pair, this
    function may instead return a pair of the string `'multi'` and a list of
    key-value pairs.
    '''
    s = s.lower()
    s = re.sub('<c=@reminder>[^<>]*</c>', '', s)
    s = s.strip()
    s = s.removesuffix('.')

    stat_name_map = {
            'power': 'power',
            'precision': 'precision',
            'ferocity': 'ferocity',
            'ferocity': 'ferocity',
            'condition damage': 'condition_damage',
            'condition damage': 'condition_damage',
            'expertise': 'expertise',
            'vitality': 'vitality',
            'toughness': 'toughness',
            'healing': 'healing_power',
            'healing power': 'healing_power',
            'concentration': 'concentration',
            }
    stat_name_re = '|'.join(re.escape(k) for k in stat_name_map.keys())

    condi_name_map = {
            'poison': 'poison',
            'bleeding': 'bleed',
            'burning': 'burn',
            'burn': 'burn',
            'confusion': 'confuse',
            'torment': 'torment',
            'weakness': None,
            'chill': None,
            'fear': None,
            'cripple': None,
            'vulnerability': None,
            # These are actually CC, not conditions
            'daze': None,
            'stun': None,
            }
    condi_name_re = '|'.join(re.escape(k) for k in condi_name_map.keys())

    boon_name_map = {
            'might': 'might',
            'fury': 'fury',
            'swiftness': 'swiftness',
            'regeneration': 'regeneration',
            'protection': 'protection',
            'quickness': 'quickness',
            }
    boon_name_re = '|'.join(re.escape(k) for k in boon_name_map.keys())

    def match(*re_fmts):
        for re_fmt in re_fmts:
            m = re.fullmatch(re_fmt.format(
                stat_name_re = stat_name_re,
                condi_name_re = condi_name_re,
                boon_name_re = boon_name_re), s)
            if m:
                return m
        return None

    if m := match(r'\+([0-9]+) ({stat_name_re})'):
        return ('stat_bonus', stat_name_map[m.group(2)]), float(m.group(1))
    elif m := match(r'\+([0-9]+) to all (?:stats|attributes)'):
        return ('stat_bonus_all',), float(m.group(1))
    elif m := match(r'convert (?P<n>[0-9]+)% of your (?P<s1>{stat_name_re}) '
                r'into (?P<s2>{stat_name_re})',
            r'(?P<n>[0-9]+)% of (?:your )?(?P<s1>{stat_name_re}) is converted '
                r'(?:in)?to (?P<s2>{stat_name_re})',
            r'gain (?P<s2>{stat_name_re}) equal to (?P<n>[0-9]+)% of '
                r'your (?P<s1>{stat_name_re})'):
        return ('stat_distribute', stat_name_map[m.group('s1')],
                stat_name_map[m.group('s2')]), float(m.group('n')) / 100

    elif m := match(r'\+(?P<n>[0-9]+)% (?P<c>{condi_name_re}) duration',
            r'increase inflicted (?P<c>{condi_name_re}) duration: (?P<n>[0-9]+)%',
            r'increase the duration of inflicted (?P<c>{condi_name_re}) by (?P<n>[0-9]+)%'):
        condi = condi_name_map[m.group('c')]
        if condi is not None:
            return ('condi_duration', condi), float(m.group('n'))
        else:
            return ('unimplemented', 'condi_duration', m.group('c')), float(m.group('n'))
    elif m := match(r'\+([0-9]+)% condition duration'):
        return ('condi_duration_all',), float(m.group(1))
    elif m := match(r'\+([0-9]+)% condition damage'):
        return ('condi_damage_percent',), float(m.group(1))

    elif m := match(r'\+?([0-9]+)% ({boon_name_re}) duration'):
        boon = boon_name_map[m.group(2)]
        if boon is not None:
            return ('boon_duration', boon), float(m.group(1))
        else:
            return ('unimplemented', 'boon_duration', m.group(2)), float(m.group(1))
    elif m := match(r'\+([0-9]+)% boon duration'):
        return ('boon_duration_all',), float(m.group(1))

    elif m := match(r'\+([0-9]+)% (increased )?maximum health'):
        return ('max_health',), float(m.group(1))
    elif m := match(r'increase strike damage dealt by \+([0-9]+)%',
            r'\+([0-9]+)% (?:strike )?damage'):
        return ('strike_damage',), float(m.group(1))
    elif m := match(r'\+([0-9]+)% damage and \+([0-9]+)% condition damage'):
        return 'multi', [
                (('strike_damage',), float(m.group(1))),
                (('condi_damage_percent',), float(m.group(2))),
                ]
    if m := match(r'\+([0-9]+) critical chance'):
        return ('crit_chance',), float(m.group(1))

    elif m := match(r'(?:gain |\+)?([0-9]+)% movement speed'):
        return ('unimplemented', 'move_speed'), float(m.group(1))
    elif m := match(r'-([0-9]+)% incoming ([^ ]*) duration'):
        return ('unimplemented', 'incoming_condi_duration', m.group(2)), -float(m.group(1))
    elif m := match(r'-([0-9]+)% incoming ([^ ]*) damage'):
        return ('unimplemented', 'incoming_condi_damage', m.group(2)), -float(m.group(1))
    elif m := match(r'-([0-9]+)% incoming damage'):
        return ('unimplemented', 'incoming_damage'), -float(m.group(1))
    elif m := match(r'\+([0-9]+)% incoming heal effectiveness'):
        return ('unimplemented', 'incoming_heal'), float(m.group(1))
    elif m := match(r'\+([0-9]+)% experience from kills'):
        return ('unimplemented', 'xp_from_kills'), float(m.group(1))
    elif m := match(r'\+([0-9]+)% (?:experience|all experience gained)'):
        return ('unimplemented', 'xp'), float(m.group(1))
    elif m := match(r'\+([0-9]+)% karma(?: bonus)'):
        return ('unimplemented', 'karma'), float(m.group(1))
    elif m := match(r'\+([0-9]+)% magic find'):
        return ('unimplemented', 'magic_find'), float(m.group(1))

    else:
        return ('unknown', s), 1

def interpret_bonuses(descs):
    dct = defaultdict(float)

    for desc in descs:
        for part in re.split(r';|(?<!\bvs)\. \b|\n', desc):
            k, v = interpret_bonus(part)
            if k == 'multi':
                for kk, vv in v:
                    dct[kk] += vv
            else:
                dct[k] += v

    return dict(dct)

def bonus_key(bonus):
    return tuple(sorted((k,v) for k,v in bonus.items()
        if k[0] not in ('unknown', 'unimplemented')))


class Writer:
    def __init__(self):
        self._indent = ''
        self.lines = []

    @contextmanager
    def indent(self):
        old = self._indent
        self._indent += '    '
        yield
        self._indent = old

    def emit(self, s):
        for line in s.splitlines():
            self.lines.append(self._indent + line)

    def finish(self):
        return '\n'.join(self.lines)

def mk_effect_impl(w, name, display_name, parts):
    w.emit('#[allow(unused_variables)]')
    w.emit('impl Effect for %s {' % name)
    for method, lines in parts.items():
        if len(lines) == 0:
            continue
        with w.indent():
            w.emit('fn %s(&self, s: &mut Stats, m: &mut Modifiers) {' % method)
            with w.indent():
                for line in lines:
                    w.emit(line)
            w.emit('}')
    w.emit('}')

    w.emit('impl Vary for %s {' % name)
    with w.indent():
        w.emit('fn num_fields(&self) -> usize { 0 }')
        w.emit('fn num_field_values(&self, _field: usize) -> u16 { panic!() }')
        w.emit('fn get_field(&self, _field: usize) -> u16 { panic!() }')
        w.emit('fn set_field(&mut self, _field: usize, _value: u16) { panic!() }')
    w.emit('}')

    w.emit('impl %s {' % name)
    with w.indent():
        w.emit("pub fn display_name(&self) -> &'static str {")
        with w.indent():
            w.emit('"%s"' % display_name)
        w.emit('}')
    w.emit('}')

def print_dispatch_enum(name, items):
    w = Writer()

    # Enum definition
    w.emit('\n#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]')
    w.emit('pub enum %s {' % name)
    with w.indent():
        for item in items:
            w.emit('%s(%s),' % (item, item))
    w.emit('}')

    # Default impl
    w.emit('impl Default for %s {' % name)
    with w.indent():
        w.emit('fn default() -> %s { %s::%s(%s) }' % (name, name, items[0], items[0]))
    w.emit('}')

    # Inherent methods
    w.emit('impl %s {' % name)
    with w.indent():
        w.emit('pub const COUNT: usize = %d;' % len(items))

        w.emit('pub fn index(self) -> usize {')
        with w.indent():
            w.emit('match self {')
            with w.indent():
                for i, item in enumerate(items):
                    w.emit('%s::%s(%s) => %d,' % (name, item, item, i))
            w.emit('}')
        w.emit('}')

        w.emit('pub fn from_index(i: usize) -> %s {' % name)
        with w.indent():
            w.emit('match i {')
            with w.indent():
                for i, item in enumerate(items):
                    w.emit('%d => %s::%s(%s),' % (i, name, item, item))
                w.emit('_ => panic!("index {} out of range for %s", i),' % name)
            w.emit('}')
        w.emit('}')

        w.emit('pub fn iter() -> impl Iterator<Item = %s> {' % name)
        with w.indent():
            w.emit('(0 .. %s::COUNT).map(%s::from_index)' % (name, name))
        w.emit('}')

        w.emit("pub fn display_name(self) -> &'static str {")
        with w.indent():
            w.emit('match self {')
            with w.indent():
                for i, item in enumerate(items):
                    w.emit('%s::%s(x) => x.display_name(),' % (name, item))
            w.emit('}')
        w.emit('}')
    w.emit('}')

    # Effect impl
    w.emit('impl Effect for %s {' % name)
    with w.indent():
        for method in ['add_permanent', 'distribute', 'add_temporary']:
            w.emit('fn %s(&self, s: &mut Stats, m: &mut Modifiers) {' % method)
            with w.indent():
                w.emit('match *self {')
                with w.indent():
                    for item in items:
                        w.emit('%s::%s(x) => x.%s(s, m),' % (name, item, method))
                w.emit('}')
            w.emit('}')
    w.emit('}')

    # From impls
    for item in items:
        w.emit('impl From<%s> for %s {' % (item, name))
        with w.indent():
            w.emit('fn from(x: %s) -> %s { %s::%s(x) }' % (item, name, name, item))
        w.emit('}')

    # Vary impl
    w.emit('impl Vary for %s {' % name)
    with w.indent():
        w.emit('fn num_fields(&self) -> usize { 1 }')
        w.emit('fn num_field_values(&self, _field: usize) -> u16 { %d }' % len(items))
        w.emit('fn get_field(&self, _field: usize) -> u16 {')
        with w.indent():
            w.emit('self.index() as u16')
        w.emit('}')
        w.emit('fn set_field(&mut self, _field: usize, value: u16) {')
        with w.indent():
            w.emit('*self = %s::from_index(value as usize);' % name)
        w.emit('}')
    w.emit('}')

    print(w.finish())

def print_known_impls(all_enum, known_enum, all_names, known_names, rep_map):
    w = Writer()

    # Inherent methods on All
    w.emit('impl %s {' % (all_enum,))
    with w.indent():
        w.emit('pub fn is_known(self) -> bool {')
        with w.indent():
            w.emit('match self {')
            with w.indent():
                for name in known_names:
                    w.emit('%s::%s(_) => true,' % (all_enum, name))
                w.emit('_ => false,')
            w.emit('}')
        w.emit('}')

        w.emit('pub fn as_known(self) -> %s {' % (known_enum,))
        with w.indent():
            w.emit('match self {')
            with w.indent():
                for name in all_names:
                    rep_name = rep_map[name]
                    w.emit('%s::%s(%s) => %s::%s(%s),' % (
                        all_enum, name, name, known_enum, rep_name, rep_name))
            w.emit('}')
        w.emit('}')
    w.emit('}')

    # Inherent methods on separate effect types
    for name in all_names:
        w.emit('impl %s {' % (name,))
        with w.indent():
            w.emit('pub fn as_known(self) -> %s {' % (known_enum,))
            with w.indent():
                rep_name = rep_map[name]
                w.emit('%s::%s(%s)' % (known_enum, rep_name, rep_name))
            w.emit('}')
        w.emit('}')

    # From<Known> for All
    w.emit('impl From<%s> for %s {' % (known_enum, all_enum))
    with w.indent():
        w.emit('fn from(x: %s) -> %s {' % (known_enum, all_enum))
        with w.indent():
            w.emit('match x {')
            with w.indent():
                for name in known_names:
                    w.emit('%s::%s(y) => %s::%s(y),' % (
                        known_enum, name, all_enum, name))
            w.emit('}')
        w.emit('}')
    w.emit('}')

    print()
    print(w.finish())


def build_bonus_lines(bonus):
    effect_lines = {
            'add_permanent': [],
            'distribute': [],
            'add_temporary': [],
            }

    dest_map = {
            'stat_bonus': 'add_permanent',
            'stat_bonus_all': 'add_permanent',
            'stat_distribute': 'distribute',
            'condi_duration': 'add_permanent',
            'condi_duration_all': 'add_permanent',
            'condi_damage_percent': 'add_permanent',
            'boon_duration': 'add_permanent',
            'boon_duration_all': 'add_permanent',
            'max_health': 'add_permanent',
            'strike_damage': 'add_permanent',
            'crit_chance': 'add_permanent',
            'unknown': 'add_permanent',
            'unimplemented': 'add_permanent',
            'raw': 'add_permanent',
            }

    for k, v in bonus:
        kind = k[0]
        dest_key = dest_map[kind]

        if kind == 'stat_bonus':
            which, = k[1:]
            line = 's.%s += %s;' % (which, v)
        elif kind == 'stat_bonus_all':
            assert len(k) == 1
            line = '*s += %s;' % (v,)
        elif kind == 'stat_distribute':
            stat1, stat2 = k[1:]
            line = 's.%s += s.%s * %s;' % (stat2, stat1, v)

        elif kind == 'condi_duration':
            which, = k[1:]
            line = 'm.condition_duration.%s += %s;' % (which, v)
        elif kind == 'condi_duration_all':
            assert len(k) == 1
            line = 'm.condition_duration += %s;' % (v,)
        elif kind == 'condi_damage_percent':
            assert len(k) == 1
            line = 'm.condition_damage += %s;' % (v,)

        elif kind == 'boon_duration':
            which, = k[1:]
            line = 'm.boon_duration.%s += %s;' % (which, v)
        elif kind == 'boon_duration_all':
            assert len(k) == 1
            line = 'm.boon_duration += %s;' % (v,)

        elif kind == 'max_health':
            assert len(k) == 1
            line = 'm.max_health += %s;' % (v,)
        elif kind == 'strike_damage':
            assert len(k) == 1
            line = 'm.strike_damage += %s;' % (v,)
        elif kind == 'crit_chance':
            assert len(k) == 1
            line = 'm.crit_chance += %s;' % (v,)

        elif kind == 'unknown':
            assert len(k) == 2
            mult = '' if v == 1 else ' (%dx)' % v
            line = '// unknown%s: %s' % (mult, k[1])
        elif kind == 'unimplemented':
            mult = '' if v == 1 else ' (%dx)' % v
            line = '// unimplemented%s: %s' % (mult, k)
        elif kind == 'raw':
            assert len(k) == 1
            line = v

        effect_lines[dest_key].append(line)

    return effect_lines

Effect = namedtuple('Effect', ('name', 'display_name', 'bonus'))

def define_effects(es):
    '''Process a list of `Effect` items and print a Rust definition for each
    one.  Returns `all_names, known_names, rep_map`, which are the names of the
    Rust structs for all items, the names of only the known items, and the map
    from each name to its known representative.

    "Known" items are those that remain after removing all unknown and
    unimplemented effects and then deduplicating.  This doesn't mean that all
    effects of the item are known, only that enough are known to distinguish it
    from all other known items.  For example, Rune of Altruism and Rune of the
    Rebirth differ only in their unknown final effect, so only one can be a
    known item (we arbitrarily pick Altruism, since it comes first
    alphabetically).
    '''
    def sort_key(x):
        if x.startswith('No') and x[2].isupper():
            return ''
        else:
            return x

    all_names = []
    groups = defaultdict(list)
    for e in sorted(es, key = lambda e: sort_key(e.name)):
        w = Writer()
        w.emit('/// %s' % e.display_name)
        w.emit('#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]')
        w.emit('pub struct %s;' % e.name)
        lines = build_bonus_lines(e.bonus.items())
        mk_effect_impl(w, e.name, e.display_name, lines)
        print('')
        print(w.finish())

        all_names.append(e.name)

        key = bonus_key(e.bonus)
        groups[key].append(e.name)

    known_names = []
    rep_map = {}
    for g in groups.values():
        g.sort(key = sort_key)
        rep_name = g[0]
        known_names.append(rep_name)
        for name in g:
            rep_map[name] = rep_name

    return all_names, known_names, rep_map


def do_runes_sigils(kind):
    items = []

    for item in gw2.items.iter_all():
        if not item['name'].startswith('Superior %s of ' % kind):
            continue
        if item['rarity'] != 'Exotic':
            continue
        if item['name'] == 'Superior Rune of Holding':
            continue
        items.append(item)

    effects = [Effect('No' + kind, 'No ' + kind, {})]
    for item in sorted(items, key=lambda i: i['name']):
        name = item['name']
        name = name.removeprefix('Superior %s of ' % kind)
        name = name.removeprefix('the ')
        name = ''.join(name.split())
        name = re.sub('[^a-zA-Z]', '', name)

        if kind == 'Rune':
            bonus_descs = item['details']['bonuses']
        elif kind == 'Sigil':
            bonus_descs = [item['details']['infix_upgrade']['buff']['description']]
        else:
            raise ValueError('bad rune/sigil kind %r' % kind)

        bonus = interpret_bonuses(bonus_descs)
        effects.append(Effect(name, item['name'], bonus))

    all_names, known_names, rep_map = define_effects(effects)
    print_dispatch_enum(kind, all_names)
    print_dispatch_enum('Known' + kind, known_names)
    print_known_impls(kind, 'Known' + kind, all_names, known_names, rep_map)

# Some food item descriptions are missing from the API.
EXTRA_DESCRIPTIONS = {
        'Red-Lentil Saobosa': '+100 Expertise; +70 Condition Damage; +1% All Experience Gained',
        'Bowl of Fruit Salad with Mint Garnish':
            '+10% Outgoing Healing; +100 Healing Power; +70 Concentration; '
            '+10% Karma; +5% All Experience Gained; +20% Magic Find; '
            '+20% Gold Find; +10% WXP Gained',
        }

def do_food_utility(kind):
    items = []

    for item in gw2.items.iter_all():
        if item['level'] != 80:
            continue
        if item['type'] != 'Consumable':
            continue
        if item['details']['type'] != kind:
            continue
        if 'description' not in item['details'] and item['name'] not in EXTRA_DESCRIPTIONS:
            continue
        items.append(item)

    all_names = set()
    effects = [Effect('No' + kind, 'No ' + kind, {})]
    for item in sorted(items, key=lambda i: i['name']):
        name = item['name']
        name = name.removeprefix('Can of ')
        name = name.removeprefix('Plate of ')
        name = name.removeprefix('Filet of ')
        name = name.removeprefix('Bowl of ')
        name = name.removeprefix('Loaf of ')
        name = ''.join(re.sub('^[a-z]', lambda m: m.group().upper(), x)
                for x in name.split())
        name = re.sub('[^a-zA-Z]', '', name)

        if name in all_names:
            print('warning: duplicate entry for %s' % name, file = sys.stderr)
            continue
        all_names.add(name)

        if kind == 'Food' or kind == 'Utility':
            bonus_descs = [item['details'].get('description') or
                    EXTRA_DESCRIPTIONS[item['name']]]
        else:
            raise ValueError('bad food/utility kind %r' % kind)

        bonus = interpret_bonuses(bonus_descs)
        effects.append(Effect(name, item['name'], bonus))

    all_names, known_names, rep_map = define_effects(effects)
    print_dispatch_enum(kind, all_names)
    print_dispatch_enum('Known' + kind, known_names)
    print_known_impls(kind, 'Known' + kind, all_names, known_names, rep_map)




def main():
    modes = sys.argv[1:]
    if len(modes) == 0:
        raise ValueError('expected at least 1 mode argument')

    print('// BEGIN GENERATED CODE')
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    print('// Generated by gen_gear_tables.py for GW2 build %s at %s' %
            (gw2.build.current(), now))

    for mode in modes:
        if mode == 'gear':
            do_gear_slots()
        elif mode == 'prefixes':
            do_prefixes()
        elif mode == 'rune':
            do_runes_sigils('Rune')
        elif mode == 'sigil':
            do_runes_sigils('Sigil')
        elif mode == 'food':
            do_food_utility('Food')
        elif mode == 'utility':
            do_food_utility('Utility')
        else:
            raise ValueError('unknown mode %r' % mode)

    print('\n// END GENERATED CODE')




if __name__ == '__main__':
    main()

