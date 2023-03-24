#[macro_use] mod macros;

mod character;
mod effect;
mod gear;
mod optimize;
mod stats;

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};

pub use crate::character::{CharacterModel, Baseline, DpsModel, CombatSecond, CombatEvent};
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

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond) {
        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

            .chain(boon::OldMight(25.))
            // Fury (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
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
            .chain_add_temporary(|_s, m, _c| {
                m.crit_damage += 15.;
                // Further bonus against disabled (or defiant?) foes
                m.crit_damage += 10.;
            })
            // Trait: Compounding Power (1 stack)
            .chain_add_temporary(|s, m, _c| {
                let strength = 1.;
                m.strike_damage += strength * 2.;
                s.condition_damage += strength * 30.;
            })
            // Trait: Deadly Blades (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
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
            .chain_add_temporary(|s, _m, _c| {
                s.condition_damage += 180.;
            })
            // Signet of Midnight
            .chain_add_temporary(|s, _m, _c| {
                s.expertise += 180.;
            })

            .apply(&BASE_STATS + gear, Modifiers::default(), CombatSecond::default())
    }

    fn evaluate(
        &self,
        _config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        _combat: &CombatSecond,
    ) -> f32 {
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

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond) {
        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

            // Trait: Empowering Flame (4/8 fire uptime)
            .chain_add_temporary(|s, _m, _c| {
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
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.strike_damage += strength * 10.;
            })
            // Trait: Persisting Flames (9 stacks)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 9.;
                m.strike_damage += strength * 1.;
            })
            // Trait: Elemental Enchantment
            .chain_add_permanent(|s, _m| {
                s.concentration += 180.;
            })
            // Trait: Superior Elements (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.crit_chance += strength * 15.;
            })
            // Trait: Weaver's Prowess (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.condition_damage += strength * 10.;
                m.condition_duration += strength * 20.;
            })
            // Trait: Elemental Polyphony
            // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
            // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
            .chain_add_temporary(|s, _m, _c| {
                s.power += 6. / 8. * 120.;
                s.healing_power += 2. / 8. * 120.;
                s.ferocity += 2. / 8. * 120.;
                s.vitality += 4. / 8. * 120.;
            })

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m, _c| {
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

            .chain(boon::OldMight(self.dps.boon_points.might))
            .chain(boon::OldFury(self.dps.boon_points.fury))

            .apply(&BASE_STATS + gear, Modifiers::default(), CombatSecond::default())
    }

    fn evaluate(
        &self,
        _config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        _combat: &CombatSecond,
    ) -> f32 {
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
        Rune::Tormenting(_) => true,
        Rune::Forgeman(_) => true,
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
            m.boon_points.might += 5. * 10. / healing_interval;
        },
        Rune::Centaur(_) => {
            // Procs on every healing skill.
            m.boon_points.swiftness += 10. / healing_interval;
        },
        Rune::Aristocracy(_) => {
            // Procs when applying weakness.
            m.boon_points.might += 5. * 4. / dual_interval;
        },
        // TODO: Tormenting
        _ => {},
    }
}

