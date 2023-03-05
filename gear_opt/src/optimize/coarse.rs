use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::gear::{GearSlot, Quality};
use crate::stats::Stats;


pub type PrefixWeights = [f32; NUM_PREFIXES];

pub fn calc_gear_stats(w: &PrefixWeights) -> Stats {
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
