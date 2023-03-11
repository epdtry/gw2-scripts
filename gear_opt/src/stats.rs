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
    pub boon_duration: PerBoon<f32>,
    pub max_health: f32,

    /// Extra condition points per second provided by gear, as opposed to points that come from the
    /// skill rotation.  One point = one stack * one second.  For example, Superior Sigil of
    /// Torment has the effect "Inflict 2 stacks of torment for 5 seconds to enemies around your
    /// target upon landing a critical hit (cooldown: 5 seconds)"; the `CharacterModel` would then
    /// add torment points equal to `2. * 5. / interval`, where `interval` is an estimate of how
    /// often the sigil will proc.
    pub condition_points: PerCondition<f32>,
    pub boon_points: PerBoon<f32>,
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


enumerated_struct! {
    #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
    pub struct PerBoon<T> {
        enum Boon;
        field type T;
        fields {
            pub aegis, Aegis;
            pub alacrity, Alacrity;
            pub fury, Fury;
            pub might, Might;
            pub protection, Protection;
            pub quickness, Quickness;
            pub regeneration, Regeneration;
            pub resistance, Resistance;
            pub resolution, Resolution;
            pub stability, Stability;
            pub swiftness, Swiftness;
            pub vigor, Vigor;
        }
        fn map<U>, FnMut(T) -> U;
    }
}

impl Boon {
    pub fn max_stacks(self) -> f32 {
        match self {
            Boon::Might => 25.,
            _ => 1.,
        }
    }
}


fn cap(x: f32, max: f32) -> f32 {
    if x < max { x } else { max }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
pub enum HealthTier {
    Low,
    Mid,
    High,
}

impl HealthTier {
    pub fn base_health(self) -> f32 {
        match self {
            HealthTier::Low => 1645.,
            HealthTier::Mid => 5922.,
            HealthTier::High => 9212.,
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
pub enum ArmorWeight {
    Light,
    Medium,
    Heavy,
}

impl ArmorWeight {
    pub fn base_armor(self) -> f32 {
        // TODO: these numbers only apply for full sets of ascended; exotic armor values are
        // slightly lower
        match self {
            ArmorWeight::Light => 967.,
            ArmorWeight::Medium => 1118.,
            ArmorWeight::Heavy => 1271.,
        }
    }
}

impl Stats {
    pub fn strike_factor(&self, mods: &Modifiers) -> f32 {
        let damage = self.power / 10.;
        let damage_bonus = 1. + mods.strike_damage / 100.;
        let crit_chance = self.crit_chance(mods);
        let crit_damage = (150. + self.ferocity / 15.) * (1. + mods.crit_damage / 100.);
        let crit_factor = 1. + crit_chance / 100. * (crit_damage - 100.) / 100.;
        damage * damage_bonus * crit_factor
    }

    pub fn crit_chance(&self, mods: &Modifiers) -> f32 {
        cap((self.precision - 895.) / 21. + mods.crit_chance, 100.)
    }

    pub fn condition_duration(&self, mods: &Modifiers, condi: Condition) -> f32 {
        cap(100. + self.expertise / 15. + mods.condition_duration[condi], 200.)
    }

    pub fn condition_factor(&self, mods: &Modifiers, condi: Condition) -> f32 {
        let (damage_base, damage_factor) = condi.damage_params();
        let damage = damage_base + damage_factor * self.condition_damage;
        let damage_bonus = 1. + mods.condition_damage[condi] / 100.;
        let duration = self.condition_duration(mods, condi);
        damage * damage_bonus * duration / 100.
    }

    /// Calculate boon duration for a specific boon, in percent.
    pub fn boon_duration(&self, mods: &Modifiers, boon: Boon) -> f32 {
        cap(100. + self.concentration / 15. + mods.boon_duration[boon], 200.)
    }

    /// Heal per second provided by each stack of regeneration.
    pub fn regen_heal(&self, _mods: &Modifiers) -> f32 {
        130. + 0.125 * self.healing_power
    }

    pub fn max_health(&self, mods: &Modifiers, tier: HealthTier) -> f32 {
        let health = tier.base_health() + self.vitality * 10.;
        let health_bonus = 1. + mods.max_health / 100.;
        health * health_bonus
    }

    pub fn armor(&self, mods: &Modifiers, weight: ArmorWeight) -> f32 {
        weight.base_armor() + self.toughness
    }
}
