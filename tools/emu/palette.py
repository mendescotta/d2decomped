# SPDX-License-Identifier: GPL-3.0-or-later
"""game.exe's D2WinPalette loader as the oracle for d2d's pal.dat reader.

    uv run python palette.py [act]...   # prints tools/palette-dump's text
"""
import sys

import emu
import unicorn.x86_const


def boot(act):
    e = emu.Emu()
    stem = f"data\\global\\palette\\act{act}\\pal"
    dat = e.mpq_file(stem + ".dat")
    pl2 = e.mpq_file(stem + ".pl2")

    def read_file(oracle):
        path = oracle.cstr(oracle.mu.reg_read(unicorn.x86_const.UC_X86_REG_EDX))
        return oracle.put(pl2 if path.lower().endswith(".pl2") else dat)

    def copy(oracle):
        destination, source, size = (oracle.arg(index) for index in range(3))
        oracle.mu.mem_write(destination, oracle.read(source, size))
        return destination

    e.hook(0x517079, read_file, 3)
    e.hook(0x6829C0, copy, 0)
    e.hook(0x4FB010, lambda oracle: 0, 0)
    e.hook(0x4F63D0, lambda oracle: 0, 1)
    e.hook(0x40B3C0, lambda oracle: 0, 2)
    dat_path = e.put(stem.upper().encode() + b".DAT\0")
    pl2_path = e.put(stem.upper().encode() + b".PL2\0")
    if e.call(0x4FB1E0, dat_path, pl2_path) != 1:
        raise RuntimeError(f"palette loader failed for act {act}")
    return e


def dump(act):
    entries = boot(act).read(0x81E668, 256 * 4)
    return "\n".join(
        f"{index:02x} {entries[index * 4]:02x} {entries[index * 4 + 1]:02x} {entries[index * 4 + 2]:02x}"
        for index in range(256)
    )


if __name__ == "__main__":
    acts = [int(arg) for arg in sys.argv[1:]] or list(range(1, 6))
    for position, act in enumerate(acts):
        if position:
            print()
        print(dump(act))
