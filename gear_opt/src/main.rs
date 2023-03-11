#[macro_use] mod macros;

mod character;
mod effect;
mod gear;
mod optimize;
mod stats;

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};

pub use crate::character::{CharacterModel, Baseline, DpsModel};
pub use crate::effect::{
    Effect, NoEffect, Rune, KnownRune, Sigil, KnownSigil, KnownFood, KnownUtility,
};
pub use crate::effect::{food, utility, rune, sigil, boon};
pub use crate::gear::{PerGearSlot, GearSlot, PerQuality, Quality, SlotInfo, Prefix, StatFormula};
pub use crate::stats::{
    PerStat, Stat, Stats, BASE_STATS, Modifiers, PerCondition, PerBoon, Condition, Boon,
    HealthTier, ArmorWeight,
};
use crate::optimize::coarse::{self, calc_gear_stats};
use crate::optimize::fine;


struct CondiVirt {
    dps: DpsModel,
}

impl CondiVirt {
    pub fn new() -> CondiVirt {
        let mut ch = CondiVirt {
            dps: DpsModel::zero(),
        };
        // The DPS model is produced by looking at arcdps results for a known build.
        ch.dps = DpsModel::new(&ch, Baseline {
            // `gear` gives the gear stats used for the baseline, as shown when mousing over the
            // gear tab in-game.  This does not include any runes, food, boons, etc, which are all
            // applied later.
            gear: Stats {
                power: 986.,
                precision: 981.,
                condition_damage: 1012.,
                expertise: 255.,
                .. Stats::default()
            },
            // `config` gives the `Character::Config` value that was used for the DPS baseline.
            config: (
                rune::Krait.into(),
                sigil::Agony.into(),
                sigil::Earth,
                food::FancyPotatoAndLeekSoup.into(),
                utility::ToxicFocusingCrystal.into(),
            ),
            // The overall DPS achieved with the baseline build.
            dps: 30063.,
            // What percent of the DPS came from each condition.  This can be found in the arcdps
            // detailed DPS report, which you can open by clicking on your name in the squad DPS
            // window.
            condition_percent: PerCondition {
                bleed: 59.9,
                torment: 10.3,
                confuse: 1.3,
                poison: 0.2,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                .. 0.0.into()
            },
        });
        ch
    }
}

impl CharacterModel for CondiVirt {
    type Config = (KnownRune, KnownSigil, sigil::Earth, KnownFood, KnownUtility);

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers) {
        let mut stats = &BASE_STATS + gear;
        let mut mods = Modifiers::default();

        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

            .chain(boon::Might(25.))
            // Fury (100% uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1.0;
                m.crit_chance += strength * 25.;
                // Further bonus from Quiet Intensity
                m.crit_chance += strength * 15.;
            })

            // Infusions
            .chain_add_permanent(|_s, _m| {
                //s.condition_damage += 16. * 5.;
                //s.precision += 2. * 5.;
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

            // Signet of Domination
            .chain_add_temporary(|s, _m| {
                s.condition_damage += 180.;
            })
            // Signet of Midnight
            .chain_add_temporary(|s, _m| {
                s.expertise += 180.;
            })

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, _config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        // Require 100% crit chance.  This is important for maximizing Jagged Mind procs, which the
        // DPS model doesn't reason about.
        let crit = stats.crit_chance(mods);
        if crit < 100. {
            return 1000. + 100. - crit;
        }

        // Optimize for DPS.
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
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: Stats {
                power: 824.,
                precision: 793.,
                condition_damage: 1173.,
                expertise: 444.,
                healing_power: 189.,
                concentration: 189.,
                .. Stats::default()
            },
            config: (
                rune::Elementalist.into(),
                sigil::Smoldering.into(),
                sigil::Battle.into(),
                food::RedLentilSaobosa.as_known(),
                utility::ToxicFocusingCrystal.into(),
            ),
            dps: 6708.,
            condition_percent: PerCondition {
                burn: 68.9,
                bleed: 10.3,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                .. 0.0.into()
            },
        });
        ch
    }

    const ROTATION_DUR: f32 = 4.5 * 8.;
    /// The rotation uses 6 dual skills per rotation.
    const DUAL_INTERVAL: f32 = Self::ROTATION_DUR / 6.;
}

impl CharacterModel for CairnSoloArcane {
    type Config = (Rune, Sigil, Sigil, KnownFood, KnownUtility);

