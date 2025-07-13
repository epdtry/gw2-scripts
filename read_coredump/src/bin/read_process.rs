use std::cmp;
use std::collections::BTreeMap;
use std::env;
use std::fs::File;
use std::io::{self, Read, BufRead, BufReader, IoSliceMut};
use std::iter;
use std::mem::{MaybeUninit, offset_of};
use std::ptr;
use std::slice;
use std::thread;
use std::time::{Instant, Duration};
use lru::LruCache;
use nix::unistd::Pid;
use nix::sys::uio::{process_vm_readv, RemoteIoVec};

use read_coredump::Pod;
use read_coredump::types::{
    AnetArray, AnetHashTable, Character, CharInventory, CharWallet, ItemDef, Item, ItemType,
    Rarity, WalletEntry,
    Item_Consumable, Item_Container, Item_CraftingMaterial, Item_Tool, Item_Trophy,
    Item_UpgradeComponent,
};


pub fn pod_bytes<'a, T: Pod>(x: &'a T) -> &'a [u8] {
    unsafe {
        slice::from_raw_parts((x as *const T).cast::<u8>(), size_of::<T>())
    }
}

pub fn pod_bytes_mut<'a, T: Pod>(x: &'a mut T) -> &'a mut [u8] {
    unsafe {
        slice::from_raw_parts_mut((x as *mut T).cast::<u8>(), size_of::<T>())
    }
}

pub fn pod_slice_bytes<'a, T: Pod>(x: &'a [T]) -> &'a [u8] {
    unsafe {
        slice::from_raw_parts(x.as_ptr().cast::<u8>(), x.len() * size_of::<T>())
    }
}

pub fn pod_slice_bytes_mut<'a, T: Pod>(x: &'a mut [T]) -> &'a mut [u8] {
    unsafe {
        slice::from_raw_parts_mut(x.as_mut_ptr().cast::<u8>(), x.len() * size_of::<T>())
    }
}

pub fn pod_zeroed<T: Pod>() -> T {
    unsafe {
        MaybeUninit::<T>::zeroed().assume_init()
    }
}

fn process_vm_readv_exact(
    pid: Pid,
    mut local_iov: &mut [IoSliceMut],
    mut remote_iov: &mut [RemoteIoVec],
) -> nix::Result<()> {
    while local_iov.len() > 0 && remote_iov.len() > 0 {
        let n = process_vm_readv(pid, local_iov, remote_iov)?;
        IoSliceMut::advance_slices(&mut local_iov, n);
        let mut remaining = n;
        while remote_iov.len() > 0 {
            let first = &mut remote_iov[0];
            if first.len <= remaining {
                remaining -= first.len;
                remote_iov = &mut remote_iov[1..];
            } else {
                first.base += remaining;
                first.len -= remaining;
                break;
            }
        }
    }
    Ok(())
}

fn vm_read<T: Pod>(pid: Pid, addr: usize) -> nix::Result<T> {
    //eprintln!("vm_read: 0x{:016}, len = {}", addr, size_of::<T>());
    let mut buf = pod_zeroed::<T>();
    process_vm_readv_exact(
        pid,
        &mut [IoSliceMut::new(pod_bytes_mut(&mut buf))],
        &mut [RemoteIoVec { base: addr, len: size_of::<T>() }],
    )?;
    Ok(buf)
}

fn vm_read_multi<T: Pod>(pid: Pid, addr: usize, n: usize) -> nix::Result<Vec<T>> {
    //eprintln!("vm_read_multi: 0x{:016}, len = {} * {}", addr, n, size_of::<T>());
    let mut buf = iter::repeat_with(pod_zeroed::<T>).take(n).collect::<Vec<_>>();
    process_vm_readv_exact(
        pid,
        &mut [IoSliceMut::new(pod_slice_bytes_mut(&mut buf))],
        &mut [RemoteIoVec { base: addr, len: n * size_of::<T>() }],
    )?;
    Ok(buf)
}

