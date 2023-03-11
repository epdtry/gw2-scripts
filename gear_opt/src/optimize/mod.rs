use std::cmp::Ordering;
use crate::character::CharacterModel;
use crate::stats::Stats;

pub mod coarse;
pub mod fine;


#[derive(Clone, Copy, PartialEq, PartialOrd, Debug, Hash, Default)]
struct AssertTotal<T>(pub T);

impl<T: PartialEq> Eq for AssertTotal<T> {}

impl<T: PartialEq + PartialOrd> Ord for AssertTotal<T> {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.partial_cmp(&other.0).unwrap()
    }
}


fn evaluate_config<C: CharacterModel>(ch: &C, gear: &Stats, cfg: &C::Config) -> f32 {
    let (stats, mods) = ch.calc_stats(gear, cfg);
    ch.evaluate(cfg, &stats, &mods)
}
