use crate::character::CombatSecond;
use crate::stats::{Stats, Modifiers};

#[macro_use] mod macros;
pub mod boon;
pub mod food;
pub mod rune;
pub mod sigil;
pub mod utility;

pub use self::food::{Food, KnownFood};
pub use self::rune::{Rune, KnownRune};
pub use self::sigil::{Sigil, KnownSigil};
pub use self::utility::{Utility, KnownUtility};


/// Represents an effect that influences the character's stats and/or modifiers.  Effects are
/// applied in three stages:
/// * `add_permanent`: Permanent additive effects, such as flat bonus stats from runes and traits.
/// * `distribute`: Multiplicative effects of the form "add X% of stat1 to stat2".
/// * `add_temporary`: Temporary additive effects, such as bonus stats from might and other buffs.
#[allow(unused_variables)]
pub trait Effect {
    fn add_permanent(&self, stats: &mut Stats, mods: &mut Modifiers) {}
    fn distribute(&self, stats: &mut Stats, mods: &mut Modifiers) {}
    /// Apply temporary effects, such as might/fury.
    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers, combat: &CombatSecond) {}
    /// Handle rune/sigil/trait procs.  Based on the combat events described in `events`, this adds
    /// new combat events to `c` representing any effect procs.
    ///
    /// For example, Superior Rune of Tormenting has the effect "gain Regeneration [for 3 seconds]
    /// after inflicting a foe with Torment. (Cooldown: 5 seconds)".  This would be implemented as
    /// follows:
    ///
    /// ```no_run
    /// let interval = proc_interval(5., events.condition.torment.interval());
    /// c.boon.regeneration += CombatEvent::single(3.) / interval;
    /// ```
    ///
    fn combat_procs(&self, events: &CombatSecond, combat: &mut CombatSecond) {}

    fn apply(
        &self,
        base_stats: Stats,
        base_mods: Modifiers,
        base_combat: CombatSecond,
    ) -> (Stats, Modifiers, CombatSecond) {
        let mut base_stats = base_stats;
        let mut base_mods = base_mods;
        self.add_permanent(&mut base_stats, &mut base_mods);
        self.distribute(&mut base_stats, &mut base_mods);

        // Calculate final stats (including temporary effects) and combat behavior in tandem.
        // These can affect each other; for example, the elementalist trait Raging Storm grants
        // fury on crit, so the amount of fury granted depends on the crit chance, and the crit
        // chance is increased by that additional fury.

        let mut stats = base_stats.clone();
        let mut mods = base_mods.clone();
        let mut combat = base_combat.clone();

        // We iterate a few times and hope the results converge.  There are some ways of setting up
        // proc chains, such as Sigil of Torment applying torment on crit and Rune of Tormenting
        // applying regen upon applying torment, but these are generally only a couple steps long.
        for i in 0 .. 5 {
            stats = base_stats.clone();
            mods = base_mods.clone();
            self.add_temporary(&mut stats, &mut mods, &combat);
            combat.update_crit(stats.crit_chance(&mods));

            let old_combat = combat;
            combat = base_combat.clone();
            self.combat_procs(&old_combat, &mut combat);
        }

        combat.update_crit(stats.crit_chance(&mods));
        (stats, mods, combat)
    }

    fn chain<E>(self, other: E) -> Chain<Self, E>
    where Self: Sized {
        Chain(self, other)
    }

    fn chain_add_permanent<F>(self, f: F) -> Chain<Self, AddPermanent<F>>
    where F: Fn(&mut Stats, &mut Modifiers), Self: Sized {
        Chain(self, AddPermanent(f))
    }

    fn chain_distribute<F>(self, f: F) -> Chain<Self, Distribute<F>>
    where F: Fn(&mut Stats, &mut Modifiers), Self: Sized {
        Chain(self, Distribute(f))
    }

    fn chain_add_temporary<F>(self, f: F) -> Chain<Self, AddTemporary<F>>
    where F: Fn(&mut Stats, &mut Modifiers, &CombatSecond), Self: Sized {
        Chain(self, AddTemporary(f))
    }

    fn chain_combat_procs<F>(self, f: F) -> Chain<Self, CombatProcs<F>>
    where F: Fn(&CombatSecond, &mut CombatSecond), Self: Sized {
        Chain(self, CombatProcs(f))
    }
}

