#[macro_use] mod macros;

mod character;
mod gear;
mod optimize;
mod stats;

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};

pub use crate::character::{CharacterModel, Baseline, DpsModel};
pub use crate::gear::{PerGearSlot, GearSlot, PerQuality, Quality, SlotInfo, Prefix, StatFormula};
pub use crate::stats::{PerStat, Stat, Stats, BASE_STATS, Modifiers, PerCondition, Condition};
use crate::optimize::coarse::{optimize_coarse, calc_gear_stats};













struct CondiVirt {
    dps: DpsModel,
}

impl CondiVirt {
    pub fn new() -> CondiVirt {
        let mut ch = CondiVirt {
            dps: DpsModel::zero(),
        };
        ch.dps = DpsModel::new(&ch, &Baseline {
            gear: Stats {
                power: 986.,
                precision: 981.,
                condition_damage: 1012.,
                expertise: 255.,
                .. Stats::default()
            },
            dps: 30063.,
            condition_percent: PerCondition {
                bleed: 59.9,
                torment: 10.3,
                confuse: 1.3,
                poison: 0.2,
                .. 0.0.into()
            },
        });
        ch
    }
}


impl CharacterModel for CondiVirt {
    fn calc_stats(&self, gear: &Stats) -> Stats {
        let mut stats = &BASE_STATS + gear;

        // Runes
        stats.condition_damage += 175.;

        // Infusions
        //stats.condition_damage += 16. * 5.;
        //stats.precision += 2. * 5.;

        // Signet of Domination
        stats.condition_damage += 180.;
        // Signet of Midnight
        stats.expertise += 180.;

        // Food
        stats.precision += 100.;
        stats.condition_damage += 70.;

        // Quiet Intensity
        stats.ferocity += stats.vitality * 0.10;

        // Utility
        stats.condition_damage += stats.power * 0.03;
        stats.condition_damage += stats.precision * 0.03;

        // Might
        stats.power += 25. * 30.;
        stats.condition_damage += 25. * 30.;

        // Compounding Power
        stats.condition_damage += 1. * 30.;

        stats
    }

    fn calc_modifiers(&self) -> Modifiers {
        let mut m = Modifiers::default();

        // Runes
        m.condition_duration.bleed += 50.;

        // Sigils
        m.condition_duration.bleed += 20.;

        // Fury +25%, fury bonus from trait +15%
        m.crit_chance += 40.;

        // Superiority Complex: +15%, +10% on disabled or defiant foes
        m.crit_damage += 25.;

        // Compounding Power
        m.strike_damage += 1. * 2.;

        // Bloodsong
        m.condition_damage.bleed += 25.;

        m
    }

    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let crit = stats.crit_chance(mods);
        if crit < 100. {
            return 1000. + 100. - crit;
        }

        -self.dps.calc_dps(stats, mods)
    }
}


struct CairnSoloArcane {
    dps: DpsModel,
}

impl CairnSoloArcane {
    pub fn new() -> CairnSoloArcane {
        let mut ch = CairnSoloArcane {
            dps: DpsModel::zero(),
        };
        ch.dps = DpsModel::new(&ch, &Baseline {
            gear: Stats {
                power: 824.,
                precision: 793.,
                condition_damage: 1173.,
                expertise: 444.,
                healing_power: 189.,
                concentration: 189.,
                .. Stats::default()
            },
            dps: 6708.,
            condition_percent: PerCondition {
                burn: 68.9,
                bleed: 10.3,
                .. 0.0.into()
            },
        });
        ch
    }
}


