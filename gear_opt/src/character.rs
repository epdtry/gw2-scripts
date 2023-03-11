use std::fmt;
use crate::stats::{Stats, Modifiers, PerCondition, Boon, PerBoon};

/// `CharacterModel` describes a build to be optimized.
pub trait CharacterModel {
    type Config: Vary + Clone + Default + fmt::Debug;

    /// Check whether a configuration is valid.  If this returns `false`, the optimizer will not
    /// try evaluating the config.
    fn is_config_valid(&self, config: &Self::Config) -> bool { true }

    /// Calculate stats and modifiers for a set of `gear` and `config`.  This captures the fixed
    /// parts of the build, such as trait choices.
    fn calc_stats(&self, gear: &Stats, config: &Self::Config) -> (Stats, Modifiers);

    /// Evaluate the quality of particular `stats` and `mods` values for this build.  The optimizer
    /// tries to minimize this function, so smaller is better.  This means DPS builds should
    /// generally return `-dps` rather than `dps`.  This captures the goals we're optimizing for
    /// with this build.
    fn evaluate(&self, config: &Self::Config, stats: &Stats, mods: &Modifiers) -> f32;
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
        let (stats, mods) = ch.calc_stats(&baseline.gear, &baseline.config);

        let total_dps = baseline.dps;

        let strike_percent = 100. - baseline.condition_percent.sum();
        let strike_dps = total_dps * strike_percent / 100.;
        let strike_points = strike_dps / stats.strike_factor(&mods);

        let condition_percent = baseline.condition_percent;
        let condition_points = PerCondition::from_fn(|condi| {
            let percent = condition_percent[condi];
            let dps = total_dps * percent / 100.;
            let points = dps / stats.condition_factor(&mods, condi);
            points
        });

        let boon_uptime = baseline.boon_uptime;
        let boon_points = PerBoon::from_fn(|boon| {
            let points = boon_uptime[boon] / stats.boon_duration(&mods, boon);
            points
        });

        DpsModel { strike_points, condition_points, boon_points }
    }

    pub fn calc_dps(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let strike_dps = self.strike_points * stats.strike_factor(mods);
        let condition_factor = PerCondition::from_fn(|condi| stats.condition_factor(mods, condi));
        let condition_dps = self.condition_points * condition_factor;
        strike_dps + condition_dps.sum()
    }

    /// Calculate the expected uptime of the given boon.  The result is a fraction indicating the
    /// average number of stacks to expect.  The result is capped at the maximum stack count for
    /// the boon in question.
    pub fn calc_boon_uptime(&self, stats: &Stats, mods: &Modifiers, boon: Boon) -> f32 {
        let stacks = self.boon_points[boon] * stats.boon_duration(mods, boon) / 100.;
        if stacks > boon.max_stacks() {
            boon.max_stacks()
        } else {
            stacks
        }
    }
}


