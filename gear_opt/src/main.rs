use std::ops::{Add, Sub, Mul, AddAssign, Index, IndexMut};

mod generated;
pub use generated::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};


macro_rules! enumerated_struct {
    (
    $(#[$struct_attrs:meta])*
    pub struct $Struct:ident $(< $A:ident >)? {
        enum $Enum:ident;
        field type $FTy:ty;
        fields {
            $(pub $field:ident, $Variant:ident;)*
        }
        fn map$(<$B:ident>)?, FnMut($MapSrcTy:ty) -> $MapDestTy:ty;
    }) => {
        $(#[$struct_attrs])*
        pub struct $Struct<$($A,)?> {
            $( pub $field: $FTy, )*
        }

        #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
        pub enum $Enum {
            $( $Variant, )*
        }

        impl<$($A,)?> $Struct<$($A,)?> {
            pub fn from_fn<F: FnMut($Enum) -> $FTy>(mut f: F) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: f($Enum::$Variant), )*
                }
            }

                pub fn map<F, $($B,)?>(self, mut f: F) -> $Struct<$($B,)?>
                where F: FnMut($Enum, $MapSrcTy) -> $MapDestTy {
                    $Struct {
                        $( $field: f($Enum::$Variant, self.$field), )*
                    }
                }
        }

        impl<$($A,)?> From<$FTy> for $Struct<$($A,)?>
        where $FTy: Clone {
            fn from(x: $FTy) -> $Struct<$($A,)?> {
                Self::from_fn(|_| x.clone())
            }
        }

        impl<$($A,)?> Add<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: Add<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn add(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field + other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> Add<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: Add<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn add(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field + &other.$field, )*
                }
            }
        }

        impl<$($A,)?> AddAssign<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where $FTy: AddAssign<$FTy> {
            fn add_assign(&mut self, other: $Struct<$($A,)?>) {
                $( self.$field += other.$field; )?
            }
        }

        impl<'a, $($A,)?> AddAssign<&'a $Struct<$($A,)?>> for $Struct<$($A,)?>
        where $FTy: AddAssign<&'a $FTy> {
            fn add_assign(&mut self, other: &'a $Struct<$($A,)?>) {
                $( self.$field += &other.$field; )?
            }
        }

        impl<$($A,)?> AddAssign<$FTy> for $Struct<$($A,)?>
        where $FTy: AddAssign<$FTy>, $FTy: Copy {
            fn add_assign(&mut self, other: $FTy) {
                $( self.$field += other; )?
            }
        }

        impl<'a, $($A,)?> AddAssign<&'a $FTy> for $Struct<$($A,)?>
        where $FTy: AddAssign<&'a $FTy> {
            fn add_assign(&mut self, other: &'a $FTy) {
                $( self.$field += other; )?
            }
        }

        impl<$($A,)?> Sub<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: Sub<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn sub(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field - other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> Sub<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: Sub<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn sub(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field - &other.$field, )*
                }
            }
        }

        impl<$($A,)?> Mul<$Struct<$($A,)?>> for $Struct<$($A,)?>
        where
            $( $A: Mul<$A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn mul(self, other: $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: self.$field * other.$field, )*
                }
            }
        }

        impl<'a, $($A,)?> Mul<&'a $Struct<$($A,)?>> for &'a $Struct<$($A,)?>
        where
            $( &'a $A: Mul<&'a $A, Output = $A>, )?
        {
            type Output = $Struct<$($A,)?>;
            fn mul(self, other: &'a $Struct<$($A,)?>) -> $Struct<$($A,)?> {
                $Struct {
                    $( $field: &self.$field * &other.$field, )*
                }
            }
        }

        impl<$($A,)?> Index<$Enum> for $Struct<$($A,)?> {
            type Output = $FTy;
            fn index(&self, x: $Enum) -> &$FTy {
                match x {
                    $( $Enum::$Variant => &self.$field, )*
                }
            }
        }

        impl<$($A,)?> IndexMut<$Enum> for $Struct<$($A,)?> {
            fn index_mut(&mut self, x: $Enum) -> &mut $FTy {
                match x {
                    $( $Enum::$Variant => &mut self.$field, )*
                }
            }
        }
    };
}


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


