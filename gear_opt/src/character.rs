use std::fmt;
use std::ops::{Add, AddAssign, Sub, SubAssign, Mul, MulAssign, Div, DivAssign};
use crate::stats::{Stats, Modifiers, Condition, PerCondition, Boon, PerBoon};

/// `CharacterModel` describes a build to be optimized.
pub trait CharacterModel {
    type Config: Vary + Clone + Default + fmt::Debug;

    /// Check whether a configuration is valid.  If this returns `false`, the optimizer will not
    /// try evaluating the config.
    fn is_config_valid(&self, config: &Self::Config) -> bool { true }

    /// Calculate stats, modifiers, and combat effects for a set of `gear` and `config`.
    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers, CombatSecond);

    /// Evaluate the quality of particular `stats` and `mods` values for this build.  The optimizer
    /// tries to minimize this function, so smaller is better.  This means DPS builds should
    /// generally return `-dps` rather than `dps`.  This captures the goals we're optimizing for
    /// with this build.
    fn evaluate(
        &self,
        config: &Self::Config,
        stats: &Stats,
        mods: &Modifiers,
        combat: &CombatSecond,
    ) -> f32;
}

/// An aspect of the character model that can vary, aside from the gear prefix selection.
pub trait Vary {
    fn num_fields(&self) -> usize;
    fn num_field_values(&self, field: usize) -> u16;
    fn get_field(&self, field: usize) -> u16;
    fn set_field(&mut self, field: usize, value: u16);
}

macro_rules! impl_vary_for_tuple {
    ($($I:tt $A:ident),*) => {
        #[allow(unused)]
        impl<$($A: Vary + 'static,)*> Vary for ($($A,)*) {
            fn num_fields(&self) -> usize {
                0
                    $( + self.$I.num_fields() )*
            }

            fn num_field_values(&self, field: usize) -> u16 {
                let mut field = field;
                $(
                    if field < self.$I.num_fields() {
                        return self.$I.num_field_values(field);
                    } else {
                        field -= self.$I.num_fields();
                    }
                )*
                unreachable!()
            }

            fn get_field(&self, field: usize) -> u16 {
                let mut field = field;
                $(
                    if field < self.$I.num_fields() {
                        return self.$I.get_field(field);
                    } else {
                        field -= self.$I.num_fields();
                    }
                )*
                unreachable!()
            }

            fn set_field(&mut self, field: usize, value: u16) {
                let mut field = field;
                $(
                    if field < self.$I.num_fields() {
                        return self.$I.set_field(field, value);
                    } else {
                        field -= self.$I.num_fields();
                    }
                )*
                unreachable!()
            }
        }
    };
}

impl_vary_for_tuple!();
impl_vary_for_tuple!(0 A);
impl_vary_for_tuple!(0 A, 1 B);
impl_vary_for_tuple!(0 A, 1 B, 2 C);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G, 7 H);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G, 7 H, 8 I);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G, 7 H, 8 I, 9 J);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G, 7 H, 8 I, 9 J, 10 K);
impl_vary_for_tuple!(0 A, 1 B, 2 C, 3 D, 4 E, 5 F, 6 G, 7 H, 8 I, 9 J, 10 K, 11 L);


#[derive(Clone, Debug)]
pub struct Baseline<C> {
    pub gear: Stats,
    pub config: C,
    pub dps: f32,
    pub condition_percent: PerCondition<f32>,
    /// Uptime of each boon, in percent.  For multi-stack boons like might, this is the average
    /// number of stacks times 100.
    pub boon_uptime: PerBoon<f32>,
}

