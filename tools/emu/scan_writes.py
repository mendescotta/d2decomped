# SPDX-License-Identifier: GPL-3.0-or-later
"""Who writes (or reads) a struct field: every .text instruction on [reg + OFFSET].

    uv run python scan_writes.py b0                 # writes to [reg + 0xb0], any size
    uv run python scan_writes.py b0 2               # 2-byte writes only
    uv run python scan_writes.py b0 - 550000-5d0000 # any size, in that address range
    uv run python scan_writes.py --reads b0         # reads instead (a source operand, cmp / test)
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

WRITERS = {"mov", "add", "sub", "or", "and", "xor", "inc", "dec", "xchg", "not", "neg", "shl", "shr", "sar"}


def main():
    args = sys.argv[1:]
    reads = "--reads" in args
    if reads:
        args.remove("--reads")
    exe = None
    if "--exe" in args:
        at = args.index("--exe")
        exe = args[at + 1]
        del args[at:at + 2]
    if not args:
        sys.exit(__doc__)
    offset = int(args[0], 16)
    size = int(args[1]) if len(args) > 1 and args[1] != "-" else None
    low, high = (int(value, 16) for value in args[2].split("-")) if len(args) > 2 else (0, 1 << 32)

    pe = pefile.PE(exe or os.path.join(data_path(), "bin", "game.exe"), fast_load=True)
    text = next(section for section in pe.sections if section.Name.rstrip(b"\0") == b".text")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    md.skipdata = True
    for ins in md.disasm(text.get_data(), pe.OPTIONAL_HEADER.ImageBase + text.VirtualAddress):
        if not low <= ins.address < high or ins.id == 0 or not ins.operands:
            continue
        if reads:
            ops = [op for op in ins.operands[1:] if op.type == x86.X86_OP_MEM]
            if ins.mnemonic in ("cmp", "test") and ins.operands[0].type == x86.X86_OP_MEM:
                ops.append(ins.operands[0])
        elif ins.mnemonic in WRITERS or ins.mnemonic.startswith("set"):
            ops = [ins.operands[0]] if ins.operands[0].type == x86.X86_OP_MEM else []
        else:
            continue
        if any(op.mem.disp == offset and op.mem.base != 0 and (not size or op.size == size) for op in ops):
            print(f"{ins.address:08x}  {ins.mnemonic:7} {ins.op_str}")


if __name__ == "__main__":
    main()
