# SPDX-License-Identifier: GPL-3.0-or-later
"""Disassemble game.exe by address, without Ghidra.

    uv run python disasm.py 623f50              # from 0x623f50 to its ret
    uv run python disasm.py 623f50 200          # 200 instructions
    uv run python disasm.py --all out.txt       # every executable section, a line an instruction
    uv run python disasm.py --exe PATH ...      # another game.exe than the MPQ folder's bin/game.exe

A line is `address  mnemonic operands`, so `--all`'s file greps for an
immediate (a string's address, a table's) or an instruction shape. It's a
linear sweep: data inside .text reads as junk, so check a hit in Ghidra.
"""
import os
import sys

import capstone
import pefile

from emu import data_path


def main():
    args, exe = sys.argv[1:], None
    if "--exe" in args:
        at = args.index("--exe")
        if at + 1 == len(args):
            sys.exit(__doc__)
        exe = args.pop(at + 1)
        del args[at]
    every = args[:1] == ["--all"]
    if len(args) not in ((2,) if every else (1, 2)) or any(arg.startswith("--") for arg in args[every:]):
        sys.exit(__doc__)
    if not every:
        try:
            va = int(args[0], 16)
            count = int(args[1]) if len(args) > 1 else None
        except ValueError:
            sys.exit(__doc__)
        if count is not None and count < 1:
            sys.exit("disasm: COUNT must be 1 or more")
    try:
        pe = pefile.PE(exe or os.path.join(data_path(), "bin", "game.exe"), fast_load=True)
    except (OSError, pefile.PEFormatError) as error:
        sys.exit(f"disasm: {error}")
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    if every:
        md.skipdata = True
        try:
            with open(args[1], "w") as out:
                for section in pe.sections:
                    if section.Characteristics & 0x20000000:           # IMAGE_SCN_MEM_EXECUTE
                        for address, _, mnemonic, operands in md.disasm_lite(section.get_data(), base + section.VirtualAddress):
                            out.write(f"{address:08x}  {mnemonic} {operands}\n")
        except OSError as error:
            sys.exit(f"disasm: {error}")
        return
    image = pe.get_memory_mapped_image()
    if not 0 <= va - base < len(image):
        sys.exit(f"disasm: {va:08x} is outside the image ({base:08x}-{base + len(image):08x})")
    end = va
    for done, ins in enumerate(md.disasm(image[va - base:], va), 1):   # stops at the image's end or a byte it can't decode
        print(f"{ins.address:08x}  {ins.mnemonic:7} {ins.op_str}")
        end = ins.address + ins.size
        if (count and done >= count) or (not count and ins.mnemonic.startswith("ret")):
            return
    if end - base < len(image):
        sys.exit(f"disasm: stopped at {end:08x}, a byte capstone can't decode")
    sys.exit(f"disasm: reached the image's end at {end:08x}")

if __name__ == "__main__":
    main()
