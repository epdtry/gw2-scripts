use std::collections::BTreeMap;
use std::env;
use std::fmt::Write as _;
use std::fs::File;
use memmap2::Mmap;
use elf::{self, ElfBytes};

mod types;
use self::types::{ItemDef, Item, ItemType, Rarity, Item_UpgradeComponent};

unsafe trait Pod {}
unsafe impl Pod for u8 {}
unsafe impl Pod for u16 {}
unsafe impl Pod for u32 {}
unsafe impl Pod for u64 {}
unsafe impl Pod for usize {}
unsafe impl Pod for i8 {}
unsafe impl Pod for i16 {}
unsafe impl Pod for i32 {}
unsafe impl Pod for i64 {}
unsafe impl Pod for isize {}
unsafe impl<T: Pod, const N: usize> Pod for [T; N] {}


struct Memory<'a> {
    /// Maps game addresses to the segment data at each address.
    m: BTreeMap<u64, &'a [u8]>,
    /// Reverse mapping: maps the address of the start of the segment data (in the current process)
    /// to the corresponding game address.
    rev: BTreeMap<usize, u64>,
}

impl<'a> Memory<'a> {
    pub fn new(seg_data: &[(&'a [u8], u64)]) -> Memory<'a> {
        Memory {
            m: seg_data.iter()
                .map(|&(data, base_addr)| (base_addr, data))
                .collect(),
            rev: seg_data.iter()
                .map(|&(data, base_addr)| (data.as_ptr().addr(), base_addr))
                .collect(),
        }
    }

    fn get_in<T: Pod>(
        &self,
        base_addr: u64,
        data: &'a [u8],
        addr: u64,
    ) -> Option<&'a T> {
        debug_assert!(base_addr <= addr);
        let offset = (addr - base_addr) as usize;
        unsafe {
            // If the requested range extends past the end of `data`, bail out.
            if offset + size_of::<T>() > data.len() {
                return None;
            }
            // If the address is not well-aligned, bail out.
            let ptr = data.as_ptr().add(offset);
            if ptr.addr() % align_of::<T>() != 0 {
                return None;
            }
            Some(&*ptr.cast::<T>())
        }
    }

    pub fn get<T: Pod>(&self, addr: u64) -> Option<&'a T> {
        // Get the last segment that starts on or before `addr`.
        let (&base_addr, &data) = self.m.range(..= addr).next_back()?;
        self.get_in(base_addr, data, addr)
    }

    /// Given a reference returned by `get`, return a reference to the same data but with a
    /// different type.
    pub fn cast<T, U: Pod>(&self, x: &T) -> Option<&'a U> {
        let (base_addr, data, addr) = self.lookup_addr(x)?;
        self.get_in(base_addr, data, addr)
    }

    fn lookup_addr<T>(&self, x: &T) -> Option<(u64, &'a [u8], u64)> {
        let ptr = (x as *const T).addr();
        let (&data_ptr, &base_addr) = self.rev.range(..= ptr).next_back()?;
        debug_assert!(data_ptr <= ptr);
        let offset = ptr - data_ptr;
        // `base_addr` came from `rev`, so it must be present in `m`.
        let data = self.m[&base_addr];
        if offset + size_of::<T>() > data.len() {
            return None;
        }
        let addr = base_addr + offset as u64;
        Some((base_addr, data, addr))
    }

    pub fn addr<T>(&self, x: &T) -> Option<u64> {
        let (_base_addr, _data, addr) = self.lookup_addr(x)?;
        Some(addr)
    }

    pub fn dump_around<T>(&self, x: &T, before: usize, after: usize) {
        let (base_addr, data, addr) = self.lookup_addr(x).unwrap();
        let offset = (addr - base_addr) as usize;
        dump_around(data, base_addr, offset, before, after);
    }
}



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

