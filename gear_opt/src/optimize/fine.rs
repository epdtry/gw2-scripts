use std::cmp::Reverse;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality, Prefix};
use crate::optimize::coarse::PrefixWeights;
use crate::stats::Stats;
use super::{AssertTotal, evaluate_config};


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
        (i as u8, slot, quality, weight)
    }).collect::<Vec<_>>();
    slots.sort_by_key(|&(_, _, _, w)| Reverse(AssertTotal(w)));

    let prefixes = prefix_idxs.iter().map(|&i| PREFIXES[i]).collect::<Vec<_>>();

    // The prefix chosen for each slot.  Each value is an index into `prefix_idxs`/`prefixes`.
    let mut choices = vec![0; slots.len()];
    let mut best = (999999999., vec![0; slots.len()]);
    let mut tried = 0;

    fn go<C: CharacterModel>(
        ch: &C,
        cfg: &C::Config,
        slots: &[(u8, GearSlot, Quality, f32)],
        prefixes: &[Prefix],
        choices: &mut [u8],
        best: &mut (f32, Vec<u8>),
        tried: &mut usize,
        i: usize,
        gear: Stats,
    ) {
        if i >= slots.len() {
            *tried += 1;
            let m = evaluate_config(ch, &gear, &cfg);
            let (ref mut best_m, ref mut best_choices) = *best;
            if m < *best_m {
                *best_m = m;
                *best_choices = choices.to_owned();
                eprintln!("metric = {}", m);
                eprintln!("gear = {:?}", gear);
                eprintln!();
            }
            return;
        }

        let (_orig_idx, slot, quality, weight) = slots[i];

        for (j, prefix) in prefixes.iter().enumerate() {
            let j = j as u8;

            // Symmetry breaking: for runs of slots with identical weights, such as Ring1/Ring2 or
            // Shoulders/Gloves/Boots, require prefixes to run in increasing order across the
            // group.
            if i > 0 && weight == slots[i - 1].3 && j < choices[i - 1] {
                continue;
            }

            choices[i] = j as u8;

            if i < 2 {
                eprintln!("{:?}", &choices[.. i + 1]);
            }

            let slot_stats = GEAR_SLOTS[slot].calc_stats(prefix, quality)
                .map(|_, x| x.round());
            go(ch, cfg, slots, prefixes, choices, best, tried, i + 1, gear + slot_stats);
        }
    }

    go(
        ch,
        cfg,
        &slots,
        &prefixes,
        &mut choices,
        &mut best,
        &mut tried,
        0,
        Stats::default(),
    );

    let (ref best_m, ref best_choices) = best;
    eprintln!("tried = {}", tried);
    //eprintln!("slots = {:?}", slots);
    //eprintln!("prefix_idxs = {:?}", prefix_idxs);
    //eprintln!("best_choices = {:?}", best_choices);
    eprintln!("best metric = {}", best_m);
    let mut out = vec![0; slots.len()];
    for (&(orig_idx, _, _, _), choice) in slots.iter().zip(best_choices.iter()) {
        out[orig_idx as usize] = prefix_idxs[*choice as usize];
    }

    out
}
