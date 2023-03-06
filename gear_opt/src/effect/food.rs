define_effects! {
    pub enum Food;
    fn add_temporary(s, m);

    pub struct PotatoLeekSoup: {
        s.precision += 100.;
        s.condition_damage += 70.;
    };

    pub struct RedLentilSaobosa: {
        s.expertise += 100.;
        s.condition_damage += 70.;
    };
}
