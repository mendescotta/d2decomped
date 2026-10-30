# SPDX-License-Identifier: GPL-3.0-or-later
"""game.exe's UTF-8 string decoder as the oracle for d2d's TBL reader.

    uv run python tbl.py [language]   # prints tools/tbl-dump's text
"""
import struct
import sys

import emu


def decode(e, source):
    capacity = len(source) + 1
    destination = e.alloc(capacity * 2)
    address = e.put(source)
    e.call(0x526320, capacity, ecx=destination, edx=address)
    units = []
    while (unit := e.r16(destination + len(units) * 2)) != 0:
        units.append(unit)
    return units


def entries(e, raw):
    if len(raw) < 21:
        raise ValueError("TBL: truncated header")
    nodes_number = struct.unpack_from("<H", raw, 2)[0]
    hash_size = struct.unpack_from("<I", raw, 4)[0]
    nodes_offset = 21 + nodes_number * 2
    if nodes_offset + hash_size * 17 > len(raw):
        raise ValueError("TBL: truncated nodes")
    result = {}
    for index in range(hash_size):
        node = nodes_offset + index * 17
        if raw[node] == 0:
            continue
        key_offset, value_offset = struct.unpack_from("<II", raw, node + 7)
        value_length = struct.unpack_from("<H", raw, node + 15)[0]
        if key_offset >= len(raw) or value_length == 0 or value_offset + value_length > len(raw):
            raise ValueError("TBL: invalid string range")
        key_end = raw.index(0, key_offset)
        value_end = raw.index(0, value_offset, value_offset + value_length)
        key = raw[key_offset:key_end]
        if key not in result:
            result[key] = decode(e, raw[value_offset:value_end + 1])
    return result


def dump(language):
    e = emu.Emu()
    output = []
    for name in ("string", "patchstring", "expansionstring"):
        raw = e.mpq_file(f"data\\local\\lng\\{language}\\{name}.tbl")
        output.append(f"[{name}]")
        for key, units in sorted(entries(e, raw).items()):
            output.append(f"{key.hex()}=" + "".join(f"{unit:04x}" for unit in units))
    return "\n".join(output)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: uv run python tbl.py [language]")
    print(dump(sys.argv[1] if len(sys.argv) == 2 else "ENG"))
