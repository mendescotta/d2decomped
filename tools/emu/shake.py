# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture stock 1.14d shake envelopes and mixer volume as C++ test cases.

Usage: D2_MPQ_DIR=/path/to/data uv run python shake.py > ../../tests/shake_cases.inc
Only the clock, player lookup, random offsets and sound backend are stubbed.
The envelope and six-unit volume smoothing execute in game.exe. Reject other
executables and incomplete calls before emitting output. No game process runs.
"""
import argparse
import hashlib
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EIP

import emu


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true', help='capture quest control missile frame gates')
    args = parser.parse_args()
    path = Path(emu.data_path()) / 'bin/game.exe'
    if hashlib.sha256(path.read_bytes()).hexdigest() != '631066c1649c4ea9ffe48bf97e24c00bca1f7a6759c21150f1a79982589adaaf':
        raise SystemExit('shake: requires stock game.exe 1.14d (1.14.3.71)')
    machine = emu.Emu(str(path))
    state = {'now': 0, 'volume': 0, 'strength': 0}
    player = machine.alloc(0x100)
    coords = machine.alloc(8)
    machine.hook(0x463dd0, lambda current: player, 0)

    def random_offset(current):
        low = current.mu.reg_read(UC_X86_REG_EDX)
        state['strength'] = -((low ^ 0x80000000) - 0x80000000)
        if current.arg(0) != state['strength'] * 2:
            raise RuntimeError('unexpected random offset range')
        return low

    def set_volume(current):
        state['volume'] = current.mu.reg_read(UC_X86_REG_EDX)
        return 0

    machine.hook(0x472280, random_offset, 1)
    machine.hook(0x4b9a00, lambda current: 1, 3)
    machine.hook(0x4b9b50, set_volume, 0)
    machine.hook(0x4b9b20, lambda current: state['volume'], 0)
    def stop_sound(current):
        state['volume'] = 0
        return 0

    machine.hook(0x4ba840, stop_sound, 0)
    clock = [slot for slot, (name, _) in machine.slots.items() if name == 'GetTickCount']
    if len(clock) != 1:
        raise RuntimeError('GetTickCount import missing or ambiguous')
    machine.slots[clock[0]] = ('GetTickCount', lambda current: (state['now'], 0))
    slots = len(machine.slots)
    rows = []
    for strength, ramp, hold, fade in ((8, 2000, 3000, 2000), (25, 0, 4000, 0), (3, 600, 4000, 3000), (4, 80, 80, 400), (20, 0, 6000, 0)):
        state.update(now=0xfffffff0, volume=0)
        machine.w32(0x7b8d2c, 0)
        machine.call(0x476a80, hold, fade, ecx=strength, edx=ramp, limit=1000)
        if machine.mu.reg_read(UC_X86_REG_EIP) != emu.RET_MAGIC:
            raise RuntimeError('shake start exceeded budget')
        samples = sorted({0, 1, ramp // 2, ramp, ramp + hold - 1, ramp + hold, ramp + hold + fade // 2, ramp + hold + fade, ramp + hold + fade + 1, *range(40, 1200, 40)})
        for elapsed in samples:
            state.update(now=(0xfffffff0 + elapsed) & 0xffffffff, strength=0)
            machine.w32(coords, 0)
            machine.w32(coords + 4, 0)
            machine.call(0x476d40, ecx=coords, edx=coords + 4, limit=10000)
            if machine.mu.reg_read(UC_X86_REG_EIP) != emu.RET_MAGIC:
                raise RuntimeError('shake update exceeded budget')
            rows.append(f'    {{ {strength}, {ramp}, {hold}, {fade}, {elapsed}, {state["strength"]}, {state["volume"]} }},')
    if len(machine.slots) != slots:
        raise RuntimeError('unexpected hook allocation')
    if args.controls:
        record = machine.alloc(0x1a4)
        tables = machine.alloc(0xc00)
        missile = machine.alloc(0x100)
        missile_data = machine.alloc(0x40)
        machine.w32(missile, 3)
        machine.w32(missile + 0x14, missile_data)
        machine.w32(0x744304, tables)
        machine.w32(tables + 0xb64, record)
        machine.w32(tables + 0xb6c, 1)
        machine.w32(record + 0x58, 25)  # stock andycontrol0 CltParam1/2
        machine.w32(record + 0x5c, 7)
        machine.hook(0x4639d0, lambda current: player, 0)
        machine.hook(0x4d30c0, lambda current: 0, 0)

        def start_shake(current):
            state['shake'] = (current.mu.reg_read(UC_X86_REG_ECX), current.mu.reg_read(UC_X86_REG_EDX), current.arg(0), current.arg(1))
            return 0

        def taunt(current):
            state['taunt'] = int(current.mu.reg_read(UC_X86_REG_ECX) == 0x121e)
            return 1

        machine.hook(0x476a80, start_shake, 2)
        machine.hook(0x4b9a00, taunt, 3)
        rows = []
        for kind, address in ((0, 0x4d5310), (1, 0x4d6540)):
            for frame in (0, 49, 50, 51, 89, 90, 91, 149, 150, 151, 249, 250, 251):
                state.update(shake=(0, 0, 0, 0), taunt=0)
                total = 350 if kind == 0 else 300
                # Real getters: +0xe total, +0x10 remaining; 0x64a3b0
                # subtracts them, while 0x64a380 reads remaining alone.
                machine.w32(missile_data + 0xe, total | ((total - frame) << 16))
                machine.call(address, ecx=missile, limit=10000)
                if machine.mu.reg_read(UC_X86_REG_EIP) != emu.RET_MAGIC:
                    raise RuntimeError('control missile exceeded budget')
                values = (kind, frame, *state['shake'], state['taunt'])
                rows.append('    { ' + ', '.join(map(str, values)) + ' },')
        print('// Stock game.exe 1.14d, FUN_004d5310/004d6540; tools/emu/shake.py --controls.')
        print('// kind, elapsed frame, strength, ramp, hold, fade, taunt')
        print('\n'.join(rows))
        return
    print('// Stock game.exe 1.14d, FUN_00476a80/00476d40/004769d0; tools/emu/shake.py.')
    print('// strength, ramp, hold, fade, elapsed, envelope, mixer volume (sequential samples)')
    print('\n'.join(rows))


if __name__ == '__main__':
    main()
