use std::cmp::Reverse;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality, Prefix, StatFormula, PerQuality};
use crate::optimize::coarse::PrefixWeights;
use crate::stats::{Stats, PerStat, Stat};
use super::{AssertTotal, evaluate_config, calc_max_weight};


#[derive(Clone, Copy, Debug)]
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
    /// Coarse prefix weights.  Assigning a prefix to a slot adds the slot's `stat_weight` to the
    /// prefix's entry here.  For a complete candidate, these values must fall within the ranges
    /// given by `Optimizer::target_prefix_weights`.
    pub prefix_weights: Vec<f32>,
}

impl Candidate {
    pub fn new(num_slots: usize, num_prefixes: usize) -> Candidate {
        Candidate {
            slot_prefixes: vec![0; num_slots],
            infusions: 0.into(),
            prefix_weights: vec![0.; num_prefixes],
        }
    }
}

struct Optimizer<'a, C: CharacterModel> {
    ch: &'a C,
    cfg: &'a C::Config,
    slots: Vec<SlotExt>,
    num_infusions: usize,
    prefixes: &'a [Prefix],
    /// For each slot, an upper bound on the stats that could be provided by choosing prefixes from
    /// `prefixes` for this slot and all further slots.
    slot_remaining_stats: Vec<Stats>,
    /// For each slot, the sum of the `stat_weight`s of this slot and all further slots.
    slot_remaining_weight: Vec<f32>,
    /// Minimum and maximum allowed weight for each prefix.
    target_prefix_weights: Option<&'a [(f32, f32)]>,
    cur: Candidate,
    best_m: f32,
    best_candidate: Candidate,
    tried: usize,
}

impl<'a, C: CharacterModel> Optimizer<'a, C> {
    pub fn new(
        ch: &'a C,
        cfg: &'a C::Config,
        slots: &[(GearSlot, Quality)],
        num_infusions: usize,
        prefixes: &'a [Prefix],
        target_prefix_weights: Option<&'a [(f32, f32)]>,
    ) -> Optimizer<'a, C> {
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

        let mut slot_remaining_stats = vec![Stats::default(); slots.len()];
        let mut slot_remaining_weight = vec![0.; slots.len()];
        for i in (0 .. slots.len()).rev() {
            let slot = &slots[i];

            // Compute remaining stats
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

            // Compute remaining weight
            let prev_weight = slot_remaining_weight.get(i + 1).cloned().unwrap_or(0.);
            slot_remaining_weight[i] = prev_weight + slot.stat_weight;
        }
        eprintln!("all stats = {:#?}", slot_remaining_stats[0]);
        let max_weight = slot_remaining_weight[0];
        eprintln!("max weight = {:#?}", max_weight);

        let candidate = Candidate::new(slots.len(), prefixes.len());

        Optimizer {
            ch, cfg, slots, num_infusions, prefixes,
            slot_remaining_stats,
            slot_remaining_weight,
            target_prefix_weights,
            cur: candidate.clone(),
            best_m: 999999999.,
            best_candidate: candidate,
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

        if let Some(tpw) = self.target_prefix_weights {
            let max_inc = self.slot_remaining_weight[i];
            for (&w, &(lo, hi)) in self.cur.prefix_weights.iter().zip(tpw.iter()) {
                if w > hi || w + max_inc < lo {
                    // Prune this branch.  It's no longer possible to make this prefix's weight
                    // land within the target range by the time we finish building the candidate.
                    return;
                }
            }
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

        let slot = self.slots[i];

        for (j, prefix) in self.prefixes.iter().enumerate() {
            // Symmetry breaking: for runs of slots with identical weights, such as Ring1/Ring2 or
            // Shoulders/Gloves/Boots, require prefixes to run in increasing order across the
            // group.
            if i > 0 &&
                    slot.stat_weight == self.slots[i - 1].stat_weight &&
                    (j as u8) < self.cur.slot_prefixes[i - 1] {
                continue;
            }

            self.cur.slot_prefixes[i] = j as u8;
            if i < 2 {
                eprintln!("{:?}", &self.cur.slot_prefixes[.. i + 1]);
            }

            let old_prefix_weight = self.cur.prefix_weights[j];
            self.cur.prefix_weights[j] += slot.stat_weight;

            let slot_stats = GEAR_SLOTS[slot.gear_slot].calc_stats(prefix, slot.quality)
                .map(|_, x| x.round());
            self.go_slots(i + 1, gear + slot_stats);

            self.cur.prefix_weights[j] = old_prefix_weight;
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
    target_prefix_weights: Option<&PrefixWeights>,
) -> (Vec<usize>, PerStat<u8>) {
    let prefixes = prefix_idxs.iter().map(|&i| PREFIXES[i]).collect::<Vec<_>>();

    /// Fraction of `max_weight` by which the final prefix weights may overshoot or undershoot the
    /// target.
    const TARGET_PREFIX_WEIGHT_MARGIN: f32 = 0.10;
    let target_prefix_weights = target_prefix_weights.map(|pw| {
        let max_weight = calc_max_weight(slots);
        let margin = TARGET_PREFIX_WEIGHT_MARGIN * max_weight;
        prefix_idxs.iter().map(|&i| (f32::max(0., pw[i] - margin), pw[i] + margin))
            .collect::<Vec<_>>()
    });
    let target_prefix_weights = target_prefix_weights.as_ref().map(|x| x as &[_]);

    let num_infusions = 0;
    let mut opt = Optimizer::new(ch, cfg, &slots, num_infusions, &prefixes, target_prefix_weights);
    opt.optimize();

    eprintln!("final = {:#?}", opt.best_candidate);

    eprintln!("tried = {}", opt.tried);
    eprintln!("best metric = {}", opt.best_m);
    let mut out = vec![0; slots.len()];
    for (slot, choice) in opt.slots.iter().zip(opt.best_candidate.slot_prefixes.iter()) {
        out[slot.orig_idx as usize] = prefix_idxs[*choice as usize];
    }

    let infusions = opt.best_candidate.infusions;

    (out, infusions)
}
