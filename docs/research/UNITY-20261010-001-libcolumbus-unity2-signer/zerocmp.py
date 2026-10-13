#!/usr/bin/env python3
"""zerocmp.py A B - zero the bytes of .note.package, .note.gnu.build-id and .gnu_debuglink in copies of two
ELF64 files (section contents only, located from the section header table), then compare the whole files
byte by byte. Also reports the ELF header, program header table and section header table separately, and
every non-section byte range (gaps/padding)."""
import struct, sys, hashlib

SKIP = {b".note.package", b".note.gnu.build-id", b".gnu_debuglink"}

def parse(path):
    d = bytearray(open(path, "rb").read())
    assert d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 1, "ELF64 LE only"
    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
     e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", d, 16)
    shdrs = []
    for i in range(e_shnum):
        shdrs.append(struct.unpack_from("<IIQQQQIIQQ", d, e_shoff + i * e_shentsize))
    stroff = shdrs[e_shstrndx][4]
    def name(n):
        e = d.index(b"\0", stroff + n)
        return bytes(d[stroff + n:e])
    secs = [(name(s[0]), s[1], s[4], s[5]) for s in shdrs]  # name, type, offset, size
    hdr = dict(ehsize=e_ehsize, phoff=e_phoff, phsz=e_phentsize * e_phnum, shoff=e_shoff, shsz=e_shentsize * e_shnum)
    return d, secs, hdr

def main(a, b):
    out = []
    da, sa, ha = parse(a)
    db, sb, hb = parse(b)
    out.append(f"sizes: {len(da)} / {len(db)}")
    out.append(f"ELF header ({ha['ehsize']} B): {'identical' if da[:ha['ehsize']] == db[:hb['ehsize']] else 'DIFFER'}")
    pa = da[ha['phoff']:ha['phoff'] + ha['phsz']]; pb = db[hb['phoff']:hb['phoff'] + hb['phsz']]
    out.append(f"program headers ({ha['phsz']} B): {'identical' if pa == pb else 'DIFFER'}")
    qa = da[ha['shoff']:ha['shoff'] + ha['shsz']]; qb = db[hb['shoff']:hb['shoff'] + hb['shsz']]
    out.append(f"section header table ({ha['shsz']} B, {len(sa)} entries): {'identical' if qa == qb else 'DIFFER'}")
    # coverage: mark bytes covered by sections (non-NOBITS) and headers; the rest are gaps
    cov = bytearray(len(da))
    for (n, t, off, size) in sa:
        if t != 8:  # SHT_NOBITS
            cov[off:off + size] = b"\1" * size
    for off, sz in ((0, ha['ehsize']), (ha['phoff'], ha['phsz']), (ha['shoff'], ha['shsz'])):
        cov[off:off + sz] = b"\1" * sz
    gaps = sum(1 for x in cov if x == 0)
    gap_diff = sum(1 for i, x in enumerate(cov) if x == 0 and (i >= len(db) or da[i] != db[i]))
    out.append(f"bytes outside headers and sections: {gaps}, of which differing: {gap_diff}")
    for d, s in ((da, sa), (db, sb)):
        for (n, t, off, size) in s:
            if n in SKIP:
                d[off:off + size] = b"\0" * size
    same = da == db
    ndiff = sum(1 for x, y in zip(da, db) if x != y) + abs(len(da) - len(db))
    out.append(f"whole file with the 3 sections zeroed: {'IDENTICAL' if same else 'DIFFER'} ({ndiff} differing bytes); "
               f"sha256 {hashlib.sha256(da).hexdigest()[:16]} / {hashlib.sha256(db).hexdigest()[:16]}")
    print("\n".join(out))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
