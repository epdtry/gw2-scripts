use crate::character::CombatSecond;
use crate::effect::Effect;
use crate::stats::{Stats, Modifiers, Boon};

/// Apply might.  The argument is a number of points; the number of stacks will be derived from the
/// points and the applicable stats and modifiers.
#[derive(Clone, Copy, Debug, Default)]
pub struct Might;

impl Effect for Might {
    fn add_temporary(&self, s: &mut Stats, m: &mut Modifiers, c: &CombatSecond) {
        let stacks = c.calc_boon_uptime(s, m, Boon::Might);
        s.power += stacks * 30.;
        s.condition_damage += stacks * 30.;
    }
}

/// Apply fury.  The argument is a number of points; the number of stacks will be derived from the
/// points and the applicable stats and modifiers.
#[derive(Clone, Copy, Debug, Default)]
pub struct Fury;

impl Effect for Fury {
    fn add_temporary(&self, s: &mut Stats, m: &mut Modifiers, c: &CombatSecond) {
        let stacks = c.calc_boon_uptime(s, m, Boon::Fury);
        m.crit_chance += stacks * 25.;
    }
}



/// Apply might.  The argument is a number of points; the number of stacks will be derived from the
/// points and the applicable stats and modifiers.
#[derive(Clone, Copy, Debug, Default)]
pub struct OldMight(pub f32);

impl Effect for OldMight {
    fn add_temporary(&self, s: &mut Stats, m: &mut Modifiers, _c: &CombatSecond) {
        let points = self.0 + m.boon_points.might;
        let stacks = points * s.boon_duration(m, Boon::Might) / 100.;
        let stacks = if stacks > 25. { 25. } else { stacks };

        s.power += stacks * 30.;
        s.condition_damage += stacks * 30.;
    }
}

/// Apply fury.  The argument is a number of points; the number of stacks will be derived from the
/// points and the applicable stats and modifiers.
#[derive(Clone, Copy, Debug, Default)]
pub struct OldFury(pub f32);

impl Effect for OldFury {
    fn add_temporary(&self, s: &mut Stats, m: &mut Modifiers, _c: &CombatSecond) {
        let points = self.0 + m.boon_points.fury;
        let stacks = points * s.boon_duration(m, Boon::Fury) / 100.;
        let stacks = if stacks > 1. { 1. } else { stacks };

        m.crit_chance += stacks * 25.;
    }
}
