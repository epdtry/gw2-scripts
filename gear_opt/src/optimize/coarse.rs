use std::cmp;
use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::{CharacterModel, Vary};
use crate::gear::{GearSlot, Quality};
use crate::stats::Stats;
use super::{AssertTotal, evaluate_config};


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

fn report<C: CharacterModel>(ch: &C, pw: &PrefixWeights, cfg: &C::Config, m: f32) {
    eprintln!("metric: {}", m);

    let mut lines = pw.iter().zip(PREFIXES.iter()).filter_map(|(&w, prefix)| {
        if w > 0.0 { Some((w, prefix.name)) } else { None }
    }).collect::<Vec<_>>();
    lines.sort_by_key(|&(w, _)| AssertTotal(-w));
    for (w, name) in lines {
        eprintln!("{} = {}", name, w);
    }
    eprintln!("config = {:?}", cfg);
    let gear = calc_gear_stats(&pw);
    eprintln!("gear stats = {:?}", gear.map(|_, x| x.round() as u32));
    let (stats, mods) = ch.calc_stats(&gear, &cfg);
    eprintln!("total stats = {:?}", stats.map(|_, x| x.round() as u32));
    eprintln!("modifiers = {:?}", mods);
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

    let cfg0 = <C::Config>::default();
    assert!(ch.is_config_valid(&cfg0));

    for i in 0 .. NUM_PREFIXES {
        for j in 0 .. NUM_PREFIXES {
            let mut pw0 = [0.; NUM_PREFIXES];
            pw0[i] += max_weight * 2. / 3.;
            pw0[j] += max_weight * 1. / 3.;
            eprintln!("start: 2/3 {}, 1/3 {}", PREFIXES[i].name, PREFIXES[j].name);

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

fn increase_prefix_weight(pw: &mut PrefixWeights, max_weight: f32, pi: usize, c: f32) {
    increase_prefix_weight_linear(pw, max_weight, pi, c)
        /*
    for w in &mut pw[..] {
        *w *= 1. - c;
    }
    pw[pi] += max_weight * c;
        */
}

/// Decrease the sum of weights in `pw` by `amount`.  The decrease is spread evenly across all
/// nonzero weights in `pw`.  If some weights are too small to reduce by their full share, then the
/// leftover amount is spread among the remaining weights.  For example, when `amount` is 5 and
/// the weights are `[5, 10, 1]`, we cannot subtract 5/3 from 1, so the excess 2/3 is distributed
/// to the other two weights, and the final result is `[3, 8, 0]`.
fn decrease_prefix_weights_linear(pw: &mut PrefixWeights, amount: f32) {
    let mut remaining = amount;
    let mut nonzero_count = pw.iter().filter(|&&w| w != 0.).count();
    while remaining > 0. && nonzero_count > 0 {
        let share = remaining / nonzero_count as f32;
        remaining = 0.;
        nonzero_count = 0;
        for w in pw.iter_mut() {
            if *w == 0. {
                continue;
            }
            if *w > share {
                *w -= share;
                nonzero_count += 1;
            } else {
                remaining += share - *w;
                *w = 0.;
            }
        }
    }
}

fn increase_prefix_weight_linear(pw: &mut PrefixWeights, max_weight: f32, pi: usize, c: f32) {
    let excess = pw.iter().cloned().sum::<f32>() + max_weight * c - max_weight;
    if excess > 0. {
        decrease_prefix_weights_linear(pw, excess);
    }
    pw[pi] += max_weight * c;
}

fn optimize_coarse_one<C: CharacterModel>(
    ch: &C,
    max_weight: f32,
    pw0: &PrefixWeights,
    cfg0: &C::Config,
) -> (PrefixWeights, C::Config) {
    optimize_coarse_one_ex(
        ch,
        max_weight,
        pw0,
        cfg0,
        Hold::None,
        |_, _, _| {},
    )
}

enum Hold {
    None,
    Prefix(usize, f32),
    Field(usize),
}

fn optimize_coarse_one_ex<C: CharacterModel>(
    ch: &C,
    max_weight: f32,
    pw0: &PrefixWeights,
    cfg0: &C::Config,
    hold: Hold,
    mut callback: impl FnMut(&PrefixWeights, &C::Config, f32),
) -> (PrefixWeights, C::Config) {
    let mut pw = *pw0;
    let mut cfg = cfg0.clone();
    let gear = calc_gear_stats(&pw);
    let mut m = evaluate_config(ch, &gear, &cfg);

    for i in 0 .. 20 {
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
                increase_prefix_weight(&mut new_pw, max_weight, j, c);

                if let Hold::Prefix(pi, x) = hold {
                    let w0 = new_pw[pi];
                    if w0 < x {
                        // Select `c` such that `new_pw[pi]` will be `x` after the adjustment.
                        let c = (x - w0) / (max_weight - w0);
                        increase_prefix_weight(&mut new_pw, max_weight, pi, c);
                        debug_assert!((new_pw[pi] - x).abs() < 1e-4);
                    }
                }

                let new_gear = calc_gear_stats(&new_pw);
                let new_m = evaluate_config(ch, &new_gear, &cfg);
                callback(&new_pw, &cfg, new_m);

                if new_m < best_m {
                    best_pw = new_pw;
                    best_cfg = cfg.clone();
                    best_m = new_m;
                    //best_desc = format!("using {} points of {}", c * 100., PREFIXES[j].name);
                }
            }
        }

        // Try adjusting config
        let gear = calc_gear_stats(&pw);
        for field in 0 .. cfg.num_fields() {
            if let Hold::Field(fi) = hold {
                if field == fi {
                    continue;
                }
            }
            for value in 0 .. cfg.num_field_values(field) {
                let mut new_cfg = cfg.clone();
                new_cfg.set_field(field, value);
                if !ch.is_config_valid(&new_cfg) {
                    continue;
                }
                let new_m = evaluate_config(ch, &gear, &new_cfg);
                callback(&pw, &new_cfg, new_m);
                if new_m < best_m {
                    //best_desc = format!("using config {:?}", new_cfg);
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

    //report(ch, &pw, &cfg, m);
    (pw, cfg)
}


/// Locally optimize from one starting point per field.
pub fn optimize_coarse_scan<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> (PrefixWeights, C::Config) {
    let max_weight = calc_max_weight(slots);

    let cfg0 = <C::Config>::default();

    let mut best_pw = [0.; NUM_PREFIXES];
    let mut best_cfg = cfg0.clone();
    assert!(ch.is_config_valid(&best_cfg));
    let mut best_m = 999999999.;

    let mut try_one = |new_pw0, new_cfg0| {
        let (new_pw, new_cfg) = optimize_coarse_one(ch, max_weight, &new_pw0, &new_cfg0);

        let new_gear = calc_gear_stats(&new_pw);
        let new_m = evaluate_config(ch, &new_gear, &new_cfg);

        if new_m < best_m {
            best_pw = new_pw;
            best_cfg = new_cfg;
            best_m = new_m;
            report(ch, &best_pw, &best_cfg, best_m);
        }
    };

    for pi in 0 .. NUM_PREFIXES {
        let mut new_pw0 = [0.; NUM_PREFIXES];
        new_pw0[pi] = max_weight;
        let new_cfg0 = <C::Config>::default();
        try_one(new_pw0, new_cfg0);
    }

    for field in 0 .. cfg0.num_fields() {
        for value in 0 .. cfg0.num_field_values(field) {
            let new_pw0 = [0.; NUM_PREFIXES];
            let mut new_cfg0 = cfg0.clone();
            new_cfg0.set_field(field, value);
            if !ch.is_config_valid(&new_cfg0) {
                continue;
            }

            try_one(new_pw0, new_cfg0);
        }
    }

    (best_pw, best_cfg)
}


pub fn optimize_coarse_anneal<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> (PrefixWeights, C::Config) {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);

    let mut pw = [0.; NUM_PREFIXES];
    let mut cfg = <C::Config>::default();
    assert!(ch.is_config_valid(&cfg));
    let mut m = 999999999.;

    let mut best_pw = pw;
    let mut best_cfg = cfg.clone();
    let mut best_m = m;

    let mut rng = StdRng::seed_from_u64(1234567);

    for iteration in 0 .. {
        let mut new_pw = pw;
        let mut new_cfg = cfg.clone();

        let i = rng.gen_range(-1 .. cfg.num_fields() as isize);
        if i == -1 {
            // Adjust prefix weights
            let pi = rng.gen_range(0 .. NUM_PREFIXES);
            let c = if rng.gen_bool(0.5) { 1.0 } else { rng.gen_range(0. .. 1.) };
            increase_prefix_weight(&mut new_pw, max_weight, pi, c);
        } else {
            let field = i as usize;
            let value = rng.gen_range(0 .. cfg.num_field_values(field));
            new_cfg.set_field(field, value);
            if !ch.is_config_valid(&new_cfg) {
                continue;
            }
        }

        let new_gear = calc_gear_stats(&new_pw);
        let new_m = evaluate_config(ch, &new_gear, &cfg);

        let t = 100. / (1. + iteration as f32 / 10.);
        let accept = new_m < m || rng.gen_bool((-(new_m - m) / t).exp() as f64);

        if accept {
            pw = new_pw;
            cfg = new_cfg;
            m = new_m;
        }

        if m < best_m {
            best_pw = pw;
            best_cfg = cfg.clone();
            best_m = m;
            report(ch, &best_pw, &best_cfg, best_m);
        }
    }

    (best_pw, best_cfg)
}


pub fn optimize_coarse_basin_hopping<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
    iter_limit: Option<usize>,
) -> (PrefixWeights, C::Config) {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);

    let (pw, cfg) = optimize_coarse_scan(ch, slots);
    let gear = calc_gear_stats(&pw);
    let m = evaluate_config(ch, &gear, &cfg);

    let mut best_pw = pw;
    let mut best_cfg = cfg;
    let mut best_m = m;

    eprintln!("initial:");
    report(ch, &best_pw, &best_cfg, best_m);

    let mut rng = StdRng::seed_from_u64(1234567);

    for iteration in 0 .. iter_limit.unwrap_or(usize::MAX) {
        let mut new_pw0 = best_pw;
        let mut new_cfg0 = best_cfg.clone();

        let n = rng.gen_range(1 .. 10);
        for _ in 0 .. n {
            let i = rng.gen_range(-1 .. new_cfg0.num_fields() as isize);
            if i == -1 {
                // Adjust prefix weights
                let pi = rng.gen_range(0 .. NUM_PREFIXES);
                let c = rng.gen_range(0. .. 1.);
                increase_prefix_weight_linear(&mut new_pw0, max_weight, pi, c);
            } else {
                let field = i as usize;
                loop {
                    let value = rng.gen_range(0 .. new_cfg0.num_field_values(field));
                    let old_value = new_cfg0.get_field(field);
                    new_cfg0.set_field(field, value);
                    if !ch.is_config_valid(&new_cfg0) {
                        new_cfg0.set_field(field, old_value);
                    } else {
                        break;
                    }
                }
            }
        }

        let (new_pw, new_cfg) = optimize_coarse_one(ch, max_weight, &new_pw0, &new_cfg0);
        let new_gear = calc_gear_stats(&new_pw);
        let new_m = evaluate_config(ch, &new_gear, &new_cfg);

        if new_m < best_m {
            best_pw = new_pw;
            best_cfg = new_cfg.clone();
            best_m = new_m;
            eprintln!("iteration {}:", iteration);
            report(ch, &best_pw, &best_cfg, best_m);
        }
    }

    (best_pw, best_cfg)
}


fn record_best_m<C: CharacterModel>(
    best_m_for_prefix: &mut [f32; NUM_PREFIXES],
    best_m_for_field_value: &mut [Vec<f32>],
    pw: &PrefixWeights,
    cfg: &C::Config,
    m: f32,
) {
    for i in 0 .. NUM_PREFIXES {
        if pw[i] < 400. {
            continue;
        }
        if m < best_m_for_prefix[i] {
            best_m_for_prefix[i] = m;
        }
    }

    for i in 0 .. cfg.num_fields() {
        let v = cfg.get_field(i);
        if m < best_m_for_field_value[i][v as usize] {
            best_m_for_field_value[i][v as usize] = m;
        }
    }
}

pub fn optimize_coarse_randomized<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> (PrefixWeights, C::Config) {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);
    let cfg0 = <C::Config>::default();
    assert!(ch.is_config_valid(&cfg0));

    let mut best_pw = [0.; NUM_PREFIXES];
    let mut best_cfg = <C::Config>::default();
    let mut best_m = 999999999.;

    let mut best_m_for_prefix = [best_m; NUM_PREFIXES];
    let mut best_m_for_field_value = Vec::with_capacity(cfg0.num_fields());
    for i in 0 .. cfg0.num_fields() {
        best_m_for_field_value.push(vec![best_m; cfg0.num_field_values(i) as usize]);
    }

    const PREFIX_HOLD_FACTOR: f32 = 0.4;

    for i in 0 .. NUM_PREFIXES {
        let mut pw0 = [0.; NUM_PREFIXES];
        pw0[i] = max_weight;
        eprintln!("start: {}", PREFIXES[i].name);

        let (pw, cfg) = optimize_coarse_one_ex(ch, max_weight, &pw0, &cfg0,
            Hold::Prefix(i, PREFIX_HOLD_FACTOR * max_weight),
            |pw, cfg, m| record_best_m::<C>(
                &mut best_m_for_prefix,
                &mut best_m_for_field_value,
                pw, cfg, m,
            ));
        let gear = calc_gear_stats(&pw);
        let m = evaluate_config(ch, &gear, &cfg);

        if m < best_m {
            best_pw = pw;
            best_cfg = cfg;
            best_m = m;
        }
    }

    for i in 0 .. cfg0.num_fields() {
        for x in 0 .. cfg0.num_field_values(i) {
            let pw0 = [0.; NUM_PREFIXES];

            let mut cfg0 = cfg0.clone();
            cfg0.set_field(i, x);
            if !ch.is_config_valid(&cfg0) {
                continue;
            }
            eprintln!("start: config {:?}", cfg0);

            let (pw, cfg) = optimize_coarse_one_ex(ch, max_weight, &pw0, &cfg0, Hold::Field(i),
                |pw, cfg, m| record_best_m::<C>(
                    &mut best_m_for_prefix,
                    &mut best_m_for_field_value,
                    pw, cfg, m,
                ));
            let gear = calc_gear_stats(&pw);
            let m = evaluate_config(ch, &gear, &cfg);

            if m < best_m {
                best_pw = pw;
                best_cfg = cfg;
                best_m = m;
            }
        }
    }

    const SKEW_FACTOR: f32 = 1./5.;
    //const SKEW_EXPONENT: f32 = -1. / SKEW_FACTOR.log2();
    fn skew(x: f32) -> f32 {
        #[allow(bad_style)]
        let SKEW_EXPONENT: f32 = -1. / SKEW_FACTOR.log2();
        x.powf(SKEW_EXPONENT)
    }
    debug_assert_eq!(skew(0.), 0.);
    debug_assert_eq!(skew(1.), 1.);
    fn pick<T: Copy>(rng: &mut impl Rng, xs: &[T]) -> T {
        debug_assert!(xs.len() > 0);
        let r = rng.gen::<f32>();
        let f = (1. - skew(r)) * xs.len() as f32;
        let i = cmp::min(xs.len() - 1, f.floor() as usize);
        xs[i]
    }


    let mut rng = StdRng::seed_from_u64(1234567);

    eprintln!("\ninitial best:");
    report(ch, &best_pw, &best_cfg, best_m);

    for iteration in 0 .. {
        let mut prefix_order = (0 .. NUM_PREFIXES).collect::<Vec<_>>();
        prefix_order.sort_by_key(|&i| AssertTotal(best_m_for_prefix[i]));

        let mut field_value_orders = (0 .. cfg0.num_fields())
            .map(|i| (0 .. cfg0.num_field_values(i)).collect::<Vec<_>>())
            .collect::<Vec<_>>();
        for (i, fvo) in field_value_orders.iter_mut().enumerate() {
            fvo.sort_by_key(|&x| AssertTotal(best_m_for_field_value[i][x as usize]));
        }


        let mut pw0 = [0.; NUM_PREFIXES];
        let pi = pick(&mut rng, &prefix_order);
        let pj = pick(&mut rng, &prefix_order);
        let c = rng.gen_range(0.5 .. 1.0_f32);
        //let c = 2./3.;
        pw0[pi] = max_weight * c;
        pw0[pj] = max_weight * (1. - c);

        let mut cfg0 = cfg0.clone();
        for fi in 0 .. cfg0.num_fields() {
            let x = pick(&mut rng, &field_value_orders[fi]);
            cfg0.set_field(fi, x);
        }

        let (pw, cfg) = optimize_coarse_one_ex(ch, max_weight, &pw0, &cfg0, Hold::None,
            |pw, cfg, m| record_best_m::<C>(
                &mut best_m_for_prefix,
                &mut best_m_for_field_value,
                pw, cfg, m,
            ));
        let gear = calc_gear_stats(&pw);
        let m = evaluate_config(ch, &gear, &cfg);

        if m < best_m {
            eprintln!("\niteration {}:", iteration);
            report(ch, &pw, &cfg, m);

            best_pw = pw;
            best_cfg = cfg.clone();
            best_m = m;
        }


        for subiter in 0 .. 5 {
            let mut pw0 = pw;
            let pi = pick(&mut rng, &prefix_order);
            let c = rng.gen_range(0. .. 0.25_f32);
            increase_prefix_weight(&mut pw0, max_weight, pi, c);
            let mut cfg0 = cfg.clone();

            let (pw, cfg) = optimize_coarse_one_ex(ch, max_weight, &pw0, &cfg0,
                Hold::Prefix(pi, c * max_weight),
                |pw, cfg, m| record_best_m::<C>(
                    &mut best_m_for_prefix,
                    &mut best_m_for_field_value,
                    pw, cfg, m,
                ));
            let gear = calc_gear_stats(&pw);
            let m = evaluate_config(ch, &gear, &cfg);

            if m < best_m {
                eprintln!("\niteration {} (alt {}):", iteration, subiter);
                report(ch, &pw, &cfg, m);

                best_pw = pw;
                best_cfg = cfg;
                best_m = m;
            }
        }
    }

    report(ch, &best_pw, &best_cfg, best_m);
    (best_pw, best_cfg)
}


#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_decrease_prefix_weights_linear() {
        let mut pw = [0.; NUM_PREFIXES];
        pw[0] = 5.;
        pw[1] = 10.;
        pw[2] = 1.;
        decrease_prefix_weights_linear(&mut pw, 5.);
        assert!((pw[0] - 3.).abs() < 1e-6);
        assert!((pw[1] - 8.).abs() < 1e-6);
        assert!((pw[2] - 0.).abs() < 1e-6);
    }
}
