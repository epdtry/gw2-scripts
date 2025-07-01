use std::fmt;
use crate::{Memory, Pod};


#[repr(C)]
pub struct AnetArray {
    pub data: u64,
    // TODO: figure out which field is length and which is capacity
    pub len: u32,
    pub cap: u32,
}
unsafe impl Pod for AnetArray {}

/// `CharClient::CInventory`
#[repr(C)]
pub struct CharInventory {
    pub _unk0: [u8; 200],
    /// `m_inventorySlots`
    pub slots: AnetArray,
}
unsafe impl Pod for CharInventory {}

impl CharInventory {
    pub fn slots<'a>(&self, mem: &Memory<'a>) -> &'a [u64] {
        self.get_slots(mem).unwrap()
    }

    pub fn get_slots<'a>(&self, mem: &Memory<'a>) -> Option<&'a [u64]> {
        mem.get_slice(self.slots.data, self.slots.len as usize)
    }
}

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
    pub vtable: u64,
    pub _unk0: [u8; 56],
    pub def: u64,
}
unsafe impl Pod for Item {}

impl Item {
    pub fn def<'a>(&self, mem: &Memory<'a>) -> &'a ItemDef {
        self.get_def(mem).unwrap()
    }

    pub fn get_def<'a>(&self, mem: &Memory<'a>) -> Option<&'a ItemDef> {
        mem.get(self.def)
    }

    pub fn count(&self, mem: &Memory) -> Option<u8> {
        unsafe {
            Some(match self.get_def(mem)?.type_ {
                // Non-stackable types
                ItemType::Armor |
                ItemType::Back |
                ItemType::JadeTechModule |
                ItemType::Trinket |
                ItemType::Weapon => 1,
                // Types with known count fields
                // TODO: add Memory method to map `self` ptr back to an address, then call `get`
                ItemType::Consumable => mem.cast::<_, Item_Consumable>(self)?.count,
                ItemType::Container =>
                    (*(self as *const Item).cast::<Item_Container>()).count,
                ItemType::CraftingMaterial =>
                    (*(self as *const Item).cast::<Item_CraftingMaterial>()).count,
                ItemType::Trophy =>
                    (*(self as *const Item).cast::<Item_Trophy>()).count,
                ItemType::UpgradeComponent =>
                    (*(self as *const Item).cast::<Item_UpgradeComponent>()).count,
                _ => return None,
            })
        }
    }
}

#[repr(C)]
pub struct Item_Consumable {
    pub base: Item,
    pub _unk0: [u8; 88],
    pub count: u8,
}
unsafe impl Pod for Item_Consumable {}

#[repr(C)]
pub struct Item_Container {
    pub base: Item,
    pub _unk0: [u8; 88],
    pub count: u8,
}
unsafe impl Pod for Item_Container {}

#[repr(C)]
pub struct Item_CraftingMaterial {
    pub base: Item,
    pub _unk0: [u8; 88],
    pub count: u8,
}
unsafe impl Pod for Item_CraftingMaterial {}

#[repr(C)]
pub struct Item_Gizmo {
    pub base: Item,
    pub _unk0: [u8; 88],
    /// Note: count is only valid if the gizmo is stackable
    pub count: u8,
}
unsafe impl Pod for Item_Gizmo {}

#[repr(C)]
pub struct Item_Tool {
    pub base: Item,
    pub _unk0: [u8; 88],
    pub count: u8,
}
unsafe impl Pod for Item_Tool {}

#[repr(C)]
pub struct Item_Trophy {
    pub base: Item,
    pub _unk0: [u8; 88],
    pub count: u8,
}
unsafe impl Pod for Item_Trophy {}

#[repr(C)]
pub struct Item_UpgradeComponent {
    pub base: Item,
    pub _unk0: [u8; 144],
    pub count: u8,
}
unsafe impl Pod for Item_UpgradeComponent {}

macro_rules! define_enum {
    ($vis:vis enum $Enum:ident($Inner:ty) {
        $( $Variant:ident = $discr:expr, )*
    }) => {
        #[derive(Clone, Copy, PartialEq, Eq, Hash)]
        #[repr(C)]
        $vis struct $Enum(pub $Inner);
        #[allow(bad_style)]
        impl $Enum {
            $( pub const $Variant: $Enum = $Enum($discr); )*
        }
        unsafe impl Pod for $Enum {}

        impl fmt::Debug for $Enum {
            fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
                match self.0 {
                    $( $discr => f.write_str(stringify!($Variant)), )*
                    x => f.debug_tuple(stringify!($Enum)).field(&x).finish(),
                }
            }
        }
    };
}

define_enum! {
    pub enum ItemType(u32) {
        Armor = 0,
        Back = 2,
        Consumable = 4,
        Container = 5,
        CraftingMaterial = 6,
        Gathering = 9,
        Gizmo = 10,
        JadeTechModule = 11,
        Tool = 19,
        Trinket = 21,
        Trophy = 22,
        UpgradeComponent = 23,
        Weapon = 24,
    }
}

/*
#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
#[repr(C)]
pub struct ItemType(pub u32);
#[allow(bad_style)]
impl ItemType {
    pub const Consumable: ItemType = ItemType(4);
    pub const Container: ItemType = ItemType(5);
    pub const Gathering: ItemType = ItemType(9);
    pub const Gizmo: ItemType = ItemType(10);
    pub const Tool: ItemType = ItemType(19);
}
unsafe impl Pod for ItemType {}
*/

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
