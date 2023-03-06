use crate::effect::Effect;
use crate::stats::{Stats, Modifiers};

#[derive(Clone, Copy, Debug, Default)]
pub struct Might(pub f32);

impl Effect for Might {
    fn add_temporary(&self, s: &mut Stats, _m: &mut Modifiers) {
        s.power += self.0 * 30.;
        s.condition_damage += self.0 * 30.;
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub struct Fury(pub f32);

impl Effect for Fury {
    fn add_temporary(&self, _s: &mut Stats, m: &mut Modifiers) {
        m.crit_chance += self.0 * 25.;
    }
}
