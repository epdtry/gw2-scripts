#[macro_use] mod macros;

mod character;
mod gear;
mod optimize;
mod stats;

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};

pub use crate::character::{CharacterModel, Baseline, DpsModel, Effect, NoEffect};
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
    fn apply_effects(&self, stats: &mut Stats, mods: &mut Modifiers) {
        NoEffect
            // Rune of the Krait
            .chain_add_permanent(|s, m| {
                s.condition_damage += 175.;
                m.condition_duration.bleed += 50.;
            })
            // Sigil of Agony
            .chain_add_permanent(|_s, m| {
                m.condition_duration.bleed += 20.;
            })
            // Infusions
            .chain_add_permanent(|_s, _m| {
                //s.condition_damage += 16. * 5.;
                //s.precision += 2. * 5.;
            })
            // Food
            .chain_add_permanent(|s, _m| {
                s.precision += 100.;
                s.condition_damage += 70.;
            })
            // Utility
            .chain_distribute(|s, _m| {
                s.condition_damage += s.power * 0.03;
                s.condition_damage += s.precision * 0.03;
            })
            // Trait: Superiority Complex
            .chain_add_temporary(|_s, m| {
                m.crit_damage += 15.;
                // Further bonus against disabled (or defiant?) foes
                m.crit_damage += 10.;
            })
            // Trait: Compounding Power (1 stack)
            .chain_add_temporary(|s, m| {
                let strength = 1.;
                m.strike_damage += strength * 2.;
                s.condition_damage += strength * 30.;
            })
            // Trait: Deadly Blades (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 0.;
                m.strike_damage += strength * 5.;
                m.condition_damage += strength * 5.;
            })
            // Trait: Quiet Intensity
            .chain_distribute(|s, _m| {
                s.ferocity += s.vitality * 0.1;
                // Also affects fury
            })
            // Trait: Bloodsong
            .chain_add_permanent(|_s, m| {
                m.condition_damage.bleed += 25.;
            })
            // Might (25 stacks)
            .chain_add_temporary(|s, _m| {
                let strength = 25.;
                s.power += strength * 30.;
                s.condition_damage += strength * 30.;
            })
            // Fury (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1.0;
                m.crit_chance += strength * 25.;
                // Further bonus from Quiet Intensity
                m.crit_chance += strength * 15.;
            })
            // Signet of Domination
            .chain_add_temporary(|s, _m| {
                s.condition_damage += 180.;
            })
            // Signet of Midnight
            .chain_add_temporary(|s, _m| {
                s.expertise += 180.;
            })
            .apply(stats, mods);
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
    fn apply_effects(&self, stats: &mut Stats, mods: &mut Modifiers) {
        NoEffect

            // Rune of the Elementalist
            .chain_add_permanent(|s, m| {
                s.power += 175.;
                s.condition_damage += 225.;
                m.condition_duration += 10.;
            })
            // Sigil of Smoldering
            .chain_add_permanent(|_s, m| {
                m.condition_duration.burn += 20.;
            })
            // Infusions
            .chain_add_permanent(|_s, _m| {
                //s.condition_damage += 16. * 5.;
                //s.precision += 2. * 5.;
            })

            // Food
            .chain_add_permanent(|s, _m| {
                s.expertise += 100.;
                s.condition_damage += 70.;
            })
            // Utility
            .chain_distribute(|s, _m| {
                s.condition_damage += s.power * 0.03;
                s.condition_damage += s.precision * 0.03;
            })

            // Trait: Empowering Flame (4/8 fire uptime)
            .chain_add_temporary(|s, _m| {
                let strength = 4. / 8.;
                s.condition_damage += strength * 150.;
            })
            // Trait: Burning Precision
            .chain_add_permanent(|_s, m| {
                m.condition_duration.burn += 20.;
            })
            // Trait: Burning Rage
            .chain_add_permanent(|s, _m| {
                s.condition_damage += 180.;
            })
            // Trait: Pyromancer's Training (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1.;
                m.strike_damage += strength * 10.;
            })
            // Trait: Persisting Flames (9 stacks)
            .chain_add_temporary(|_s, m| {
                let strength = 9.;
                m.strike_damage += strength * 1.;
            })
            // Trait: Elemental Enchantment
            .chain_add_permanent(|s, _m| {
                s.concentration += 180.;
            })
            // Trait: Superior Elements (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1.;
                m.crit_chance += strength * 15.;
            })
            // Trait: Weaver's Prowess (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1.;
                m.condition_damage += strength * 10.;
                m.condition_duration += strength * 20.;
            })
            // Trait: Elemental Polyphony
            // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
            // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
            .chain_add_temporary(|s, _m| {
                s.power += 6. / 8. * 120.;
                s.healing_power += 2. / 8. * 120.;
                s.ferocity += 2. / 8. * 120.;
                s.vitality += 4. / 8. * 120.;
            })

            // Might (12 stacks)
            .chain_add_temporary(|s, _m| {
                let strength = 12.;
                s.power += strength * 30.;
                s.condition_damage += strength * 30.;
            })
            // Fury (10% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 0.1;
                m.crit_chance += strength * 25.;
            })
            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

            .apply(stats, mods);
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
    let ch = CondiVirt::new();
    //let ch = CairnSoloArcane::new();

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
    let _ = [
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
    let mut stats = BASE_STATS + gear;
    let mut mods = Modifiers::default();
    ch.apply_effects(&mut stats, &mut mods);
    eprintln!("{:?}", stats.map(|_, x| x.round() as u32));
}