impl CharacterModel for CairnSoloArcane {
    fn calc_stats(&self, gear: &Stats) -> Stats {
        let mut stats = &BASE_STATS + gear;

        // Rune of the Elementalist
        stats.power += 175.;
        stats.condition_damage += 225.;

        // Infusions

        // Trait: Empowering Flame (4/8 fire uptime)
        stats.condition_damage += 150. * 4. / 8.;
        // Trait: Burning Rage
        stats.condition_damage += 180.;
        // Trait: Elemental Enchantment
        stats.concentration += 180.;
        // Trait: Elemental Polyphony
        // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
        // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
        stats.power += 120. * 6. / 8.;
        stats.healing_power += 120. * 2. * 2. / 8.;
        stats.ferocity += 120. * 2. * 2. / 8.;
        stats.vitality += 120. * 2. * 4. / 8.;

        // Food
        stats.expertise += 100.;
        stats.condition_damage += 70.;

        // Utility
        stats.condition_damage += stats.power * 0.03;
        stats.condition_damage += stats.precision * 0.03;

        // Might
        stats.power += 12. * 30.;
        stats.condition_damage += 12. * 30.;

        stats
    }

    fn calc_modifiers(&self) -> Modifiers {
        let mut m = Modifiers::default();

        // Rune of the Elementalist
        m.condition_duration += 50.;

        // Sigil of Smoldering
        m.condition_duration.burn += 20.;

        // Fury +25%
        m.crit_chance += 0.1 * 25.;

        // Trait: Burning Precision
        m.condition_duration.burn += 20.;
        // Trait: Pyromancer's Training
        m.strike_damage += 10.;
        // Trait: Persisting Flames
        m.strike_damage += 15. / 16. * 10.;
        // Trait: Superior Elements
        m.crit_chance += 15.;
        // Trait: Weaver's Prowess
        m.condition_damage += 10.;
        m.condition_duration += 20.;

        // Woven Fire (1/3 uptime)
        m.condition_damage += 20. * 1./3.;

        m
    }

    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let min_healing_power = 0.;
        let min_concentration = 0.;

        if stats.healing_power < min_healing_power {
            return 2000. + min_healing_power - stats.healing_power;
        }

        if stats.concentration < min_concentration {
            return 1000. + min_concentration - stats.concentration;
        }

        let min_dps = 6900.;
        let dps = self.dps.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        -stats.healing_power
        //-dps
    }
}


fn main() {
    //let ch = CondiVirt::new();
    let ch = CairnSoloArcane::new();

    let slots = [
        (GearSlot::Weapon1H, Quality::Exotic),
        (GearSlot::Weapon1H, Quality::Exotic),
        (GearSlot::Helm, Quality::Exotic),
        (GearSlot::Shoulders, Quality::Exotic),
        (GearSlot::Coat, Quality::Exotic),
        (GearSlot::Gloves, Quality::Exotic),
        (GearSlot::Leggings, Quality::Exotic),
        (GearSlot::Boots, Quality::Exotic),
        (GearSlot::Amulet, Quality::Ascended),
        (GearSlot::Ring1, Quality::Exotic),
        (GearSlot::Ring2, Quality::Exotic),
        (GearSlot::Accessory1, Quality::Exotic),
        (GearSlot::Accessory2, Quality::Exotic),
        (GearSlot::Backpack, Quality::Exotic),
    ];
    let slots = [
        (GearSlot::Weapon1H, Quality::Ascended),
        (GearSlot::Weapon1H, Quality::Ascended),
        (GearSlot::Helm, Quality::Ascended),
        (GearSlot::Shoulders, Quality::Ascended),
        (GearSlot::Coat, Quality::Ascended),
        (GearSlot::Gloves, Quality::Ascended),
        (GearSlot::Leggings, Quality::Ascended),
        (GearSlot::Boots, Quality::Ascended),
        (GearSlot::Amulet, Quality::Ascended),
        (GearSlot::Ring1, Quality::Ascended),
        (GearSlot::Ring2, Quality::Ascended),
        (GearSlot::Accessory1, Quality::Ascended),
        (GearSlot::Accessory2, Quality::Ascended),
        (GearSlot::Backpack, Quality::Ascended),
    ];

    let w = optimize_coarse(&ch, &slots);

    let gear = calc_gear_stats(&w);
    //eprintln!("{:?}", gear.map(|_, x| x.round() as u32));
    let stats = ch.calc_stats(&gear);
    eprintln!("{:?}", stats.map(|_, x| x.round() as u32));
}
