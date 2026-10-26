// SPDX-License-Identifier: GPL-3.0-or-later
// The norespawn mod's store and rule (components/mods/norespawn): the
// file round trip and what it refuses, a room's batch thinned to its
// budget (minions with their leader, quests' monsters kept), what a
// budget leaves owed, and a save over a game's session.
#include <norespawn.hpp>

#include <cassert>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <system_error>
#include <vector>

using namespace d2d::mods::norespawn;

namespace {

Counts counts(int regular, int leader, int minion) {
    Counts out;
    out[Kind::regular] = std::uint16_t(regular);
    out[Kind::leader] = std::uint16_t(leader);
    out[Kind::minion] = std::uint16_t(minion);
    return out;
}

Store sample_store() {
    Store store{ .map_seed = 0x12345678 };
    store.rooms[{ 0, 2, 7 }] = counts(3, 1, 4);
    store.rooms[{ 2, 8, 0 }] = counts(0, 0, 0);
    return store;
}

void test_store_round_trip_reads_back_equal() {
    const auto store = sample_store();
    const auto bytes = encode(store);
    const auto back = decode(bytes);
    assert(back && *back == store);
}

void test_store_damaged_bytes_refused() {
    const auto bytes = encode(sample_store());
    auto flipped = bytes;
    flipped[20] ^= std::byte{ 1 };                                      // a count's bit: the checksum no longer holds
    assert(!decode(flipped));
    assert(!decode(std::span(bytes).first(bytes.size() - 1)));        // cut short
    auto other_version = bytes;
    other_version[4] = std::byte{ 2 };
    assert(!decode(other_version));
    assert(!decode({}));
}

void test_thin_budget_keeps_first_of_each_kind() {
    // A room's batch: 4 regulars, a unique (unit 4) with 3 minions; its budget 2 regulars, the unique, 1 minion.
    const std::vector<Made> made = { { 5, Kind::regular }, { 5, Kind::regular }, { 5, Kind::regular }, { 5, Kind::regular },
                                     { 5, Kind::leader, 4 }, { 5, Kind::minion, 4 }, { 5, Kind::minion, 4 }, { 5, Kind::minion, 4 } };
    std::map<int, Counts> owed;
    const auto up = thin(made, { { 5, counts(2, 1, 1) } }, owed);
    assert((up == std::vector<bool>{ true, true, false, false, true, true, false, false }));
    assert(owed.at(5) == counts(0, 0, 0));
}

void test_thin_dead_leader_takes_its_minions() {
    const std::vector<Made> made = { { 1, Kind::leader, 0 }, { 1, Kind::minion, 0 }, { 1, Kind::minion, 0 } };
    std::map<int, Counts> owed;
    const auto up = thin(made, { { 1, counts(0, 0, 5) } }, owed);
    assert((up == std::vector<bool>{ false, false, false }));
    assert(owed.at(1) == counts(0, 0, 5));                              // the minions it didn't spend stay owed
}

void test_thin_room_without_budget_keeps_all() {
    const std::vector<Made> made = { { 3, Kind::regular }, { 4, Kind::regular } };
    std::map<int, Counts> owed;
    const auto up = thin(made, { { 4, counts(0, 0, 0) } }, owed);
    assert((up == std::vector<bool>{ true, false }));
    assert(!owed.contains(3));
}

void test_thin_exempt_kept_and_spends_nothing() {
    const std::vector<Made> made = { { 2, Kind::leader, 0, true }, { 2, Kind::minion, 0, true }, { 2, Kind::regular } };
    std::map<int, Counts> owed;
    const auto up = thin(made, { { 2, counts(1, 0, 0) } }, owed);
    assert((up == std::vector<bool>{ true, true, true }));
    assert(owed.at(2) == counts(0, 0, 0));
}

void test_thin_short_roll_leaves_budget_owed() {
    const std::vector<Made> made = { { 6, Kind::regular } };
    std::map<int, Counts> owed;
    const auto up = thin(made, { { 6, counts(4, 0, 0) } }, owed);
    assert((up == std::vector<bool>{ true }));
    assert(owed.at(6) == counts(3, 0, 0));
}

void test_session_save_then_next_game_thins() {
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path() / "d2d_test_norespawn";
    fs::remove_all(dir);
    const auto file = dir / "Hero.norespawn";
    // A first game: nothing kept, every room up; one room left with 2 regulars, another emptied.
    Session first{ .on = true };
    first.begin(file, 99, 1);
    assert(first.active());
    const std::vector<Made> batch = { { 0, Kind::regular }, { 0, Kind::regular }, { 0, Kind::regular } };
    assert((first.thin(2, batch) == std::vector<bool>{ true, true, true }));
    assert(first.record({ { { 2, 0 }, counts(2, 0, 0) }, { { 2, 1 }, counts(0, 0, 0) } }).empty());
    // The next game on the same map: room 0 makes 2 of its 3, room 1 none; a short roll leaves room 0 owing.
    Session next{ .on = true };
    next.begin(file, 99, 1);
    assert((next.thin(2, batch) == std::vector<bool>{ true, true, false }));
    assert((next.thin(2, std::vector<Made>{ { 1, Kind::regular } }) == std::vector<bool>{ false }));
    // Another difficulty's rooms aren't these.
    Session hell{ .on = true };
    hell.begin(file, 99, 2);
    assert((hell.thin(2, batch) == std::vector<bool>{ true, true, true }));
    // Another map: nothing kept.
    Session other_map{ .on = true };
    other_map.begin(file, 100, 1);
    assert(other_map.active() && other_map.store.rooms.empty());
    // Off, or no file: nothing thinned, nothing written.
    Session off;
    off.begin(file, 99, 1);
    assert(!off.active() && (off.thin(2, batch) == std::vector<bool>{ true, true, true }) && off.record({}).empty());
    // A damaged store: off for the game, the file left as it was.
    { std::ofstream bad(file, std::ios::binary | std::ios::trunc); bad << "not a store"; }
    Session damaged{ .on = true };
    damaged.begin(file, 99, 1);
    assert(!damaged.active());
    assert(damaged.record({ { { 2, 0 }, counts(9, 0, 0) } }).empty() && fs::file_size(file) == 11);
    std::error_code error;
    fs::remove_all(dir, error);
}

}  // namespace

int main() {
    test_store_round_trip_reads_back_equal();
    test_store_damaged_bytes_refused();
    test_thin_budget_keeps_first_of_each_kind();
    test_thin_dead_leader_takes_its_minions();
    test_thin_room_without_budget_keeps_all();
    test_thin_exempt_kept_and_spends_nothing();
    test_thin_short_roll_leaves_budget_owed();
    test_session_save_then_next_game_thins();
}
