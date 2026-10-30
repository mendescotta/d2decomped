# SPDX-License-Identifier: GPL-3.0-or-later
"""game.exe's cast animation rate and cast length as the oracle.

    uv run python cast_rates.py > game.txt
    ../../build/tests/test_combat --cast-rates | diff game.txt -

Both parts run game.exe's own code:

- `rate FCR SPEED RATE`: FUN_00623f50's cast branch (0x623fcb..0x624012).
  FUN_00621740 turns stat 105 (faster cast rate) into the effective FCR
  through the row at 0x6e8e3c; the rate is 100 + that, at most 175; the
  speed is the AnimData speed x rate / 100. The stat getter (FUN_00625500)
  is replaced by the FCR, everything else is game.exe.
- `ticks KIND FRAMES SPEED FCR TICKS`: how many client ticks a cast of that
  length runs. FUN_00463390 steps a player mode of class 1 as FUN_006217c0
  (is it over?), FUN_00623e00 (step) if not, then FUN_006217c0 again; the
  mode ends when that second answer is yes. KIND plain: the unit state
  FUN_00624390 leaves a plain mode in (`+0x48` = frames << 8, no sequence);
  seq: FUN_00621260's (`+0x48` = steps << 8, a sequence in `+0x30`). The
  speed is the one `rate` prints.
"""
import emu

FCRS = list(range(0, 401))
SPEEDS = (208, 256)
PLAIN = ((14, 256), (20, 256), (16, 256), (17, 256), (15, 208))   # SO / BA, AM, NE / PA, AI, DZ: AnimData frames and speed
SEQ = ()                                                  # Lightning's steps; SQ has no AnimData record, so 256


def main():
    e = emu.Emu()
    mu = e.mu
    fcr = [0]
    e.hook(0x625500, lambda emu_: fcr[0], 3)       # the stat getter: stat 105 is the FCR
    e.hook(0x621210, lambda emu_: 0, 1)            # a sequence's event lookup: no event
    unit = e.alloc(0x100)
    anim = e.alloc(0x40)

    def rate(fcr_value, speed):
        fcr[0] = fcr_value
        e.w32(anim + 0xc, speed)
        mu.reg_write(emu.UC_X86_REG_EDI, unit)
        mu.reg_write(emu.UC_X86_REG_ESI, anim)
        mu.reg_write(emu.UC_X86_REG_ESP, emu.STACK + emu.STACK_SIZE - 0x1000)
        mu.emu_start(0x623fcb, 0x624015)
        return e.r16(unit + 0x4c)

    for speed in SPEEDS:
        for value in FCRS:
            print("rate", value, speed, rate(value, speed))

    def ticks(kind, frames, speed, value):
        step = rate(value, speed)
        mu.mem_write(unit, b"\0" * 0x100)
        e.w32(unit + 0x48, frames << 8)
        mu.mem_write(unit + 0x4c, step.to_bytes(2, "little"))
        e.w32(unit + 0x3c, step)
        if kind == "seq":
            e.w32(unit + 0x30, 1)                  # any sequence
            e.w32(unit + 0x34, frames << 8)
        for count in range(1, 200):
            if not e.call(0x6217c0, unit):
                e.call(0x623e00, unit)
            if e.call(0x6217c0, unit):
                return count
        return 0

    for kind, rows in (("plain", PLAIN), ("seq", SEQ)):
        for frames, speed in rows:
            for value in FCRS:
                print("ticks", kind, frames, speed, value, ticks(kind, frames, speed, value))


if __name__ == "__main__":
    main()
