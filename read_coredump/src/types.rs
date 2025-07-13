use std::fmt;
use crate::{Memory, Pod};


#[derive(Debug)]
#[repr(C)]
pub struct AnetArray {
    pub data: u64,
    pub cap: u32,
    pub len: u32,
}
unsafe impl Pod for AnetArray {}

#[derive(Debug)]
#[repr(C)]
pub struct AnetHashTable {
    pub cap: u32,
    pub len: u32,
    pub data: u64,
}
unsafe impl Pod for AnetHashTable {}

#[repr(C)]
pub struct Character {
    pub vtable0: u64,
    pub vtable1: u64,
    pub _unk0: [u8; 16],
    pub inventory: u64,
    pub wallet: u64,
}
unsafe impl Pod for Character {}

impl Character {
    pub fn inventory<'a>(&self, mem: &Memory<'a>) -> &'a CharInventory {
        self.get_inventory(mem).unwrap()
    }

    pub fn get_inventory<'a>(&self, mem: &Memory<'a>) -> Option<&'a CharInventory> {
        mem.get(self.inventory)
    }

    pub fn wallet<'a>(&self, mem: &Memory<'a>) -> &'a CharWallet {
        self.get_wallet(mem).unwrap()
    }

    pub fn get_wallet<'a>(&self, mem: &Memory<'a>) -> Option<&'a CharWallet> {
        mem.get(self.wallet)
    }
}

#[repr(C)]
pub struct CharWallet {
    pub vtable: u64,
    pub entries: AnetHashTable,
}
unsafe impl Pod for CharWallet {}

impl CharWallet {
    pub fn entries<'a>(&self, mem: &Memory<'a>) -> &'a [WalletEntry] {
        self.get_entries(mem).unwrap()
    }

    pub fn get_entries<'a>(&self, mem: &Memory<'a>) -> Option<&'a [WalletEntry]> {
        mem.get_slice(self.entries.data, self.entries.cap as usize)
    }
}

/// These are hash table entries.
#[derive(Debug)]
#[repr(C)]
pub struct WalletEntry {
    pub currency_id: u32,
    pub amount: u32,
    pub hash: u32,
}
unsafe impl Pod for WalletEntry {}

/// `CharClient::CInventory`
#[repr(C)]
pub struct CharInventory {
    pub _unk0: [u8; 200],
    /// `m_inventorySlots`
    pub slots: AnetArray,
    pub _unk1: [u8; 48],
    pub shared_slots: AnetArray,
}
unsafe impl Pod for CharInventory {}

impl CharInventory {
    pub fn slots<'a>(&self, mem: &Memory<'a>) -> &'a [u64] {
        self.get_slots(mem).unwrap()
    }

    pub fn get_slots<'a>(&self, mem: &Memory<'a>) -> Option<&'a [u64]> {
        mem.get_slice(self.slots.data, self.slots.len as usize)
    }

    pub fn shared_slots<'a>(&self, mem: &Memory<'a>) -> &'a [u64] {
        self.get_shared_slots(mem).unwrap()
    }

    pub fn get_shared_slots<'a>(&self, mem: &Memory<'a>) -> Option<&'a [u64]> {
        mem.get_slice(self.shared_slots.data, self.shared_slots.len as usize)
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
        #[derive(Clone, Copy, PartialEq, Eq, Hash, Default)]
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

define_enum! {
    pub enum Rarity(u32) {
        Basic = 1,
        Fine = 2,
        Masterwork = 3,
        Rare = 4,
        Exotic = 5,
        Ascended = 6,
        Legendary = 7,
    }
}
