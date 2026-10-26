// SPDX-License-Identifier: GPL-3.0-or-later
// The norespawn mod (docs/mods/norespawn.md, off unless --toggle
// norespawn=on or d2d.cfg's norespawn = 1): offline, a room's own
// population (FUN_0054ec90's groups, its random bosses and their packs,
// the nests) stays as the player left it, as Diablo's levels did. A save
// keeps each room's living count by kind in <name>.norespawn beside the
// .d2s; the next game makes the room as ever (every seed steps the same),
// then lays those past the count down unseen. Presets (superuniques, act
// bosses, quest monsters) and what's made later (summons, raises, a
// nest's young) aren't population: they come back as ever.
// This part has no game types: the store, the rule, a game's session.
// norespawn_game.hpp hooks it to the Fight.
#pragma once

#include <array>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace d2d::mods::norespawn {

// A population monster's kind: a group's (champion packs' parties too), a
// random champion or unique, a unique's minion.
enum class Kind : std::uint8_t { regular, leader, minion };

struct Counts {
    std::array<std::uint16_t, 3> by_kind{};
    [[nodiscard]] std::uint16_t& operator[](Kind kind) { return by_kind[std::size_t(kind)]; }
    [[nodiscard]] std::uint16_t operator[](Kind kind) const { return by_kind[std::size_t(kind)]; }
    [[nodiscard]] int total() const { return by_kind[0] + by_kind[1] + by_kind[2]; }
    bool operator==(const Counts&) const = default;
};

// A room: the difficulty, its Levels.txt id, its Level::rooms index.
struct RoomKey {
    std::uint8_t difficulty = 0;
    std::uint16_t level = 0, room = 0;
    auto operator<=>(const RoomKey&) const = default;
};

// A character's rooms, each its count still to come, for one map seed.
struct Store {
    std::uint32_t map_seed = 0;
    std::map<RoomKey, Counts> rooms;
    bool operator==(const Store&) const = default;
};

// The file, little-endian: "D2NR", version, map seed, the row count, the
// rows (difficulty u8, level u16, room u16, three u16 counts), then an
// FNV-1a of every byte before it. decode: none when it isn't one, or it's
// damaged or of another version.
inline constexpr std::uint32_t kVersion = 1;
[[nodiscard]] std::vector<std::byte> encode(const Store& store);
[[nodiscard]] std::optional<Store> decode(std::span<const std::byte> bytes);

enum class Read : std::uint8_t { none, ok, damaged };
struct Loaded {
    Read read = Read::none;
    Store store;
};
[[nodiscard]] Loaded load(const std::filesystem::path& file);
// "" when written: a temp file beside it, renamed over it.
[[nodiscard]] std::string save(const std::filesystem::path& file, const Store& store);

// One population monster as a room's batch made it: its room, kind, its
// leader's place in the batch (-1 none) and whether a quest keeps it
// (`exempt`: up, its room's budget not spent).
struct Made {
    int room = -1;
    Kind kind = Kind::regular;
    int leader = -1;
    bool exempt = false;
};

// Which of `made` stay up: in a room with a budget the first of each kind
// up to its count, a minion going down with its leader; a room without
// one keeps all. Each budgeted room's unspent count goes in `owed`.
[[nodiscard]] std::vector<bool> thin(std::span<const Made> made, const std::map<int, Counts>& budgets, std::map<int, Counts>& owed);

// A game's: the store as it loaded and what its rooms didn't spend.
struct Session {
    bool on = false;                                  // the toggle
    std::filesystem::path file;                       // empty: nothing this game (no saves, a damaged store)
    int difficulty = 0;
    Store store;
    std::map<std::pair<int, int>, Counts> owed;       // (level id, room)

    // A game starts on `map_seed`; `file` empty: none kept (--no-save, a
    // joined game). A store of another map starts over; a damaged one
    // turns the mod off for the game and is left as it is.
    void begin(const std::filesystem::path& file, std::uint32_t map_seed, int difficulty);
    [[nodiscard]] bool active() const { return on && !file.empty(); }
    // A batch of level `level`'s population: which stay up.
    [[nodiscard]] std::vector<bool> thin(int level, std::span<const Made> made);
    // A save: the rooms this game brought up with their living counts,
    // each kept as that plus what it owes; "" when written.
    [[nodiscard]] std::string record(const std::map<std::pair<int, int>, Counts>& alive);
};

}  // namespace d2d::mods::norespawn
