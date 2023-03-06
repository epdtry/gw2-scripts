use crate::{GEAR_SLOTS, PREFIXES, NUM_PREFIXES};
use crate::character::CharacterModel;
use crate::effect::{Effect, Rune, Sigil, Food, Utility};
use crate::effect::{rune, sigil, food, utility};
use crate::gear::{GearSlot, Quality};
use crate::stats::{Stats, Modifiers, BASE_STATS};


pub type PrefixWeights = [f32; NUM_PREFIXES];

#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub prefix_weights: [f32; NUM_PREFIXES],
    pub rune: Rune,
    pub sigils: [Sigil; 2],
    pub food: Food,
    pub utility: Utility,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            prefix_weights: [0.; NUM_PREFIXES],
            rune: rune::NoRune.into(),
            sigils: [
                sigil::NoSigil.into(),
                sigil::NoSigil.into(),
            ],
            food: food::NoFood.into(),
            utility: utility::NoUtility.into(),
        }
    }
}

impl Config {
    pub fn effect<C: CharacterModel>(&self, ch: &C) -> impl Effect {
        let rune = if ch.vary_rune() { Some(self.rune) } else { None };
        let sigil0 = if ch.vary_sigils() >= 1 { Some(self.sigils[0]) } else { None };
        let sigil1 = if ch.vary_sigils() >= 2 && self.sigils[1] != self.sigils[0] {
            Some(self.sigils[1])
        } else {
            None
        };
        let food = if ch.vary_food() { Some(self.food) } else { None };
        let utility = if ch.vary_utility() { Some(self.utility) } else { None };
        rune.chain(sigil0).chain(sigil1).chain(food).chain(utility)
    }
}


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

fn evaluate_config<C: CharacterModel>(ch: &C, cfg: &Config) -> f32 {
    let gear = calc_gear_stats(&cfg.prefix_weights);
    let mut stats = BASE_STATS + gear;
    let mut mods = Modifiers::default();
    ch.apply_effects(cfg.effect(ch), &mut stats, &mut mods);
    ch.evaluate(&stats, &mods)
}

fn report<C: CharacterModel>(ch: &C, cfg: &Config, m: f32) {
    eprintln!("metric: {}", m);

    let mut lines = cfg.prefix_weights.iter().zip(PREFIXES.iter()).filter_map(|(&w, prefix)| {
        if w > 0.0 { Some((w, prefix.name)) } else { None }
    }).collect::<Vec<_>>();
    lines.sort_by(|&(w1, _), &(w2, _)| w2.partial_cmp(&w1).unwrap());
    for (w, name) in lines {
        eprintln!("{} = {}", name, w);
    }
    if ch.vary_rune() {
        eprintln!("rune = {}", cfg.rune.display_name());
    }
    for i in 0 .. ch.vary_sigils() as usize {
        eprintln!("sigil {} = {}", i + 1, cfg.sigils[i].display_name());
    }
    if ch.vary_food() {
        eprintln!("food = {}", cfg.food.display_name());
    }
    if ch.vary_utility() {
        eprintln!("utility = {}", cfg.utility.display_name());
    }
    eprintln!();
}

pub fn optimize_coarse<C: CharacterModel>(
    ch: &C,
    slots: &[(GearSlot, Quality)],
) -> Config {
    // Calculate the maximum weight to be distributed across all prefixes, which corresponds to the
    // total stats provided by the gear.
    let max_weight = calc_max_weight(slots);

    let mut best_cfg = Config::default();
    let mut best_m = 999999999.;

    for i in 0 .. NUM_PREFIXES {
        for j in 0 .. NUM_PREFIXES {
            let mut cfg0 = Config::default();
            cfg0.prefix_weights[i] += max_weight * 2. / 3.;
            cfg0.prefix_weights[j] += max_weight * 1. / 3.;
            eprintln!("start: 2/3 {}, 1/3 {}", PREFIXES[i].name, PREFIXES[j].name);

            let cfg = optimize_coarse_one(ch, max_weight, &cfg0);
            let m = evaluate_config(ch, &cfg);

            if m < best_m {
                best_cfg = cfg;
                best_m = m;
            }
        }
    }

    report(ch, &best_cfg, best_m);
    best_cfg
}

fn optimize_coarse_one<C: CharacterModel>(
    ch: &C,
    max_weight: f32,
    cfg0: &Config,
) -> Config {
    let mut cfg = *cfg0;
    let mut m = evaluate_config(ch, &cfg);

    for i in 0 .. 10 {
        let c_base = 0.85_f32.powi(i);

        let mut best_cfg = cfg;
        let mut best_m = m;
        let mut best_desc = String::new();

        // Try adjusting prefix weights
        for j in 0 .. NUM_PREFIXES {
            for k in 1 ..= 100 {
                let c = c_base * k as f32 / 100.;

                let mut new_cfg = cfg;
                for w in &mut new_cfg.prefix_weights {
                    *w *= 1. - c;
                }
                new_cfg.prefix_weights[j] += max_weight * c;

                let new_m = evaluate_config(ch, &new_cfg);

                if new_m < best_m {
                    best_cfg = new_cfg;
                    best_m = new_m;
                    best_desc = format!("using {} points of {}", c * 100., PREFIXES[j].name);
                }
            }
        }

        // Try adjusting runes
        if ch.vary_rune() {
            for rune in Rune::iter() {
                let mut new_cfg = cfg;
                new_cfg.rune = rune;

                let new_m = evaluate_config(ch, &new_cfg);

                if new_m < best_m {
                    best_cfg = new_cfg;
                    best_m = new_m;
                    best_desc = format!("using rune {:?}", rune);
                }
            }
        }

        for i in 0 .. ch.vary_sigils() as usize {
            for sigil in Sigil::iter() {
                let mut new_cfg = cfg;
                new_cfg.sigils[i] = sigil;

                let new_m = evaluate_config(ch, &new_cfg);

                if new_m < best_m {
                    best_cfg = new_cfg;
                    best_m = new_m;
                    best_desc = format!("using sigil {:?} in slot {}", sigil, i);
                }
            }
        }

        if ch.vary_food() {
            for food in Food::iter() {
                let mut new_cfg = cfg;
                new_cfg.food = food;

                let new_m = evaluate_config(ch, &new_cfg);

                if new_m < best_m {
                    best_cfg = new_cfg;
                    best_m = new_m;
                    best_desc = format!("using food {:?}", food);
                }
            }
        }

        if ch.vary_utility() {
            for utility in Utility::iter() {
                let mut new_cfg = cfg;
                new_cfg.utility = utility;

                let new_m = evaluate_config(ch, &new_cfg);

                if new_m < best_m {
                    best_cfg = new_cfg;
                    best_m = new_m;
                    best_desc = format!("using utility {:?}", utility);
                }
            }
        }

        if best_desc.len() > 0 {
            eprintln!("iteration {}: improved {} -> {} {}",
                i, m, best_m, best_desc);
        }

        cfg = best_cfg;
        m = best_m;
    }

    report(ch, &cfg, m);
    cfg
}
