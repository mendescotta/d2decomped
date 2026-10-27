# SPDX-License-Identifier: GPL-3.0-or-later
"""Who writes (or reads) a struct field: every .text instruction on [reg + OFFSET].

    uv run python scan_writes.py b0                 # writes to [reg + 0xb0], any size
    uv run python scan_writes.py b0 2               # 2-byte writes only
    uv run python scan_writes.py b0 - 550000-5d0000 # any size, in that address range
    uv run python scan_writes.py --reads b0         # reads instead (`add [reg + 0xb0], 1` is both)
    uv run python scan_writes.py --exe PATH b0      # another game.exe than the MPQ folder's

Finds who sets a field Ghidra's xrefs can't (a unit's +0xb0 hit class, a
record's flags). A linear sweep, so a hit inside a data island is possible;
check each in Ghidra.
"""
import os
import sys

import capstone
import pefile
from capstone import x86

from emu import data_path


def main():
    args, exe = sys.argv[1:], None
    reads = "--reads" in args
    if reads:
        args.remove("--reads")
    if "--exe" in args:
        at = args.index("--exe")
        if at + 1 == len(args):
            sys.exit(__doc__)
        exe = args.pop(at + 1)
        del args[at]
    if not 1 <= len(args) <= 3 or any(arg.startswith("--") for arg in args):
        sys.exit(__doc__)
    try:
        offset = int(args[0], 16)
        size = int(args[1]) if len(args) > 1 and args[1] != "-" else None
        low, high = (int(value, 16) for value in args[2].split("-")) if len(args) > 2 else (0, 1 << 32)
    except ValueError:
        sys.exit(__doc__)
    if low >= high:
        sys.exit(f"scan_writes: empty range {low:x}-{high:x}")

    try:
        pe = pefile.PE(exe or os.path.join(data_path(), "bin", "game.exe"), fast_load=True)
    except (OSError, pefile.PEFormatError) as error:
        sys.exit(f"scan_writes: {error}")
    text = next((section for section in pe.sections if section.Name.rstrip(b"\0") == b".text"), None)
    if text is None:
        sys.exit("scan_writes: no .text section")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    md.skipdata = True
    found = False
    for ins in md.disasm(text.get_data(), pe.OPTIONAL_HEADER.ImageBase + text.VirtualAddress):
        if not low <= ins.address < high or ins.id == 0 or not ins.operands:
            continue
        if ins.mnemonic == "lea":                        # an address, not a memory access
            continue
        # capstone's operand access says which memory operand is read or written (adc, bts, cmpxchg, ...)
        want = capstone.CS_AC_READ if reads else capstone.CS_AC_WRITE
        ops = [op for op in ins.operands if op.type == x86.X86_OP_MEM and op.access & want]
        if any(op.mem.disp == offset and op.mem.base != 0 and (not size or op.size == size) for op in ops):
            print(f"{ins.address:08x}  {ins.mnemonic:7} {ins.op_str}")
            found = True
    if not found:
        sys.exit(f"scan_writes: nothing {'reads' if reads else 'writes'} [reg + {offset:#x}]"
                 + (f" in {size} bytes" if size else "") + (f" in {low:x}-{high:x}" if len(args) > 2 else ""))


if __name__ == "__main__":
    main()