pub trait CharacterModel {
    fn calc_stats(&self, gear: &Stats) -> Stats;
    fn calc_modifiers(&self) -> Modifiers;
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
        let stats = ch.calc_stats(&baseline.gear);
        let mods = ch.calc_modifiers();

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


enumerated_struct! {
    #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
    pub struct PerGearSlot<T> {
        enum GearSlot;
        field type T;
        fields {
            pub weapon_1h, Weapon1H;
            pub weapon_2h, Weapon2H;
            pub helm, Helm;
            pub shoulders, Shoulders;
            pub coat, Coat;
            pub gloves, Gloves;
            pub leggings, Leggings;
            pub boots, Boots;
            pub amulet, Amulet;
            pub ring1, Ring1;
            pub ring2, Ring2;
            pub accessory1, Accessory1;
            pub accessory2, Accessory2;
            pub backpack, Backpack;
        }
        fn map<U>, FnMut(T) -> U;
    }
}

impl GearSlot {
    pub fn is_trinket(self) -> bool {
        match self {
            GearSlot::Amulet => true,
            GearSlot::Ring1 => true,
            GearSlot::Ring2 => true,
            GearSlot::Accessory1 => true,
            GearSlot::Accessory2 => true,
            GearSlot::Backpack => true,
            _ => false,
        }
    }
}

enumerated_struct! {
    #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
    pub struct PerQuality<T> {
        enum Quality;
        field type T;
        fields {
            pub exotic, Exotic;
            pub ascended, Ascended;
        }
        fn map<U>, FnMut(T) -> U;
    }
}

pub struct SlotInfo {
    /// Prefix-agnostic measure of stats for this piece.  This is multiplied by the per-stat
    /// factors for the chosen prefix when computing the actual stats of the piece.
    pub points: PerQuality<f32>,
    /// Whether to add the `base` component of the `StatFormula`.  This is set only for trinket
    /// slots.
    pub add_base: bool,
}

pub struct Prefix {
    pub name: &'static str,
    pub formulas: PerStat<StatFormula>,
}

pub struct StatFormula {
    pub factor: f32,
    pub base: PerQuality<f32>,
}

impl StatFormula {
    pub const ZERO: StatFormula = StatFormula {
        factor: 0.,
        base: PerQuality {
            exotic: 0.,
            ascended: 0.,
        },
    };
}

impl Prefix {
    pub fn calc_stats_coarse(&self, points: f32) -> Stats {
        Stats::from_fn(|stat| {
            let formula = &self.formulas[stat];
            formula.factor * points
        })
    }
}

impl SlotInfo {
    /// Calculate the stats provided by an item of the given `prefix` and `quality` in this slot.
    ///
    /// The resulting stats are not rounded off.
    pub fn calc_stats(&self, prefix: &Prefix, quality: Quality) -> Stats {
        Stats::from_fn(|stat| {
            let formula = &prefix.formulas[stat];
            let base = if self.add_base { formula.base[quality] } else { 0. };
            formula.factor * self.points[quality] + base
        })
    }
}


pub type PrefixWeights = [f32; NUM_PREFIXES];

fn calc_gear_stats(w: &PrefixWeights) -> Stats {
    let mut gear = Stats::default();
    for (&w, prefix) in w.iter().zip(PREFIXES.iter()) {
        gear = gear + prefix.calc_stats_coarse(w);
    }
    gear
}

fn calc_max_weight(slots: &[(GearSlot, Quality)]) -> f32 {
    // Use the power stat of full berserker's as a baseline.
    let prefix = PREFIXES.iter().find(|p| p.name == "Berserker's").unwrap();

    let mut acc = 0.;
    for &(slot, quality) in slots {
        let x = GEAR_SLOTS[slot].calc_stats(prefix, quality).power;
        acc += GEAR_SLOTS[slot].calc_stats(prefix, quality).power;
    }
    acc / prefix.formulas.power.factor
}

fn evaluate_weights<C: CharacterModel>(ch: &C, w: &PrefixWeights) -> f32 {
    let gear = calc_gear_stats(&w);
    let stats = ch.calc_stats(&gear);
    let mods = ch.calc_modifiers();
    ch.evaluate(&stats, &mods)
}

fn report(w: &PrefixWeights, m: f32) {
    eprintln!("metric: {}", m);

    let mut lines = w.iter().zip(PREFIXES.iter()).filter_map(|(&w, prefix)| {
        if w > 0.0 { Some((w, prefix.name)) } else { None }
    }).collect::<Vec<_>>();
    lines.sort_by(|&(w1, _), &(w2, _)| w2.partial_cmp(&w1).unwrap());
    for (w, name) in lines {
        eprintln!("{} = {}", name, w);
    }
    eprintln!();
}

pub fn optimize_coarse<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> PrefixWeights {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);