fn cairn_solo_sigil_valid(sigil: Sigil) -> bool {
    match sigil {
        Sigil::Blight(_) => true,
        Sigil::Blood(_) => true,
        Sigil::Earth(_) => true,
        Sigil::Strength(_) => true,
        Sigil::Torment(_) => true,

        Sigil::Agility(_) => true,
        Sigil::Battle(_) => true,
        Sigil::Doom(_) => true,
        Sigil::Leeching(_) => true,
        Sigil::Renewal(_) => true,

        Sigil::Frailty(_) => true,
        Sigil::Incapacitation(_) => true,

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
        // TODO: Blood
        Sigil::Earth(_) => {
            // Procs on crit; ICD: 2 seconds.
            m.condition_points.bleed += 6. / 2.5;
        },
        Sigil::Strength(_) => {
            // Procs on crit; ICD: 1 second.
            m.boon_points.might += 10. / 2.;
        },
        Sigil::Torment(_) => {
            // Procs on crit; ICD: 5 seconds.
            m.condition_points.torment += 2. * 5. / 5.5;
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
        // TODO: Leeching
        // TODO: Renewal

        // TODO: Frailty
        // TODO: Incapacitation

        _ => {},
    }
}


struct CairnSoloAir {
    base_combat: CombatSecond,
}

impl CairnSoloAir {
    pub fn new() -> CairnSoloAir {
        let mut ch = CairnSoloAir {
            base_combat: CombatSecond::default(),
        };

        // 2023-03-11
        let baseline = Baseline {
            gear: Stats {
                power: 606.,
                precision: 452.,
                toughness: 416.,
                healing_power: 579.,
                condition_damage: 1158.,
                expertise: 179.,
                .. Stats::default()
            },
            config: (
                rune::Baelfire.into(),
                sigil::Battle.into(),
                sigil::Torment.into(),
                food::RedLentilSaobosa.as_known(),
                utility::ToxicFocusingCrystal.into(),
            ),
            dps: 10586.,
            condition_percent: PerCondition {
                burn: 66.8,
                bleed: 8.3,
                torment: 6.1,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 950.,
                fury: 91.,
                swiftness: 112.,
                vigor: 36.,
                regeneration: 55.,
                .. 0.0.into()
            },
        };

        ch.base_combat = CombatSecond {
            strike: CombatEvent::new(1006. / 378., 0.),
            flanking: 0.23,
            cast: 1.2,

            .. CombatSecond::default()
        };
        ch.base_combat = baseline.update_base_combat(&ch, &ch.base_combat);

        eprintln!("{:#?}", ch.base_combat);

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

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond) {
        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

            // Trait: Empowering Flame (2/3 fire uptime)
            .chain_add_temporary(|s, _m, _c| {
                let strength = 2. / 3.;
                s.condition_damage += strength * 150.;
            })
            // Trait: Burning Precision
            .chain_add_permanent(|_s, m| {
                m.condition_duration.burn += 20.;
            })
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(5., evt.crit / 3.);
                c.condition.burn += CombatEvent::single(3.) * freq;
            })
            // Trait: Sunspot
            .chain_combat_procs(|evt, c| {
                c.aura += CombatEvent::single(3.) * 2. / Self::ROTATION_DUR;
            })
            // Trait: Burning Rage
            .chain_add_permanent(|s, _m| {
                s.condition_damage += 180.;
            })
            // Trait: Pyromancer's Training (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.strike_damage += strength * 10.;
            })
            // Trait: Persisting Flames (9 stacks)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 9.;
                m.strike_damage += strength * 1.;
            })

            // Trait: Zephyr's Speed
            .chain_add_permanent(|_s, m| {
                m.crit_chance += 5.;
            })
            // Trait: Zephyr's Boon
            .chain_combat_procs(|evt, c| {
                let freq = evt.aura.count;
                c.boon.fury += CombatEvent::single(5.) * freq;
                c.boon.swiftness += CombatEvent::single(5.) * freq;
            })
            // Trait: Inscription - handled in the rotation below
            // Trait: Aeromancer's Training
            .chain_add_permanent(|s, _m| {
                s.ferocity += 150.;
                // Also adds +150 ferocity while attuned to air.
            })
            // Trait: Bolt to the Heart - ignored, since it's hard to model when we only have
            // baselines from the first half of the fight.

            // Trait: Superior Elements (100% uptime)
            .chain_add_temporary(|s, m, c| {
                let strength = c.calc_condition_uptime(s, m, Condition::Weakness);
                m.crit_chance += strength * 15.;
            })
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(4., evt.cast_weaver_dual);
                c.condition.weakness += CombatEvent::single(5.) * freq;
            })
            // Trait: Elemental Refreshment
            .chain_combat_procs(|evt, c| {
                let freq = evt.cast_weaver_dual;
                c.heal_flat += CombatEvent::single(523.) * freq;
                c.heal += CombatEvent::single(0.2875) * freq;
            })
            // Trait: Weaver's Prowess (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.condition_damage += strength * 10.;
                m.condition_duration += strength * 20.;
            })
            // Trait: Elemental Polyphony
            // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
            // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
            .chain_add_temporary(|s, _m, _c| {
                s.power += 6. / 8. * 120.;
                s.healing_power += 2. / 8. * 120.;
                s.ferocity += 2. / 8. * 120.;
                s.vitality += 4. / 8. * 120.;
            })
            // Trait: Woven Stride
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(3., evt.boon.swiftness.count);
                c.boon.regeneration += CombatEvent::single(3.) * freq;
            })

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })

            // Rune and sigil procs
            .chain_combat_procs(|evt, c| {
                match rune {
                    Rune::Fireworks(_) => {
                        let freq = 1. / 20.;
                        c.boon.might += CombatEvent::single(6. * 6.) * freq;
                        c.boon.fury += CombatEvent::single(6.) * freq;
                        c.boon.vigor += CombatEvent::single(6.) * freq;
                    },
                    Rune::Pack(_) => {
                        let freq = 1. / 30.;
                        c.boon.might += CombatEvent::single(5. * 8.) * freq;
                        c.boon.fury += CombatEvent::single(8.) * freq;
                        c.boon.swiftness += CombatEvent::single(8.) * freq;
                    },
                    Rune::Brawler(_) => {
                        let freq = effect::proc_frequency(10., evt.cast_healing);
                        c.boon.might += CombatEvent::single(5. * 10.) * freq;
                    },
                    Rune::Centaur(_) => {
                        let freq = effect::proc_frequency(10., evt.cast_healing);
                        c.boon.swiftness += CombatEvent::single(10.) * freq;
                    },
                    Rune::Aristocracy(_) => {
                        let freq = effect::proc_frequency(1., evt.condition.weakness.count);
                        c.boon.might += CombatEvent::single(5. * 4.) * freq;
                    },
                    Rune::Tormenting(_) => {
                        let freq = effect::proc_frequency(5., evt.condition.torment.count);
                        c.boon.regeneration += CombatEvent::single(3.) * freq;
                    },
                    Rune::Forgeman(_) => {
                        // Procs when struck while below 75% health; ICD: 20 seconds.
                        let freq = 1. / 25.;
                        c.aura += CombatEvent::single(4.) * freq;
                    },
                    _ => {},
                }
            })

            .chain_combat_procs(|evt, c| {
                for &sigil in [sigil1, sigil2].iter() {
                    match sigil {
                        Sigil::Blight(_) => {
                            let freq = effect::proc_frequency(8., evt.crit);
                            c.condition.poison += CombatEvent::single(2. * 4.) * freq;
                        },
                        Sigil::Blood(_) => {
                            let freq = effect::proc_frequency(5., evt.crit);
                            c.strike_flat += CombatEvent::single(451.) * freq;
                            //c.strike += CombatEvent::single(0.75) * freq;
                            c.heal_flat += CombatEvent::single(453.) * freq;
                            c.heal += CombatEvent::single(0.1) * freq;
                        },
                        Sigil::Earth(_) => {
                            let freq = effect::proc_frequency(2., evt.crit);
                            c.condition.bleed += CombatEvent::single(6.) * freq;
                        },
                        Sigil::Strength(_) => {
                            let freq = effect::proc_frequency(1., evt.crit);
                            c.boon.might += CombatEvent::single(10.) * freq;
                        },
                        Sigil::Torment(_) => {
                            let freq = effect::proc_frequency(5., evt.crit);
                            c.condition.bleed += CombatEvent::single(2. * 5.) * freq;
                        },

                        Sigil::Agility(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.boon.swiftness += CombatEvent::single(5.) * freq;
                            c.boon.quickness += CombatEvent::single(1.) * freq;
                        },
                        Sigil::Battle(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.boon.might += CombatEvent::single(5. * 12.) * freq;
                        },
                        Sigil::Doom(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.condition.poison += CombatEvent::single(3. * 8.) * freq;
                        },
                        Sigil::Leeching(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.strike_flat += CombatEvent::single(975.) * freq;
                            c.heal_flat += CombatEvent::single(975.) * freq;
                        },
                        Sigil::Renewal(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.heal_flat += CombatEvent::single(345.) * freq;
                            c.heal += CombatEvent::single(0.4) * freq;
                        },

                        Sigil::Frailty(_) => {
                            let freq = effect::proc_frequency(2., evt.flanking);
                            c.condition.vulnerable += CombatEvent::single(2. * 8.) * freq;
                        },
                        Sigil::Incapacitation(_) => {
                            let freq = effect::proc_frequency(5., evt.flanking);
                            c.condition.cripple += CombatEvent::single(2.) * freq;
                        },

                        _ => {},
                    }
                }
            })

            // Important rotation skills
            .chain_combat_procs(|evt, c| {
                // Weapon/attunement swap
                c.weapon_swap += 1. / 4.5;

                // Fire Shield (fire 5)
                c.aura += CombatEvent::single(4.) / 20.;

                // Phoenix (fire 3)
                c.boon.vigor += CombatEvent::single(5.) / Self::ROTATION_DUR;

                // Rock Barrier (earth 2)
                c.heal_flat += CombatEvent::single(1735.) / Self::ROTATION_DUR;
                c.heal += CombatEvent::single(0.4) / Self::ROTATION_DUR;
                c.boon.resistance += CombatEvent::single(4.) / Self::ROTATION_DUR;

                // Dual attacks
                c.cast_weaver_dual += 1. / Self::ROTATION_DUR;

                // Glyph of Elemental Harmony (healing skill)
                // Cooldown is 16s due to inscription trait.
                let freq = 1. / 16.;
                c.cast_healing += freq;
                c.heal_flat += CombatEvent::single(6494.) * freq;
                c.heal += CombatEvent::single(1.2) * freq;
                // Assume we usually use the heal in fire attunement
                c.boon.might += CombatEvent::single(3. * 20.) * freq;
                // Additional might from the Inscription trait
                c.boon.might += CombatEvent::single(10.) * freq;
                // Assume we use the heal in air attunement 1/4 of the time
                //c.boon.swiftness += CombatEvent::single(10.) * freq * 0.25;
                //c.boon.swiftness += CombatEvent::single(10.) * freq * 0.25;

                // Stone Resonance
                c.heal_flat += CombatEvent::single(1069.) * 5. / 50.;
                c.heal += CombatEvent::single(0.15) * 5. / 50.;
                c.boon.stability += CombatEvent::single(5.) / 50.;
            })

            .chain(boon::Might)
            .chain(boon::Fury)

            .apply(&BASE_STATS + gear, Modifiers::default(), self.base_combat)
    }

    fn evaluate(
        &self,
        _config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        combat: &CombatSecond,
    ) -> f32 {
        let rotation_dur = Self::ROTATION_DUR;
        let dual_interval = Self::DUAL_INTERVAL;

        // Approximate heal per second from regen, glyph, and barrier
        let hps = combat.calc_heal_per_second(stats, mods);

        let aura_dps = 3100000. / stats.armor(mods, ArmorWeight::Light) / 3. *
            stats.incoming_strike_damage_multiplier(mods);
        //let aura_dps = 500.;
        let agony_dps = stats.max_health(mods, HealthTier::Low) * 0.10 / 3.;
        let hps_margin = 50.;

        //let min_hps = 0.;
        let min_hps = aura_dps + agony_dps + hps_margin;
        if hps < min_hps {
            return 30000. + min_hps - hps;
        }

        let min_swiftness = 1.05;
        let swiftness = combat.calc_boon_uptime_raw(stats, mods, Boon::Swiftness);
        if swiftness < min_swiftness {
            return 20000. + (min_swiftness - swiftness) * 100.;
        }

        // Require a certain amount of DPS.
        let min_dps = 0.;
        let dps = combat.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        // Optimize for DPS or for sustain.
        -dps
        //-(hps - agony_dps - aura_dps)
    }
}