    fn is_config_valid(&self, config: &Self::Config) -> bool {
        let (rune, sigil1, sigil2, _, _) = *config;


        if sigil1 == sigil2 && sigil1 != sigil::NoSigil.into() {
            return false;
        }

        cairn_solo_rune_valid(rune) &&
        cairn_solo_sigil_valid(sigil1) &&
        cairn_solo_sigil_valid(sigil2)
    }

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers) {
        let mut stats = &BASE_STATS + gear;
        let mut mods = Modifiers::default();

        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

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

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

            .chain_add_permanent(|s, m| {
                // Healing skill has a 20s cooldown.
                let healing_interval = 20.;
                let dual_interval = Self::DUAL_INTERVAL;
                cairn_solo_rune_effect(s, m, rune, healing_interval, dual_interval);
            })
            .chain_add_permanent(|s, m| {
                for &sigil in [sigil1, sigil2].iter() {
                    cairn_solo_sigil_effect(s, m, sigil);
                }
            })

            .chain(boon::Might(self.dps.boon_points.might))
            .chain(boon::Fury(self.dps.boon_points.fury))

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, _config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        // Require a certain amount of sustain.
        let min_healing_power = 0.;
        let min_concentration = 0.;

        if stats.healing_power < min_healing_power {
            return 2000. + min_healing_power - stats.healing_power;
        }

        if stats.concentration < min_concentration {
            return 1000. + min_concentration - stats.concentration;
        }

        // Require a certain amount of DPS.
        let min_dps = 0.;
        let dps = self.dps.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        // Optimize for DPS or for sustain.
        -dps
        //-stats.healing_power
    }
}


fn cairn_solo_rune_valid(rune: Rune) -> bool {
    match rune {
        Rune::Fireworks(_) => true,
        Rune::Pack(_) => true,
        Rune::Brawler(_) => true,
        Rune::Centaur(_) => true,
        Rune::Aristocracy(_) => true,
        s => s.is_known(),
    }
}

fn cairn_solo_rune_effect(
    s: &mut Stats,
    m: &mut Modifiers,
    rune: Rune,
    healing_interval: f32,
    dual_interval: f32,
) {
    // Healing skill has a 16s cooldown, after applying the reduction from the air
    // glyph trait.
    let healing_interval = 16.;

    match rune {
        Rune::Fireworks(_) => {
            // Procs once per 20 seconds while in combat.
            m.boon_points.might += 6. * 6. / 20.;
            m.boon_points.fury += 6. / 20.;
            m.boon_points.vigor += 6. / 20.;
        },
        Rune::Pack(_) => {
            // Procs once per 30 seconds while in combat.
            m.boon_points.might += 5. * 8. / 30.;
            m.boon_points.fury += 8. / 30.;
            m.boon_points.swiftness += 8. / 30.;
        },
        Rune::Brawler(_) => {
            // Procs on every healing skill.  Our healing skill has a 16s cooldown,
            // after applying the reduction from the air glyph trait.
            m.boon_points.might += 5. * 10. / 16.;
        },
        Rune::Centaur(_) => {
            // Procs on every healing skill.
            m.boon_points.swiftness += 10. / 16.;
        },
        Rune::Aristocracy(_) => {
            // Procs when applying weakness.
            m.boon_points.might += 5. * 4. / dual_interval;
        },
        _ => {},
    }
}

fn cairn_solo_sigil_valid(sigil: Sigil) -> bool {
    match sigil {
        Sigil::Blight(_) => true,
        Sigil::Earth(_) => true,
        Sigil::Torment(_) => true,
        Sigil::Strength(_) => true,
        Sigil::Agility(_) => true,
        Sigil::Battle(_) => true,
        Sigil::Doom(_) => true,
        s => s.is_known(),
    }
}

fn cairn_solo_sigil_effect(
    s: &mut Stats,
    m: &mut Modifiers,
    sigil: Sigil,
) {
    match sigil {
        Sigil::Blight(_) => {
            // Procs on crit; ICD: 8 seconds.
            m.condition_points.poison += 2. * 4. / 8.5;
        },
        Sigil::Earth(_) => {
            // Procs on crit; ICD: 2 seconds.
            m.condition_points.bleed += 6. / 2.5;
        },
        Sigil::Torment(_) => {
            // Procs on crit; ICD: 5 seconds.
            m.condition_points.torment += 2. * 5. / 5.5;
        },
        Sigil::Strength(_) => {
            // Procs on crit; ICD: 1 second.
            m.boon_points.might += 10. / 2.;
        },

        Sigil::Agility(_) => {
            // Procs on weapon/attunement swap; ICD: 9 seconds.
            m.boon_points.swiftness += 5. / 10.;
            m.boon_points.quickness += 1. / 10.;
        },
        Sigil::Battle(_) => {
            // Procs on weapon/attunement swap; ICD: 9 seconds.
            m.boon_points.might += 5. * 12. / 10.;
        },
        Sigil::Doom(_) => {
            // Procs on weapon/attunement swap; ICD: 9 seconds.
            m.condition_points.poison += 3. * 8. / 10.;
        },

        _ => {},
    }
}