    let mut best_w = [0.; NUM_PREFIXES];
    let mut best_m = 999999999.;

    /*
    let ps = [
        PREFIXES.iter().position(|p| p.name == "Rampager's").unwrap(),
        PREFIXES.iter().position(|p| p.name == "Viper's").unwrap(),
        PREFIXES.iter().position(|p| p.name == "Sinister").unwrap(),
        PREFIXES.iter().position(|p| p.name == "Seraph").unwrap(),
    ];
    */

    for i in 0 .. NUM_PREFIXES {
        for j in 0 .. NUM_PREFIXES {
            let mut w0 = [0.; NUM_PREFIXES];
            w0[i] += max_weight * 2. / 3.;
            w0[j] += max_weight * 1. / 3.;
            eprintln!("start: 2/3 {}, 1/3 {}", PREFIXES[i].name, PREFIXES[j].name);

            let w = optimize_coarse_one(ch, max_weight, &w0);
            let m = evaluate_weights(ch, &w);

            if m < best_m {
                best_w = w;
                best_m = m;
            }
        }
    }

    report(&best_w, best_m);
    best_w
}

fn optimize_coarse_one<C: CharacterModel>(
    ch: &C,
    max_weight: f32,
    w0: &PrefixWeights,
) -> PrefixWeights {
    let mut w = *w0;
    let mut m = evaluate_weights(ch, &w);

    for i in 0 .. 10 {
        let c_base = 0.85_f32.powi(i);

        let mut best_w = w;
        let mut best_m = m;
        let mut best_c = 0.0;
        let mut best_j = 0;
        for j in 0 .. NUM_PREFIXES {
            for k in 1 ..= 100 {
                let c = c_base * k as f32 / 100.;

                let mut new_w = w;
                for w in &mut new_w {
                    *w *= 1. - c;
                }
                new_w[j] += max_weight * c;

                let new_m = evaluate_weights(ch, &new_w);

                if new_m < best_m {
                    best_w = new_w;
                    best_m = new_m;
                    best_c = c;
                    best_j = j;
                }
            }
        }

        if best_c > 0.0 {
            eprintln!("iteration {}: improved {} -> {} using {} points of {}",
                i, m, best_m, best_c * 100., PREFIXES[best_j].name);
        }

        w = best_w;
        m = best_m;
    }

    report(&w, m);
    w
}


struct CondiVirt {
    dps: DpsModel,
}

impl CondiVirt {
    pub fn new() -> CondiVirt {
        let mut ch = CondiVirt {
            dps: DpsModel::zero(),
        };
        ch.dps = DpsModel::new(&ch, &Baseline {
            gear: Stats {
                power: 986.,
                precision: 981.,
                condition_damage: 1012.,
                expertise: 255.,
                .. Stats::default()
            },
            dps: 30063.,
            condition_percent: PerCondition {
                bleed: 59.9,
                torment: 10.3,
                confuse: 1.3,
                poison: 0.2,
                .. 0.0.into()
            },
        });
        ch
    }
}


impl CharacterModel for CondiVirt {
    fn calc_stats(&self, gear: &Stats) -> Stats {
        let mut stats = &BASE_STATS + gear;

        // Runes
        stats.condition_damage += 175.;

        // Infusions
        //stats.condition_damage += 16. * 5.;
        //stats.precision += 2. * 5.;

        // Signet of Domination
        stats.condition_damage += 180.;
        // Signet of Midnight
        stats.expertise += 180.;

        // Food
        stats.precision += 100.;
        stats.condition_damage += 70.;

        // Quiet Intensity
        stats.ferocity += stats.vitality * 0.10;

        // Utility
        stats.condition_damage += stats.power * 0.03;
        stats.condition_damage += stats.precision * 0.03;

        // Might
        stats.power += 25. * 30.;
        stats.condition_damage += 25. * 30.;

        // Compounding Power
        stats.condition_damage += 1. * 30.;

        stats
    }

