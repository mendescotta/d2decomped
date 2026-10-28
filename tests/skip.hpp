// SPDX-License-Identifier: GPL-3.0-or-later
// A test that can't run here (no MPQs, ISO or game.exe found) prints why and
// returns kSkipped. tests/CMakeLists.txt makes it ctest's SKIP_RETURN_CODE,
// so the run lists the test as skipped, not passed.
#pragma once

namespace d2d::test {
inline constexpr int kSkipped = 77;
}