impl<C> Baseline<C> {
    /// Update the `strike`, `condition`, and `boon` parts of `base_combat` based on the values in
    /// this `Baseline`.
    pub fn update_base_combat(
        &self,
        ch: &impl CharacterModel<Config = C>,
        base_combat: &CombatSecond,
    ) -> CombatSecond
    where C: Vary + Clone + Default + fmt::Debug {
        let (stats, mods, combat) = ch.calc_stats(&self.gear, &self.config);
        // `combat` gives the total combat effects supplied by the gear and config, plus whatever
        // is currently in `ch.base_combat`.

        // `ch` should not be using the old `Modifiers` condition/boon points system.
        assert_eq!(mods.condition_points, 0.0.into());
        assert_eq!(mods.boon_points, 0.0.into());

        let total_dps = self.dps;

        let strike_percent = 100. - self.condition_percent.sum();
        let strike_dps = total_dps * strike_percent / 100.;
        let strike_points = strike_dps / stats.strike_factor(&mods);

        let condition_percent = self.condition_percent;
        let condition_points = PerCondition::from_fn(|condi| {
            if condi.does_damage() {
                let percent = condition_percent[condi];
                let dps = total_dps * percent / 100.;
                let points = dps / stats.condition_factor(&mods, condi);
                points
            } else {
                // TODO
                0.
            }
        });

        let boon_uptime = self.boon_uptime;
        let boon_points = PerBoon::from_fn(|boon| {
            let points = boon_uptime[boon] / stats.boon_duration(&mods, boon);
            points
        });

        // Calculate how many strike, condition, and boon points came from the rotation, as opposed
        // to gear.
        let rotation_strike_points = strike_points - combat.strike.magnitude;
        let rotation_condition_points = condition_points - combat.condition.map(|condi, e| {
            if condi.does_damage() {
                e.magnitude
            } else {
                // TODO: need to include non-damaging conditions in `condition_points` first
                0.
            }
        });
        let rotation_boon_points = boon_points - combat.boon.map(|_, e| e.magnitude);

        CombatSecond {
            // This is a hack, since we don't know the actual number of strike hits per second.
            strike: CombatEvent::new(1., base_combat.strike.magnitude + rotation_strike_points),
            condition: base_combat.condition + rotation_condition_points.map(|condi, x| {
                CombatEvent::new(x / 5., x)
            }),
            boon: base_combat.boon + rotation_boon_points.map(|condi, x| {
                CombatEvent::new(x / 5., x)
            }),
            .. *base_combat
        }
    }
}

#[derive(Clone, Debug)]
pub struct DpsModel {
    /// Strike points per second.  One strike point is one 100-damage attack at 1000 power.
    pub strike_points: f32,
    /// Condition points per second.  One condition point is one stack with 1 second base duration.
    pub condition_points: PerCondition<f32>,
    /// Boon points per second.  One boon point is one stack with 1 second base duration.
    pub boon_points: PerBoon<f32>,
}

impl DpsModel {
    /// `DpsModel` that always outputs zero.  Useful as a placeholder in some situations.
    pub fn zero() -> DpsModel {
        DpsModel {
            strike_points: 0.,
            condition_points: 0.0.into(),
            boon_points: 0.0.into(),
        }
    }

    pub fn new<C: CharacterModel>(
        ch: &C,
        baseline: Baseline<C::Config>,
    ) -> DpsModel {
        let (stats, mods, _combat) = ch.calc_stats(&baseline.gear, &baseline.config);

        let total_dps = baseline.dps;

        let strike_percent = 100. - baseline.condition_percent.sum();
        let strike_dps = total_dps * strike_percent / 100.;
        let strike_points = strike_dps / stats.strike_factor(&mods);

        let condition_percent = baseline.condition_percent;
        let total_condition_points = PerCondition::from_fn(|condi| {
            if condi.does_damage() {
                let percent = condition_percent[condi];
                let dps = total_dps * percent / 100.;
                let points = dps / stats.condition_factor(&mods, condi);
                points
            } else {
                // TODO
                0.
            }
        });
        // We subtract out the points provided by gear, so that the `DpsModel` only reflects the
        // effect of the rotation.  Note that these numbers may be negative, which typically means
        // the rotation failed to proc the relevant runes/sigils as often as expected.
        let condition_points = total_condition_points - mods.condition_points;

        let boon_uptime = baseline.boon_uptime;
        let total_boon_points = PerBoon::from_fn(|boon| {
            let points = boon_uptime[boon] / stats.boon_duration(&mods, boon);
            points
        });
        let boon_points = total_boon_points - mods.boon_points;

        DpsModel { strike_points, condition_points, boon_points }
    }

