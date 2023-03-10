#[macro_use] mod macros;

mod character;
mod effect;
mod gear;
mod optimize;
mod stats;

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};

pub use crate::character::{CharacterModel, Baseline, DpsModel};
pub use crate::effect::{Effect, NoEffect, KnownRune, KnownSigil, KnownFood, KnownUtility};
pub use crate::effect::{food, utility, rune, sigil, boon};
pub use crate::gear::{PerGearSlot, GearSlot, PerQuality, Quality, SlotInfo, Prefix, StatFormula};
pub use crate::stats::{
    PerStat, Stat, Stats, BASE_STATS, Modifiers, PerCondition, PerBoon, Condition, Boon,
    HealthTier, ArmorWeight,
};
use crate::optimize::coarse::{optimize_coarse, calc_gear_stats};


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
}

impl CharacterModel for CairnSoloArcane {
    type Config = (KnownRune, KnownSigil, sigil::Battle, KnownFood, KnownUtility);

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

            .chain(boon::Might(12.))
            .chain(boon::Fury(0.1))

            // Infusions
            .chain_add_permanent(|_s, _m| {
                //s.condition_damage += 16. * 5.;
                //s.precision += 2. * 5.;
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

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

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

        let config_torment = (
            rune::Tormenting.into(),
            sigil::Bursting.into(),
            sigil::Torment,
            food::RedLentilSaobosa.as_known(),
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

        ch
    }
}

impl CharacterModel for CairnSoloAir {
    type Config = (KnownRune, KnownSigil, sigil::Torment, KnownFood, KnownUtility);

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

            //.chain(rune::Tormenting)
            .chain(sigil::Torment)
            //.chain(food::RedLentilSaobosa)
            //.chain(utility::ToxicCrystal)

            .chain(boon::Might(6.7))
            .chain(boon::Fury(0.75))

            // Infusions
            .chain_add_permanent(|_s, _m| {
                //s.condition_damage += 16. * 5.;
                //s.precision += 2. * 5.;
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

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        let mut dps = self.dps.clone();

        if config.0 != rune::Tormenting.into() {
            // Assume 3 seconds of regen per 6 seconds (5s ICD + 1s to get a crit)
            dps.boon_points.regeneration -= 0.5;
            if dps.boon_points.regeneration < 0. {
                dps.boon_points.regeneration = 0.;
            }
        }

        // Approximate heal per second from regen, glyph, and barrier
        let glyph_heal = 6494. + 1.2 * stats.healing_power;
        let stone_heal = (1069. + 0.15 * stats.healing_power) * 5.;
        let rock_heal = 1753. + 0.4 * stats.healing_power;
        let water_heal = 1832. + 1.0 * stats.healing_power;
        let dual_heal = 523. + 0.2875 * stats.healing_power;
        let regen_heal =
            dps.calc_boon_uptime(stats, mods, Boon::Regeneration) * stats.regen_heal(mods);
        let rotation_dur = 4.5 * 9.;
        let hps = regen_heal
            + glyph_heal / 16.
            + stone_heal / 50.
            + rock_heal * 2. / rotation_dur
            + water_heal * 2. / rotation_dur
            + dual_heal * 6. / rotation_dur
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

        let min_swiftness = 1.0;
        let swiftness = dps.calc_boon_uptime(stats, mods, Boon::Swiftness);
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


struct CairnSoloAirStaff {
    dps: DpsModel,
}

impl CairnSoloAirStaff {
    pub fn new() -> CairnSoloAirStaff {
        let mut ch = CairnSoloAirStaff {
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

        let config_torment = (
            rune::Tormenting.into(),
            sigil::Bursting.into(),
            sigil::Torment,
            food::RedLentilSaobosa.as_known(),
            utility::ToxicFocusingCrystal.into(),
        );

        // 2023-03-09, staff with double water
        ch.dps = DpsModel::new(&ch, Baseline {
            gear: gear_viper_seraph,
            config: config_torment,
            dps: 5489.,
            condition_percent: PerCondition {
                burn: 50.9,
                bleed: 11.6,
                torment: 11.5,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 243.,
                fury: 57.,
                regeneration: 0.,
                vigor: 0.,
                swiftness: 120.,
                .. 0.0.into()
            },
        });

        ch
    }
}

impl CharacterModel for CairnSoloAirStaff {
    type Config = (KnownRune, KnownSigil, sigil::Torment, KnownFood, KnownUtility);

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

            //.chain(rune::Tormenting)
            .chain(sigil::Torment)
            //.chain(food::RedLentilSaobosa)
            //.chain(utility::ToxicCrystal)

            .chain(boon::Might(2.5))
            .chain(boon::Fury(0.6))

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
            // Woven Air (1/4 uptime)
            .chain_add_temporary(|_s, m| {
                let strength = 1./4.;
                m.strike_damage += strength * 10.;
            })

            .apply(&mut stats, &mut mods);

        (stats, mods)
    }

    fn evaluate(&self, config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32 {
        let mut dps = self.dps.clone();

        // Approximate heal per second from regen, glyph, and barrier
        let regen_factor = stats.regen_heal(mods)
            * stats.boon_duration(mods, Boon::Regeneration) / 100.;
        let glyph_heal = 6494. + 1.2 * stats.healing_power;
        let stone_heal = (1069. + 0.15 * stats.healing_power) * 5.;
        let dual_heal = 523. + 0.2875 * stats.healing_power;
        let torment_hps = if config.0 == rune::Tormenting.into() {
            0.5 * regen_factor
        } else { 0. };
        let geyser_heal = 2760. + 2.0 * stats.healing_power;
        let rain_heal = 3. * 4. * regen_factor;
        let rotation_dur = 4. * 9.;
        let hps = 0.
            + torment_hps
            + glyph_heal / 16.
            + stone_heal / 50.
            + dual_heal * 6. / rotation_dur
            + geyser_heal / rotation_dur
            + rain_heal / rotation_dur
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

        let min_swiftness = 1.0;
        let swiftness = dps.calc_boon_uptime(stats, mods, Boon::Swiftness);
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
    let ch = CondiVirt::new();
    let ch = CairnSoloArcane::new();
    let ch = CairnSoloAir::new();
    //let ch = CairnSoloAirStaff::new();


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
    let (pw, config) = optimize_coarse(&ch, &slots);

    let gear = calc_gear_stats(&pw);
    let (stats, mods) = ch.calc_stats(&gear, &config);
    eprintln!("{:?}", stats.map(|_, x| x.round() as u32));
}