struct CairnSoloAir {
    dps: DpsModel,
}

impl CairnSoloAir {
    pub fn new() -> CairnSoloAir {
        let mut ch = CairnSoloAir {
            dps: DpsModel::zero(),
        };

        let gear_viper_seraph = Stats {
            power: 824.,
            precision: 793.,
            condition_damage: 1173.,
            expertise: 444.,
            healing_power: 189.,
            concentration: 189.,
            .. Stats::default()
        };

        let gear_viper_apothecary = Stats {
            power: 770.,
            precision: 414.,
            condition_damage: 1103.,
            expertise: 414.,
            toughness: 333.,
            healing_power: 470.,
            .. Stats::default()
        };

        let config_torment: <Self as CharacterModel>::Config = (
            rune::Tormenting.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::RedLentilSaobosa.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        let config_torment_beef: <Self as CharacterModel>::Config = (
            rune::Tormenting.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::BeefRendang.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        /*
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: gear_viper_seraph,
            config: config_torment,
            dps: 8358.,
            condition_percent: PerCondition {
                burn: 60.61,
                bleed: 8.729,
                torment: 8.589,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 677.8,
                fury: 75.419,
                regeneration: 43.26,
                vigor: 25.868,
                swiftness: 89.016,
                .. 0.0.into()
            },
        });
        */

        /*
        // 2023-03-09, with water trident
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: gear_viper_seraph,
            config: config_torment,
            dps: 7844.,
            condition_percent: PerCondition {
                burn: 63.5,
                bleed: 6.1,
                torment: 8.3,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 525.,
                fury: 78.,
                regeneration: 54.,
                vigor: 30.,
                swiftness: 131.,
                .. 0.0.into()
            },
        });
        */

        // 2023-03-09, with water trident
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: gear_viper_apothecary,
            config: config_torment,
            dps: 7959.,
            condition_percent: PerCondition {
                burn: 64.3,
                bleed: 7.8,
                torment: 9.7,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 380.,
                fury: 66.,
                regeneration: 130.,
                vigor: 22.,
                swiftness: 107.,
                .. 0.0.into()
            },
        });

        ch
    }

    const ROTATION_DUR: f32 = 4.5 * 3.;
    /// The rotation uses one dual skill per rotation.
    const DUAL_INTERVAL: f32 = Self::ROTATION_DUR / 1.;
}

impl CharacterModel for CairnSoloAir {
    type Config = (Rune, Sigil, Sigil, KnownFood, KnownUtility);