fn dump_around(bytes: &[u8], base_addr: u64, offset: usize, before: usize, after: usize) {
    let start = offset.saturating_sub(before);
    let end = offset.saturating_add(after).min(bytes.len());
    const LINE_BYTES: usize = 16;
    let start_addr = (base_addr as usize + start) & !(LINE_BYTES - 1);
    let end_addr = (base_addr as usize + end + LINE_BYTES - 1) & !(LINE_BYTES - 1);
    let mut hex_buf = String::with_capacity(2 * (end_addr - start_addr));
    let mut ascii_buf = String::with_capacity(end_addr - start_addr);
    let start_padding = (base_addr as usize + start) - start_addr;
    let end_padding = end_addr - (base_addr as usize + end);
    for _ in 0 .. start_padding {
        hex_buf.push_str("  ");
        ascii_buf.push(' ');
    }
    for &b in &bytes[start .. end] {
        write!(hex_buf, "{:02x}", b).unwrap();
        if b.is_ascii_graphic() || b == b' ' {
            ascii_buf.push(b as char);
        } else {
            ascii_buf.push('.');
        }
    }
    for _ in 0 .. end_padding {
        hex_buf.push_str("  ");
        ascii_buf.push(' ');
    }
    debug_assert!(hex_buf.len() % (2 * LINE_BYTES) == 0);
    debug_assert!(ascii_buf.len() % LINE_BYTES == 0);

    debug_assert!(start_addr % LINE_BYTES == 0);
    debug_assert!(end_addr % LINE_BYTES == 0);
    let num_lines = (end_addr - start_addr) / LINE_BYTES;
    const LINE_CHARS: usize = 16 + 1 + (1 + 2 + 2) * LINE_BYTES/2 + 2 + LINE_BYTES + 1;
    let mut buf = String::with_capacity(LINE_CHARS * num_lines);
    for i in 0 .. num_lines {
        write!(buf, "{:08x}:", start_addr + i * LINE_BYTES).unwrap();
        for j in 0 .. LINE_BYTES {
            if j % 2 == 0 {
                buf.push(' ');
            }
            let hex_idx = (i * LINE_BYTES + j) * 2;
            buf.push_str(&hex_buf[hex_idx .. hex_idx + 2]);
        }
        buf.push_str("  ");
        let ascii_idx = i * LINE_BYTES;
        buf.push_str(&ascii_buf[ascii_idx .. ascii_idx + LINE_BYTES]);
        buf.push('\n');
    }

    eprintln!("{buf}");
}


fn find_in_segs<'a, T: Pod, F: FnMut(&T) -> bool>(
    seg_data: &'a [(&'a [u8], u64)],
    dump_before: usize,
    dump_after: usize,
    mut filter: F,
) -> FindInSegsResult<'a> {
    let mut opts = Vec::new();
    for (i, &(data, base_addr)) in seg_data.iter().enumerate() {
        let seg_opts = find_ref(data, |x| filter(x));
        for (offset, _) in seg_opts {
            opts.push((i, offset, base_addr + offset as u64));
        }
    }

    FindInSegsResult {
        seg_data,
        dump_before,
        dump_after: size_of::<T>() + dump_after,
        opts,
    }
}

struct FindInSegsResult<'a> {
    seg_data: &'a [(&'a [u8], u64)],
    dump_before: usize,
    dump_after: usize,
    opts: Vec<(usize, usize, u64)>,
}

impl<'a> FindInSegsResult<'a> {
    pub fn print_candidates(&self) {
        eprintln!("found {} candidates", self.opts.len());
        for (i, &(seg_idx, offset, addr)) in self.opts.iter().enumerate() {
            let (data, base_addr) = self.seg_data[seg_idx];
            eprintln!("candidate {i} @ 0x{addr:016x}:");
            dump_around(data, base_addr, offset, self.dump_before, self.dump_after);
        }
    }

    pub fn sole(self) -> (usize, usize, u64) {
        match self.opts.len() {
            0 => panic!("not found"),
            1 => {
                let (seg_idx, offset, addr) = self.opts[0];
                eprintln!("  found 0x{addr:016x} (seg {seg_idx}, offset 0x{offset:x})");
                self.opts[0]
            },
            _ => {
                self.print_candidates();
                panic!("multiple candidates");
            },
        }
    }

    pub fn opts(&self) -> &[(usize, usize, u64)] {
        &self.opts
    }
}

fn find_item_def(
    seg_data: &[(&[u8], u64)],
    id: u32,
    type_: Option<ItemType>,
    rarity: Option<Rarity>,
) -> u64 {
    eprintln!("looking for ItemDef id = {id}, type = {type_:?}, rarity = {rarity:?}");
    find_in_segs(seg_data, 32, 32, |item_def: &ItemDef| {
        item_def.id == id
            && type_.map_or(true, |type_| item_def.type_ == type_)
            && rarity.map_or(true, |rarity| item_def.rarity == rarity)
    }).sole().2
}

fn find_item(
    seg_data: &[(&[u8], u64)],
    def: u64,
    count: Option<u8>,
) -> u64 {
    eprintln!("looking for Item def = 0x{def:016x}, count = {count:?}");
    find_in_segs(seg_data, 32, 32, |item: &Item_UpgradeComponent| { // FIXME
        item.base.def == def
            && count.map_or(true, |count| item.count == count)
    }).sole().2
}