struct CairnSoloEarth {
    base_combat: CombatSecond,
}

impl CairnSoloEarth {
    pub fn new() -> CairnSoloEarth {
        let mut ch = CairnSoloEarth {
            base_combat: CombatSecond::default(),
        };

        // 2023-03-12
        let baseline = Baseline {
            gear: Stats {
                power: 860.,
                precision: 612.,
                toughness: 365.,
                vitality: 331.,
                ferocity: 331.,
                healing_power: 378.,
                condition_damage: 894.,
                concentration: 331.,
                expertise: 612.,
            },
            config: (
                rune::Pack.into(),
                sigil::Agility.into(),
                sigil::Strength.into(),
                food::FireMeatChili.into(),
                utility::ToxicFocusingCrystal.into(),
            ),
            dps: 10094.,
            condition_percent: PerCondition {
                burn: 68.4,
                bleed: 9.8,
                .. 0.0.into()
            },
            boon_uptime: PerBoon {
                might: 1309.,
                fury: 40.,
                swiftness: 113.,
                vigor: 50.,
                regeneration: 47.,
                .. 0.0.into()
            },
        };

        ch.base_combat = CombatSecond {
            strike: CombatEvent::new(1093. / 398., 0.),
            flanking: 0.223,
            cast: 1.2,

            .. CombatSecond::default()
        };
        ch.base_combat = baseline.update_base_combat(&ch, &ch.base_combat);

        eprintln!("{:#?}", ch.base_combat);

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

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond) {
        let (rune, sigil1, sigil2, food, utility) = *config;

        NoEffect
            .chain(rune)
            .chain(sigil1)
            .chain(sigil2)
            .chain(food)
            .chain(utility)

            // Trait: Empowering Flame (2/3 fire uptime)
            .chain_add_temporary(|s, _m, _c| {
                let strength = 2. / 3.;
                s.condition_damage += strength * 150.;
            })
            // Trait: Burning Precision
            .chain_add_permanent(|_s, m| {
                m.condition_duration.burn += 20.;
            })
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(5., evt.crit / 3.);
                c.condition.burn += CombatEvent::single(3.) * freq;
            })
            // Trait: Sunspot
            .chain_combat_procs(|evt, c| {
                c.aura += CombatEvent::single(3.) * 2. / Self::ROTATION_DUR;
            })
            // Trait: Burning Rage
            .chain_add_permanent(|s, _m| {
                s.condition_damage += 180.;
            })
            // Trait: Pyromancer's Training (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.strike_damage += strength * 10.;
            })
            // Trait: Persisting Flames (9 stacks)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 9.;
                m.strike_damage += strength * 1.;
            })

            // Trait: Stone Flesh
            .chain_distribute(|_s, m| {
                m.incoming_strike_damage_reduction += 7.;
            })
            // Trait: Earth's Embrace
            .chain_combat_procs(|evt, c| {
                c.heal_flat += CombatEvent::single(1302.) / Self::ROTATION_DUR;
                c.heal += CombatEvent::single(0.75) / Self::ROTATION_DUR;
            })
            // Trait: Strength of Stone
            .chain_distribute(|s, _m| {
                s.condition_damage += s.toughness * 0.10;
            })
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(3., evt.condition.immobilize.count);
                c.condition.bleed += CombatEvent::single(3. * 10.) * freq;
            })

            // Trait: Superior Elements (100% uptime)
            .chain_add_temporary(|s, m, c| {
                let strength = c.calc_condition_uptime(s, m, Condition::Weakness);
                m.crit_chance += strength * 15.;
            })
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(4., evt.cast_weaver_dual);
                c.condition.weakness += CombatEvent::single(5.) * freq;
            })
            // Trait: Elemental Refreshment
            .chain_combat_procs(|evt, c| {
                let freq = evt.cast_weaver_dual;
                c.heal_flat += CombatEvent::single(523.) * freq;
                c.heal += CombatEvent::single(0.2875) * freq;
            })
            // Trait: Weaver's Prowess (100% uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1.;
                m.condition_damage += strength * 10.;
                m.condition_duration += strength * 20.;
            })
            // Trait: Elemental Polyphony
            // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
            // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
            .chain_add_temporary(|s, _m, _c| {
                s.power += 6. / 8. * 120.;
                s.healing_power += 2. / 8. * 120.;
                s.ferocity += 2. / 8. * 120.;
                s.vitality += 4. / 8. * 120.;
            })
            // Trait: Woven Stride
            .chain_combat_procs(|evt, c| {
                let freq = effect::proc_frequency(3., evt.boon.swiftness.count);
                c.boon.regeneration += CombatEvent::single(3.) * freq;
            })

            // Woven Fire (1/3 uptime)
            .chain_add_temporary(|_s, m, _c| {
                let strength = 1./3.;
                m.condition_damage += strength * 20.;
            })
            // Signet of Fire (passive)
            .chain_add_temporary(|s, _m, _c| {
                s.precision += 180.;
            })

            // Rune and sigil procs
            .chain_combat_procs(|evt, c| {
                match rune {
                    Rune::Fireworks(_) => {
                        let freq = 1. / 20.;
                        c.boon.might += CombatEvent::single(6. * 6.) * freq;
                        c.boon.fury += CombatEvent::single(6.) * freq;
                        c.boon.vigor += CombatEvent::single(6.) * freq;
                    },
                    Rune::Pack(_) => {
                        let freq = 1. / 30.;
                        c.boon.might += CombatEvent::single(5. * 8.) * freq;
                        c.boon.fury += CombatEvent::single(8.) * freq;
                        c.boon.swiftness += CombatEvent::single(8.) * freq;
                    },
                    Rune::Brawler(_) => {
                        let freq = effect::proc_frequency(10., evt.cast_healing);
                        c.boon.might += CombatEvent::single(5. * 10.) * freq;
                    },
                    Rune::Centaur(_) => {
                        let freq = effect::proc_frequency(10., evt.cast_healing);
                        c.boon.swiftness += CombatEvent::single(10.) * freq;
                    },
                    Rune::Aristocracy(_) => {
                        let freq = effect::proc_frequency(1., evt.condition.weakness.count);
                        c.boon.might += CombatEvent::single(5. * 4.) * freq;
                    },
                    Rune::Tormenting(_) => {
                        let freq = effect::proc_frequency(5., evt.condition.torment.count);
                        c.boon.regeneration += CombatEvent::single(3.) * freq;
                    },
                    Rune::Forgeman(_) => {
                        // Procs when struck while below 75% health; ICD: 20 seconds.
                        let freq = 1. / 25.;
                        c.aura += CombatEvent::single(4.) * freq;
                    },
                    _ => {},
                }
            })

            .chain_combat_procs(|evt, c| {
                for &sigil in [sigil1, sigil2].iter() {
                    match sigil {
                        Sigil::Blight(_) => {
                            let freq = effect::proc_frequency(8., evt.crit);
                            c.condition.poison += CombatEvent::single(2. * 4.) * freq;
                        },
                        Sigil::Blood(_) => {
                            let freq = effect::proc_frequency(5., evt.crit);
                            c.strike_flat += CombatEvent::single(451.) * freq;
                            //c.strike += CombatEvent::single(0.75) * freq;
                            c.heal_flat += CombatEvent::single(453.) * freq;
                            c.heal += CombatEvent::single(0.1) * freq;
                        },
                        Sigil::Earth(_) => {
                            let freq = effect::proc_frequency(2., evt.crit);
                            c.condition.bleed += CombatEvent::single(6.) * freq;
                        },
                        Sigil::Strength(_) => {
                            let freq = effect::proc_frequency(1., evt.crit);
                            c.boon.might += CombatEvent::single(10.) * freq;
                        },
                        Sigil::Torment(_) => {
                            let freq = effect::proc_frequency(5., evt.crit);
                            c.condition.bleed += CombatEvent::single(2. * 5.) * freq;
                        },

                        Sigil::Agility(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.boon.swiftness += CombatEvent::single(5.) * freq;
                            c.boon.quickness += CombatEvent::single(1.) * freq;
                        },
                        Sigil::Battle(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.boon.might += CombatEvent::single(5. * 12.) * freq;
                        },
                        Sigil::Doom(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.condition.poison += CombatEvent::single(3. * 8.) * freq;
                        },
                        Sigil::Leeching(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.strike_flat += CombatEvent::single(975.) * freq;
                            c.heal_flat += CombatEvent::single(975.) * freq;
                        },
                        Sigil::Renewal(_) => {
                            let freq = effect::proc_frequency(9., evt.weapon_swap);
                            c.heal_flat += CombatEvent::single(345.) * freq;
                            c.heal += CombatEvent::single(0.4) * freq;
                        },

                        Sigil::Frailty(_) => {
                            let freq = effect::proc_frequency(2., evt.flanking);
                            c.condition.vulnerable += CombatEvent::single(2. * 8.) * freq;
                        },
                        Sigil::Incapacitation(_) => {
                            let freq = effect::proc_frequency(5., evt.flanking);
                            c.condition.cripple += CombatEvent::single(2.) * freq;
                        },

                        _ => {},
                    }
                }
            })

            // Important rotation skills
            .chain_combat_procs(|evt, c| {
                // Weapon/attunement swap
                c.weapon_swap += 1. / 4.5;

                // Fire Shield (fire 5)
                c.aura += CombatEvent::single(4.) / 20.;

                // Phoenix (fire 3)
                c.boon.vigor += CombatEvent::single(5.) / Self::ROTATION_DUR;

                // Rock Barrier (earth 2)
                c.heal_flat += CombatEvent::single(1735.) / Self::ROTATION_DUR;
                c.heal += CombatEvent::single(0.4) / Self::ROTATION_DUR;
                c.boon.resistance += CombatEvent::single(4.) / Self::ROTATION_DUR;

                // Dual attacks
                c.cast_weaver_dual += 1. / Self::ROTATION_DUR;

                // Signet of Restoration (healing skill)
                // Active:
                {
                    let freq = 1. / 20.;
                    c.cast_healing += freq;
                    c.heal_flat += CombatEvent::single(3275.) * freq;
                    c.heal += CombatEvent::single(0.5) * freq;
                }
                // Passive:
                {
                    let freq = evt.cast;
                    c.heal_flat += CombatEvent::single(202.) * freq;
                    c.heal += CombatEvent::single(0.1) * freq;
                }

                // Stone Resonance
                c.heal_flat += CombatEvent::single(1069.) * 5. / 50.;
                c.heal += CombatEvent::single(0.15) * 5. / 50.;
                c.boon.stability += CombatEvent::single(5.) / 50.;
            })

            .chain(boon::Might)
            .chain(boon::Fury)

            .apply(&BASE_STATS + gear, Modifiers::default(), self.base_combat)
    }

    fn evaluate(
        &self,
        _config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        combat: &CombatSecond,
    ) -> f32 {
        let rotation_dur = Self::ROTATION_DUR;
        let dual_interval = Self::DUAL_INTERVAL;

        // Approximate heal per second from regen, glyph, and barrier
        let hps = combat.calc_heal_per_second(stats, mods);

        let aura_dps = 3100000. / stats.armor(mods, ArmorWeight::Light) / 3. *
            stats.incoming_strike_damage_multiplier(mods);
        //let aura_dps = 500.;
        let agony_dps = stats.max_health(mods, HealthTier::Low) * 0.10 / 3.;
        let hps_margin = 100.;

        //let min_hps = 0.;
        let min_hps = aura_dps + agony_dps + hps_margin;
        if hps < min_hps {
            return 30000. + min_hps - hps;
        }

        /*
        let min_healing_power = 500.;
        if stats.healing_power < min_healing_power {
            return 30000. + min_healing_power - stats.healing_power;
        }
        */

        let min_swiftness = 1.05;
        let swiftness = combat.calc_boon_uptime_raw(stats, mods, Boon::Swiftness);
        if swiftness < min_swiftness {
            return 20000. + (min_swiftness - swiftness) * 100.;
        }

        // Require a certain amount of DPS.
        let min_dps = 0.;
        let dps = combat.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        // Optimize for DPS or for sustain.
        -dps
        //-(hps - agony_dps - aura_dps)
    }
}


