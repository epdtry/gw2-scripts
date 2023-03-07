use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::{CharacterModel, Vary};
use crate::gear::{GearSlot, Quality};
use crate::stats::Stats;


pub type PrefixWeights = [f32; NUM_PREFIXES];


pub fn calc_gear_stats(pw: &PrefixWeights) -> Stats {
    let mut gear = Stats::default();
    for (&w, prefix) in pw.iter().zip(PREFIXES.iter()) {
        gear = gear + prefix.calc_stats_coarse(w);
    }
    gear
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

fn evaluate_config<C: CharacterModel>(ch: &C, gear: &Stats, cfg: &C::Config) -> f32 {
    let (stats, mods) = ch.calc_stats(gear, cfg);
    ch.evaluate(cfg, &stats, &mods)
}

fn report<C: CharacterModel>(_ch: &C, pw: &PrefixWeights, cfg: &C::Config, m: f32) {
    eprintln!("metric: {}", m);

    let mut lines = pw.iter().zip(PREFIXES.iter()).filter_map(|(&w, prefix)| {
        if w > 0.0 { Some((w, prefix.name)) } else { None }
    }).collect::<Vec<_>>();
    lines.sort_by(|&(w1, _), &(w2, _)| w2.partial_cmp(&w1).unwrap());
    for (w, name) in lines {
        eprintln!("{} = {}", name, w);
    }
    eprintln!("config = {:?}", cfg);
    eprintln!();
}

pub fn optimize_coarse<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> (PrefixWeights, C::Config) {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);

    let mut best_pw = [0.; NUM_PREFIXES];
    let mut best_cfg = <C::Config>::default();
    let mut best_m = 999999999.;

    for i in 0 .. NUM_PREFIXES {
        for j in 0 .. NUM_PREFIXES {
            let mut pw0 = [0.; NUM_PREFIXES];
            pw0[i] += max_weight * 2. / 3.;
            pw0[j] += max_weight * 1. / 3.;
            eprintln!("start: 2/3 {}, 1/3 {}", PREFIXES[i].name, PREFIXES[j].name);

            let cfg0 = <C::Config>::default();

            let (pw, cfg) = optimize_coarse_one(ch, max_weight, &pw0, &cfg0);
            let gear = calc_gear_stats(&pw);
            let m = evaluate_config(ch, &gear, &cfg);

            if m < best_m {
                best_pw = pw;
                best_cfg = cfg;
                best_m = m;
            }
        }
    }

    report(ch, &best_pw, &best_cfg, best_m);
    (best_pw, best_cfg)
}

fn optimize_coarse_one<C: CharacterModel>(
    ch: &C,
    max_weight: f32,
    pw0: &PrefixWeights,
    cfg0: &C::Config,
) -> (PrefixWeights, C::Config) {
    let mut pw = *pw0;
    let mut cfg = cfg0.clone();
    let gear = calc_gear_stats(&pw);
    let mut m = evaluate_config(ch, &gear, &cfg);

    for i in 0 .. 10 {
        let c_base = 0.85_f32.powi(i);

        let mut best_pw = pw;
        let mut best_cfg = cfg.clone();
        let mut best_m = m;
        let mut best_desc = String::new();

        // Try adjusting prefix weights
        for j in 0 .. NUM_PREFIXES {
            for k in 1 ..= 100 {
                let c = c_base * k as f32 / 100.;

                let mut new_pw = pw;
                for w in &mut new_pw {
                    *w *= 1. - c;
                }
                new_pw[j] += max_weight * c;

                let new_gear = calc_gear_stats(&new_pw);
                let new_m = evaluate_config(ch, &new_gear, &cfg);

                if new_m < best_m {
                    best_pw = new_pw;
                    best_cfg = cfg.clone();
                    best_m = new_m;
                    best_desc = format!("using {} points of {}", c * 100., PREFIXES[j].name);
                }
            }
        }

        // Try adjusting config
        let gear = calc_gear_stats(&pw);
        for field in 0 .. cfg.num_fields() {
            for value in 0 .. cfg.num_field_values(field) {
                let mut new_cfg = cfg.clone();
                new_cfg.set_field(field, value);
                let new_m = evaluate_config(ch, &gear, &new_cfg);
                if new_m < best_m {
                    best_desc = format!("using config {:?}", new_cfg);
                    best_pw = pw;
                    best_cfg = new_cfg;
                    best_m = new_m;
                }
            }
        }


        if best_desc.len() > 0 {
            eprintln!("iteration {}: improved {} -> {} {}",
                i, m, best_m, best_desc);
        }

        pw = best_pw;
        cfg = best_cfg;
        m = best_m;
    }

    report(ch, &pw, &cfg, m);
    (pw, cfg)
}
