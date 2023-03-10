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
    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers) {}

    fn apply(&self, stats: &mut Stats, mods: &mut Modifiers) {
        self.add_permanent(stats, mods);
        self.distribute(stats, mods);
        self.add_temporary(stats, mods);
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
    where F: Fn(&mut Stats, &mut Modifiers), Self: Sized {
        Chain(self, AddTemporary(f))
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

    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers) {
        self.0.add_temporary(stats, mods);
        self.1.add_temporary(stats, mods);
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

impl<F: Fn(&mut Stats, &mut Modifiers)> Effect for AddTemporary<F> {
    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers) {
        (self.0)(stats, mods);
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

    fn add_temporary(&self, stats: &mut Stats, mods: &mut Modifiers) {
        if let Some(ref x) = *self {
            x.add_temporary(stats, mods);
        }
    }
}