struct MechTank;

impl CharacterModel for MechTank {
    type Config = (
        rune::Monk,
        sigil::Paralyzation,
        sigil::Transference,
        food::FruitSaladWithMintGarnish,
        utility::BountifulMaintenanceOil,
    );

    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond) {
        (&BASE_STATS + gear, Modifiers::default(), CombatSecond::default())
    }

    fn evaluate(
        &self,
        _config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        _combat: &CombatSecond,
    ) -> f32 {
        let min_healing_power = 961. * 0.9;
        let min_concentration = 961. * 0.9;

        if stats.healing_power < min_healing_power {
            return 20000. + (min_healing_power - stats.healing_power);
        }

        if stats.concentration < min_concentration {
            return 20000. + (min_concentration - stats.concentration);
        }

        let armor = stats.armor(mods, ArmorWeight::Medium);
        let base_armor = ArmorWeight::Medium.base_armor() + BASE_STATS.toughness;
        let hp = stats.max_health(mods, HealthTier::Mid);
        let effective_hp = hp * armor / base_armor;
        return -effective_hp;
    }
}


fn main() {
    //let ch = CondiVirt::new();
    let ch = CairnSoloArcane::new();
    let ch = CairnSoloAir::new();
    //let ch = CairnSoloAirStaff::new();
    //let ch = CairnSoloEarth::new();
    //let ch = MechTank;


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
    let (pw, cfg) = coarse::optimize_coarse_basin_hopping(&ch, &slots, Some(300));
    //let (pw, cfg) = coarse::optimize_coarse_randomized(&ch, &slots);

    fn print_coarse_prefix_weights(pw: &coarse::PrefixWeights) {
        let mut lines = pw.iter().zip(PREFIXES.iter()).filter_map(|(&w, prefix)| {
            if w > 0.0 { Some((w, prefix.name)) } else { None }
        }).collect::<Vec<_>>();
        lines.sort_by_key(|&(w, _)| optimize::AssertTotal(-w));
        for (w, name) in lines {
            println!("{} = {}", name, w);
        }
    }

    const OPTIMIZE_FINE: bool = true;
    let gear = if OPTIMIZE_FINE {
        let prefix_idxs = (0 .. NUM_PREFIXES).filter(|&i| pw[i] > 0.).collect::<Vec<_>>();
        eprintln!("running fine optimization with {} prefixes", prefix_idxs.len());
        let (slot_prefixes, infusions) = fine::optimize_fine(
            &ch, &cfg, &slots, &prefix_idxs, Some(&pw));

        /*
        let prefix_idxs = (0 .. NUM_PREFIXES).filter(|&i| match PREFIXES[i].name {
            "Viper's" | "Celestial" | "Sinister" | "Seraph" | "Apothecary's" => true,
            _ => false,
        }).collect::<Vec<_>>();
        let (slot_prefixes, infusions) = fine::optimize_fine(
            &ch, &cfg, &slots, &prefix_idxs, None);
        */

        println!("\nfinal build:");
        print_coarse_prefix_weights(&pw);
        println!();

        let mut gear = Stats::default();
        for (&(slot, quality), &prefix_idx) in slots.iter().zip(slot_prefixes.iter()) {
            println!("{:?} = {}", slot, PREFIXES[prefix_idx].name);
            gear += GEAR_SLOTS[slot].calc_stats(&PREFIXES[prefix_idx], quality)
                .map(|_, x| x.round());
        }
        for stat in Stat::iter() {
            if infusions[stat] == 0 {
                continue;
            }
            println!("infusion: {:?} = {}", stat, infusions[stat]);
            gear[stat] += 5. * infusions[stat] as f32;
        }

        gear
    } else {
        println!("\nfinal build:");
        print_coarse_prefix_weights(&pw);
        calc_gear_stats(&pw)
    };

    let (rune, sigil1, sigil2, food, utility) = cfg;
    println!("rune = {}", rune.display_name());
    println!("sigil1 = {}", sigil1.display_name());
    println!("sigil2 = {}", sigil2.display_name());
    println!("food = {}", food.display_name());
    println!("utility = {}", utility.display_name());

    println!("\ngear stats = {:?}", gear.map(|_, x| x.round() as u32));
    let (stats, mods, combat) = ch.calc_stats(&gear, &cfg);
    println!("total stats = {:?}", stats.map(|_, x| x.round() as u32));
    let m = ch.evaluate(&cfg, &stats, &mods, &combat);
    println!("metric = {}", m);
    //eprintln!("combat = {:#?}", combat);
    eprintln!("dps = {}", combat.calc_dps(&stats, &mods));
    eprintln!("hps = {}", combat.calc_heal_per_second(&stats, &mods));
    eprintln!("might = {}", combat.calc_boon_uptime_raw(&stats, &mods, Boon::Might));
    eprintln!("swiftness = {}", combat.calc_boon_uptime_raw(&stats, &mods, Boon::Swiftness));
}
