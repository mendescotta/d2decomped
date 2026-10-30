# DT1 block coordinates

`game.exe` 1.14d preserves signed DT1 block coordinates and adds them directly
to screen coordinates when drawing. d2d's `y_shift = max(0, -min(block.y))`
is therefore an **internal pixel-buffer packing rule**, not an offset computed
by game.exe.

## Loading and block fixup

- `FUN_00600790` caches a DT1 and calls `FUN_0060a390` to validate its header.
- `FUN_005fdea0` reads the tile's 20-byte block records on demand.
- `FUN_0060a4c0` rebases each block's encoded-data pointer at record `+0x10`;
  it does not alter the signed X or Y at `+0x00` and `+0x02`.

The wall draw routines then use those signed values directly:

- `FUN_005130a0`, at `0x00513114–0x00513122`, sign-extends `block.y` and adds
  the screen-Y argument, and sign-extends `block.x` and adds screen X.
- `FUN_005131b0` repeats the same operations at `0x00513228–0x00513236`.
- `FUN_00512f90` does the same for tile shadows.
- Wrappers `FUN_004f6920`, `FUN_004f6950`, and `FUN_004f6980` forward the
  cell's screen coordinates without a tile-block minimum or Y adjustment.

No minimum-Y pass occurs in the loader, block fixup, wrappers, or draw loops.

## d2d representation

`components/dt1/dt1.hpp` decodes all blocks into one nonnegative,
`width × abs(height)` pixel array per tile. It first computes

```text
min_y = min(0, every signed block.y)
y_shift = -min_y = max(0, -min(block.y))
```

It stores each block position as `(block.x, block.y + y_shift)` and uses the
same shift in `put_pixel`. This is a suitable representation for d2d's packed
buffer, provided the renderer accounts for the shift when choosing the
buffer's screen position. It should not be cited as a game.exe formula.

Traced 2026-10-30 through `FUN_005fdea0`, `FUN_0060a4c0`, `FUN_005130a0`,
`FUN_005131b0`, and `FUN_00512f90`.