    pub fn calc_dps(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let strike_dps = self.strike_points * stats.strike_factor(mods);
        let condition_factor = PerCondition::from_fn(|condi| stats.condition_factor(mods, condi));
        let condition_points = self.condition_points + mods.condition_points;
        let condition_dps = condition_points * condition_factor;
        strike_dps + condition_dps.sum()
    }

    /// Calculate the expected uptime of the given boon.  The result is a fraction indicating the
    /// average number of stacks to expect.  This may exceed the max stacks possible for the boon,
    /// which is useful for establishing a margin for error in the build.
    pub fn calc_boon_uptime_raw(&self, stats: &Stats, mods: &Modifiers, boon: Boon) -> f32 {
        let points = self.boon_points[boon] + mods.boon_points[boon];
        let stacks = points * stats.boon_duration(mods, boon) / 100.;
        stacks
    }

    /// Calculate the expected uptime of the given boon.  The result is a fraction indicating the
    /// average number of stacks to expect.  The result is capped at the maximum stack count for
    /// the boon in question.
    pub fn calc_boon_uptime(&self, stats: &Stats, mods: &Modifiers, boon: Boon) -> f32 {
        let stacks = self.calc_boon_uptime_raw(stats, mods, boon);
        if stacks > boon.max_stacks() {
            boon.max_stacks()
        } else {
            stacks
        }
    }
}




#[derive(Clone, Copy, PartialEq, Debug, Default)]
/// A summary of the average effects of one second of combat.
pub struct CombatSecond {
    /// Number and total points of strike damage hits.
    pub strike: CombatEvent,
    /// Number and total damage of flat strike damage, which is unaffected by power.
    pub strike_flat: CombatEvent,
    /// Number and total points of healing applied.
    pub heal: CombatEvent,
    /// Number and total HP of flat healing, which is unaffected by healing power.
    pub heal_flat: CombatEvent,
    /// Number of times each condition was applied, and the total amount of points across all
    /// applications.
    pub condition: PerCondition<CombatEvent>,
    pub boon: PerBoon<CombatEvent>,
    /// Number of times and total duration of auras applied.
    pub aura: CombatEvent,

    /// Number of skills cast.
    pub cast: f32,
    /// Number of healing skills cast.
    pub cast_healing: f32,
    /// Number of weaver dual attacks cast.
    pub cast_weaver_dual: f32,
    /// Number of weapon swaps performed.
    pub weapon_swap: f32,
    /// Number of flanking strikes.
    pub flanking: f32,

    /// Number of critical hits.  This is updated automatically, so it doesn't need to be set on
    /// initialization.
    pub crit: f32,
}

impl CombatSecond {
    pub fn update_crit(&mut self, crit_chance: f32) {
        self.crit = self.strike.count * crit_chance / 100.;
    }

    pub fn calc_dps(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let strike_dps = self.strike.magnitude * stats.strike_factor(mods);
        let condition_dps = Condition::iter().filter(|c| c.does_damage()).map(|condi| {
            let points = self.condition[condi].magnitude + mods.condition_points[condi];
            let factor = stats.condition_factor(mods, condi);
            points * factor
        }).sum::<f32>();
        strike_dps + condition_dps
    }

    pub fn calc_heal_per_second(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let heal = stats.healing_power * self.heal.magnitude;
        let heal_flat = self.heal_flat.magnitude;
        let regen =
            self.calc_boon_uptime(stats, mods, Boon::Regeneration) * stats.regen_heal(mods);
        heal + heal_flat + regen
    }