fn find_pointer_exact(
    seg_data: &[(&[u8], u64)],
    addr: u64,
) -> u64 {
    eprintln!("looking for pointer 0x{:016x} (exact)", addr);
    find_in_segs(seg_data, 128, 128, |x: &u64| {
        *x == addr
    }).sole().2
}

fn find_inventory_array(
    seg_data: &[(&[u8], u64)],
    item0_ptr: u64,
    item1_ptr: u64,
) -> u64 {
    eprintln!("looking for adjacent pointers 0x{item0_ptr:016x} and 0x{item1_ptr:016x}");
    find_in_segs(seg_data, 32, 32, |ptrs: &[u64; 2]| {
        *ptrs == [item0_ptr, item1_ptr]
    }).sole().2
}


/// Given the address of some field of a struct, where the offset of the field within the struct is
/// unknown, this function looks for possible pointers to the start of the struct and prints the
/// field offset implied by each one.
fn guess_pointers_and_offset(
    seg_data: &[(&[u8], u64)],
    field_addr: u64,
    search_before: usize,
    search_after: usize,
) {
    let r = find_in_segs(&seg_data, 32, 32, |&x: &u64| {
        field_addr - search_before as u64 <= x
            && x <= field_addr + search_after as u64
    });
    for &(seg_idx, offset, addr) in r.opts() {
        let ptr_val = get::<u64>(seg_data[seg_idx].0, offset).unwrap();
        eprintln!("found pointer @ 0x{addr:016x} to struct @ 0x{ptr_val:16x} (offset = {})",
            ptr_val as isize - field_addr as isize);
    }
}


fn find_seg_for_addr<'a>(
    seg_data: &[(&'a [u8], u64)],
    addr: u64,
) -> Option<(&'a [u8], usize)> {
    for &(data, base_addr) in seg_data {
        if addr < base_addr {
            continue;
        }
        if addr >= base_addr + data.len() as u64 {
            continue;
        }
        return Some((data, (addr - base_addr) as usize));
    }
    None
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


fn main() {
    let args = env::args().collect::<Vec<_>>();
    assert_eq!(args.len(), 2);

    let file = File::open(&args[1]).unwrap();
    let mem = unsafe { Mmap::map(&file) }.unwrap();
    let elf = ElfBytes::<elf::endian::NativeEndian>::minimal_parse(&mem).unwrap();
    println!("got elf");

    println!("section header count = {}", elf.section_headers().unwrap().into_iter().count());
    println!("segment count = {}", elf.segments().unwrap().into_iter().count());


    let seg_data = elf.segments().unwrap().iter()
        .map(|seg| (elf.segment_data(&seg).unwrap(), seg.p_vaddr))
        .collect::<Vec<_>>();
    let mem = Memory::new(&seg_data);

    let item_def_1_addr =
        find_item_def(&seg_data, 44602, Some(ItemType::Tool), Some(Rarity::Basic));
    let item_def_2_addr =
        find_item_def(&seg_data, 67027, Some(ItemType::Tool), Some(Rarity::Rare));
    let item_def_3_addr =
        find_item_def(&seg_data, 24518, None, Some(Rarity::Rare));

    let item1_addr = find_item(&seg_data, item_def_1_addr, Some(0));
    let item2_addr = find_item(&seg_data, item_def_2_addr, Some(0));
    let item3a_addr = find_item(&seg_data, item_def_3_addr, Some(250));
    let item3b_addr = find_item(&seg_data, item_def_3_addr, Some(248));

    //for &field_addr in &[item1_addr, item2_addr, item3a_addr, item3b_addr] {
    //    guess_pointers_and_offset(&seg_data, field_addr, 128, 0);
    //}

    let inv_array_addr = find_inventory_array(&seg_data, item1_addr, item2_addr);
    //let inv_array_addr2 = find_inventory_array(&seg_data, item3a_addr, item3b_addr);
    //eprintln!("implied slot distance = {}", (inv_array_addr2 - inv_array_addr) / 8);

    print_inventory(&mem, inv_array_addr, 480);
    //print_inventory(&seg_data, inv_array_addr2, 10);

    //guess_pointers_and_offset(&seg_data, inv_array_addr, 32, 0);

    //inspect_inventory(&mem, inv_array_addr, 480);

    /*
    for i in [0, 39, 130, 264, 290, 384, 71, 72] {
        dump_inventory_item(&seg_data, inv_array_addr, i);
    }
    */


}
