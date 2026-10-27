# SPDX-License-Identifier: GPL-3.0-or-later
"""game.exe's excel column lists: how each .txt column is read into its record.

    uv run python txt_fields.py HitClass           # the list holding a column name
    uv run python txt_fields.py 661b20             # the list a loader function builds
    uv run python txt_fields.py HitClass --all     # every list holding the name, its line in each
    uv run python txt_fields.py --exe PATH ...     # another game.exe than the MPQ folder's bin/game.exe

Each table's loader (Missiles.txt: FUN_00661b20, MonStats2: FUN_006571a0,
Skills.txt: FUN_00613f80, ...) builds its column list on the stack, one
0x14-byte entry a column: {name, type, size or bit, record offset, link}.
This reads the loader's code (capstone, from its `push ebp` to its end),
tracking the constants it keeps in registers, and prints a line a column:

    HitClass             type 0x4   size 0x0    +0x94

Types seen: 2 a dword, 3 a word, 4 a byte, 0x1a a bit (`size` is the bit,
of the dword at the offset: MonStats2's large 11, small 10, soft 12,
critter 13 at +4), 0x11 / 0x14 a code or id looked up in the `link` table,
0x19 a calc the `link` function compiles. Check a type you rely on against
a column whose meaning you know. A field the compiler kept in a register
it lost track of prints the register's name.
"""
import os
import struct
import sys

import capstone
import pefile
from capstone import x86

from emu import data_path


def strings_at(pe, name):
    """The VAs of `name` as a NUL-terminated string in the image."""
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    needle, out, at = b"\0" + name.encode() + b"\0", [], 0
    while (at := image.find(needle, at)) >= 0:
        out.append(base + at + 1)
        at += 1
    return out


def string(image, base, va):
    """A printable NUL-terminated string at `va`, else None."""
    offset = va - base
    if not 0 < offset < len(image):
        return None
    text = image[offset:offset + 64].split(b"\0")[0]
    return text.decode() if text and all(32 <= c < 127 for c in text) else None


def function_start(image, base, va):
    """The nearest `push ebp; mov ebp, esp` at or before `va`."""
    for at in range(va - base, max(va - base - 0x4000, 0), -1):
        if image[at:at + 3] == b"\x55\x8b\xec":
            return base + at
    sys.exit(f"txt_fields: no function start before {va:08x}")


def stores(pe, start):
    """The function's `mov [ebp + disp], value` stores up to its end, in
    order, as [(disp, value)], registers resolved to the constant last moved into
    them (else their name)."""
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    regs, out = {}, []
    for ins in md.disasm(image[start - base:start - base + 0x10000], start):
        if ins.mnemonic == "ret":                        # the function's end: padding or the next one next
            after = ins.address + ins.size - base
            if image[after] == 0xCC or image[after:after + 3] == b"\x55\x8b\xec":
                break
        ops = ins.operands
        if ins.mnemonic == "mov" and len(ops) == 2 and ops[0].type == x86.X86_OP_REG:
            regs[ins.reg_name(ops[0].reg)] = ops[1].imm if ops[1].type == x86.X86_OP_IMM else None
        elif ins.mnemonic == "xor" and len(ops) == 2 and ops[0].type == ops[1].type == x86.X86_OP_REG and ops[0].reg == ops[1].reg:
            regs[ins.reg_name(ops[0].reg)] = 0
        elif ins.mnemonic == "mov" and len(ops) == 2 and ops[0].type == x86.X86_OP_MEM and ins.reg_name(ops[0].mem.base) == "ebp":
            if ops[1].type == x86.X86_OP_IMM:
                out.append((ops[0].mem.disp, ops[1].imm))
            elif ops[1].type == x86.X86_OP_REG:
                reg = ins.reg_name(ops[1].reg)
                out.append((ops[0].mem.disp, regs[reg] if regs.get(reg) is not None else reg))
        elif ops and ops[0].type == x86.X86_OP_REG:       # anything else writing a register forgets it
            regs.pop(ins.reg_name(ops[0].reg), None)
        elif ins.mnemonic == "call":                     # and a call, eax / ecx / edx
            for reg in ("eax", "ecx", "edx"):
                regs.pop(reg, None)
    return out


def column_list(pe, start):
    """The column list the function at `start` builds: [(name, type, size, offset, link)].
    Long lists are built a chunk at a time in the same stack buffer, so an entry's
    fields are the next stores to its slots after its name's (or, one the
    compiler left from an earlier entry, the last store before)."""
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    found = stores(pe, start)
    rows = []
    for at, (disp, value) in enumerate(found):
        name = string(image, base, value) if isinstance(value, int) else None
        if not name:
            continue
        entry = [None] * 4
        for later_disp, later_value in found[at + 1:]:
            if later_disp == disp:
                break
            field = (later_disp - disp) // 4 - 1
            if (later_disp - disp) % 4 == 0 and 0 <= field < 4 and entry[field] is None:
                entry[field] = later_value
        for earlier_disp, earlier_value in reversed(found[:at]):    # a field the compiler stored before the name
            field = (earlier_disp - disp) // 4 - 1
            if (earlier_disp - disp) % 4 == 0 and 0 <= field < 4 and entry[field] is None:
                entry[field] = earlier_value
        if all(field is not None for field in entry[:3]):
            rows.append((name, *entry))
    return rows


def refs_to(pe, va):
    """Code that stores `va` into an [ebp + disp] slot (`mov dword [ebp + disp], va`)."""
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    needle, out, at = struct.pack("<I", va), [], 0
    while (at := image.find(needle, at)) >= 0:
        if at >= 6 and image[at - 6] == 0xC7 and image[at - 5] in (0x85, 0x45):
            out.append(base + at - 6)
        elif at >= 3 and image[at - 3] == 0xC7 and image[at - 2] == 0x45:
            out.append(base + at - 3)
        at += 1
    return out


def show(start, rows, mark=None, count=None):
    def num(value):
        return f"{value:#x}" if isinstance(value, int) else str(value)
    print(f"column list built at FUN_{start:08x}: {len(rows) if count is None else count} columns")
    for name, kind, size, offset, link in rows:
        line = f"  {name:<20} type {num(kind):<5} size {num(size):<6} +{num(offset)}"
        if isinstance(link, int) and link:
            line += f"  link {num(link)}"
        print(line + ("   <==" if name == mark else ""))


def main():
    args = sys.argv[1:]
    exe = None
    if "--exe" in args:
        at = args.index("--exe")
        exe = args[at + 1]
        del args[at:at + 2]
    every = "--all" in args
    args = [arg for arg in args if arg != "--all"]
    if len(args) != 1:
        sys.exit(__doc__)
    args = [exe or os.path.join(data_path(), "bin", "game.exe"), *args]
    pe = pefile.PE(args[0], fast_load=True)
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    try:
        function = int(args[1], 16)
    except ValueError:
        function = None
    if function is not None and function >= base:
        rows = column_list(pe, function)
        if not rows:
            sys.exit(f"txt_fields: FUN_{function:08x} builds no column list")
        show(function, rows)
        return
    starts = list(dict.fromkeys(function_start(image, base, ref) for va in strings_at(pe, args[1]) for ref in refs_to(pe, va)))
    if not starts:
        sys.exit(f"txt_fields: no column list names {args[1]!r}")
    for start in starts if every else starts[:1]:
        rows = column_list(pe, start)
        show(start, [row for row in rows if row[0] == args[1]] if every else rows, mark=args[1], count=len(rows))


if __name__ == "__main__":
    main()
