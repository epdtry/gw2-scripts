define_effects! {
    pub enum Sigil;
    fn add_temporary(s, m);

    pub struct Agony: {
        m.condition_duration.bleed += 20.;
    };

    pub struct Smoldering: {
        m.condition_duration.burn += 20.;
    };
}
