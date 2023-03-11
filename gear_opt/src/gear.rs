use crate::stats::{Stats, PerStat};


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

#[derive(Clone, Copy, Debug, Default)]
pub struct Prefix {
    pub name: &'static str,
    pub formulas: PerStat<StatFormula>,
}

#[derive(Clone, Copy, Debug, Default)]
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


