use std::cmp::Ordering;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality};
use crate::stats::Stats;

pub mod coarse;
pub mod fine;


#[derive(Clone, Copy, PartialEq, PartialOrd, Debug, Hash, Default)]
pub struct AssertTotal<T>(pub T);

impl<T: PartialEq> Eq for AssertTotal<T> {}

impl<T: PartialEq + PartialOrd> Ord for AssertTotal<T> {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.partial_cmp(&other.0).unwrap()
    }
}


fn evaluate_config<C: CharacterModel>(ch: &C, gear: &Stats, cfg: &C::Config) -> f32 {
    let (stats, mods, combat) = ch.calc_stats(gear, cfg);
    ch.evaluate(cfg, &stats, &mods, &combat)
}


fn calc_max_weight(slots: &[(GearSlot, Quality)]) -> f32 {
    // Use the power stat of full berserker's as a baseline.
    let prefix = PREFIXES.iter().find(|p| p.name == "Berserker's").unwrap();

    let mut acc = 0.;
    for &(slot, quality) in slots {
        acc += GEAR_SLOTS[slot].calc_stats(prefix, quality).power;
    }
    acc / prefix.formulas.power.factor
}

