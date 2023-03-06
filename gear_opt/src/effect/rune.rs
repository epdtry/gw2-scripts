define_effects! {
    pub enum Rune;
    fn add_permanent(s, m);

    pub struct Elementalist: {
        s.power += 175.;
        s.condition_damage += 225.;
        m.condition_duration += 10.;
    };

    pub struct Krait: {
        s.condition_damage += 175.;
        m.condition_duration.bleed += 50.;
    };
}
