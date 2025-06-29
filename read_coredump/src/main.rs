use std::env;
use std::fmt::Write as _;
use std::fs::File;
use memmap2::Mmap;
use elf::{self, ElfBytes};

unsafe trait Pod: Copy {}
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

fn get<T: Pod>(bytes: &[u8], pos: usize) -> Option<T> {
    unsafe {
        if pos >= bytes.len() || pos + size_of::<T>() > bytes.len() {
            return None;
        }
        let ptr = bytes.as_ptr().add(pos);
        assert!(ptr.addr() % align_of::<T>() == 0);
        Some(*(ptr as *const T))
    }
}

fn find<T: Pod, F: FnMut(T) -> bool>(bytes: &[u8], mut filter: F) -> Vec<(usize, T)> {
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

fn main() {
    let args = env::args().collect::<Vec<_>>();
    assert_eq!(args.len(), 2);

    let file = File::open(&args[1]).unwrap();
    let mem = unsafe { Mmap::map(&file) }.unwrap();
    let elf = ElfBytes::<elf::endian::NativeEndian>::minimal_parse(&mem).unwrap();
    println!("got elf");

    println!("section header count = {}", elf.section_headers().unwrap().into_iter().count());
    println!("segment count = {}", elf.segments().unwrap().into_iter().count());

    let (search_id, search_rarity): (u32, u8) = (44602, 1);
    let (search_id2, search_rarity2): (u32, u8) = (67027, 4);
    let search_align = align_of_val(&search_id);

    for seg in elf.segments().unwrap() {
        let data = elf.segment_data(&seg).unwrap();
        assert!(seg.p_vaddr as usize % search_align == 0);
        for (off, val) in find(data, |x: u32| x == search_id) {
            eprintln!("found {} (0x{:x}) @ 0x{:x}", val, val, seg.p_vaddr as usize + off);
            if get(data, off + 0x38) == Some(search_rarity) {
                eprintln!("  found rarity {} @ 0x{:x}", search_rarity, seg.p_vaddr as usize + off);
                dump_around(data, seg.p_vaddr, off, 0, 64);
            }
        }

        for (off, val) in find(data, |x: u32| x == search_id2) {
            eprintln!("found {} (0x{:x}) @ 0x{:x}", val, val, seg.p_vaddr as usize + off);
            if get(data, off + 0x38) == Some(search_rarity2) {
                eprintln!("  found rarity {} @ 0x{:x}", search_rarity2, seg.p_vaddr as usize + off);
                dump_around(data, seg.p_vaddr, off, 0, 64);
            }
        }
    }
}
