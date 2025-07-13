use std::collections::BTreeMap;
use std::env;
use std::fmt::Write as _;
use std::fs::File;
use std::slice;
use memmap2::Mmap;
use elf::{self, ElfBytes};

use read_coredump::{Memory, Pod, dump_around};
use read_coredump::types::{
    AnetArray, Character, CharInventory, CharWallet, ItemDef, Item, ItemType, Rarity, WalletEntry,
};


fn get<T: Pod + Copy>(bytes: &[u8], pos: usize) -> Option<T> {
    unsafe {
        if pos >= bytes.len() || pos + size_of::<T>() > bytes.len() {
            return None;
        }
        let ptr = bytes.as_ptr().add(pos);
        assert!(ptr.addr() % align_of::<T>() == 0);
        Some(*(ptr as *const T))
    }
}

fn get_ref<'a, T: Pod>(bytes: &'a [u8], pos: usize) -> Option<&'a T> {
    unsafe {
        if pos >= bytes.len() || pos + size_of::<T>() > bytes.len() {
            return None;
        }
        let ptr = bytes.as_ptr().add(pos);
        assert!(ptr.addr() % align_of::<T>() == 0);
        Some(&*(ptr as *const T))
    }
}

fn find<T: Pod + Copy, F: FnMut(T) -> bool>(bytes: &[u8], mut filter: F) -> Vec<(usize, T)> {
    let mut out = Vec::new();
    unsafe {
        let align = align_of::<T>();
        assert!(bytes.as_ptr().addr() % align == 0);
        let max = bytes.len().saturating_sub(align - 1);
        for i in (0 .. max).step_by(align) {
            let ptr = bytes.as_ptr().add(i).cast::<T>();
            if filter(*ptr) {
                out.push((i, *ptr));
            }
        }
    }
    out
}

fn find_ref<T: Pod, F: FnMut(&T) -> bool>(bytes: &[u8], mut filter: F) -> Vec<(usize, &T)> {
    let mut out = Vec::new();
    unsafe {
        let align = align_of::<T>();
        assert!(bytes.as_ptr().addr() % align == 0);
        let max = bytes.len().saturating_sub(align - 1);
        for i in (0 .. max).step_by(align) {
            let ptr = bytes.as_ptr().add(i).cast::<T>();
            if filter(&*ptr) {
                out.push((i, &*ptr));
            }
        }
    }
    out
}


fn find_in_segs<'a, T: Pod, F: FnMut(&T) -> bool>(
    mem: &'a Memory<'a>,
    dump_before: usize,
    dump_after: usize,
    mut filter: F,
) -> FindInSegsResult<'a> {
    let mut opts = Vec::new();
    for (i, (base_addr, data)) in mem.segments().enumerate() {
        let seg_opts = find_ref(data, |x| filter(x));
        for (offset, _) in seg_opts {
            opts.push(base_addr + offset as u64);
        }
    }

    FindInSegsResult {
        mem,
        dump_before,
        dump_after: size_of::<T>() + dump_after,
        opts,
    }
}

struct FindInSegsResult<'a> {
    mem: &'a Memory<'a>,
    dump_before: usize,
    dump_after: usize,
    opts: Vec<u64>,
}

impl<'a> FindInSegsResult<'a> {
    pub fn print_candidates(&self) {
        eprintln!("found {} candidates", self.opts.len());
        for (i, &addr) in self.opts.iter().enumerate() {
            eprintln!("candidate {i} @ 0x{addr:016x}:");
            self.mem.dump_around_addr(addr, self.dump_before, self.dump_after);
        }
    }

    pub fn sole(self) -> u64 {
        match self.opts.len() {
            0 => panic!("not found"),
            1 => {
                let addr = self.opts[0];
                eprintln!("  found 0x{addr:016x}");
                self.opts[0]
            },
            _ => {
                self.print_candidates();
                panic!("multiple candidates");
            },
        }
    }

    pub fn opts(&self) -> &[u64] {
        &self.opts
    }
}

fn find_item_def(
    mem: &Memory,
    id: u32,
    type_: Option<ItemType>,
    rarity: Option<Rarity>,
) -> u64 {
    eprintln!("looking for ItemDef id = {id}, type = {type_:?}, rarity = {rarity:?}");
    find_in_segs(mem, 32, 32, |item_def: &ItemDef| {
        item_def.id == id
            && type_.map_or(true, |type_| item_def.type_ == type_)
            && rarity.map_or(true, |rarity| item_def.rarity == rarity)
    }).sole()
}

fn find_item(
    mem: &Memory,
    def: u64,
    count: Option<u8>,
) -> u64 {
    eprintln!("looking for Item def = 0x{def:016x}, count = {count:?}");
    find_in_segs(mem, 32, 32, |item: &Item| {
        item.def == def
            && count.map_or(true, |count| item.count(mem) == Some(count))
    }).sole()
}