fn vm_read_gather<T: Pod>(pid: Pid, addrs: &[usize]) -> nix::Result<Vec<T>> {
    //eprintln!("vm_read_gather: len = {} * {}", addrs.len(), size_of::<T>());
    let mut buf = iter::repeat_with(pod_zeroed::<T>).take(addrs.len()).collect::<Vec<_>>();
    let mut remote = addrs.iter()
        .map(|&addr| RemoteIoVec { base: addr, len: size_of::<T>() })
        .collect::<Vec<_>>();
    process_vm_readv_exact(
        pid,
        &mut [IoSliceMut::new(pod_slice_bytes_mut(&mut buf))],
        &mut remote,
    )?;
    Ok(buf)
}


const PAGE_SIZE: usize = 4096;
type PageBuffer = [usize; PAGE_SIZE / size_of::<usize>()];

struct PageCache {
    pid: Pid,
    m: LruCache<usize, Box<PageBuffer>>,
}

impl PageCache {
    pub fn new(pid: Pid) -> PageCache {
        PageCache {
            pid,
            m: LruCache::new(1024.try_into().unwrap()),
        }
    }

    pub fn clear(&mut self) {
        self.m.clear()
    }

    pub fn get(&mut self, addr: usize) -> nix::Result<&PageBuffer> {
        let addr = addr & !(PAGE_SIZE - 1);
        let buf = self.m.try_get_or_insert(addr, || {
            let mut buf = Box::new([0_usize; PAGE_SIZE / size_of::<usize>()]);
            let mut pos = 0;
            while pos < PAGE_SIZE {
                let buf = &mut buf[pos..];
                let bytes = unsafe {
                    slice::from_raw_parts_mut(
                        buf.as_mut_ptr().cast::<u8>(),
                        size_of_val(buf),
                    )
                };
                let n = process_vm_readv(
                    self.pid,
                    &mut [IoSliceMut::new(bytes)],
                    &[RemoteIoVec { base: addr + pos, len: PAGE_SIZE - pos }],
                )?;
                pos += n;
            }
            Ok(buf)
        })?;
        Ok(buf)
    }

    unsafe fn read_bytes_uninit(
        &mut self,
        addr: usize,
        dest: *mut u8,
        len: usize,
    ) -> nix::Result<()> {
        let mut dest = dest;
        let mut start = addr;
        let end = addr + len;
        let start_page = start & !(PAGE_SIZE - 1);
        let end_page = (end + PAGE_SIZE - 1) & !(PAGE_SIZE - 1);
        for page in (start_page .. end_page).step_by(PAGE_SIZE) {
            let words = self.get(page)?;
            let start_offset = start - page;
            let end_offset = cmp::min(words.len() * size_of::<usize>(), end - page);
            //eprintln!("start {start}, page {page}, len {}, off {start_offset} {end_offset}", bytes.len());
            let n = end_offset - start_offset;
            debug_assert!(n <= end - start);
            ptr::copy_nonoverlapping(words.as_ptr().cast::<u8>().add(start_offset), dest, n);
            start += n;
            dest = dest.add(n);
        }
        Ok(())
    }

    pub fn read_bytes(&mut self, addr: usize, buf: &mut [u8]) -> nix::Result<()> {
        unsafe { self.read_bytes_uninit(addr, buf.as_mut_ptr(), buf.len()) }
    }

    pub fn read<'a, T: Pod>(
        &'a mut self,
        addr: usize,
        buf: &'a mut MaybeUninit<T>,
    ) -> nix::Result<&'a T> {
        unsafe {
            let page_addr = addr & !(PAGE_SIZE - 1);
            let offset = addr - page_addr;
            if offset + size_of::<T>() <= PAGE_SIZE {
                let bytes = self.get(page_addr)?;
                Ok(&*bytes.as_ptr().add(offset).cast::<T>())
            } else {
                self.read_bytes_uninit(addr, buf.as_mut_ptr().cast::<u8>(), size_of::<T>())?;
                Ok(buf.assume_init_ref())
            }
        }
    }

    pub fn read_copy<T: Pod>(
        &mut self,
        addr: usize,
    ) -> nix::Result<T> {
        unsafe {
            let mut buf = MaybeUninit::<T>::uninit();
            self.read_bytes_uninit(addr, buf.as_mut_ptr().cast::<u8>(), size_of::<T>())?;
            Ok(buf.assume_init())
        }
    }
}


