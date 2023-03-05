use std::ops::Add;

enumerated_struct! {
    #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
    pub struct PerStat<T> {
        enum Stat;
        field type T;
        fields {
            pub power, Power;
            pub precision, Precision;
            pub ferocity, Ferocity;
            pub condition_damage, ConditionDamage;
            pub expertise, Expertise;
            pub vitality, Vitality;
            pub toughness, Toughness;
            pub healing_power, HealingPower;
            pub concentration, Concentration;
        }
        fn map<U>, FnMut(T) -> U;
    }
}

pub type Stats = PerStat<f32>;

pub const BASE_STATS: Stats = Stats {
    power: 1000.,
    precision: 1000.,
    ferocity: 0.,
    condition_damage: 0.,
    expertise: 0.,
    vitality: 1000.,
    toughness: 1000.,
    healing_power: 0.,
    concentration: 0.,
};


/// Percentage modifiers.  Values are percentage increases, so `strike_damage: 5.0` means all
/// strike damage is multiplied by `1.05`.
#[derive(Clone, Copy, Debug, Default)]
pub struct Modifiers {
    pub strike_damage: f32,
    pub crit_chance: f32,
    /// Multiplicative increase to critical hit damage.  This is not equivalent to an increase in
    /// ferocity, but instead multiplies the final damage, similar to `strike_damage` but only for
    /// crits.
    pub crit_damage: f32,
    pub condition_damage: PerCondition<f32>,
    pub condition_duration: PerCondition<f32>,
}


enumerated_struct! {
    #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
    pub struct PerCondition<T> {
        enum Condition;
        field type T;
        fields {
            pub bleed, Bleed;
            pub burn, Burn;
            pub confuse, Confuse;
            pub poison, Poison;
            pub torment, Torment;
        }
        fn map<U>, FnMut(T) -> U;
    }
}

impl Condition {
    pub fn damage_params(self) -> (f32, f32) {
        match self {
            Condition::Bleed => (22., 0.06),
            Condition::Burn => (131., 0.155),
            // Confusion, over time, PvE
            Condition::Confuse => (11., 0.03),
            Condition::Poison => (33.5, 0.06),
            // Torment, while stationary, PvE
            Condition::Torment => (31.8, 0.09),
        }
    }
}

impl<T> PerCondition<T> {
    pub fn sum(&self) -> T
    where for<'a> &'a T: Add<&'a T, Output = T> {
        let acc = &self.bleed + &self.burn;
        let acc = &acc + &self.confuse;
        let acc = &acc + &self.poison;
        let acc = &acc + &self.torment;
        acc
    }
}


fn cap(x: f32, max: f32) -> f32 {
    if x < max { x } else { max }
}

impl Stats {
    pub fn strike_factor(&self, mods: &Modifiers) -> f32 {
        let damage = self.power / 10. * mods.strike_damage;
        let crit_chance = self.crit_chance(mods);
        let crit_damage = (150. + self.ferocity / 15.) * (1. + mods.crit_damage / 100.);
        let crit_factor = 1. + crit_chance / 100. * (crit_damage - 100.) / 100.;
        damage * crit_factor
    }

    pub fn crit_chance(&self, mods: &Modifiers) -> f32 {
        cap((self.precision - 895.) / 21. + mods.crit_chance, 100.)
    }

    pub fn condition_factor(&self, mods: &Modifiers, condi: Condition) -> f32 {
        let (damage_base, damage_factor) = condi.damage_params();
        let damage = damage_base + damage_factor * self.condition_damage;
        let damage_bonus = 1. + mods.condition_damage[condi] / 100.;
        let duration = cap(100. + self.expertise / 15. + mods.condition_duration[condi], 200.);
        damage * damage_bonus * duration / 100.
    }
}
