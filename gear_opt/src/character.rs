use crate::effect::Effect;
use crate::stats::{Stats, Modifiers, PerCondition, BASE_STATS};

/// `CharacterModel` describes a build to be optimized.
pub trait CharacterModel {
    /// Whether the optimizer should try changing runes.  If this is set, then `apply_effects`
    /// should not apply a rune effect; the rune effect will be included in `base_effect` by the
    /// optimizer.
    fn vary_rune(&self) -> bool { false }

    /// How many of the sigils the optimizer should try changing.  If this is to `N`, then
    /// `apply_effects` should only apply `2 - N` sigil effects; the other `N` sigil effects will
    /// be included in `base_effect` by the optimizer.
    fn vary_sigils(&self) -> u8 { 0 }

    fn vary_food(&self) -> bool { false }
    fn vary_utility(&self) -> bool { false }

    /// Apply `effect` plus any fixed effects to update the provided `stats` and `mods`.  This
    /// captures the fixed parts of the build, such as trait choices.
    fn apply_effects<E: Effect>(&self, base_effect: E, stats: &mut Stats, mods: &mut Modifiers);
    /// Evaluate the quality of particular `stats` and `mods` values for this build.  The optimizer
    /// tries to minimize this function, so smaller is better.  This means DPS builds should
    /// generally return `-dps` rather than `dps`.  This captures the goals we're optimizing for
    /// with this build.
    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32;
}


#[derive(Clone, Debug)]
pub struct Baseline<E> {
    pub gear: Stats,
    pub dps: f32,
    pub condition_percent: PerCondition<f32>,
    pub effect: E,
}

#[derive(Clone, Debug)]
pub struct DpsModel {
    strike_points: f32,
    condition_points: PerCondition<f32>,
}

impl DpsModel {
    /// `DpsModel` that always outputs zero.  Useful as a placeholder in some situations.
    pub fn zero() -> DpsModel {
        DpsModel {
            strike_points: 0.,
            condition_points: 0.0.into(),
        }
    }

    pub fn new<C: CharacterModel, E: Effect>(
        ch: &C,
        baseline: Baseline<E>,
    ) -> DpsModel {
        let mut stats = BASE_STATS + baseline.gear;
        let mut mods = Modifiers::default();
        ch.apply_effects(baseline.effect, &mut stats, &mut mods);

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

        DpsModel { strike_points, condition_points }
    }

    pub fn calc_dps(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let strike_dps = self.strike_points * stats.strike_factor(mods);
        let condition_factor = PerCondition::from_fn(|condi| stats.condition_factor(mods, condi));
        let condition_dps = self.condition_points * condition_factor;
        strike_dps + condition_dps.sum()
    }
}