struct Maps {
    m: BTreeMap<usize, usize>,
}

impl Maps {
    pub fn new() -> Maps {
        Maps {
            m: BTreeMap::new(),
        }
    }

    pub fn len(&self) -> usize {
        self.m.len()
    }

    pub fn insert(&mut self, addr: usize, len: usize) {
        self.m.insert(addr, len);
    }

    pub fn contains(&self, addr: usize, len: usize) -> bool {
        if addr.checked_add(len).is_none() {
            return false;
        }

        let mut start = addr;
        let mut end = addr + len;
        while start < end {
            let seg = match self.m.range(..= start).next_back() {
                Some(x) => x,
                None => return false,
            };
            let seg_end = seg.0 + seg.1;
            if seg_end <= start {
                return false;
            }
            start = seg_end;
        }
        true
    }

    pub fn iter<'a>(&'a self) -> impl Iterator<Item = (usize, usize)> + 'a {
        self.m.iter().map(|(&k, &v)| (k, v))
    }
}


/// Read `/proc/{pid}/maps` and return a list of `(address, length)` pairs for all readable,
/// non-file-backed mappings.
fn read_maps(pid: Pid) -> io::Result<Maps> {
    let mut f = BufReader::new(File::open(format!("/proc/{}/maps", pid.as_raw()))?);
    let mut maps = Maps::new();
    for line in f.lines() {
        let line = line?;
        let parts = line.split_ascii_whitespace().collect::<Vec<_>>();
        let (addr0_str, addr1_str) = parts[0].split_once('-').unwrap();
        let addr0 = usize::from_str_radix(addr0_str, 16).unwrap();
        let addr1 = usize::from_str_radix(addr1_str, 16).unwrap();
        let perms = parts[1];
        if !perms.contains('r') {
            continue;
        }
        let inode = parts[4].parse::<u64>().unwrap();
        if inode != 0 {
            continue;
        }
        maps.insert(addr0, addr1 - addr0);
    }
    Ok(maps)
}


fn check_mem<T: Pod>(
    maps: &Maps,
    cache: &mut PageCache,
    addr: usize,
    f: impl FnOnce(&mut PageCache, &T) -> bool,
) -> bool {
    if !maps.contains(addr, size_of::<T>()) {
        return false;
    }
    let x = match cache.read_copy::<T>(addr) {
        Ok(x) => x,
        Err(_) => return false,
    };
    f(cache, &x)
}

fn search<T: Pod>(
    maps: &Maps,
    cache: &mut PageCache,
    mut f: impl FnMut(&mut PageCache, &T) -> bool,
) -> Vec<usize> {
    search_addr(maps, cache, align_of::<T>(), |cache, addr| {
        check_mem(maps, cache, addr, |cache, x| f(cache, x))
    })
}

fn search_addr(
    maps: &Maps,
    cache: &mut PageCache,
    align: usize,
    mut f: impl FnMut(&mut PageCache, usize) -> bool,
) -> Vec<usize> {
    let mut found = Vec::new();
    for (i, (start, len)) in maps.iter().enumerate() {
        eprintln!("region {}/{}: 0x{:016}, len {}", i, maps.len(), start, len);
        for addr in (start .. start + len).step_by(align) {
            if f(cache, addr) {
                found.push(addr);
            }
        }
    }
    found
}


fn read_copy_if_mapped<T: Pod>(maps: &Maps, cache: &mut PageCache, addr: usize) -> nix::Result<T> {
    if !maps.contains(addr, size_of::<T>()) {
        return Err(nix::errno::Errno::EFAULT);
    }
    cache.read_copy(addr)
}

