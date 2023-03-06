use crate::stats::{Stats, Modifiers, PerCondition, BASE_STATS};

pub trait CharacterModel {
    fn apply_effects(&self, stats: &mut Stats, mods: &mut Modifiers);
    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32;
}


pub struct Baseline {
    pub gear: Stats,
    pub dps: f32,
    pub condition_percent: PerCondition<f32>,
}

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

    pub fn new<C: CharacterModel>(ch: &C, baseline: &Baseline) -> DpsModel {
        let mut stats = BASE_STATS + baseline.gear;
        let mut mods = Modifiers::default();
        ch.apply_effects(&mut stats, &mut mods);

        let strike_percent = 100. - baseline.condition_percent.sum();
        let strike_dps = baseline.dps * strike_percent / 100.;
        let strike_points = strike_dps / stats.strike_factor(&mods);

        let condition_points = PerCondition::from_fn(|condi| {
            let percent = baseline.condition_percent[condi];
            let dps = baseline.dps * percent / 100.;
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