    /// Calculate the expected uptime of the given boon.  The result is a fraction indicating the
    /// average number of stacks to expect.  This may exceed the max stacks possible for the boon,
    /// which is useful for establishing a margin for error in the build.
    pub fn calc_boon_uptime_raw(&self, stats: &Stats, mods: &Modifiers, boon: Boon) -> f32 {
        let points = self.boon[boon].magnitude + mods.boon_points[boon];
        let stacks = points * stats.boon_duration(mods, boon) / 100.;
        stacks
    }

    /// Calculate the expected uptime of the given boon.  The result is a fraction indicating the
    /// average number of stacks to expect.  The result is capped at the maximum stack count for
    /// the boon in question.
    pub fn calc_boon_uptime(&self, stats: &Stats, mods: &Modifiers, boon: Boon) -> f32 {
        let stacks = self.calc_boon_uptime_raw(stats, mods, boon);
        if stacks > boon.max_stacks() {
            boon.max_stacks()
        } else {
            stacks
        }
    }

    pub fn calc_condition_uptime_raw(&self, stats: &Stats, mods: &Modifiers, condi: Condition) -> f32 {
        let points = self.condition[condi].magnitude + mods.condition_points[condi];
        let stacks = points * stats.condition_duration(mods, condi) / 100.;
        stacks
    }

    pub fn calc_condition_uptime(&self, stats: &Stats, mods: &Modifiers, condi: Condition) -> f32 {
        let stacks = self.calc_condition_uptime_raw(stats, mods, condi);
        if stacks > condi.max_stacks() {
            condi.max_stacks()
        } else {
            stacks
        }
    }
}

#[derive(Clone, Copy, PartialEq, Debug, Default)]
pub struct CombatEvent {
    /// Number of times the event occurred.
    pub count: f32,
    /// Total magnitude (damage/stacks) of all occurrences.
    pub magnitude: f32,
}

impl CombatEvent {
    pub fn new(count: f32, magnitude: f32) -> CombatEvent {
        CombatEvent { count, magnitude }
    }

    pub fn single(magnitude: f32) -> CombatEvent {
        CombatEvent { count: 1., magnitude }
    }
}

impl Add<CombatEvent> for CombatEvent {
    type Output = CombatEvent;
    fn add(self, other: CombatEvent) -> CombatEvent {
        CombatEvent {
            count: self.count + other.count,
            magnitude: self.magnitude + other.magnitude,
        }
    }
}

impl AddAssign<CombatEvent> for CombatEvent {
    fn add_assign(&mut self, other: CombatEvent) {
        self.count += other.count;
        self.magnitude += other.magnitude;
    }
}

impl Sub<CombatEvent> for CombatEvent {
    type Output = CombatEvent;
    fn sub(self, other: CombatEvent) -> CombatEvent {
        CombatEvent {
            count: self.count - other.count,
            magnitude: self.magnitude - other.magnitude,
        }
    }
}

impl SubAssign<CombatEvent> for CombatEvent {
    fn sub_assign(&mut self, other: CombatEvent) {
        self.count -= other.count;
        self.magnitude -= other.magnitude;
    }
}

impl Mul<f32> for CombatEvent {
    type Output = CombatEvent;
    fn mul(self, other: f32) -> CombatEvent {
        CombatEvent {
            count: self.count * other,
            magnitude: self.magnitude * other,
        }
    }
}

impl MulAssign<f32> for CombatEvent {
    fn mul_assign(&mut self, other: f32) {
        self.count *= other;
        self.magnitude *= other;
    }
}

impl Div<f32> for CombatEvent {
    type Output = CombatEvent;
    fn div(self, other: f32) -> CombatEvent {
        CombatEvent {
            count: self.count / other,
            magnitude: self.magnitude / other,
        }
    }
}

impl DivAssign<f32> for CombatEvent {
    fn div_assign(&mut self, other: f32) {
        self.count /= other;
        self.magnitude /= other;
    }
}