macro_rules! check {
    (QUIET, $e:expr) => {
        if !$e {
            return false;
        }
    };
    ($addr:expr, $e:expr) => {
        if !$e {
            //eprintln!("  check failed at 0x{:016x}: {}", $addr, stringify!($e));
            return false;
        }
    };
}

macro_rules! check_read {
    (<$T:ty> $maps:expr, $cache:expr, $addr:expr) => {
        match read_copy_if_mapped::<$T>($maps, $cache, $addr) {
            Ok(x) => x,
            Err(_) => {
                //eprintln!("  read of {} failed at 0x{:016x}", stringify!($T), $addr);
                return false;
            },
        }
    };
}

fn is_character(
    maps: &Maps,
    cache: &mut PageCache,
    expect_items: &[(u32, ItemType, Rarity)],
    expect_shared_items: &[(u32, ItemType, Rarity)],
    expect_currencies: &BTreeMap<u32, u32>,
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, chr: &Character| {
        check!(addr, valid_ptr::<CharInventory>(maps, chr.inventory as usize));
        check!(addr, valid_ptr::<CharWallet>(maps, chr.wallet as usize));
        check!(addr, is_inventory(maps, cache, expect_items, expect_shared_items,
                chr.inventory as usize));
        check!(addr, is_wallet(maps, cache, expect_currencies, chr.wallet as usize));
        true
    })
}

fn is_inventory(
    maps: &Maps,
    cache: &mut PageCache,
    expect_items: &[(u32, ItemType, Rarity)],
    expect_shared_items: &[(u32, ItemType, Rarity)],
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, inv: &CharInventory| {
        check!(QUIET, inv.slots.len == 480);
        check!(addr, is_inventory_array(maps, cache, expect_items, inv.slots.data as usize));
        check!(addr,
            is_inventory_array(maps, cache, expect_shared_items, inv.shared_slots.data as usize));
        true
    })
}

fn is_inventory_array(
    maps: &Maps,
    cache: &mut PageCache,
    expect_items: &[(u32, ItemType, Rarity)],
    addr: usize,
) -> bool {
    for (i, &expect_item) in expect_items.iter().enumerate() {
        let addr_i = addr + i * size_of::<usize>();
        check!(addr_i, is_item_ptr(maps, cache, expect_item, addr_i));
    }
    true
}

fn is_item_ptr(
    maps: &Maps,
    cache: &mut PageCache,
    expect_item: (u32, ItemType, Rarity),
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, &ptr: &usize| {
        check!(addr, is_item(maps, cache, expect_item, ptr));
        true
    })
}

fn is_item(
    maps: &Maps,
    cache: &mut PageCache,
    expect_item: (u32, ItemType, Rarity),
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, item: &Item| {
        check!(addr, valid_ptr::<usize>(maps, item.vtable as usize));
        check!(addr, is_item_def(maps, cache, expect_item, item.def as usize));
        true
    })
}

fn is_item_def(
    maps: &Maps,
    cache: &mut PageCache,
    expect_item: (u32, ItemType, Rarity),
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, def: &ItemDef| {
        let (id, type_, rarity) = expect_item;
        check!(addr, def.id == id);
        check!(addr, def.type_ == type_);
        check!(addr, def.rarity == rarity);
        true
    })
}

fn is_wallet(
    maps: &Maps,
    cache: &mut PageCache,
    expect_currencies: &BTreeMap<u32, u32>,
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, wallet: &CharWallet| {
        check!(addr, wallet.entries.cap.is_power_of_two());
        check!(addr, wallet.entries.len < wallet.entries.cap);
        check!(addr, is_wallet_array(maps, cache, expect_currencies,
                wallet.entries.data as usize, wallet.entries.cap as usize));
        true
    })
}

