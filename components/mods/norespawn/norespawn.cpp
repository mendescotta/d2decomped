// SPDX-License-Identifier: GPL-3.0-or-later
#include "norespawn.hpp"

#include <log.hpp>

#include <algorithm>
#include <fstream>
#include <ios>
#include <iterator>
#include <system_error>

namespace d2d::mods::norespawn {

namespace {

constexpr std::array<std::byte, 4> kMagic{ std::byte{ 'D' }, std::byte{ '2' }, std::byte{ 'N' }, std::byte{ 'R' } };
constexpr std::size_t kHeader = 16, kRow = 11, kChecksum = 4;

std::uint32_t fnv1a(std::span<const std::byte> bytes) {
    std::uint32_t hash = 2166136261u;
    for (const auto byte : bytes) hash = (hash ^ std::uint32_t(byte)) * 16777619u;
    return hash;
}

void put(std::vector<std::byte>& out, std::uint32_t value, int size) {
    for (int i = 0; i < size; ++i) out.push_back(std::byte(value >> (8 * i) & 0xff));
}

std::uint32_t get(std::span<const std::byte> bytes, std::size_t at, int size) {
    std::uint32_t value = 0;
    for (int i = 0; i < size; ++i) value |= std::uint32_t(bytes[at + std::size_t(i)]) << (8 * i);
    return value;
}

}  // namespace

std::vector<std::byte> encode(const Store& store) {
    std::vector<std::byte> out(kMagic.begin(), kMagic.end());
    put(out, kVersion, 4);
    put(out, store.map_seed, 4);
    put(out, std::uint32_t(store.rooms.size()), 4);
    for (const auto& [key, counts] : store.rooms) {
        put(out, key.difficulty, 1);
        put(out, key.level, 2);
        put(out, key.room, 2);
        for (const auto count : counts.by_kind) put(out, count, 2);
    }
    put(out, fnv1a(out), 4);
    return out;
}

std::optional<Store> decode(std::span<const std::byte> bytes) {
    if (bytes.size() < kHeader + kChecksum || !std::equal(kMagic.begin(), kMagic.end(), bytes.begin())) return std::nullopt;
    if (get(bytes, 4, 4) != kVersion) return std::nullopt;
    const std::size_t rows = get(bytes, 12, 4);
    if (rows > (bytes.size() - kHeader - kChecksum) / kRow || bytes.size() != kHeader + rows * kRow + kChecksum) return std::nullopt;
    if (get(bytes, bytes.size() - kChecksum, 4) != fnv1a(bytes.first(bytes.size() - kChecksum))) return std::nullopt;
    Store store{ .map_seed = get(bytes, 8, 4) };
    for (std::size_t row = 0, at = kHeader; row < rows; ++row, at += kRow) {
        const RoomKey key{ std::uint8_t(get(bytes, at, 1)), std::uint16_t(get(bytes, at + 1, 2)), std::uint16_t(get(bytes, at + 3, 2)) };
        Counts counts;
        for (std::size_t kind = 0; kind < counts.by_kind.size(); ++kind) counts.by_kind[kind] = std::uint16_t(get(bytes, at + 5 + 2 * kind, 2));
        if (!store.rooms.emplace(key, counts).second) return std::nullopt;   // a room twice: not one encode() wrote
    }
    return store;
}

Loaded load(const std::filesystem::path& file) {
    std::error_code error;
    if (!std::filesystem::exists(file, error)) return { Read::none, {} };
    std::ifstream in(file, std::ios::binary);
    if (!in) return { Read::damaged, {} };
    std::vector<char> raw{ std::istreambuf_iterator<char>(in), {} };
    auto store = decode(std::as_bytes(std::span(raw)));
    if (!store) return { Read::damaged, {} };
    return { Read::ok, std::move(*store) };
}

std::string save(const std::filesystem::path& file, const Store& store) {
    namespace fs = std::filesystem;
    std::error_code error;
    fs::create_directories(file.parent_path(), error);
    auto tmp = file;
    tmp += ".tmp";
    const auto bytes = encode(store);
    {
        std::ofstream out(tmp, std::ios::binary | std::ios::trunc);
        out.write(reinterpret_cast<const char*>(bytes.data()), std::streamsize(bytes.size()));
        if (!out.flush()) return "couldn't write " + tmp.string();
    }
    fs::rename(tmp, file, error);
    return error ? "couldn't replace " + file.string() + ": " + error.message() : std::string{};
}

std::vector<bool> thin(std::span<const Made> made, const std::map<int, Counts>& budgets, std::map<int, Counts>& owed) {
    std::vector<bool> up(made.size(), true);
    std::map<int, Counts> left;
    for (std::size_t i = 0; i < made.size(); ++i) {
        const auto& unit = made[i];
        const auto budget = budgets.find(unit.room);
        if (unit.exempt || budget == budgets.end()) continue;
        auto& room_left = left.try_emplace(unit.room, budget->second).first->second;
        const bool leader_down = unit.kind == Kind::minion && unit.leader >= 0 && std::size_t(unit.leader) < i && !up[std::size_t(unit.leader)];
        if (leader_down || room_left[unit.kind] == 0) up[i] = false;
        else --room_left[unit.kind];
    }
    for (const auto& [room, room_left] : left) owed[room] = room_left;
    return up;
}

void Session::begin(const std::filesystem::path& to, std::uint32_t map_seed, int game_difficulty) {
    file.clear();
    owed.clear();
    store = { .map_seed = map_seed };
    difficulty = game_difficulty;
    if (!on || to.empty()) return;
    auto loaded = load(to);
    if (loaded.read == Read::damaged) {
        d2d::log::warn("norespawn: {} isn't a store this d2d reads; monsters respawn this game and it's left as it is", to.string());
        return;
    }
    file = to;
    if (loaded.read == Read::ok && loaded.store.map_seed == map_seed) store = std::move(loaded.store);
    else if (loaded.read == Read::ok) d2d::log::info("norespawn: {} is of another map, starting over", to.string());
    d2d::log::info("norespawn: on, {} rooms kept", store.rooms.size());
}

std::vector<bool> Session::thin(int level, std::span<const Made> made) {
    std::map<int, Counts> budgets, room_owed;
    for (const auto& unit : made)
        if (const auto found = store.rooms.find({ std::uint8_t(difficulty), std::uint16_t(level), std::uint16_t(unit.room) }); found != store.rooms.end())
            budgets.emplace(unit.room, found->second);
    auto up = norespawn::thin(made, budgets, room_owed);
    for (const auto& [room, counts] : room_owed) owed[{ level, room }] = counts;
    if (!budgets.empty()) {
        const auto kept = std::ranges::count(up, true);
        d2d::log::info("norespawn: level {}: {} of {} up, {} room(s) counted", level, kept, made.size(), budgets.size());
    }
    return up;
}

std::string Session::record(const std::map<std::pair<int, int>, Counts>& alive) {
    if (!active()) return {};
    for (const auto& [where, counts] : alive) {
        Counts kept = counts;
        if (const auto found = owed.find(where); found != owed.end())
            for (std::size_t kind = 0; kind < kept.by_kind.size(); ++kind)
                kept.by_kind[kind] = std::uint16_t(std::min(int(kept.by_kind[kind]) + found->second.by_kind[kind], 0xffff));
        store.rooms[{ std::uint8_t(difficulty), std::uint16_t(where.first), std::uint16_t(where.second) }] = kept;
    }
    auto why = save(file, store);
    if (why.empty()) d2d::log::info("norespawn: {} rooms kept", store.rooms.size());
    return why;
}

}  // namespace d2d::mods::norespawn