    fn is_config_valid(&self, config: &Self::Config) -> bool {
        let (rune, sigil1, sigil2, _, _) = *config;


        if sigil1 == sigil2 && sigil1 != sigil::NoSigil.into() {
            return false;
        }

        cairn_solo_rune_valid(rune) &&
        cairn_solo_sigil_valid(sigil1) &&
        cairn_solo_sigil_valid(sigil2)
    }

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers) {
        let mut stats = &BASE_STATS + gear;
        let mut mods = Modifiers::default();

        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

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
            // Trait: Zephyr's Speed
            .chain_add_permanent(|_s, m| {
                m.crit_chance += 5.;
            })
            // Trait: Aeromancer's Training
            .chain_add_permanent(|s, _m| {
                s.ferocity += 150.;
                // Also adds +150 ferocity while attuned to air.
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

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

            .chain_add_permanent(|s, m| {
                // Healing skill has a 16s cooldown, after applying the reduction from the air
                // glyph trait.
                let healing_interval = 16.;
                let dual_interval = Self::DUAL_INTERVAL;
                cairn_solo_rune_effect(s, m, rune, healing_interval, dual_interval);
            })
            .chain_add_permanent(|s, m| {
                for &sigil in [sigil1, sigil2].iter() {
                    cairn_solo_sigil_effect(s, m, sigil);
                }
            })

            .chain(boon::Might(self.dps.boon_points.might))
            .chain(boon::Fury(self.dps.boon_points.fury))

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        let mut dps = self.dps.clone();

        let rotation_dur = Self::ROTATION_DUR;
        let dual_interval = Self::DUAL_INTERVAL;

        let (rune, sigil1, sigil2, _, _) = *config;

        // Approximate heal per second from regen, glyph, and barrier
        let glyph_heal = 6494. + 1.2 * stats.healing_power;
        let stone_heal = (1069. + 0.15 * stats.healing_power) * 5.;
        let rock_heal = 1753. + 0.4 * stats.healing_power;
        let water_heal = 1832. + 1.0 * stats.healing_power;
        let dual_heal = 523. + 0.2875 * stats.healing_power;
        let regen_heal =
            dps.calc_boon_uptime(stats, mods, Boon::Regeneration) * stats.regen_heal(mods);
        let hps = regen_heal
            + glyph_heal / 16.
            + stone_heal / 50.
            + rock_heal * 1. / rotation_dur
            + dual_heal / dual_interval
            ;

        let aura_dps = 3100000. / stats.armor(mods, ArmorWeight::Light) / 3.;
        //let aura_dps = 500.;
        let agony_dps = stats.max_health(mods, HealthTier::Low) * 0.10 / 3.;
        let hps_margin = 100.;

        //let min_hps = 0.;
        let min_hps = aura_dps + agony_dps + hps_margin;
        if hps < min_hps {
            return 30000. + min_hps - hps;
        }

        let min_swiftness = 1.05;
        let swiftness = dps.calc_boon_uptime_raw(stats, mods, Boon::Swiftness);
        if swiftness < min_swiftness {
            return 20000. + (min_swiftness - swiftness) * 100.;
        }

        // Require a certain amount of DPS.
        let min_dps = 0.;
        let dps = dps.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        // Optimize for DPS or for sustain.
        -dps
        //-(hps - agony_dps - aura_dps)
    }
}


struct CairnSoloEarth {
    dps: DpsModel,
}

impl CairnSoloEarth {
    pub fn new() -> CairnSoloEarth {
        let mut ch = CairnSoloEarth {
            dps: DpsModel::zero(),
        };

        let gear_viper_seraph = Stats {
            power: 824.,
            precision: 793.,
            condition_damage: 1173.,
            expertise: 444.,
            healing_power: 189.,
            concentration: 189.,
            .. Stats::default()
        };

        let gear_viper_celestial_apothecary = Stats {
            power: 770.,
            precision: 414.,
            condition_damage: 1103.,
            expertise: 414.,
            toughness: 333.,
            healing_power: 470.,
            .. Stats::default()
        };

        let config_torment: <Self as CharacterModel>::Config = (
            rune::Tormenting.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::RedLentilSaobosa.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        let config_torment_beef: <Self as CharacterModel>::Config = (
            rune::Tormenting.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::BeefRendang.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        let config_nightmare: <Self as CharacterModel>::Config = (
            rune::Nightmare.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::BeefRendang.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        let config_centaur: <Self as CharacterModel>::Config = (
            rune::Centaur.into(),
            sigil::Torment.into(),
            sigil::Bursting.into(),
            food::BeefRendang.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        // 2023-03-09
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: gear_viper_celestial_apothecary,
            config: config_centaur,
            dps: 7829.,
            condition_percent: PerCondition {
                burn: 66.6,
                bleed: 8.7,
                torment: 6.8,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 415.,
                fury: 0.,
                regeneration: 12.,
                vigor: 32.,
                swiftness: 68.,
                .. 0.0.into()
            },
        });

        eprintln!("{:#?}", ch.dps);
        ch.dps.boon_points.swiftness = 0.;

        ch
    }

    const ROTATION_DUR: f32 = 4.5 * 3.;
    /// The rotation uses one dual skill per rotation.
    const DUAL_INTERVAL: f32 = Self::ROTATION_DUR / 1.;
}

impl CharacterModel for CairnSoloEarth {
    type Config = (Rune, Sigil, Sigil, KnownFood, KnownUtility);

    fn is_config_valid(&self, config: &Self::Config) -> bool {
        let (rune, sigil1, sigil2, _, _) = *config;


        if sigil1 == sigil2 && sigil1 != sigil::NoSigil.into() {
            return false;
        }

        cairn_solo_rune_valid(rune) &&
        cairn_solo_sigil_valid(sigil1) &&
        cairn_solo_sigil_valid(sigil2)
    }

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers) {
        let mut stats = &BASE_STATS + gear;
        let mut mods = Modifiers::default();

        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

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
            // Trait: Strength of Stone
            .chain_distribute(|s, _m| {
                s.condition_damage += s.toughness * 0.10;
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

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

            .chain_add_permanent(|s, m| {
                // Healing skill has a 20s cooldown, after applying the reduction from the earth
                // signet trait.
                let healing_interval = 20.;
                let dual_interval = Self::DUAL_INTERVAL;
                cairn_solo_rune_effect(s, m, rune, healing_interval, dual_interval);
            })
            .chain_add_permanent(|s, m| {
                for &sigil in [sigil1, sigil2].iter() {
                    cairn_solo_sigil_effect(s, m, sigil);
                }
            })

            .chain(boon::Might(self.dps.boon_points.might))
            .chain(boon::Fury(self.dps.boon_points.fury))

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        let mut dps = self.dps.clone();

        let rotation_dur = Self::ROTATION_DUR;
        let dual_interval = Self::DUAL_INTERVAL;

        let (rune, sigil1, sigil2, _, _) = *config;

        // Approximate heal per second from regen, glyph, and barrier
        let signet_heal = 3275. + 0.5 * stats.healing_power;
        let signet_proc_heal = 202. + 0.1 * stats.healing_power;
        let stone_heal = (1069. + 0.15 * stats.healing_power) * 5.;
        let earth_heal = 1302. + 0.75 * stats.healing_power;
        let rock_heal = 1753. + 0.4 * stats.healing_power;
        let dual_heal = 523. + 0.2875 * stats.healing_power;
        let regen_heal =
            dps.calc_boon_uptime(stats, mods, Boon::Regeneration) * stats.regen_heal(mods);
        let hps = regen_heal
            + signet_heal / 16.
            + signet_proc_heal * 1.5
            + earth_heal / rotation_dur
            + stone_heal / 50.
            + rock_heal / rotation_dur
            + dual_heal / dual_interval
            ;

        let aura_dps = 3100000. / stats.armor(mods, ArmorWeight::Light) / 3.;
        //let aura_dps = 500.;
        let agony_dps = stats.max_health(mods, HealthTier::Low) * 0.10 / 3.;
        let hps_margin = 150.;

        //let min_hps = 0.;
        let min_hps = aura_dps + agony_dps + hps_margin;
        if hps < min_hps {
            return 30000. + min_hps - hps;
        }

        let min_swiftness = 1.05;
        let swiftness = dps.calc_boon_uptime_raw(stats, mods, Boon::Swiftness);
        if swiftness < min_swiftness {
            return 20000. + (min_swiftness - swiftness) * 100.;
        }

        // Require a certain amount of DPS.
        let min_dps = 0.;
        let dps = dps.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        // Optimize for DPS or for sustain.
        -dps
        //-(hps - agony_dps - aura_dps)
    }
}


fn main() {
    //let ch = CondiVirt::new();
    let ch = CairnSoloArcane::new();
    let ch = CairnSoloAir::new();
    //let ch = CairnSoloAirStaff::new();
    //let ch = CairnSoloEarth::new();


    // Slot quality configuration.  The last `let slots = ...` takes precedence.

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

    // Full ascended in every slot
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


    // Run the optimizer and report results
    //let (pw, cfg) = coarse::optimize_coarse(&ch, &slots);
    let (pw, cfg) = coarse::optimize_coarse_basin_hopping(&ch, &slots, Some(200));
    //let (pw, cfg) = coarse::optimize_coarse_randomized(&ch, &slots);

    let prefix_idxs = (0 .. NUM_PREFIXES).filter(|&i| pw[i] > 0.).collect::<Vec<_>>();
    eprintln!("running fine optimization with {} prefixes", prefix_idxs.len());
    let (slot_prefixes, infusions) = fine::optimize_fine(&ch, &cfg, &slots, &prefix_idxs);

    let mut gear = Stats::default();
    for (&(slot, quality), &prefix_idx) in slots.iter().zip(slot_prefixes.iter()) {
        eprintln!("{:?} = {}", slot, PREFIXES[prefix_idx].name);
        gear += GEAR_SLOTS[slot].calc_stats(&PREFIXES[prefix_idx], quality)
            .map(|_, x| x.round());
    }
    for stat in Stat::iter() {
        if infusions[stat] == 0 {
            continue;
        }
        eprintln!("infusion: {:?} = {}", stat, infusions[stat]);
        gear[stat] += 5. * infusions[stat] as f32;
    }

    //let gear = calc_gear_stats(&pw);
    eprintln!("{:?}", gear.map(|_, x| x.round() as u32));
    let (stats, mods) = ch.calc_stats(&gear, &cfg);
    eprintln!("{:?}", stats.map(|_, x| x.round() as u32));
    //eprintln!("{:#?}", mods);
}
