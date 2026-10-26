// SPDX-License-Identifier: GPL-3.0-or-later
// The norespawn mod's hooks (norespawn.hpp) on the game's types: the
// Fight's batch of a room's monsters thinned as it's made, the living
// counted as the World saves. For the game's sources only.
#pragma once

#include "norespawn.hpp"

#include <fight.hpp>
#include <gamedata.hpp>

#include <monsters.hpp>
#include <quests.hpp>
#include <quests_act3.hpp>
#include <shrines.hpp>

#include <cstddef>
#include <map>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace d2d::mods::norespawn {

[[nodiscard]] inline Kind kind_of(const d2d::game::Monster& monster) {
    using d2d::rules::Boss;
    return monster.boss == Boss::champion || monster.boss == Boss::unique ? Kind::leader : monster.boss == Boss::minion ? Kind::minion : Kind::regular;
}

// Down unseen, as gone as the Dark Wanderer (no corpse, no kill, not
// drawn); its place in the pack kept, Monster::leader indexing it.
inline void lay_down(d2d::game::Monster& monster) {
    monster.hit_points = 0;
    monster.gone = true;
    monster.corpse_used = true;
}

// Fight::rooms_up's batch: `made` from the level's spawns `from` on.
// Off in local co-op (who the rooms are kept for isn't one player).
// Two quests count the population; while they're open it stays as ever:
// the Den of Evil's monsters left (World::den_count) and the Golden
// Bird's carrier, the first unique act 3 makes (World::act3_update).
inline void thin(Session& session, const d2d::game::Level& level, std::span<d2d::game::Monster> made, std::size_t from,
                 const d2d::rules::QuestBits& quests, std::size_t heroes) {
    using d2d::rules::quest::bit;
    using Den = d2d::rules::DenQuest;
    using Bird = d2d::rules::GoldenBirdQuest;
    if (!session.active() || heroes > 1) return;
    const bool den_open = level.id == Den::kDen && !bit(quests, Den::kQuest, 0) && !bit(quests, Den::kQuest, 15);
    const bool bird_open = d2d::rules::level_act(level.id) == 2 && !bit(quests, Bird::kQuest, 0) && !bit(quests, Bird::kQuest, 1);
    std::vector<Made> units;
    std::vector<std::size_t> made_at;
    std::vector<int> unit_of(made.size(), -1);
    for (std::size_t i = 0; i < made.size(); ++i) {
        const auto& monster = made[i];
        if (monster.pop_room < 0) continue;
        const int lead = monster.leader - int(from);
        const bool bird_boss = monster.boss == d2d::rules::Boss::unique || monster.boss == d2d::rules::Boss::minion;
        unit_of[i] = int(units.size());
        units.push_back({ monster.pop_room, kind_of(monster), lead >= 0 && std::size_t(lead) < made.size() ? unit_of[std::size_t(lead)] : -1,
                          den_open || (bird_open && bird_boss) });
        made_at.push_back(i);
    }
    if (units.empty()) return;
    const auto up = session.thin(level.id, units);
    for (std::size_t unit = 0; unit < up.size(); ++unit)
        if (!up[unit]) lay_down(made[made_at[unit]]);
}

// Every room this game brought up (towns aside), each its population
// still alive: the level the player's on and those kept.
[[nodiscard]] inline std::map<std::pair<int, int>, Counts> alive(const d2d::game::Fight& fight) {
    std::map<std::pair<int, int>, Counts> out;
    for (const auto& [level, state] : fight.spawning.levels) {
        if (!level || d2d::game::in_town(level)) continue;
        for (const auto room : state.order) out.try_emplace({ level->id, int(room) });
    }
    const auto count = [&](const d2d::game::Level* level, const std::vector<d2d::game::Monster>& monsters) {
        if (!level) return;
        for (const auto& monster : monsters)
            if (monster.pop_room >= 0 && monster.alive())
                if (const auto found = out.find({ level->id, monster.pop_room }); found != out.end()) ++found->second[kind_of(monster)];
    };
    count(fight.mon_level, fight.monsters);
    for (const auto& [level, monsters] : fight.kept) count(level, monsters);
    return out;
}

// World::save's, the .d2s written: "" when kept (or nothing to keep).
[[nodiscard]] inline std::string saved(Session& session, const d2d::game::Fight& fight) {
    if (!session.active() || fight.heroes.size() > 1 || fight.remote_monsters) return {};
    return session.record(alive(fight));
}

}  // namespace d2d::mods::norespawn
