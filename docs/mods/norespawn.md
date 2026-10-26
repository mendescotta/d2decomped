# Mod: norespawn — killed monsters stay dead offline

Status: done (the `mods` branch). Off unless turned on:
`--toggle norespawn=on`, or `norespawn = 1` in `d2d.cfg`.

game.exe fills every area again each time a game starts. Diablo kept its
levels as the player left them. With this mod, each room's own
population stays as it was when you saved: what you killed stays dead,
what you left alive is still there.

## What stays, what comes back

**Kept (the room's population).** What `ObjectRooms::populate()`
(FUN_0054ec90) makes for a room: its monster groups, its random champion
and unique packs (minions too), its nests.

**Back every game, as ever.**
- A room's presets: superuniques (Bishibosh, Pindleskin...), act bosses,
  quest monsters, the map's own placed monsters (Corpsefire, a fetish
  camp).
- Whatever the game makes later: summons, raises, shamans' revives, a
  nest's young, traps, Baal's waves, the quests' scripted monsters.

**Quests.** Only two count ordinary population; while they're open their
monsters come back as ever:
- The Den of Evil (quest 1) is done when the Den's monsters are all dead
  (`World::den_count`). While it's open (bits 0 and 15 clear), the Den
  fills as ever. Once done it's kept like anywhere else.
- The Golden Bird (quest 0x14): the first unique act 3 makes carries the
  jade figurine (`World::act3_update`). While it's open (bits 0 and 1
  clear), act 3's uniques and their minions come back.

Every other quest's monsters are presets or scripted.

**Off** for a joined game, local co-op with more than one player,
`--no-save`, and a store it can't read (warned, left as it is).

## How

1. `room_objects` tags each spawn `populate()` makes with its room
   (`Spawn::pop_room`, copied to `Monster::pop_room`).
2. A save (`World::save`, the .d2s written): for every room this game
   brought up, its population still alive by kind (regular / leader /
   minion) is kept in `<name>.norespawn` beside the .d2s: per difficulty,
   level and room, for the map seed. A temp file, then a rename.
3. The next game makes each room as ever (every seed steps the same).
   `Fight::rooms_up` then keeps the first of each kind up to the room's
   count; a minion goes with its leader. The rest are laid down unseen:
   `gone`, no life, the corpse used. That's no drop, experience, corpse
   or kill. Their place in the pack is kept, since `Monster::leader`
   indexes it.
4. A room's population is rolled again every game (on the game seed,
   in the order rooms come up), so a roll can come up short of its
   count. What it couldn't make stays owed: the next save keeps it on top
   of the living count.

A store of another map seed starts over.

## Files

- `components/mods/norespawn/norespawn.{hpp,cpp}`: the store and the
  rule; no game types.
- `components/mods/norespawn/norespawn_game.hpp`: the hooks on the
  game's types.
- Hook points: `rules::Spawn` / `Monster` (`pop_room`), `room_objects`,
  `spawn_monsters`, `Fight::rooms_up`, `World::new_game`, `World::save`,
  `main.cpp`'s toggle.
- Tests: `tests/test_norespawn.cpp` (the store, the rule, a session) and
  `tests/norespawn_d2d.py` (games of one character over devctl: kills
  kept, a level emptied, the Den, the Golden Bird, the mod off).
  Configure with `D2_MPQ_DIR` and `D2_PATCH_INSTALLER` to make missing
  data fail this integration test; without them it skips.
  `D2D_TEST_FAIL_AFTER_START=1` checks its cleanup path by injecting an
  error after game startup; `tests/headless_cleanup.py` runs that check
  automatically with a fake devctl server.
