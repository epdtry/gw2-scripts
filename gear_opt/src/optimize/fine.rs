use std::cmp::Reverse;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality, Prefix};
use crate::optimize::coarse::PrefixWeights;
use crate::stats::Stats;
use super::{AssertTotal, evaluate_config};


struct SlotExt {
    orig_idx: u8,
    gear_slot: GearSlot,
    quality: Quality,
    stat_weight: f32,
}

#[derive(Clone, Debug)]
struct Candidate {
    slot_prefixes: Vec<u8>,
}

impl Candidate {
    pub fn new(num_slots: usize) -> Candidate {
        Candidate {
            slot_prefixes: vec![0; num_slots],
        }
    }
}

struct Optimizer<'a, C: CharacterModel> {
    ch: &'a C,
    cfg: &'a C::Config,
    slots: &'a [SlotExt],
    prefixes: &'a [Prefix],
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
        prefixes: &'a [Prefix],
    ) -> Optimizer<'a, C> {
        Optimizer {
            ch, cfg, slots, prefixes,
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

    fn go(&mut self, i: usize, gear: Stats) {
        if i >= self.slots.len() {
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
            self.go(i + 1, gear + slot_stats);
        }
    }

    pub fn optimize(&mut self) {
        self.go(0, Stats::default());
    }
}

pub fn optimize_fine<C: CharacterModel>(
    ch: &C,
    cfg: &C::Config,
    slots: &[(GearSlot, Quality)],
    prefix_idxs: &[usize],
) -> Vec<usize> {
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

    let mut opt = Optimizer::new(ch, cfg, &slots, &prefixes);
    opt.optimize();

    eprintln!("tried = {}", opt.tried);
    eprintln!("best metric = {}", opt.best_m);
    let mut out = vec![0; slots.len()];
    for (slot, choice) in slots.iter().zip(opt.best_candidate.slot_prefixes.iter()) {
        out[slot.orig_idx as usize] = prefix_idxs[*choice as usize];
    }

    out
}