/// A placeholder effect that changes nothing.
pub struct NoEffect;

impl Effect for NoEffect {}


pub struct Chain<T, U>(T, U);

impl<T: Effect, U: Effect> Effect for Chain<T, U> {
    fn add_permanent(&self, stats: &mut Stats, mods: &mut Modifiers) {
        self.0.add_permanent(stats, mods);
        self.1.add_permanent(stats, mods);
    }

    fn distribute(&self, stats: &mut Stats, mods: &mut Modifiers) {
        self.0.distribute(stats, mods);
        self.1.distribute(stats, mods);
    }

    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers, combat: &CombatSecond) {
        self.0.add_temporary(stats, mods, combat);
        self.1.add_temporary(stats, mods, combat);
    }

    fn combat_procs(&self, events: &CombatSecond, combat: &mut CombatSecond) {
        self.0.combat_procs(events, combat);
        self.1.combat_procs(events, combat);
    }
}

pub struct AddPermanent<F>(F);

impl<F: Fn(&mut Stats, &mut Modifiers)> Effect for AddPermanent<F> {
    fn add_permanent(&self, stats: &mut Stats, mods: &mut Modifiers) {
        (self.0)(stats, mods);
    }
}

pub struct Distribute<F>(F);

impl<F: Fn(&mut Stats, &mut Modifiers)> Effect for Distribute<F> {
    fn distribute(&self, stats: &mut Stats, mods: &mut Modifiers) {
        (self.0)(stats, mods);
    }
}

pub struct AddTemporary<F>(F);

impl<F: Fn(&mut Stats, &mut Modifiers, &CombatSecond)> Effect for AddTemporary<F> {
    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers, combat: &CombatSecond) {
        (self.0)(stats, mods, combat);
    }
}

pub struct CombatProcs<F>(F);

impl<F: Fn(&CombatSecond, &mut CombatSecond)> Effect for CombatProcs<F> {
    fn combat_procs(&self, events: &CombatSecond, combat: &mut CombatSecond) {
        (self.0)(events, combat);
    }
}

impl<E: Effect> Effect for Option<E> {
    fn add_permanent(&self, stats: &mut Stats, mods: &mut Modifiers) {
        if let Some(ref x) = *self {
            x.add_permanent(stats, mods);
        }
    }

    fn distribute(&self, stats: &mut Stats, mods: &mut Modifiers) {
        if let Some(ref x) = *self {
            x.distribute(stats, mods);
        }
    }

    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers, combat: &CombatSecond) {
        if let Some(ref x) = *self {
            x.add_temporary(stats, mods, combat);
        }
    }

    fn combat_procs(&self, events: &CombatSecond, combat: &mut CombatSecond) {
        if let Some(ref x) = *self {
            x.combat_procs(events, combat);
        }
    }
}


/// Compute how many times per second a passive effect will proc.  `icd` is the internal cooldown
/// of the passive and `trigger_frequency` is how often the triggering event happens.
pub fn proc_frequency(icd: f32, trigger_frequency: f32) -> f32 {
    if trigger_frequency <= 0. {
        return 0.;
    }

    let trigger_interval = 1. / trigger_frequency;
    if trigger_interval > icd {
        // The passive is always off cooldown when the triggering event happens.
        trigger_frequency
    } else {
        // When the passive comes off cooldown, assume we're halfway between the previous
        // triggering event and the next one, on average.
        1. / (icd + trigger_interval * 0.5)
    }
}