fn find_pointer_exact(
    mem: &Memory,
    addr: u64,
) -> u64 {
    eprintln!("looking for pointer 0x{:016x} (exact)", addr);
    find_in_segs(mem, 128, 128, |x: &u64| {
        *x == addr
    }).sole()
}

fn find_inventory_data(
    mem: &Memory,
    item0_ptr: u64,
    item1_ptr: u64,
) -> u64 {
    eprintln!("looking for adjacent pointers 0x{item0_ptr:016x} and 0x{item1_ptr:016x}");
    find_in_segs(mem, 32, 32, |ptrs: &[u64; 2]| {
        *ptrs == [item0_ptr, item1_ptr]
    }).sole()
}

fn find_anet_array(
    mem: &Memory,
    data_ptr: u64,
    len: u32,
) -> u64 {
    eprintln!("looking for ANet::Array with data pointer 0x{data_ptr:016x}, len = {len}");
    find_in_segs(mem, 32, 32, |x: &AnetArray| {
        x.data == data_ptr && x.len == len
    }).sole()
}

const MAX_BAG_SPACE: u32 = 15 * 32;
fn find_char_inventory(
    mem: &Memory,
    inv_data_ptr: u64,
) -> u64 {
    eprintln!("looking for CharClient::CInventory \
        with data pointer 0x{inv_data_ptr:016x}, len = {MAX_BAG_SPACE}");
    find_in_segs(mem, 32, 32, |x: &CharInventory| {
        x.slots.data == inv_data_ptr && x.slots.len == MAX_BAG_SPACE
    }).sole()
}

fn find_char_wallet(
    mem: &Memory,
    wallet_data_ptr: u64,
) -> u64 {
    eprintln!("looking for CharWallet with data pointer 0x{wallet_data_ptr:016x}");
    find_in_segs(mem, 32, 32, |x: &CharWallet| {
        x.entries.data == wallet_data_ptr
    }).sole()
}

fn find_character(
    mem: &Memory,
    inv_ptr: u64,
    wallet_ptr: u64,
) -> u64 {
    eprintln!("looking for Character with inventory pointer 0x{inv_ptr:016x}, \
        wallet pointer 0x{wallet_ptr:016x}");
    find_in_segs(mem, 32, 32, |x: &Character| {
        x.inventory == inv_ptr && x.wallet == wallet_ptr
    }).sole()
}


/// Given the address of some field of a struct, where the offset of the field within the struct is
/// unknown, this function looks for possible pointers to the start of the struct and prints the
/// field offset implied by each one.
fn guess_pointers_and_offset(
    mem: &Memory,
    field_addr: u64,
    search_before: usize,
    search_after: usize,
) {
    let r = find_in_segs(mem, 32, 32, |&x: &u64| {
        field_addr - search_before as u64 <= x
            && x <= field_addr + search_after as u64
    });
    for &addr in r.opts() {
        let ptr_val = *mem.get::<u64>(addr).unwrap();
        eprintln!("found pointer @ 0x{addr:016x} to struct @ 0x{ptr_val:16x} (offset = {})",
            ptr_val as isize - field_addr as isize);
        mem.dump_around_addr(addr, 128, 128);
    }
}

fn try_get_item<'a>(
    mem: &Memory<'a>,
    inv_array_ptr: u64,
    i: usize,
) -> Option<(u64, &'a Item, &'a ItemDef)> {
    let inv_array_slot_ptr = inv_array_ptr + i as u64 * 8;
    let item_ptr = *mem.get::<u64>(inv_array_slot_ptr)?;
    let item = mem.get::<Item>(item_ptr)?;
    let item_def = item.get_def(mem)?;
    Some((item_ptr, item, item_def))
}

fn print_inventory(
    mem: &Memory,
    inv_array_ptr: u64,
    count: usize,
) {
    println!("dumping {} items:", count);
    for i in 0 .. count {
        match try_get_item(mem, inv_array_ptr, i) {
            Some((item_ptr, item, item_def)) => {
                let count = item.count(mem).unwrap_or(0);
                let id = item_def.id;
                println!("slot {i:3}: {count:3}x {id} (@0x{item_ptr:016x})");
            },
            None => {
                println!("slot {i:3}: read error");
            },
        }
    }
}

/// Print item ID and type for each item in the inventory.  Useful for figuring out unknown values
/// in the `ItemType` enum: look up each unknown item in the API to get its actual type.
fn inspect_inventory(
    mem: &Memory,
    inv_array_ptr: u64,
    count: usize,
) {
    for i in 0..count {
        match try_get_item(mem, inv_array_ptr, i) {
            Some((item_ptr, item, item_def)) => {
                let id = item_def.id;
                let type_ = item_def.type_;
                println!("slot {i:3}: id {id}, type {type_:?}");
            },
            None => {
                println!("slot {i:3}: read error");
            },
        }
    }
}

