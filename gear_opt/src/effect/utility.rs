define_effects! {
    pub enum Utility;
    fn distribute(s, m);

    pub struct ToxicCrystal: {
        s.condition_damage += s.power * 0.03;
        s.condition_damage += s.precision * 0.03;
    };
}
