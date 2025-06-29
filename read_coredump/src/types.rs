use crate::Pod;


#[repr(C)]
pub struct ItemDef {
    pub _unk0: [u8; 40],
    pub id: u32,
    pub type_: ItemType,
    pub _unk1: [u8; 48],
    pub rarity: Rarity,
}
unsafe impl Pod for ItemDef {}

#[repr(C)]
pub struct Item {
    pub _unk0: [u8; 64],
    pub def: u64,
    pub _unk1: [u8; 144],
    pub count: u8,
}
unsafe impl Pod for Item {}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
#[repr(C)]
pub struct ItemType(pub u32);
#[allow(bad_style)]
impl ItemType {
    pub const SalvageKit: ItemType = ItemType(19);
}
unsafe impl Pod for ItemType {}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
#[repr(C)]
pub struct Rarity(pub u32);
#[allow(bad_style)]
impl Rarity {
    pub const Basic: Rarity = Rarity(1);
    pub const Fine: Rarity = Rarity(2);
    pub const Masterwork: Rarity = Rarity(3);
    pub const Rare: Rarity = Rarity(4);
    pub const Exotic: Rarity = Rarity(5);
    pub const Ascended: Rarity = Rarity(6);
    pub const Legendary: Rarity = Rarity(7);
}
unsafe impl Pod for Rarity {}