fn dump_inventory_item(
    mem: &Memory,
    inv_array_ptr: u64,
    i: usize,
) {
    match try_get_item(mem, inv_array_ptr, i) {
        Some((item_ptr, item, item_def)) => {
            let id = item_def.id;
            let type_ = item_def.type_;
            let vtable = item.vtable;
            println!("slot {i} @0x{item_ptr:016x}, id {id}, type {type_:?}, vtable 0x{vtable:016x}:");
            mem.dump_around(item, 32, 256);
        },
        None => {
            println!("slot {i:3}: read error");
        },
    }
}

fn print_wallet(
    mem: &Memory,
    wallet_data_ptr: u64,
    count: usize,
) {
    println!("dumping {} wallet entries:", count);
    for i in 0 .. count {
        match mem.get::<WalletEntry>(wallet_data_ptr + (size_of::<WalletEntry>() * i) as u64) {
            Some(we) => {
                println!("slot {i:3}: id = {}, amount = {}, hash table bucket = {} (0x{:08x})",
                    we.currency_id, we.amount, we.hash % 128, we.hash);
            },
            None => {
                println!("slot {i:3}: read error");
            },
        }
    }
}

static WALLET: &[[u32; 2]] = &[
    // jq <wallet.json  '.[] | [.id, .value]'
];


