use std::cmp::Reverse;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality, Prefix, StatFormula, PerQuality};
use crate::optimize::coarse::PrefixWeights;
use crate::stats::{Stats, PerStat, Stat};
use super::{AssertTotal, evaluate_config};


struct SlotExt {
    orig_idx: u8,
    gear_slot: GearSlot,
    quality: Quality,
    stat_weight: f32,
}

#[derive(Clone, Debug)]
pub struct Candidate {
    pub slot_prefixes: Vec<u8>,
    pub infusions: PerStat<u8>,
}

impl Candidate {
    pub fn new(num_slots: usize) -> Candidate {
        Candidate {
            slot_prefixes: vec![0; num_slots],
            infusions: 0.into(),
        }
    }
}

struct Optimizer<'a, C: CharacterModel> {
    ch: &'a C,
    cfg: &'a C::Config,
    slots: &'a [SlotExt],
    num_infusions: usize,
    prefixes: &'a [Prefix],
    /// For each slot, an upper bound on the stats that could be provided by choosing prefixes from
    /// `prefixes` for this slot and all further slots.
    slot_remaining_stats: Vec<Stats>,
    cur: Candidate,
    best_m: f32,
    best_candidate: Candidate,
    tried: usize,
}

impl<'a, C: CharacterModel> Optimizer<'a, C> {
    pub fn new(
        ch: &'a C,
        cfg: &'a C::Config,
        slots: &'a [SlotExt],
        num_infusions: usize,
        prefixes: &'a [Prefix],
    ) -> Optimizer<'a, C> {
        let mut slot_remaining_stats = vec![Stats::default(); slots.len()];
        for i in (0 .. slots.len()).rev() {
            let slot = &slots[i];
            let prev = slot_remaining_stats.get(i + 1).cloned()
                .unwrap_or_else(|| max_infusion_stats(num_infusions));

            let mut slot_stats = Stats::default();
            for prefix in prefixes {
                let s = GEAR_SLOTS[slot.gear_slot].calc_stats(&prefix, slot.quality);
                slot_stats = Stats::from_fn(|stat| {
                    f32::max(slot_stats[stat], s[stat])
                });
            }
            let slot_stats = slot_stats.map(|_, x| x.round());

            slot_remaining_stats[i] = prev + slot_stats;
        }
        eprintln!("all stats = {:#?}", slot_remaining_stats[0]);

        Optimizer {
            ch, cfg, slots, num_infusions, prefixes,
            slot_remaining_stats,
            cur: Candidate::new(slots.len()),
            best_m: 999999999.,
            best_candidate: Candidate::new(slots.len()),
            tried: 0,
        }
    }

    fn evaluate_current(&mut self, gear: Stats) -> f32 {
        self.tried += 1;
        evaluate_config(self.ch, &gear, self.cfg)
    }

    fn go_slots(&mut self, i: usize, gear: Stats) {
        if i >= self.slots.len() {
            self.go_infusions(0, self.num_infusions, gear);
            return;
        }

        let max_gear = gear + self.slot_remaining_stats[i];
        let max_m = self.evaluate_current(max_gear);
        if max_m > self.best_m {
            // Prune this branch.  Even with a wildly optimistic upper bound on what stats we can
            // achieve with the remaining slots, we still can't improve on the current `best_m`.
            //
            // NB: This assumes that higher stats are always better.  This might not be true in
            // some cases!
            return;
        }

        let slot = &self.slots[i];

        for (j, prefix) in self.prefixes.iter().enumerate() {
            let j = j as u8;

            // Symmetry breaking: for runs of slots with identical weights, such as Ring1/Ring2 or
            // Shoulders/Gloves/Boots, require prefixes to run in increasing order across the
            // group.
            if i > 0 &&
                    slot.stat_weight == self.slots[i - 1].stat_weight &&
                    j < self.cur.slot_prefixes[i - 1] {
                continue;
            }

            self.cur.slot_prefixes[i] = j as u8;

            if i < 2 {
                eprintln!("{:?}", &self.cur.slot_prefixes[.. i + 1]);
            }

            let slot_stats = GEAR_SLOTS[slot.gear_slot].calc_stats(prefix, slot.quality)
                .map(|_, x| x.round());
            self.go_slots(i + 1, gear + slot_stats);
        }
    }

    fn go_infusions(&mut self, stat_idx: usize, num_unassigned: usize, gear: Stats) {
        if stat_idx >= Stat::COUNT || num_unassigned == 0 {
            let m = self.evaluate_current(gear);
            if m < self.best_m {
                self.best_m = m;
                self.best_candidate = self.cur.clone();
                eprintln!("metric = {}", m);
                eprintln!("gear = {:?}", gear);
                eprintln!();
            }
            return;
        }

        let optimistic_gear = Stats::from_fn(|stat| {
            if (stat as usize) < stat_idx {
                0.
            } else {
                5. * num_unassigned as f32
            }
        });
        let max_gear = gear + optimistic_gear;
        let max_m = self.evaluate_current(max_gear);
        if max_m > self.best_m {
            // Prune this branch.
            //
            // NB: This assumes that higher stats are always better.  This might not be true in
            // some cases!
            return;
        }

        let stat = Stat::from_index(stat_idx);
        for n in 0 ..= num_unassigned {
            self.cur.infusions[stat] = n as u8;
            let mut infusion_stats = Stats::from(0.);
            infusion_stats[stat] = 5. * n as f32;
            self.go_infusions(stat_idx + 1, num_unassigned - n, gear + infusion_stats);
            self.cur.infusions[stat] = 0;
        }
    }

    pub fn optimize(&mut self) {
        self.go_slots(0, Stats::default());
    }
}

/// Get an upper bound on the total stats that could be supplied by `n` infusions.
fn max_infusion_stats(n: usize) -> Stats {
    // The upper bound on infusions is +5 to all stats per infusion.
    Stats::from(5. * n as f32)
}

pub fn optimize_fine<C: CharacterModel>(
    ch: &C,
    cfg: &C::Config,
    slots: &[(GearSlot, Quality)],
    prefix_idxs: &[usize],
) -> (Vec<usize>, PerStat<u8>) {
    // Sort slots in decreasing order by amount of stats provided.  This results in us picking
    // prefixes for the biggest pieces first.
    let prefix_berserker = PREFIXES.iter().find(|p| p.name == "Berserker's").unwrap();
    let mut slots = slots.iter().enumerate().map(|(i, &(slot, quality))| {
        let power = GEAR_SLOTS[slot].calc_stats(prefix_berserker, quality).power;
        let weight = power / prefix_berserker.formulas.power.factor;
        SlotExt {
            orig_idx: i as u8,
            gear_slot: slot,
            quality,
            stat_weight: weight,
        }
    }).collect::<Vec<_>>();
    slots.sort_by_key(|s| Reverse(AssertTotal(s.stat_weight)));

    let prefixes = prefix_idxs.iter().map(|&i| PREFIXES[i]).collect::<Vec<_>>();

    let num_infusions = 0;
    let mut opt = Optimizer::new(ch, cfg, &slots, num_infusions, &prefixes);
    opt.optimize();

    eprintln!("tried = {}", opt.tried);
    eprintln!("best metric = {}", opt.best_m);
    let mut out = vec![0; slots.len()];
    for (slot, choice) in slots.iter().zip(opt.best_candidate.slot_prefixes.iter()) {
        out[slot.orig_idx as usize] = prefix_idxs[*choice as usize];
    }

    let infusions = opt.best_candidate.infusions;

    (out, infusions)
}