fn is_wallet_array(
    maps: &Maps,
    cache: &mut PageCache,
    expect_currencies: &BTreeMap<u32, u32>,
    addr: usize,
    cap: usize,
) -> bool {
    let mut found = 0;
    for i in 0 .. cap {
        let addr_i = addr + i * size_of::<WalletEntry>();
        if is_wallet_entry(maps, cache, expect_currencies, addr_i) {
            found += 1;
        }
    }
    check!(addr, found == expect_currencies.len());
    true
}

fn is_wallet_entry(
    maps: &Maps,
    cache: &mut PageCache,
    expect_currencies: &BTreeMap<u32, u32>,
    addr: usize,
) -> bool {
    check_mem(maps, cache, addr, |cache, entry: &WalletEntry| {
        if entry.hash == 0 {
            return false;
        }
        let expect_amount = match expect_currencies.get(&entry.currency_id) {
            Some(&x) => x,
            None => return false,
        };
        entry.amount == expect_amount
    })
}


fn valid_ptr<T>(maps: &Maps, addr: usize) -> bool {
    addr % align_of::<T>() == 0
        && maps.contains(addr, size_of::<T>())
}


fn read_inventory_and_wallet(
    pid: Pid,
    character_addr: usize,
) -> nix::Result<(BTreeMap<u32, u32>, BTreeMap<u32, u32>)> {
    let inv_offset = offset_of!(Character, inventory);
    let wallet_offset = offset_of!(Character, wallet);
    debug_assert_eq!(wallet_offset, inv_offset + size_of::<usize>());
    let [inv_addr, wallet_addr] = vm_read(pid, character_addr + inv_offset)?;
    //eprintln!("inv = 0x{:016x}", inv_addr);
    //eprintln!("inv = 0x{:016x}", wallet_addr);

    let inv = read_inventory(pid, inv_addr)?;
    let wallet = read_wallet(pid, wallet_addr)?;

    Ok((inv, wallet))
}

fn read_inventory(
    pid: Pid,
    inv_addr: usize,
) -> nix::Result<BTreeMap<u32, u32>> {
    let array = vm_read::<AnetArray>(pid, inv_addr + offset_of!(CharInventory, slots))?;
    let item_ptrs = vm_read_multi::<usize>(pid, array.data as usize, array.len as usize)?;
    let non_null_item_ptrs = || item_ptrs.iter().copied().filter(|&ptr| ptr != 0);

    // Load `ItemDef` for each non-null item
    let item_def_field_ptrs = non_null_item_ptrs()
        .map(|ptr| ptr + offset_of!(Item, def))
        .collect::<Vec<_>>();
    let def_ptrs = vm_read_gather::<usize>(pid, &item_def_field_ptrs)?;
    let defs = vm_read_gather::<ItemDef>(pid, &def_ptrs)?;

    let mut inv = BTreeMap::new();

    // Process items and defs.  For non-stacking items, we immediately record an entry in `inv`.
    // For stacking items, we record the address of the `count` field and the item ID for later
    // processing.
    let mut count_ptrs = Vec::with_capacity(item_ptrs.len());
    let mut count_item_ids = Vec::with_capacity(item_ptrs.len());
    for (d, item_ptr) in defs.iter().zip(non_null_item_ptrs()) {
        let offset = match d.type_ {
            ItemType::Consumable => offset_of!(Item_Consumable, count),
            ItemType::Container => offset_of!(Item_Container, count),
            ItemType::CraftingMaterial => offset_of!(Item_CraftingMaterial, count),
            // ItemType::Gizmo counts are not always accurate
            ItemType::Tool => offset_of!(Item_Tool, count),
            ItemType::Trophy => offset_of!(Item_Trophy, count),
            ItemType::UpgradeComponent => offset_of!(Item_UpgradeComponent, count),
            _ => {
                // No count to fetch for this item, so just record it immediately.
                *inv.entry(d.id).or_insert(0) += 1;
                continue;
            },
        };
        count_ptrs.push(item_ptr + offset);
        count_item_ids.push(d.id);
    }

    // Load counts for all stacking items.
    let counts = vm_read_gather::<u8>(pid, &count_ptrs)?;
    for (&item_id, &count) in count_item_ids.iter().zip(counts.iter()) {
        *inv.entry(item_id).or_insert(0) += count as u32;
    }

    Ok(inv)
}