fn main() {
    let args = env::args().collect::<Vec<_>>();
    assert_eq!(args.len(), 2);

    let file = File::open(&args[1]).unwrap();
    let mem = unsafe { Mmap::map(&file) }.unwrap();
    let elf = ElfBytes::<elf::endian::NativeEndian>::minimal_parse(&mem).unwrap();
    println!("got elf");

    println!("section header count = {}", elf.section_headers().unwrap().into_iter().count());
    println!("segment count = {}", elf.segments().unwrap().into_iter().count());


    for seg in elf.segments().unwrap().iter() {
        if seg.p_type == elf::abi::PT_NOTE {
            eprintln!("notes at 0x{:016x}", seg.p_vaddr);
            eprintln!("  size = 0x{:016x}", seg.p_filesz);
        }
    }

    let seg_data = elf.segments().unwrap().iter()
        .map(|seg| (elf.segment_data(&seg).unwrap(), seg.p_vaddr))
        .collect::<Vec<_>>();
    let mem = Memory::new(&seg_data);

    /*
    let mut addrs = Vec::new();
    for &entry in WALLET {
        eprintln!("try {:?}", entry);
        let r = find_in_segs(&mem, 16, 16, |&x: &[u32; 2]| {
            x == entry
        });
        if r.opts.len() == 1 {
            addrs.push(r.sole());
        } else {
            r.print_candidates();
        }
    }

    addrs.sort();
    for addr in addrs {
        mem.dump_around_addr(addr, 128, 128);
        guess_pointers_and_offset(&mem, addr, 512, 0);
    }
    */

    // wallet_data_addr is obtained by calling `guess_pointers_and_offset` with the lowest-address
    // wallet entry found above.  Or, use any wallet entry and set the `before` distance to 12*128.
    let wallet_data_addr: u64 = 0x00000000693b2200;
    let wallet_addr: u64 = 0x000000005608f8c0; //find_char_wallet(&mem, wallet_data_addr);
    //guess_pointers_and_offset(&mem, wallet_data_addr, 512, 0);
    //guess_pointers_and_offset(&mem, 0x000000005608f8d0, 512, 0);
    //let wallet_addr: u64 = 0x000000005608f8c0;
    //mem.dump_around_addr(wallet_addr, 16, 64);

    //print_wallet(&mem, wallet_data_addr, 128);

    /*
    let wallet_addr = 0x00000000693b2200;
    let parent1_addr: u64 = 0x000000005608f8d0;
    //guess_pointers_and_offset(&mem, parent1_addr, 512, 0);
    let parent2_addr: u64 = 0x00000000ae986e18;
    //guess_pointers_and_offset(&mem, parent2_addr, 512, 0);
    let parent3_addr: u64 = 0x00000000a0f73830;
    //guess_pointers_and_offset(&mem, parent3_addr, 512, 0);
    let parent4_addr: u64 = 0x00000000105011a0;
    //guess_pointers_and_offset(&mem, parent4_addr, 512, 0);

    let parent5a_addr: u64 = 0x000000000fe70060;
    //guess_pointers_and_offset(&mem, parent5a_addr, 512, 0);
    let parent6_addr: u64 = 0x000000000fe70070;
    //guess_pointers_and_offset(&mem, parent6_addr, 512, 0);
    // This is some kind of linked list, with each pointer pointing to a lower address

    let parent5b_addr: u64 = 0x00000000ae9db890;
    //guess_pointers_and_offset(&mem, parent5b_addr, 512, 0);
    let parent7a_addr: u64 = 0x0000000010501200;
    //guess_pointers_and_offset(&mem, parent7a_addr, 512, 0);
    let parent8_addr: u64 = 0x00000000ae9db8b0;
    //guess_pointers_and_offset(&mem, parent8_addr, 512, 0);
    let parent7b_addr: u64 = 0x00000000ae9db858;
    //guess_pointers_and_offset(&mem, parent5b_addr, 512, 0);
    */

    let item_def_1_addr =
        0x000000002ab5f62c; //find_item_def(&mem, 44602, Some(ItemType::Tool), Some(Rarity::Basic));
    let item_def_2_addr =
        0x000000002ab5df4c; //find_item_def(&mem, 67027, Some(ItemType::Tool), Some(Rarity::Rare));
    //let item_def_3_addr =
    //    find_item_def(&mem, 24518, None, Some(Rarity::Rare));

    let item1_addr = 0x0000000068c47ee0; //find_item(&mem, item_def_1_addr, None);
    let item2_addr = 0x0000000068c47fa0; //find_item(&mem, item_def_2_addr, None);
    //let item3a_addr = find_item(&mem, item_def_3_addr, Some(250));
    //let item3b_addr = find_item(&mem, item_def_3_addr, Some(248));

    let inv_data_addr = 0x0000000061062530; //find_inventory_data(&mem, item1_addr, item2_addr);

    let inv_array_addr = 0x000000006106b1b8; //find_anet_array(&mem, inv_data_addr, 480);
    let inventory_addr = 0x000000006106b0f0; //find_char_inventory(&mem, inv_data_addr);
                                             //
    let item_def_3_addr =
        0x0000000035b58f8c; //find_item_def(&mem, 97009, Some(ItemType::Gizmo), Some(Rarity::Ascended));
    let item_def_4_addr =
        0x000000002b9c0a64; //find_item_def(&mem, 100939, Some(ItemType::Gizmo), Some(Rarity::Ascended));
    let item3_addr = 0x0000000068c6d880; //find_item(&mem, item_def_3_addr, None);
    let item4_addr = 0x0000000068c6d950; //find_item(&mem, item_def_4_addr, None);
    let shared_inv_data_addr = 0x00000000442d4bd8; //find_inventory_data(&mem, item3_addr, item4_addr);
    //guess_pointers_and_offset(&mem, shared_inv_data_addr, 32, 0);

    /*
    let inventory = mem.get::<CharInventory>(inventory_addr).unwrap();
    for (i, &item_ptr) in inventory.slots(&mem).iter().enumerate() {
        if item_ptr == 0 {
            println!("slot {i:3}: empty");
            continue;
        }
        let item = mem.get::<Item>(item_ptr).unwrap();
        let id = item.def(&mem).id;
        let count = item.count(&mem).unwrap_or(0);
        println!("slot {i:3}: {count:3}x {id}");
    }
    */

    //guess_pointers_and_offset(&mem, inventory_addr, 0, 0);

    /*
    let item_array_addr = find_in_segs(&mem, 32, 32, |x: &AnetArray| {
        if x.len == 480 && x.cap == 480 {
            eprintln!("candidate pointer = 0x{:016x}, valid = {}",
                x.data, mem.get::<u64>(x.data).is_some());
            true
        } else {
            false
        }
    }).sole();
    */

    /*
    let char_addr_inner = find_in_segs(&mem, 32, 32, |x: &[u64; 2]| {
        *x == [inventory_addr, wallet_addr]
    }).sole();

    //guess_pointers_and_offset(&mem, char_addr_inner, 512, 0);
    //mem.dump_around_addr(char_addr_inner, 64, 64);
    //mem.dump_around_addr(0x00000000a0f73830, 64, 64);
    */

    let char_addr: u64 = 0x00000000ae986df0; //find_character(&mem, inventory_addr, wallet_addr);
    eprintln!("character = 0x{:016x}", char_addr);


    let chr = mem.get::<Character>(char_addr).unwrap();
    let wallet = chr.wallet(&mem);
    eprintln!("wallet addr = 0x{:016x}", mem.addr(wallet).unwrap());
    eprintln!("entries = {:?}", wallet.entries);
    println!("wallet:");
    let mut count = 0;
    for entry in wallet.entries(&mem) {
        if entry.currency_id == 0 {
            continue;
        }
        println!("{:3}: {}", entry.currency_id, entry.amount);
        count += 1;
    }
    println!("wallet has {} currencies", count);

    let inv = chr.inventory(&mem);
    println!("shared inventory:");
    inspect_inventory(&mem, inv.shared_slots.data, inv.shared_slots.len as usize);
    println!("main inventory:");
    inspect_inventory(&mem, inv.slots.data, inv.slots.len as usize);
}
