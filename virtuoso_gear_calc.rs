// rustc -O virtuoso_gear_calc.rs && ./virtuoso_gear_calc

#[derive(Clone, Copy, Debug, Default)]
struct SlotInfo {
    name: &'static str,
    stats3: (u32, u32),
    stats4: (u32, u32),
}

macro_rules! slot {
    ($name:expr, $stats3_major:expr, $stats3_minor:expr,
        $stats4_major:expr, $stats4_minor:expr) => {
        SlotInfo {
            name: $name,
            stats3: ($stats3_major, $stats3_minor),
            stats4: ($stats4_major, $stats4_minor),
        }
    };
}

static SLOTS_ASCENDED: [SlotInfo; 14] = [
    // Weapons
    slot!("Weapon1",    125,  90,   108,  59),
    slot!("Weapon2",    125,  90,   108,  59),
    // Armor
    slot!("Head",        63,  45,    54,  30),
    slot!("Shoulders",   47,  34,    40,  22),
    slot!("Chest",      141, 101,   121,  67),
    slot!("Gloves",      47,  34,    40,  22),
    slot!("Legs",        94,  67,    81,  44),
    slot!("Boots",       47,  34,    40,  22),
    // Trinkets
    slot!("Amulet",     157, 108,   133,  71),
    slot!("Ring1",      126,  85,   106,  56),
    slot!("Ring2",      126,  85,   106,  56),
    slot!("Accessory1", 110,  74,    92,  49),
    slot!("Accessory2", 110,  74,    92,  49),
    slot!("Back",        63,  40,    52,  27),
];

static SLOTS_EXOTIC: [SlotInfo; 14] = [
    // Weapons
    slot!("Weapon1",    120,  85,   102,  56),
    slot!("Weapon2",    120,  85,   102,  56),
    // Armor
    slot!("Head",        60,  43,    51,  28),
    slot!("Shoulders",   45,  32,    38,  21),
    slot!("Chest",      134,  96,   115,  63),
    slot!("Gloves",      45,  32,    38,  21),
    slot!("Legs",        90,  64,    77,  42),
    slot!("Boots",       45,  32,    38,  21),
    // Trinkets
    slot!("Amulet",     145, 100,   122,  66),
    slot!("Ring1",      115,  79,    97,  52),
    slot!("Ring2",      115,  79,    97,  52),
    slot!("Accessory1", 100,  68,    84,  45),
    slot!("Accessory2", 100,  68,    84,  45),
    slot!("Back",        55,  36,    46,  24),
];

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
struct Stats {
    power: u32,
    precision: u32,
    condition_damage: u32,
    expertise: u32,
}

impl Stats {
    fn crit_chance(&self, offset: f32) -> f32 {
        let mut chance = (self.precision as f32 - 895.) / 21. + offset;
        if chance > 100. {
            chance = 100.;
        }
        chance
    }

    fn bleed_damage(&self) -> f32 {
        22. + 0.06 * self.condition_damage as f32
    }

    fn bleed_duration(&self, offset: f32) -> f32 {
        let mut duration = 100. + self.expertise as f32 / 15. + offset;
        if duration > 200. {
            duration = 200.;
        }
        duration
    }

    fn bleed_damage_coeff(&self, duration_offset: f32) -> f32 {
        let damage = self.bleed_damage();
        let duration = self.bleed_duration(duration_offset);
        damage * duration / 100.
    }
}

fn eval(mut n: usize, slots: &[SlotInfo], base_stats: Stats) -> Stats {
    let mut stats = base_stats;

    for slot in slots {
        let i = n % 3;
        n /= 3;
        match i {
            0 => {
                // Viper's
                stats.power += slot.stats4.0;
                stats.condition_damage += slot.stats4.0;
                stats.precision += slot.stats4.1;
                stats.expertise += slot.stats4.1;
            },
            1 => {
                // Rampager's
                stats.precision += slot.stats3.0;
                stats.power += slot.stats3.1;
                stats.condition_damage += slot.stats3.1;
            },
            2 => {
                // Sinister
                stats.condition_damage += slot.stats3.0;
                stats.power += slot.stats3.1;
                stats.precision += slot.stats3.1;
            },
            _ => unreachable!(),
        }
    }

    stats
}