fn read_wallet(
    pid: Pid,
    wallet_addr: usize,
) -> nix::Result<BTreeMap<u32, u32>> {
    let hash = vm_read::<AnetHashTable>(pid, wallet_addr + offset_of!(CharWallet, entries))?;
    let entries = vm_read_multi::<WalletEntry>(pid, hash.data as usize, hash.cap as usize)?;

    let mut wallet = BTreeMap::new();
    for entry in &entries {
        if entry.hash == 0 {
            continue;
        }
        wallet.insert(entry.currency_id, entry.amount);
    }

    Ok(wallet)
}

fn map_delta(old: &BTreeMap<u32, u32>, new: &BTreeMap<u32, u32>) -> Vec<(u32, i32)> {
    let mut out = Vec::new();
    for (&k, &old_v) in old {
        let new_v = new.get(&k).copied().unwrap_or(0);
        if new_v != old_v {
            out.push((k, new_v as i32 - old_v as i32));
        }
    }

    for (&k, &new_v) in new {
        if !old.contains_key(&k) {
            out.push((k, new_v as i32));
        }
    }

    out
}


fn main() {
    let args = env::args().collect::<Vec<_>>();
    assert_eq!(args.len(), 2);
    let pid = Pid::from_raw(args[1].parse().unwrap());

    let maps = read_maps(pid).unwrap();
    for m in maps.iter() {
        eprintln!("{m:?}");
    }

    let mut cache = PageCache::new(pid);

    let expect_items = [
        (44602, ItemType::Tool, Rarity::Basic),     // Copper-fed
        (67027, ItemType::Tool, Rarity::Rare),      // Silver-fed
    ];
    let expect_shared_items = [
        (78599, ItemType::Gizmo, Rarity::Exotic),       // Level 80 boost
        (97009, ItemType::Gizmo, Rarity::Ascended),     // Arborstone
        (100939, ItemType::Gizmo, Rarity::Ascended),    // Wizard's Tower
    ];
    let expect_currencies: BTreeMap<u32, u32> = [
        (64, 16076),    // Jade Sliver
        (15, 6832),     // Badge of Honor
    ].into();

    let found = search_addr(&maps, &mut cache, align_of::<Character>(), |cache, addr| {
        is_character(&maps, cache, &expect_items, &expect_shared_items, &expect_currencies, addr)
    });
    eprintln!("found {} matches", found.len());
    for &addr in &found {
        eprintln!("0x{:016x}", addr);
    }
    assert_eq!(found.len(), 1);
    let character_addr = found[0];

    let start = std::time::Instant::now();
    let (inv, wallet) = read_inventory_and_wallet(pid, character_addr).unwrap();
    let dur = start.elapsed();

    eprintln!("\ninv");
    for (k, v) in &inv {
        eprintln!("{} => {}", k, v);
    }

    eprintln!("\nwallet");
    for (k, v) in &wallet {
        eprintln!("{} => {}", k, v);
    }
    eprintln!("\nread in {:?}", dur);

    let (mut inv, mut wallet) = (inv, wallet);
    loop {
        let start = Instant::now();
        let (new_inv, new_wallet) = read_inventory_and_wallet(pid, character_addr).unwrap();
        let dur = start.elapsed();

        let inv_delta = map_delta(&inv, &new_inv);
        let wallet_delta = map_delta(&wallet, &new_wallet);
        for &(k, v) in &inv_delta {
            eprintln!("{:+} item {}", v, k);
        }
        for &(k, v) in &wallet_delta {
            eprintln!("{:+} currency {}", v, k);
        }
        if inv_delta.len() > 0 || wallet_delta.len() > 0 {
            eprintln!("scanned in {:?}\n", dur);
        }

        inv = new_inv;
        wallet = new_wallet;

        thread::sleep(Duration::from_millis(1));
    }
}
