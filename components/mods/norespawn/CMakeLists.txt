# SPDX-License-Identifier: GPL-3.0-or-later
# norespawn (docs/mods/norespawn.md): the store and the rule, no game
# types; norespawn_game.hpp, the hooks on them, is the game's to include.
add_library(mods_norespawn STATIC norespawn.cpp)
target_include_directories(mods_norespawn PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(mods_norespawn PUBLIC log)
target_compile_features(mods_norespawn PUBLIC cxx_std_${CMAKE_CXX_STANDARD})