fn describe(mut n: usize, slots: &[SlotInfo]) -> String {
    let mut s = String::new();
    for slot in slots {
        if s.len() > 0 {
            s.push_str(", ");
        }

        s.push_str(slot.name);
        s.push_str("=");

        let i = n % 3;
        n /= 3;
        s.push_str(match i {
            0 => "Viper's",
            1 => "Rampager's",
            2 => "Sinister",
            _ => unreachable!(),
        });
    }

    s
}

fn describe_short(mut n: usize, slots: &[SlotInfo]) -> String {
    let mut s = String::new();
    for _ in slots {
        let i = n % 3;
        n /= 3;
        s.push_str(match i {
            0 => "V",
            1 => "R",
            2 => "S",
            _ => unreachable!(),
        });
    }

    s
}

fn slot_is_legendary(name: &str) -> bool {
    match name {
        "Amulet" => true,
        "Chest" | "Legs" | "Back" | "Accessory1" => true,
        _ => false,
    }
}

fn main() {
    let mut n = 1;
    for _ in &SLOTS_ASCENDED {
        n *= 3;
    }


    let mut slots = Vec::new();
    let mut num_ascended = 0;
    for (ascended, exotic) in SLOTS_ASCENDED.iter().zip(SLOTS_EXOTIC.iter()) {
        let slot = if slot_is_legendary(ascended.name) {
            num_ascended += 1;
            *ascended
        } else {
            *exotic
        };
        slots.push(slot);
        //slots.push(*ascended);
    }
    //assert_eq!(num_ascended, 5);


    let mut base_stats = Stats {
        power: 1000,
        precision: 1000,
        condition_damage: 0,
        expertise: 0,
    };

    // Runes
    base_stats.condition_damage += 175;

    // Infusions
    base_stats.condition_damage += 5 * 16;
    base_stats.precision += 5 * 2;

    // Signet of Domination
    base_stats.condition_damage += 180;

    // Signet of Midnight
    base_stats.expertise += 180;

    // Food
    base_stats.precision += 100;
    base_stats.condition_damage += 70;

    // Utility
    let apply_utility = |stats: &mut Stats| {
        stats.condition_damage += stats.power * 3 / 100;
        stats.condition_damage += stats.precision * 3 / 100;
    };


    let mut options = Vec::new();
    for i in 0 .. n {
        if i % 1000 == 0 {
            eprintln!("{} / {}", i, n);
        }
        let mut stats = eval(i, &slots, base_stats);
        apply_utility(&mut stats);
        options.push((i, stats));
    }

    options.sort_by_key(|&(_, ref stats)| {
        (
            (1000. * stats.crit_chance(40.)) as u32,
            (1000. * stats.bleed_damage_coeff(70.)) as u32,
        )
    });

    //let target = "VVVRVRSRRVRRRR";
    //options.retain(|x| describe_short(x.0, &slots) == target);

    let best = options.last().unwrap().1;
    let mut equivalents = options.iter().filter(|x| x.1 == best).cloned().collect::<Vec<_>>();
    let target = "VVVRVRSRRVRRRR";
    let count_same = |i| {
        let desc = describe_short(i, &slots);
        target.chars().zip(desc.chars()).enumerate().filter(|&(i, (c1, c2))| {
            c1 == c2 || slot_is_legendary(slots[i].name)
        }).count()
    };
    equivalents.sort_by_cached_key(|&(i, _)| count_same(i));

    for (i, stats) in equivalents.into_iter().rev().take(10) {
        //eprintln!("{}", target);
        eprintln!("{}  same={}  {:?}  {}",
            describe_short(i, &slots),
            count_same(i),
            stats, describe(i, &slots));
        eprintln!("  crit = {}, bleed dmg = {}, dur = {}, coeff = {}",
            stats.crit_chance(40.), stats.bleed_damage(), stats.bleed_duration(70.),
            stats.bleed_damage_coeff(70.));
    }
}