    fn calc_modifiers(&self) -> Modifiers {
        let mut m = Modifiers::default();

        // Runes
        m.condition_duration.bleed += 50.;

        // Sigils
        m.condition_duration.bleed += 20.;

        // Fury +25%, fury bonus from trait +15%
        m.crit_chance += 40.;

        // Superiority Complex: +15%, +10% on disabled or defiant foes
        m.crit_damage += 25.;

        // Compounding Power
        m.strike_damage += 1. * 2.;

        // Bloodsong
        m.condition_damage.bleed += 25.;

        m
    }

    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let crit = stats.crit_chance(mods);
        if crit < 100. {
            return 1000. + 100. - crit;
        }

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
        ch.dps = DpsModel::new(&ch, &Baseline {
            gear: Stats {
                power: 824.,
                precision: 793.,
                condition_damage: 1173.,
                expertise: 444.,
                healing_power: 189.,
                concentration: 189.,
                .. Stats::default()
            },
            dps: 6708.,
            condition_percent: PerCondition {
                burn: 68.9,
                bleed: 10.3,
                .. 0.0.into()
            },
        });
        ch
    }
}


impl CharacterModel for CairnSoloArcane {
    fn calc_stats(&self, gear: &Stats) -> Stats {
        let mut stats = &BASE_STATS + gear;

        // Rune of the Elementalist
        stats.power += 175.;
        stats.condition_damage += 225.;

        // Infusions

        // Trait: Empowering Flame (4/8 fire uptime)
        stats.condition_damage += 150. * 4. / 8.;
        // Trait: Burning Rage
        stats.condition_damage += 180.;
        // Trait: Elemental Enchantment
        stats.concentration += 180.;
        // Trait: Elemental Polyphony
        // Rotation: F/F, E/F, A/E, F/A, F/F, E/F, W/E, F/W
        // When either the mainhand or offhand attunement is fire, gain 120 power (etc.)
        stats.power += 120. * 6. / 8.;
        stats.healing_power += 120. * 2. * 2. / 8.;
        stats.ferocity += 120. * 2. * 2. / 8.;
        stats.vitality += 120. * 2. * 4. / 8.;

        // Food
        stats.expertise += 100.;
        stats.condition_damage += 70.;

        // Utility
        stats.condition_damage += stats.power * 0.03;
        stats.condition_damage += stats.precision * 0.03;

        // Might
        stats.power += 12. * 30.;
        stats.condition_damage += 12. * 30.;

        stats
    }

    fn calc_modifiers(&self) -> Modifiers {
        let mut m = Modifiers::default();

        // Rune of the Elementalist
        m.condition_duration += 50.;

        // Sigil of Smoldering
        m.condition_duration.burn += 20.;

        // Fury +25%
        m.crit_chance += 0.1 * 25.;

        // Trait: Burning Precision
        m.condition_duration.burn += 20.;
        // Trait: Pyromancer's Training
        m.strike_damage += 10.;
        // Trait: Persisting Flames
        m.strike_damage += 15. / 16. * 10.;
        // Trait: Superior Elements
        m.crit_chance += 15.;
        // Trait: Weaver's Prowess
        m.condition_damage += 10.;
        m.condition_duration += 20.;

        // Woven Fire (1/3 uptime)
        m.condition_damage += 20. * 1./3.;

        m
    }

    fn evaluate(&self, stats: &Stats, mods: &Modifiers) -> f32 {
        let min_healing_power = 0.;
        let min_concentration = 0.;

        if stats.healing_power < min_healing_power {
            return 2000. + min_healing_power - stats.healing_power;
        }

        if stats.concentration < min_concentration {
            return 1000. + min_concentration - stats.concentration;
        }

        let min_dps = 6900.;
        let dps = self.dps.calc_dps(stats, mods);
        if dps < min_dps {
            return 10000. + min_dps - dps;
        }

        -stats.healing_power
        //-dps
    }
}


fn main() {
    //let ch = CondiVirt::new();
    let ch = CairnSoloArcane::new();

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

    let w = optimize_coarse(&ch, &slots);

    let gear = calc_gear_stats(&w);
    //eprintln!("{:?}", gear.map(|_, x| x.round() as u32));
    let stats = ch.calc_stats(&gear);
    eprintln!("{:?}", stats.map(|_, x| x.round() as u32));
}
