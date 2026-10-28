# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with: python3 -m unittest tools/test_presubmit.py"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("presubmit", Path(__file__).with_name("presubmit.py"))
presubmit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presubmit)


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class PresubmitTests(unittest.TestCase):
    def setUp(self):
        presubmit.results.clear()

    def levels(self, check):
        return [level for level, name, _ in presubmit.results if name == check]

    def test_short_names_as_clang_tidy(self):
        flagged = {"        const std::uint32_t at = 26 * kTickMs;": "at", "    auto c = foo();": "c",
                   "    const int n{3};": "n", "        std::vector<Channel*> of;": "of",
                   "    std::map<int, std::pair<int, int>> ab = {};": "ab"}
        allowed = ["    for (const auto& x : xs)", "    int row = 0;", "    for (std::size_t i = 0; i < n; ++i)",
                   "    const auto& [a, b] = pair;", "    return a ? b : c;", "    bool ok = true;",
                   "    std::vector<Instance> playing;", "    if (a < b && c > d) e = 1;"]
        for text, name in flagged.items():
            self.assertEqual([hit.group(1) for hit in presubmit.SHORT_NAME.finditer(text)], [name], text)
        for text in allowed:
            names = [presubmit.short_name(text, hit) for hit in presubmit.SHORT_NAME.finditer(text)]
            self.assertTrue(not any(names), (text, names))

    def test_short_names_loop_counters_only_in_a_for_init(self):
        # .clang-tidy: IgnoredLoopCounterNames ^[ijkxy]$ and 2+ letters in a for-init;
        # elsewhere (a plain or range-for variable) the variable rules
        def names(text):
            return [presubmit.short_name(text, hit) for hit in presubmit.SHORT_NAME.finditer(text)]
        self.assertEqual(names("    int i = 0;"), ["i"])
        self.assertEqual(names("    for (int i = 0; i < 3; ++i)"), [None])
        self.assertEqual(names("    for (int ab = 0; ab < 3; ++ab)"), [None])
        self.assertEqual(names("    for (auto& c : list)"), ["c"])

    def test_trap_handler_must_exit_in_its_own_body(self):
        # #101: a greedy match ran to the file's last `}`, so a later `exit` passed a handler that never exits
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.sh").write_text("#!/bin/sh\nstop() {\n    rm -f x\n}\ntrap stop INT\nlater() {\n    exit 1\n}\n")
            (root / "b.sh").write_text("#!/bin/sh\nstop() { rm -f x; exit 130; }\ntrap stop INT\n")
            presubmit.check_traps(root, ["a.sh", "b.sh"])
        self.assertEqual([message.split(":")[0] for level, name, message in presubmit.results if name == "shell-trap"], ["a.sh"])

    def test_short_names_reports_added_cpp_only(self):
        presubmit.check_short_names({"a.cpp": [(3, "    auto c = 1;")], "b.py": [(1, "c = 1")]})
        self.assertEqual(self.levels("short-names"), ["FAIL"])
        presubmit.results.clear()
        presubmit.check_short_names({"a.cpp": [(3, "    auto count = 1;   // auto c = 1;")]})
        self.assertEqual(self.levels("short-names"), ["ok"])

    def test_added_lines_numbers_the_new_side(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "test")
            (root / "a.cpp").write_text("one\ntwo\nthree\n")
            git(root, "add", "a.cpp")
            git(root, "commit", "-q", "-m", "base")
            git(root, "checkout", "-q", "-b", "topic")
            (root / "a.cpp").write_text("one\nnew\ntwo\nthree\nlast\n")
            git(root, "commit", "-q", "-am", "change")
            numbers, texts = presubmit.added_lines(root, "main")
            self.assertEqual(numbers, {"a.cpp": {2, 5}})
            self.assertEqual(texts, {"a.cpp": [(2, "new"), (5, "last")]})

    def test_siblings_warn_on_one_unit_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            presubmit.check_review(Path(directory), "main", ["components/game/fight.cpp"],
                                   {"components/game/fight.cpp": [(10, "    if (player.alive()) hurt(player);"),
                                                                  (11, "    player.mode = kModeGH;")],
                                    "tests/test_game.cpp": [(5, "    assert(merc.alive());")]})
        warnings = [message for level, name, message in presubmit.results if name == "siblings"]
        self.assertTrue(any(message.startswith("unit kinds: the diff touches player,") for message in warnings), warnings)
        self.assertIn("test-gap", [name for _, name, _ in presubmit.results])

    def test_siblings_quiet_outside_the_game_or_on_one_mention(self):
        # #101: it fired on nearly every diff that says `player`
        with tempfile.TemporaryDirectory() as directory:
            presubmit.check_review(Path(directory), "main", ["apps/d2d/town.cpp", "components/game/fight.cpp"],
                                   {"apps/d2d/town.cpp": [(1, "    draw(player);"), (2, "    label(player);")],
                                    "components/game/fight.cpp": [(3, "    hurt(player);")]})
        self.assertFalse([message for level, name, message in presubmit.results
                          if name == "siblings" and message.startswith("unit kinds")])

    def test_ctest_skipped_is_not_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            (build / "CTestTestfile.cmake").write_text("")
            log = ("The following tests did not run:\n\t  7 - test_monsters (Skipped)\n"
                   "The following tests FAILED:\n\t 12 - test_game (Failed)\n")
            orig = presubmit.subprocess.run
            presubmit.subprocess.run = lambda *a, stdout=None, **k: (stdout.write(log), type("R", (), {"returncode": 8})())[1]
            try:
                presubmit.check_ctest(build, quick=False, docker=False, built=True)
            finally:
                presubmit.subprocess.run = orig
        self.assertEqual(self.levels("ctest-skipped"), ["WARN"])
        fails = [text for level, name, text in presubmit.results if name == "ctest" and level == "FAIL"]
        self.assertTrue(fails and "test_game" in fails[0] and "test_monsters" not in fails[0], presubmit.results)

    def test_build_jobs_at_least_one(self):
        self.assertGreaterEqual(presubmit.build_jobs(), 1)
        self.assertGreaterEqual(presubmit.memory_cap_gb(), 4)


if __name__ == "__main__":
    unittest.main()
