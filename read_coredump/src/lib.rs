use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::slice;

pub mod types;


pub unsafe trait Pod {}
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


pub struct Memory<'a> {
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

    pub fn segments<'b>(&'b self) -> impl Iterator<Item = (u64, &'a [u8])> + 'b {
        self.m.iter().map(|(&k, &v)| (k, v))
    }

    pub fn get<T: Pod>(&self, addr: u64) -> Option<&'a T> {
        // Get the last segment that starts on or before `addr`.
        let (&base_addr, &data) = self.m.range(..= addr).next_back()?;
        self.get_in(base_addr, data, addr)
    }

    pub fn get_slice<T: Pod>(&self, addr: u64, len: usize) -> Option<&'a [T]> {
        // Get the last segment that starts on or before `addr`.
        let (&base_addr, &data) = self.m.range(..= addr).next_back()?;
        debug_assert!(base_addr <= addr);
        let offset = (addr - base_addr) as usize;
        unsafe {
            // If the requested range extends past the end of `data`, bail out.
            if offset + len * size_of::<T>() > data.len() {
                return None;
            }
            // If the address is not well-aligned, bail out.
            let ptr = data.as_ptr().add(offset);
            if ptr.addr() % align_of::<T>() != 0 {
                return None;
            }
            Some(slice::from_raw_parts(ptr.cast::<T>(), len))
        }
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

    pub fn dump_around_addr(&self, addr: u64, before: usize, after: usize) {
        let (&base_addr, &data) = self.m.range(..= addr).next_back().unwrap();
        debug_assert!(base_addr <= addr);
        let offset = (addr - base_addr) as usize;
        dump_around(data, base_addr, offset, before, after);
    }
}


pub fn dump_around(bytes: &[u8], base_addr: u64, offset: usize, before: usize, after: usize) {
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
